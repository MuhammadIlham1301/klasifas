#!/usr/bin/env bash
#
# Backup PostgreSQL dan uploads KlasiFas.
# Jalankan sebagai root (cron/systemd timer) pada server Linux.
set -euo pipefail
umask 077

usage() {
    cat <<'EOF'
Usage: backup.sh

Membaca konfigurasi dari /etc/klasifas/backup.env (atau BACKUP_ENV_FILE).
Menghasilkan daily/YYYY-MM-DDTHHMMSSZ berisi db.dump, uploads.tar.gz,
dan SHA256SUMS. Retensi: 7 harian + 4 mingguan. BACKUP_REMOTE opsional
untuk salinan offsite melalui rsync.
EOF
}

log() {
    printf '%s %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*" >&2
}

die() {
    log "ERROR: $*"
    exit 1
}

need_cmd() {
    command -v "$1" >/dev/null 2>&1 || die "Command tidak ditemukan: $1"
}

secure_file_mode() {
    local path="$1" label="$2" mode
    [ -f "$path" ] || die "$label tidak ditemukan: $path"
    mode="$(stat -c '%a' "$path")"
    [ "$mode" = "600" ] || die "$label wajib bermode 0600, ditemukan $mode"
}

is_uint() {
    case "${1:-}" in
        ''|*[!0-9]*) return 1 ;;
        *) return 0 ;;
    esac
}

prune_to_count() {
    local root="$1" keep="$2"
    [ -d "$root" ] || return 0
    keep=$((10#$keep))

    find "$root" -mindepth 1 -maxdepth 1 -type d -name '20*' \
        -printf '%T@ %p\n' \
        | sort -nr \
        | tail -n +$((keep + 1)) \
        | cut -d' ' -f2- \
        | while IFS= read -r old; do
            [ -n "$old" ] || continue
            log "Menghapus backup lama: $old"
            rm -rf -- "$old"
        done
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    usage
    exit 0
fi
[ $# -eq 0 ] || die "Argumen tidak dikenal. Gunakan --help."

ENV_FILE="${BACKUP_ENV_FILE:-/etc/klasifas/backup.env}"
case "$ENV_FILE" in
    /*) ;;
    *) die "File konfigurasi backup harus path absolut" ;;
esac
[ -f "$ENV_FILE" ] || die "File konfigurasi tidak ditemukan: $ENV_FILE"
secure_file_mode "$ENV_FILE" "File konfigurasi backup"

# shellcheck disable=SC1090
set -a
. "$ENV_FILE"
set +a

: "${BACKUP_DIR:?BACKUP_DIR wajib diisi}"
: "${UPLOAD_DIR:?UPLOAD_DIR wajib diisi}"
: "${PGHOST:?PGHOST wajib diisi}"
: "${PGPORT:?PGPORT wajib diisi}"
: "${PGDATABASE:?PGDATABASE wajib diisi}"
: "${PGUSER:?PGUSER wajib diisi}"
: "${PGPASSFILE:?PGPASSFILE wajib diisi}"

BACKUP_LOCK_FILE="${BACKUP_LOCK_FILE:-/run/lock/klasifas-backup.lock}"
BACKUP_DAILY_RETENTION="${BACKUP_DAILY_RETENTION:-7}"
BACKUP_WEEKLY_RETENTION="${BACKUP_WEEKLY_RETENTION:-4}"
PG_DUMP_BIN="${PG_DUMP_BIN:-pg_dump}"

is_uint "$BACKUP_DAILY_RETENTION" || die "BACKUP_DAILY_RETENTION harus bilangan bulat >= 1"
is_uint "$BACKUP_WEEKLY_RETENTION" || die "BACKUP_WEEKLY_RETENTION harus bilangan bulat >= 1"
[ "$BACKUP_DAILY_RETENTION" -ge 1 ] || die "BACKUP_DAILY_RETENTION minimal 1"
[ "$BACKUP_WEEKLY_RETENTION" -ge 1 ] || die "BACKUP_WEEKLY_RETENTION minimal 1"

case "$BACKUP_DIR" in
    /*) ;;
    *) die "BACKUP_DIR harus path absolut" ;;
esac
case "$UPLOAD_DIR" in
    /*) ;;
    *) die "UPLOAD_DIR harus path absolut" ;;
esac
[ "$BACKUP_DIR" != "/" ] || die "BACKUP_DIR tidak boleh /"
[ "$UPLOAD_DIR" != "/" ] || die "UPLOAD_DIR tidak boleh /"
while [ "${BACKUP_DIR%/}" != "$BACKUP_DIR" ]; do BACKUP_DIR="${BACKUP_DIR%/}"; done
while [ "${UPLOAD_DIR%/}" != "$UPLOAD_DIR" ]; do UPLOAD_DIR="${UPLOAD_DIR%/}"; done
case "$BACKUP_DIR/" in
    "$UPLOAD_DIR/"*) die "BACKUP_DIR tidak boleh berada di dalam UPLOAD_DIR" ;;
esac
case "$UPLOAD_DIR/" in
    "$BACKUP_DIR/"*) die "UPLOAD_DIR tidak boleh berada di dalam BACKUP_DIR" ;;
esac
[ -d "$UPLOAD_DIR" ] || die "UPLOAD_DIR tidak ditemukan: $UPLOAD_DIR"

case "$PGPASSFILE" in
    /*) ;;
    *) die "PGPASSFILE harus path absolut" ;;
esac
secure_file_mode "$PGPASSFILE" "PGPASSFILE"
unset PGPASSWORD

case "$PGPASSFILE/" in
    "$UPLOAD_DIR/"*) die "PGPASSFILE tidak boleh berada di dalam UPLOAD_DIR" ;;
esac
case "$ENV_FILE/" in
    "$UPLOAD_DIR/"*) die "File konfigurasi backup tidak boleh berada di dalam UPLOAD_DIR" ;;
esac

need_cmd "$PG_DUMP_BIN"
need_cmd tar
need_cmd sha256sum
need_cmd flock
need_cmd find
need_cmd sort
need_cmd tail
need_cmd cut
need_cmd stat
if [ -n "${BACKUP_REMOTE:-}" ]; then
    need_cmd rsync
    case "$BACKUP_REMOTE" in
        "$BACKUP_DIR"|"$BACKUP_DIR/"*) die "BACKUP_REMOTE tidak boleh menunjuk ke BACKUP_DIR sendiri" ;;
    esac
    case "$BACKUP_REMOTE/" in
        "$UPLOAD_DIR/"*) die "BACKUP_REMOTE tidak boleh berada di dalam UPLOAD_DIR" ;;
    esac
    case "$BACKUP_DIR/" in
        "$BACKUP_REMOTE/"*) die "BACKUP_REMOTE tidak boleh menjadi parent BACKUP_DIR" ;;
    esac
    case "$UPLOAD_DIR/" in
        "$BACKUP_REMOTE/"*) die "BACKUP_REMOTE tidak boleh menjadi parent UPLOAD_DIR" ;;
    esac
fi

install -d -m 0700 "$BACKUP_DIR" "$BACKUP_DIR/daily" "$BACKUP_DIR/weekly"
chmod 0700 "$BACKUP_DIR" "$BACKUP_DIR/daily" "$BACKUP_DIR/weekly"

exec 9>"$BACKUP_LOCK_FILE"
flock -n 9 || die "Backup lain sedang berjalan"

tmp_dir=""
cleanup() {
    if [ -n "${tmp_dir:-}" ] && [ -d "$tmp_dir" ]; then
        rm -rf -- "$tmp_dir"
    fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

stamp="$(date -u +'%Y-%m-%dT%H%M%SZ')"
daily_root="$BACKUP_DIR/daily"
weekly_root="$BACKUP_DIR/weekly"
daily_dir="$daily_root/$stamp"
[ -e "$daily_dir" ] && daily_dir="${daily_dir}-$$"
tmp_dir="$daily_root/.tmp-$stamp-$$"
mkdir -m 0700 "$tmp_dir"

log "Memulai backup database $PGDATABASE ke $daily_dir"
"$PG_DUMP_BIN" \
    --format=custom \
    --compress=9 \
    --no-owner \
    --no-privileges \
    --no-password \
    --dbname="$PGDATABASE" \
    --file="$tmp_dir/db.dump"

log "Membackup uploads dari $UPLOAD_DIR"
tar -C "$UPLOAD_DIR" -czf "$tmp_dir/uploads.tar.gz" .

chmod 0600 "$tmp_dir/db.dump" "$tmp_dir/uploads.tar.gz"
(
    cd "$tmp_dir"
    sha256sum db.dump uploads.tar.gz > SHA256SUMS
    chmod 0600 SHA256SUMS
)

mv -T "$tmp_dir" "$daily_dir"
tmp_dir=""
log "Backup harian dibuat: $daily_dir"

if [ "$(date -u +%u)" = "7" ]; then
    week="$(date -u +'%G-W%V')"
    weekly_dir="$weekly_root/$week"
    if [ ! -d "$weekly_dir" ]; then
        if ! cp -al "$daily_dir" "$weekly_dir"; then
            rm -rf -- "$weekly_dir"
            cp -a "$daily_dir" "$weekly_dir"
        fi
        log "Backup mingguan dibuat: $weekly_dir"
    fi
fi

prune_to_count "$daily_root" "$BACKUP_DAILY_RETENTION"
prune_to_count "$weekly_root" "$BACKUP_WEEKLY_RETENTION"

if [ -n "${BACKUP_REMOTE:-}" ]; then
    log "Menyinkronkan backup ke remote: $BACKUP_REMOTE"
    rsync -a --delete "$BACKUP_DIR/" "$BACKUP_REMOTE/"
    log "Sinkronisasi remote selesai"
else
    log "BACKUP_REMOTE kosong; salinan offsite dilewati"
fi

log "Backup selesai: $daily_dir"
