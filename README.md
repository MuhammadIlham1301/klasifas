# KlasiFas — Klasifikasi Keluhan Fasilitas Kampus

**Rancang Bangun Sistem Klasifikasi Keluhan dan Dasbor Pemantauan Fasilitas Kampus Menggunakan Algoritma Naive Bayes**

| Informasi | Keterangan |
|---|---|
| Institusi | Universitas Muhammadiyah Prof. Dr. HAMKA (UHAMKA) |
| Fakultas | Fakultas Teknologi Industri dan Informatika (FTII) |
| Kelompok | 7 |
| Anggota Tim | Egi Bayu Setiawan (2303045028), Muhammad Adrian (2303045016), Muhammad Ilham (2303045036) |
| Status Proyek | Implementasi MVP dan pengujian |
| Status Dokumen | Revisi dokumentasi berdasarkan implementasi aktual |

---

## 1. Tentang Proyek

**KlasiFas** merupakan aplikasi web untuk pelaporan, klasifikasi, pemantauan, dan pengelolaan tindak lanjut keluhan fasilitas kampus.

Sistem dirancang untuk mengintegrasikan klasifikasi teks menggunakan algoritma **Multinomial Naive Bayes** dengan dashboard pemantauan interaktif. Rekomendasi kategori hasil klasifikasi menjadi informasi pendukung bagi Admin Sarpras sebelum tiket diteruskan kepada teknisi.

KlasiFas dikembangkan sebagai proyek akademik Capstone berupa MVP/prototipe lokal untuk lingkungan FTII UHAMKA.

### Tujuan Proyek

1. Menyediakan sarana pelaporan keluhan fasilitas kampus secara terstruktur.
2. Mengembangkan rekomendasi klasifikasi keluhan menggunakan NLP dan Naive Bayes.
3. Memudahkan Admin Sarpras melakukan verifikasi kategori dan penugasan teknisi.
4. Memungkinkan pelapor memantau perkembangan tiket secara mandiri dan aman.
5. Menyediakan dashboard agregat untuk memantau kondisi fasilitas kampus.

## 2. Ruang Lingkup dan Fitur Utama

KlasiFas mencakup sepuluh kebutuhan fungsional:

| ID | Fitur | Deskripsi |
|---|---|---|
| FR-01 | Pelaporan Keluhan | Pengiriman deskripsi, lokasi, kategori opsional, dan foto pendukung. |
| FR-02 | Pelacakan Tiket | Pelacakan menggunakan kode referensi dan token rahasia. |
| FR-03 | Klasifikasi Otomatis | Preprocessing teks dan rekomendasi kategori menggunakan Naive Bayes. |
| FR-04 | Verifikasi Kategori | Admin Sarpras memverifikasi atau mengoreksi kategori. |
| FR-05 | Penugasan Teknisi | Admin menetapkan teknisi untuk menangani tiket. |
| FR-06 | Pembaruan Pengerjaan | Teknisi memperbarui status dan catatan penyelesaian. |
| FR-07 | Dashboard Manajerial | Visualisasi agregat kategori, lokasi, status, dan tren laporan. |
| FR-08 | Pencarian dan Filter | Pencarian dan penyaringan tiket operasional oleh Admin Sarpras. |
| FR-09 | Audit Log | Pencatatan perubahan kategori dan status resmi. |
| FR-10 | Fallback Manual | Laporan tetap diterima ketika klasifikasi otomatis tidak tersedia atau gagal. |

### 2.1 Kategori Keluhan

1. **K1** — Ruang kelas dan perabot
2. **K2** — Laboratorium dan perangkat
3. **K3** — Jaringan dan internet
4. **K4** — Kebersihan dan sanitasi
5. **K5** — Listrik, AC, dan penerangan
6. **K6** — Keamanan, parkir, dan akses
7. **K7** — Lainnya

### 2.2 Status Tiket

`Baru → Terverifikasi → Diproses → Selesai`

Penugasan teknisi merupakan atribut operasional, bukan status tiket tersendiri.

### 2.3 Peran Pengguna

- **Pelapor:** Mengirim keluhan dan melacak tiket menggunakan kredensial yang valid.
- **Admin Sarpras:** Memverifikasi kategori, menugaskan teknisi, mengelola tiket, membaca audit log, dan mengakses dashboard.
- **Teknisi:** Melihat tiket yang ditugaskan kepadanya dan memperbarui pengerjaan.
- **Pimpinan/Kaprodi:** Mengakses dashboard agregat secara read-only.

## 3. Teknologi

| Komponen | Teknologi |
|---|---|
| Bahasa | Python 3.11 |
| Backend | Flask |
| Arsitektur | Modular Monolith, Application Factory |
| Database | PostgreSQL |
| ORM | SQLAlchemy 2.0 |
| Migrasi | Flask-Migrate / Alembic |
| UI | HTML5, CSS3, Bootstrap 5 |
| Template | Jinja2 |
| Visualisasi | Chart.js |
| Machine Learning | scikit-learn |
| Algoritma | Multinomial Naive Bayes, TF-IDF |
| NLP | PySastrawi |
| Pengolahan data | pandas, NumPy |
| Serialisasi model | joblib |
| Password hashing | Werkzeug scrypt |
| CSRF | Flask-WTF |
| Pengujian | pytest |

Rincian teknis dapat dibaca pada [docs/TECHSTACK.md](docs/TECHSTACK.md).

## 4. Struktur Direktori

Struktur aktual utama aplikasi:

```text
Klasifas/
├── app/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── routes/
│   ├── services/
│   ├── models/
│   ├── ml/
│   ├── utils/
│   ├── templates/
│   └── static/
├── docs/
│   ├── ui-ux-reference/
│   ├── PRD.md
│   ├── TECHSTACK.md
│   ├── SECURITY.md
│   ├── DESIGN.md
│   ├── TASKS.md
│   └── SKILLS.md
├── migrations/
├── tests/
├── uploads/
├── .env.example
├── .gitignore
├── requirements.txt
├── AGENTS.md
└── README.md
```

Direktori `uploads/` digunakan untuk penyimpanan foto keluhan non-publik. File konfigurasi rahasia `.env` dan data lokal tidak boleh dimasukkan ke Git.

## 5. Persyaratan Lingkungan

Persiapan pengembangan lokal membutuhkan:

- Python 3.11.
- PostgreSQL.
- pip.
- Virtual environment (`venv`).
- Git.
- Browser modern.

## 6. Instalasi dan Konfigurasi

Contoh langkah persiapan menggunakan Windows PowerShell.

### 6.1 Membuat Virtual Environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 6.2 Instalasi Dependensi

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 6.3 Konfigurasi Environment

Salin template konfigurasi:

```powershell
Copy-Item .env.example .env
```

Lengkapi variabel environment sesuai konfigurasi proyek:

- `FLASK_CONFIG`: mode konfigurasi environment aplikasi (`development`, `testing`, atau `production`). Gunakan `development` untuk lingkungan pengembangan lokal.
- `SECRET_KEY`: kunci rahasia kriptografis untuk sesi dan proteksi CSRF sepanjang 64 karakter heksadesimal (32 bytes).
- `DEV_DATABASE_URL`: URL koneksi database PostgreSQL untuk lingkungan pengembangan (`development`).
- `TEST_DATABASE_URL`: URL koneksi database PostgreSQL terpisah khusus untuk pengujian otomatis (`testing`).
- `DATABASE_URL`: URL koneksi database PostgreSQL untuk lingkungan produksi (`production`).
- `ML_CONFIDENCE_THRESHOLD`: ambang batas keyakinan klasifikasi teks Naive Bayes (FR-04 / FR-10). Nilai default `0.60` pada template masih berupa placeholder dan belum ditetapkan sebagai threshold final berdasarkan evaluasi model.

Sesuaikan parameter koneksi PostgreSQL dengan konfigurasi lokal dan pastikan database pengembangan serta pengujian terpisah sudah tersedia.

**Penting:** Jangan membagikan isi `.env`, memasukkan secret ke Git, atau menggunakan database pengembangan sebagai database pengujian.

### 6.4 Migrasi Database

Setelah konfigurasi database tersedia, jalankan:

```powershell
flask --app "app:create_app('development')" db upgrade
```

## 7. Menjalankan Aplikasi

Aktifkan virtual environment dan pastikan konfigurasi pengembangan sudah tersedia.

Jalankan:

```powershell
flask --app "app:create_app('development')" run --debug
```

Aplikasi dapat diakses melalui:

`http://127.0.0.1:5000`

Halaman utama `/` diarahkan ke login pelapor. Halaman pelaporan publik tersedia pada `/lapor`, halaman login staf pada `/auth/login`, dan halaman login pelapor pada `/auth/pelapor/login`.

### 7.1 Provisioning Akun Staf dan Pelapor

Akun staf dan pelapor dibuat melalui CLI lokal menggunakan perintah `create-staff` dan `create-reporter`.

Contoh:

```powershell
flask --app "app:create_app('development')" create-staff `
  --username nama.staf `
  --role admin_sarpras `
  --full-name "Nama Lengkap Staf"

flask --app "app:create_app('development')" create-reporter `
  --username nama.pelapor `
  --full-name "Nama Lengkap Pelapor"
```

Role staf yang tersedia:

- `admin_sarpras`
- `teknisi`
- `pimpinan`

Password dimasukkan melalui prompt tersembunyi, bukan sebagai argumen perintah. Panjang minimal password adalah 12 karakter.

Tidak tersedia registrasi akun publik.

## 8. Pengujian

Pengujian otomatis menggunakan pytest.

Jalankan seluruh pengujian:

```powershell
python -m pytest -q
```

Pengujian harus menggunakan database khusus pengujian (`TEST_DATABASE_URL`), bukan database pengembangan.

**Baseline pengujian terakhir:** 545 test lulus. Hasil tersebut merupakan catatan baseline pada saat audit, bukan jaminan bahwa seluruh perubahan berikutnya otomatis tetap lulus.

Kriteria pengujian proyek adalah seluruh skenario yang dijalankan lulus tanpa error maupun failure. Target tersebut bukan target code coverage 100%.

## 9. Keamanan dan Privasi

Ketentuan keamanan utama:

- Password staf di-hash menggunakan Werkzeug scrypt.
- Token pelacakan menggunakan nilai acak kriptografis dan hanya hash SHA-256 yang disimpan.
- Verifikasi token menggunakan `hmac.compare_digest()`.
- Token rahasia ditampilkan satu kali pada respons POST dan tidak ditempatkan pada URL atau log.
- Otorisasi menggunakan RBAC server-side dan prinsip deny-by-default.
- Formulir perubahan data dilindungi CSRF.
- Foto divalidasi dan disimpan dengan nama acak pada lokasi non-publik.
- Artefak `.joblib` hanya dimuat dari lokasi internal tepercaya.
- Dashboard manajerial menggunakan data agregat tanpa identitas pribadi pelapor.

Dokumentasi lengkap tersedia pada [docs/SECURITY.md](docs/SECURITY.md).

## 10. Batasan MVP

Hal-hal berikut berada di luar cakupan MVP:

- Registrasi publik dan pemulihan password.
- Aplikasi mobile native.
- Integrasi SIAKAD atau Single Sign-On.
- Klasifikasi gambar fasilitas.
- NLP multibahasa.
- Notifikasi SMS/WhatsApp berbayar.
- Penjadwalan teknisi otomatis.
- Pengelolaan inventaris dan penggajian.
- Deployment cloud publik berskala produksi.

**Catatan ML:** Pipeline klasifikasi merupakan bagian dari ruang lingkup proyek, tetapi dataset, proses pelatihan, artefak model final, dan evaluasi performa masih perlu diselesaikan. Karena itu, target metrik ML dalam PRD belum boleh dianggap sebagai hasil yang telah dicapai. Sistem menyediakan mekanisme fallback manual.

## 11. Status Pengembangan

Status berdasarkan backlog `docs/TASKS.md`:

| Fase | Ruang Lingkup | Status |
|---|---|---|
| 1 | Fondasi arsitektur, database, konfigurasi | Selesai |
| 2 | Autentikasi, sesi, RBAC | Selesai |
| 3 | Pelaporan dan pelacakan tiket | Selesai |
| 4 | Pipeline NLP dan Machine Learning | Sebagian selesai; dataset dan pelatihan belum selesai |
| 5 | Operasional Admin Sarpras | Selesai |
| 6 | Portal Teknisi | Selesai |
| 7 | Dashboard manajerial | Selesai |
| 8 | Pengujian, hardening, persiapan demo | Sebagian selesai |

Status fase mengikuti rincian task dan kriteria penyelesaian pada `docs/TASKS.md`. Fase yang ditandai selesai tidak berarti seluruh keputusan TBD atau pekerjaan lanjutan telah ditutup.

## 12. Dokumentasi Proyek

| Dokumen | Keterangan |
|---|---|
| [PRD.md](docs/PRD.md) | Kebutuhan produk dan FR-01 sampai FR-10 |
| [TECHSTACK.md](docs/TECHSTACK.md) | Arsitektur dan teknologi |
| [SECURITY.md](docs/SECURITY.md) | Kebijakan keamanan dan privasi |
| [DESIGN.md](docs/DESIGN.md) | Spesifikasi UI/UX dan design tokens |
| [TASKS.md](docs/TASKS.md) | Work Breakdown Structure dan backlog |
| [SKILLS.md](docs/SKILLS.md) | Katalog kapabilitas AI Coding Agent |
| [AGENTS.md](AGENTS.md) | Aturan kerja AI Coding Agent |

---

**KlasiFas — Sistem Klasifikasi Keluhan Fasilitas Kampus**  
Fakultas Teknologi Industri dan Informatika (FTII)  
Universitas Muhammadiyah Prof. Dr. HAMKA (UHAMKA)  
Kelompok 7 — Seminar Capstone Project