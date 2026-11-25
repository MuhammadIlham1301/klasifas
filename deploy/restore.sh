#!/usr/bin/env bash
#
# Restore PostgreSQL dan uploads KlasiFas ke database target.
# Restore selalu meminta konfirmasi nama database. Tidak ada mode otomatis.
set -euo pipefail
umask 077

usage() {
    cat <<'EOF'
Usage: restore.sh --backup DIR --database NAMA_DB

Contoh staging:
  restore.sh --backup /var/backups/klasifas/daily/2026-11-22T020000Z \
             --database klasifas_staging

Konfigurasi dibaca dari /etc/klasifas/restore.env bila ada, atau
BACKUP_ENV_FILE (/etc/klasifas/backup.env). Script meminta konfirmasi
nama database target sebelum menimpa objek database dan uploads.

Target yang terlihat seperti produksi memerlukan ALLOW_PRODUCTION_RESTORE=1
dan konfirmasi tambahan. Script tidak pernah menimpa production secara otomatis.
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

BACKUP_SOURCE=""
TARGET_DB=""

while [ $# -gt 0 ]; do
    case "$1" in
        --backup)
            [ $# -ge 2 ] || die "Opsi --backup memerlukan path"
            BACKUP_SOURCE="$2"
            shift 2
            ;;
        --database)
            [ $# -ge 2 ] || die "Opsi --database memerlukan nama database"
            TARGET_DB="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            die "Argumen tidak dikenal: $1"
            ;;
    esac
done

[ -n "$BACKUP_SOURCE" ] || die "Wajib menentukan --backup DIR"
[ -n "$TARGET_DB" ] || die "Wajib menentukan --database NAMA_DB"

RESTORE_ENV_FILE="${RESTORE_ENV_FILE:-/etc/klasifas/restore.env}"
if [ -f "$RESTORE_ENV_FILE" ]; then
    ENV_FILE="$RESTORE_ENV_FILE"
elif [ -f "${BACKUP_ENV_FILE:-/etc/klasifas/backup.env}" ]; then
    ENV_FILE="${BACKUP_ENV_FILE:-/etc/klasifas/backup.env}"
else
    die "File konfigurasi restore/backup tidak ditemukan"
fi

case "$ENV_FILE" in
    /*) ;;
    *) die "File konfigurasi restore harus path absolut" ;;
esac
secure_file_mode "$ENV_FILE" "File konfigurasi restore"

# shellcheck disable=SC1090
set -a
. "$ENV_FILE"
set +a

: "${UPLOAD_DIR:?UPLOAD_DIR wajib diisi}"
: "${PGHOST:?PGHOST wajib diisi}"
: "${PGPORT:?PGPORT wajib diisi}"
: "${PGUSER:?PGUSER wajib diisi}"
: "${PGPASSFILE:?PGPASSFILE wajib diisi}"

BACKUP_LOCK_FILE="${BACKUP_LOCK_FILE:-/run/lock/klasifas-backup.lock}"
PG_RESTORE_BIN="${PG_RESTORE_BIN:-pg_restore}"
PSQL_BIN="${PSQL_BIN:-psql}"

case "$UPLOAD_DIR" in
    /*) ;;
    *) die "UPLOAD_DIR harus path absolut" ;;
esac
[ "$UPLOAD_DIR" != "/" ] || die "UPLOAD_DIR tidak boleh /"
while [ "${UPLOAD_DIR%/}" != "$UPLOAD_DIR" ]; do UPLOAD_DIR="${UPLOAD_DIR%/}"; done
if [ -e "$UPLOAD_DIR" ] && [ -L "$UPLOAD_DIR" ]; then
    die "UPLOAD_DIR tidak boleh berupa symlink"
fi
if command -v mountpoint >/dev/null 2>&1 && [ -e "$UPLOAD_DIR" ] && mountpoint -q "$UPLOAD_DIR"; then
    die "UPLOAD_DIR adalah mount point; restore uploads harus dilakukan secara terkontrol"
fi
case "$PGPASSFILE" in
    /*) ;;
    *) die "PGPASSFILE harus path absolut" ;;
esac

[ -d "$BACKUP_SOURCE" ] || die "Backup tidak ditemukan: $BACKUP_SOURCE"
BACKUP_SOURCE="$(cd "$BACKUP_SOURCE" && pwd)"
[ "$BACKUP_SOURCE" != "/" ] || die "Backup source tidak boleh /"
case "$BACKUP_SOURCE/" in
    "$UPLOAD_DIR/"*) die "Backup source tidak boleh berada di dalam UPLOAD_DIR" ;;
esac
case "$UPLOAD_DIR/" in
    "$BACKUP_SOURCE/"*) die "UPLOAD_DIR tidak boleh berada di dalam backup source" ;;
esac

DB_DUMP="$BACKUP_SOURCE/db.dump"
UPLOADS_ARCHIVE="$BACKUP_SOURCE/uploads.tar.gz"
MANIFEST="$BACKUP_SOURCE/SHA256SUMS"

[ -f "$DB_DUMP" ] || die "db.dump tidak ditemukan"
[ -f "$UPLOADS_ARCHIVE" ] || die "uploads.tar.gz tidak ditemukan"
[ -f "$MANIFEST" ] || die "SHA256SUMS tidak ditemukan"

case "$TARGET_DB" in
    ""|postgres|template0|template1)
        die "Database target tidak valid atau merupakan database sistem"
        ;;
    [A-Za-z_]*)
        ;;
    *)
        die "Nama database target harus diawali huruf atau underscore"
        ;;
esac
case "$TARGET_DB" in
    *[!A-Za-z0-9_]*)
        die "Nama database target hanya boleh berisi huruf, angka, dan underscore"
        ;;
esac

secure_file_mode "$PGPASSFILE" "PGPASSFILE"
unset PGPASSWORD

case "$PGPASSFILE/" in
    "$UPLOAD_DIR/"*) die "PGPASSFILE tidak boleh berada di dalam UPLOAD_DIR" ;;
esac
case "$ENV_FILE/" in
    "$UPLOAD_DIR/"*) die "File konfigurasi restore tidak boleh berada di dalam UPLOAD_DIR" ;;
esac

need_cmd "$PG_RESTORE_BIN"
need_cmd "$PSQL_BIN"
need_cmd tar
need_cmd grep
need_cmd sha256sum
need_cmd flock
need_cmd stat
need_cmd find
need_cmd wc
need_cmd cp
need_cmd mv
need_cmd chown
need_cmd install
need_cmd mktemp
need_cmd dirname
need_cmd date

exec 9>"$BACKUP_LOCK_FILE"
flock -n 9 || die "Backup/restore lain sedang berjalan"

tmp_uploads=""
cleanup() {
    if [ -n "${tmp_uploads:-}" ] && [ -d "$tmp_uploads" ]; then
        rm -rf -- "$tmp_uploads"
    fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

log "Memverifikasi manifest SHA-256"
(
    cd "$BACKUP_SOURCE"
    sha256sum -c SHA256SUMS
)

log "Memverifikasi format custom pg_dump"
"$PG_RESTORE_BIN" --list "$DB_DUMP" >/dev/null

log "Memeriksa koneksi ke target $PGHOST:$PGPORT/$TARGET_DB"
"$PSQL_BIN" \
    --no-password \
    --dbname="$TARGET_DB" \
    --set=ON_ERROR_STOP=1 \
    --tuples-only \
    --no-align \
    --command='SELECT 1' >/dev/null

protected=0
if [ -n "${KLASIFAS_PRODUCTION_DB:-}" ] && [ "$TARGET_DB" = "$KLASIFAS_PRODUCTION_DB" ]; then
    protected=1
fi
shopt -s nocasematch
case "$TARGET_DB" in
    *prod*) protected=1 ;;
esac
shopt -u nocasematch

if [ "$protected" -eq 1 ]; then
    [ "${ALLOW_PRODUCTION_RESTORE:-0}" = "1" ] || die \
        "Target terlihat seperti production. Restore production tidak otomatis; set ALLOW_PRODUCTION_RESTORE=1 bila benar-benar disengaja."
    log "PERINGATAN: target terlihat seperti production"
    read -r -p "Ketik RESTORE PRODUCTION untuk melanjutkan: " production_confirm
    [ "$production_confirm" = "RESTORE PRODUCTION" ] || die "Konfirmasi production tidak cocok"
fi

printf 'Backup source : %s\n' "$BACKUP_SOURCE"
printf 'Target DB     : %s:%s/%s\n' "$PGHOST" "$PGPORT" "$TARGET_DB"
printf 'Uploads target: %s\n' "$UPLOAD_DIR"
printf 'PERINGATAN: restore akan menimpa objek database target dan mengganti uploads.\n'
read -r -p "Ketik nama database target '$TARGET_DB' untuk melanjutkan: " target_confirm
[ "$target_confirm" = "$TARGET_DB" ] || die "Konfirmasi database target tidak cocok; restore dibatalkan"

upload_parent="$(dirname "$UPLOAD_DIR")"
[ -d "$upload_parent" ] || die "Parent UPLOAD_DIR tidak ditemukan: $upload_parent"

if [ -n "${RESTORE_OWNER:-}" ]; then
    upload_owner="$RESTORE_OWNER"
elif [ -d "$UPLOAD_DIR" ]; then
    upload_owner="$(stat -c '%u:%g' "$UPLOAD_DIR")"
else
    die "RESTORE_OWNER wajib diisi jika UPLOAD_DIR belum ada"
fi

log "Memeriksa path di dalam arsip uploads"
archive_listing="$(tar -tzf "$UPLOADS_ARCHIVE")" || die "Gagal membaca arsip uploads"
if printf '%s\n' "$archive_listing" | grep -E '(^|/)\.\.(/|$)|^/' >/dev/null; then
    die "Arsip uploads berisi path absolut atau '..'; restore dibatalkan"
fi

tmp_uploads="$(mktemp -d "$upload_parent/.klasifas-restore-uploads.XXXXXX")"
log "Mengekstrak uploads ke area sementara"
tar -xzf "$UPLOADS_ARCHIVE" -C "$tmp_uploads" --no-same-owner

if [ -n "$(find "$tmp_uploads" ! -type f ! -type d -print -quit)" ]; then
    die "Arsip uploads berisi symlink atau special file; restore dibatalkan"
fi

log "Memulihkan database target"
"$PG_RESTORE_BIN" \
    --no-password \
    --clean \
    --if-exists \
    --single-transaction \
    --exit-on-error \
    --no-owner \
    --no-privileges \
    --dbname="$TARGET_DB" \
    "$DB_DUMP"

old_uploads=""
if [ -e "$UPLOAD_DIR" ]; then
    [ -L "$UPLOAD_DIR" ] && die "UPLOAD_DIR tidak boleh berupa symlink"
    old_uploads="${UPLOAD_DIR}.pre-restore.$(date -u +'%Y%m%dT%H%M%SZ')-$$"
    mv -T "$UPLOAD_DIR" "$old_uploads"
    log "Uploads lama dipindahkan ke: $old_uploads"
fi

install -d -m 0750 "$UPLOAD_DIR"
cp -a "$tmp_uploads/." "$UPLOAD_DIR/"
chown -R "$upload_owner" "$UPLOAD_DIR"

table_count="$("$PSQL_BIN" \
    --no-password \
    --dbname="$TARGET_DB" \
    --set=ON_ERROR_STOP=1 \
    --tuples-only \
    --no-align \
    --command="SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")"
upload_count="$(find "$UPLOAD_DIR" -type f | wc -l)"

log "Restore selesai. Tabel public: $table_count; file uploads: $upload_count"
log "Jalankan aplikasi dan verifikasi sebelum menghapus uploads lama."
