# Deployment KlasiFas (Tahap 1-2 P0)

Dokumen ini adalah panduan deployment on-prem/Linux untuk lingkungan terkontrol.
Ini bukan deployment cloud publik dan tidak mengubah status proyek sebagai MVP
akademik.

## 1. Status tahap ini

Sudah disediakan:

- `requirements-prod.txt` dengan Gunicorn.
- `wsgi.py` yang memakai factory `production`.
- `deploy/gunicorn.conf.py` yang hanya bind ke `127.0.0.1:8000`.
- `deploy/klasifas.service` dengan hardening systemd.
- Kerangka `deploy/nginx-klasifas.conf`.
- `deploy/backup.sh` dan `deploy/backup.env.example` untuk backup harian.
- `deploy/restore.sh` untuk restore ke database target dengan konfirmasi eksplisit.
- Dokumen operasional ini.

Belum termasuk pada tahap ini:

- Rate limit `/lapor`.
- Health check aplikasi.
- HSTS aktif (sengaja dikomentari).
- Dependency lock dan audit kerentanan.
- Tuning koneksi PostgreSQL/SSL.
- Point-in-time recovery (WAL) dan enkripsi backup bawaan.

## 2. Prasyarat

- Linux dengan systemd.
- Python 3.11.
- PostgreSQL.
- Nginx.
- Sertifikat TLS (misalnya Let's Encrypt).
- User sistem `klasifas` tanpa shell login.
- PostgreSQL client tools (`pg_dump`, `pg_restore`, `psql`) sesuai versi server.
- `flock` dari util-linux; `rsync` hanya jika memakai `BACKUP_REMOTE`.

Contoh Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx postgresql postgresql-client certbot python3-certbot-nginx util-linux rsync
getent group klasifas >/dev/null || sudo groupadd --system klasifas
id -u klasifas >/dev/null 2>&1 || sudo useradd --system --gid klasifas --home /opt/klasifas --shell /usr/sbin/nologin klasifas
sudo install -d -m 0755 -o klasifas -g klasifas /opt/klasifas
sudo install -d -m 0750 -o klasifas -g klasifas /opt/klasifas/uploads
sudo install -d -m 0750 -o root -g klasifas /etc/klasifas
```

Letakkan source code di `/opt/klasifas`, lalu buat virtual environment:

```bash
sudo -u klasifas python3 -m venv /opt/klasifas/venv
sudo -u klasifas /opt/klasifas/venv/bin/pip install --upgrade pip
sudo -u klasifas /opt/klasifas/venv/bin/pip install -r /opt/klasifas/requirements-prod.txt
```

## 3. Konfigurasi environment produksi

Buat `/etc/klasifas/klasifas.env` dari template, lalu isi nilai produksi:

```bash
sudo install -m 0640 -o root -g klasifas /opt/klasifas/.env.example /etc/klasifas/klasifas.env
sudo editor /etc/klasifas/klasifas.env
```

Isi minimum:

```dotenv
FLASK_CONFIG=production
SECRET_KEY=<64 karakter heksadesimal>
DATABASE_URL=postgresql+psycopg2://<user>:<password>@<host>:5432/<database>
TRUSTED_PROXIES_COUNT=1
ML_CONFIDENCE_THRESHOLD=0.60
```

Buat `SECRET_KEY` baru, jangan memakai nilai development:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Ketentuan:

- Jangan menyimpan `.env` atau nilai secret ke repository.
- Jangan menyalin kredensial development ke environment produksi.
- `DEV_DATABASE_URL` dan `TEST_DATABASE_URL` tidak dipakai oleh
  `ProductionConfig`; jangan mengisinya dengan kredensial produksi.
- File environment hanya boleh dibaca root dan group service (`0640 root:klasifas`).
- `TRUSTED_PROXIES_COUNT=1` hanya benar jika tepat ada satu reverse proxy
  tepercaya (Nginx) di depan Gunicorn. Jika ada CDN tambahan, sesuaikan jumlah hop.
- `GUNICORN_WORKERS` opsional; nilai default dihitung oleh
  `deploy/gunicorn.conf.py`.

### 3.1 Konfigurasi backup dan restore

Salin template, lalu isi path, koneksi, dan retensi:

```bash
sudo install -m 0600 -o root -g root /opt/klasifas/deploy/backup.env.example /etc/klasifas/backup.env
sudo editor /etc/klasifas/backup.env
```

File `/etc/klasifas/backup.env` wajib `0600 root:root`. Untuk restore ke
staging, buat file terpisah `/etc/klasifas/restore.env` dengan mode yang sama.
`restore.sh` memakai `RESTORE_ENV_FILE` bila ada, lalu fallback ke
`BACKUP_ENV_FILE`.

Buat password file PostgreSQL, jangan menaruh password di environment:

```bash
sudo install -m 0600 -o root -g root /dev/null /etc/klasifas/.pgpass
sudo editor /etc/klasifas/.pgpass
```

Format satu baris: `host:port:database:user:password`. File harus `0600`;
`backup.sh` dan `restore.sh` menolak mode lain. Jangan commit file ini.

User backup sebaiknya hanya membaca. Contoh untuk database `klasifas_db`
(ganti password placeholder):

```sql
CREATE ROLE klasifas_backup LOGIN PASSWORD '<password-kuat>';
GRANT CONNECT ON DATABASE klasifas_db TO klasifas_backup;
GRANT USAGE ON SCHEMA public TO klasifas_backup;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO klasifas_backup;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO klasifas_backup;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO klasifas_backup;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON SEQUENCES TO klasifas_backup;
```

Jangan memakai user aplikasi atau superuser untuk backup rutin. Untuk restore,
gunakan role staging yang menjadi owner database target, bukan role backup
read-only.

## 4. Migrasi database

Hentikan service sebelum migrasi:

```bash
cd /opt/klasifas
sudo systemctl stop klasifas 2>/dev/null || true
sudo -u klasifas /opt/klasifas/venv/bin/flask --app wsgi:app --env-file /etc/klasifas/klasifas.env db upgrade
```

Jangan menjalankan migrasi terhadap database development atau testing.
Migration yang mengubah/menghapus data tetap memerlukan review dan persetujuan.

## 5. Gunicorn dan systemd

Periksa konfigurasi Gunicorn terlebih dahulu:

```bash
cd /opt/klasifas
sudo -u klasifas bash -c 'set -a; . /etc/klasifas/klasifas.env; set +a; /opt/klasifas/venv/bin/gunicorn --check-config -c /opt/klasifas/deploy/gunicorn.conf.py wsgi:app'
```

Pasang unit systemd:

```bash
sudo cp /opt/klasifas/deploy/klasifas.service /etc/systemd/system/klasifas.service
sudo systemd-analyze verify /etc/systemd/system/klasifas.service
sudo systemctl daemon-reload
sudo systemctl enable --now klasifas
sudo systemctl status klasifas
```

Gunicorn hanya listen di `127.0.0.1:8000`. Jangan mengubah bind menjadi
`0.0.0.0` atau membuka port 8000 ke publik.

Lihat log:

```bash
journalctl -u klasifas -f
```

## 6. Nginx dan TLS

Salin kerangka konfigurasi, lalu ganti `example.com` dan path sertifikat:

```bash
sudo cp /opt/klasifas/deploy/nginx-klasifas.conf /etc/nginx/sites-available/klasifas
sudo ln -s /etc/nginx/sites-available/klasifas /etc/nginx/sites-enabled/klasifas
sudo nginx -t
sudo systemctl reload nginx
```

Pasang sertifikat TLS, misalnya:

```bash
sudo certbot certonly --nginx -d example.com -d www.example.com
```

Setelah sertifikat tersedia, pastikan path di `nginx-klasifas.conf` benar,
lalu jalankan ulang:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

Jangan aktifkan HSTS sebelum HTTPS benar-benar berfungsi. Uji dulu:

```bash
curl -I https://example.com/
```

Jika status HTTPS, sertifikat, dan aplikasi sudah benar, buka
`/etc/nginx/sites-available/klasifas`, hapus tanda komentar pada baris:

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

Lalu:

```bash
sudo nginx -t
sudo systemctl reload nginx
curl -I https://example.com/ | grep -i strict-transport-security
```

HSTS tidak dapat dibatalkan dengan cepat oleh browser. Untuk percobaan awal,
pertimbangkan `max-age` pendek sebelum nilai satu tahun.

## 7. Firewall dan akses langsung

Pastikan hanya Nginx yang dapat diakses dari luar:

```bash
sudo ufw allow 'Nginx Full'
sudo ufw deny 8000/tcp
sudo ufw enable
sudo ufw status
```

Verifikasi Gunicorn dari server:

```bash
curl -I http://127.0.0.1:8000/
```

Verifikasi port 8000 tidak terbuka dari luar. Jika port tersebut terbuka,
rate limit dan header proxy dapat dilewati.

## 8. Verifikasi setelah deploy

```bash
curl -I http://example.com/
curl -I https://example.com/
curl -I https://example.com/lapor
sudo systemctl status klasifas nginx
journalctl -u klasifas -n 100 --no-pager
```

Yang diharapkan:

- HTTP mengembalikan `301` ke HTTPS.
- HTTPS mengembalikan respons aplikasi.
- HSTS belum ada sebelum diaktifkan secara manual.
- `127.0.0.1:8000` hanya dapat diakses dari server.
- Tidak ada secret atau stack trace pada log/respons.

## 9. Backup harian

`deploy/backup.sh` menghasilkan satu direktori
`daily/YYYY-MM-DDTHHMMSSZ` berisi:

- `db.dump` — `pg_dump --format=custom` dari database.
- `uploads.tar.gz` — arsip direktori uploads.
- `SHA256SUMS` — checksum untuk verifikasi restore.

Setiap hari Minggu, backup harian disalin ke `weekly/YYYY-Www`. Retensi default
menyimpan 7 backup harian dan 4 backup mingguan. Backup memakai `flock` agar
dua proses backup tidak berjalan bersamaan.

Jalankan backup manual pertama:

```bash
sudo /opt/klasifas/deploy/backup.sh
sudo ls -l /var/backups/klasifas/daily
sudo ls -l /var/backups/klasifas/weekly
```

Jadwalkan lewat crontab root:

```bash
sudo crontab -e
```

```cron
15 2 * * * /opt/klasifas/deploy/backup.sh >> /var/log/klasifas-backup.log 2>&1
```

Periksa log dan ukuran backup secara berkala. Backup yang tidak pernah diuji
restore belum bisa dianggap dapat dipakai.

`BACKUP_REMOTE` opsional menyalin seluruh direktori backup dengan
`rsync -a --delete`; direktori tujuan harus sudah ada dan akses SSH harus
memakai key. Jika sinkronisasi remote gagal, backup lokal tetap ada tetapi
script keluar non-zero.

Batasan:

- `pg_dump` adalah backup logis, bukan point-in-time recovery. RPO mengikuti
  jadwal backup.
- Backup tidak dienkripsi oleh script. Gunakan filesystem/remote terenkripsi
  dan batasi akses karena arsip uploads dapat berisi data pelapor.
- Backup mingguan hanya dibuat jika backup berjalan pada hari Minggu.

## 10. Restore ke staging

Restore dilakukan ke database target yang sudah ada. Script tidak membuat
database dan tidak menghentikan aplikasi. Jangan restore ke database yang
sedang dipakai aplikasi.

Siapkan database staging dan role yang menjadi owner-nya:

```bash
sudo -u postgres createuser --login --pwprompt klasifas_restore
sudo -u postgres createdb -O klasifas_restore klasifas_staging
```

Buat `/etc/klasifas/restore.env` dari template backup, lalu ubah minimal:

```dotenv
UPLOAD_DIR=/opt/klasifas-staging/uploads
PGUSER=klasifas_restore
PGDATABASE=klasifas_staging
KLASIFAS_PRODUCTION_DB=klasifas_db
RESTORE_OWNER=klasifas:klasifas
```

`PGPASSFILE` harus berisi entri untuk user dan database target. Target database
hanya boleh berisi huruf, angka, dan underscore, serta diawali huruf atau
underscore. `RESTORE_OWNER` wajib diisi jika `UPLOAD_DIR` belum ada; jika sudah
ada, script memakai owner direktori lama.

Jalankan restore:

```bash
sudo env RESTORE_ENV_FILE=/etc/klasifas/restore.env \
  /opt/klasifas/deploy/restore.sh \
  --backup /var/backups/klasifas/daily/2026-11-22T020000Z \
  --database klasifas_staging
```

Script akan:

1. Memeriksa `SHA256SUMS`, format custom dump, dan koneksi ke target.
2. Menolak arsip uploads yang berisi path absolut, `..`, symlink, atau special file.
3. Meminta konfirmasi persis nama database target.
4. Menjalankan `pg_restore --clean --if-exists --single-transaction --exit-on-error`.
5. Memindahkan uploads lama ke `UPLOAD_DIR.pre-restore.<timestamp>-<pid>`,
   lalu memasang uploads hasil restore dan mengubah owner ke `RESTORE_OWNER`.

Setelah restore, jalankan aplikasi staging dan verifikasi login, daftar tiket,
detail tiket, serta file uploads. Hapus direktori uploads lama hanya setelah
verifikasi selesai.

Target yang terlihat seperti production diblokir. Untuk restore production
yang benar-benar disetujui:

1. Hentikan service `klasifas` dan pastikan tidak ada proses menulis ke database.
2. Buat backup terbaru dan verifikasi hasilnya.
3. Set `ALLOW_PRODUCTION_RESTORE=1`.
4. Ketik `RESTORE PRODUCTION`, lalu ketik nama database target saat diminta.

Tanpa dua konfirmasi tersebut, restore production tidak berjalan. Jangan
menjalankan langkah ini tanpa persetujuan dan jendela pemeliharaan.

## 11. Rollback sederhana

Jika deploy gagal:

```bash
sudo systemctl stop klasifas
```

Kembalikan source code ke versi sebelumnya, lalu:

```bash
sudo -u klasifas /opt/klasifas/venv/bin/pip install -r /opt/klasifas/requirements-prod.txt
sudo systemctl daemon-reload
sudo systemctl start klasifas
sudo systemctl status klasifas
```

Rollback database menggunakan prosedur restore di atas; restore production tetap
memerlukan persetujuan eksplisit.

## 12. Catatan keamanan

- `wsgi.py` memakai `create_app("production")`; konfigurasi
  development/testing tidak diubah.
- `deploy/gunicorn.conf.py` hanya bind ke loopback.
- `deploy/klasifas.service` memakai user non-root, `ProtectSystem=strict`,
  `NoNewPrivileges`, dan pembatasan filesystem.
- Direktori `uploads/` harus tetap di luar `app/static/` dan tidak boleh
  diekspos langsung oleh Nginx.
- Jangan menaruh secret, password, token, atau kredensial di repository.
- `/etc/klasifas/backup.env` dan `/etc/klasifas/restore.env` wajib `0600 root:root`;
  `PGPASSFILE` juga wajib `0600`. Jangan menaruh `PGPASSWORD` di environment.
- Backup berisi dump database dan uploads; perlakukan sebagai data sensitif.
  Batasi akses ke `BACKUP_DIR` dan remote.
- `restore.sh` menolak target sistem, path arsip tidak aman, dan symlink di
  arsip uploads. Target production memerlukan override dan dua konfirmasi.
- HSTS, rate limit `/lapor`, dan health check adalah pekerjaan tahap berikutnya.

## 13. Batasan yang diketahui

- `requirements-prod.txt` masih mengimpor `requirements.txt`, sehingga `pytest`
  ikut terpasang. Pemisahan dependency runtime penuh adalah pekerjaan P1.
- Rate limiter login masih in-memory per worker Gunicorn. Ini belum diselesaikan
  pada tahap ini.
- Backup adalah `pg_dump` logis; belum ada WAL/PITR, enkripsi bawaan, atau
  verifikasi restore otomatis.
- `restore.sh` memerlukan role yang menjadi owner database target agar
  `pg_restore --clean` dapat menghapus objek lama; role backup read-only tidak
  cukup untuk restore.
- `restore.sh` tidak menghentikan aplikasi. Restore production harus dilakukan
  saat service berhenti dan setelah backup terbaru diverifikasi.
- `backup.sh` dan `restore.sh` baru diverifikasi dengan `bash -n` dan simulasi
  di Windows; PostgreSQL, Nginx, dan systemd nyata belum dijalankan pada tahap ini.
- Deployment multi-host, shared uploads, dan database SSL belum termasuk.
