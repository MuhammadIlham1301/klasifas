# KlasiFas — Klasifikasi Keluhan Fasilitas Kampus

**Rancang Bangun Sistem Klasifikasi Keluhan dan Dasbor Pemantauan Fasilitas Kampus Menggunakan Algoritma Naive Bayes**

| Informasi | Keterangan |
|---|---|
| Institusi | Universitas Muhammadiyah Prof. Dr. HAMKA (UHAMKA) |
| Fakultas | Fakultas Teknologi Industri dan Informatika (FTII) |
| Kelompok | 7 |
| Anggota Tim | Egi Bayu Setiawan (2303045028)<br>Muhammad Adrian (2303045016)<br>Muhammad Ilham (2303045036) |
| Status Proyek | Persiapan spesifikasi dan fondasi dokumentasi (Fase 0) |
| Versi Dokumen | 0.1 — Draft (Menunggu Review Kelompok) |

---

## 1. Tentang Proyek

**KlasiFas** merupakan rancangan sistem informasi berbasis web untuk memfasilitasi proses pelaporan, klasifikasi otomatis, pemantauan, dan pengelolaan tindak lanjut keluhan fasilitas kampus.

Sistem dirancang untuk mengintegrasikan klasifikasi teks menggunakan algoritma **Multinomial Naive Bayes** dengan dasbor pemantauan (*dashboard*) interaktif. Keluhan yang disampaikan pelapor diproses menggunakan *Natural Language Processing* (NLP) untuk memperoleh rekomendasi kategori, yang selanjutnya diverifikasi oleh Admin Sarpras sebelum diteruskan kepada teknisi lapangan.

KlasiFas dikembangkan sebagai proyek akademik Capstone berupa *Minimum Viable Product* (MVP) atau prototipe lokal untuk lingkungan FTII UHAMKA.

### Tujuan Proyek

1. Menyediakan sarana pelaporan keluhan fasilitas kampus secara terstruktur dan mudah diakses.
2. Mengotomatisasi rekomendasi klasifikasi keluhan menggunakan NLP dan Naive Bayes.
3. Memudahkan Admin Sarpras dalam melakukan verifikasi kategori dan penugasan teknisi.
4. Memungkinkan pelapor memantau perkembangan penanganan keluhan secara mandiri dan aman.
5. Menyediakan dasbor visualisasi bagi pihak manajemen untuk memantau distribusi keluhan berdasarkan kategori, lokasi gedung/lantai, status, dan tren waktu.

## 2. Latar Belakang

Pengelolaan keluhan sarana dan prasarana kampus membutuhkan proses pencatatan, penelaahan, dan pemantauan yang terorganisasi. KlasiFas dirancang untuk membantu proses tersebut melalui satu sistem informasi terintegrasi:

- **Natural Language Processing dan Naive Bayes:** Membantu mempercepat pengelompokan awal laporan keluhan mahasiswa atau sivitas akademika ke kategori fasilitas yang relevan.
- **Portal kerja berbasis peran:** Memastikan alur kerja terstruktur mulai dari verifikasi Admin Sarpras hingga pelaksanaan tugas oleh teknisi lapangan.
- **Dasbor pemantauan manajerial:** Menyajikan ringkasan analitik kondisi fasilitas kampus bagi pimpinan tanpa membocorkan data pribadi pelapor.

## 3. Ruang Lingkup dan Fitur Utama

KlasiFas mencakup sepuluh kebutuhan fungsional utama (FR-01 sampai FR-10).

| ID | Fitur Utama | Deskripsi Ringkas |
|---|---|---|
| FR-01 | Pelaporan Keluhan | Pelapor mengirim deskripsi keluhan, lokasi gedung/lantai/ruang, kategori opsional, dan foto pendukung opsional. |
| FR-02 | Pelacakan Tiket | Pelapor memantau status dan riwayat tindak lanjut tiket menggunakan mekanisme kode referensi dan token rahasia. |
| FR-03 | Klasifikasi Otomatis | Sistem melakukan preprocessing teks bahasa Indonesia dan memprediksi rekomendasi kategori menggunakan Multinomial Naive Bayes. |
| FR-04 | Verifikasi Kategori | Admin Sarpras memverifikasi atau mengoreksi rekomendasi kategori sebelum tiket diproses lebih lanjut. |
| FR-05 | Penugasan Teknisi | Admin Sarpras menetapkan teknisi yang bertanggung jawab menangani keluhan sebagai atribut operasional. |
| FR-06 | Pembaruan Pengerjaan | Teknisi melihat daftar tugas yang ditugaskan kepadanya serta memperbarui status resmi dan catatan tindakan penyelesaian. |
| FR-07 | Dasbor Manajerial | Menyajikan agregasi statistik keluhan berdasarkan kategori, lokasi, status, dan periode waktu secara visual. |
| FR-08 | Pencarian dan Filter | Admin Sarpras mencari dan menyaring tiket operasional berdasarkan kombinasi kriteria. |
| FR-09 | Audit Log | Sistem mencatat riwayat perubahan kategori dan status resmi. |
| FR-10 | Fallback Manual | Sistem tetap menerima keluhan dengan status Baru dan menandai perlunya verifikasi manual apabila model ML tidak tersedia atau gagal melakukan inferensi. |

### 3.1 Kategori Keluhan Resmi

Sistem dirancang mengklasifikasikan keluhan ke dalam tujuh kategori fasilitas kampus:

1. **K1 —** Ruang kelas dan perabot
2. **K2 —** Laboratorium dan perangkat
3. **K3 —** Jaringan dan internet
4. **K4 —** Kebersihan dan sanitasi
5. **K5 —** Listrik, AC, dan penerangan
6. **K6 —** Keamanan, parkir, dan akses
7. **K7 —** Lainnya

### 3.2 Siklus Status Tiket Resmi

Siklus penanganan tiket menerapkan empat status resmi:

`Baru → Terverifikasi → Diproses → Selesai`

**Catatan:** Penugasan teknisi merupakan atribut penugasan operasional dan bukan status tiket terpisah.

### 3.3 Peran Pengguna (RBAC)

- **Pelapor (publik):** Mengirim formulir keluhan dan memantau progres tiket secara mandiri.
- **Admin Sarpras:** Memverifikasi kategori, menugaskan teknisi, mencari tiket operasional, melihat audit log, dan mengakses dasbor agregat.
- **Teknisi:** Melihat antrean tugas yang ditugaskan kepadanya dan memperbarui status pengerjaan beserta catatan tindakan lapangan.
- **Pimpinan/Kaprodi:** Memantau ringkasan dasbor secara *read-only* dengan filter dimensi agregat.

## 4. Arsitektur dan Teknologi

KlasiFas dirancang menggunakan arsitektur **Modular Monolith** berbasis Flask. Modul inferensi *Machine Learning* dijalankan secara *in-process* di lingkungan lokal.

| Komponen | Teknologi |
|---|---|
| Bahasa Pemrograman | Python 3.11 |
| Backend Framework | Flask |
| Arsitektur | Modular Monolith dan Application Factory |
| Basis Data | PostgreSQL |
| Database ORM | SQLAlchemy 2.0 |
| Migrasi Database | Alembic / Flask-Migrate |
| UI dan Styling | HTML5, CSS3, Bootstrap 5 |
| Template Engine | Jinja2 |
| Visualisasi Dasbor | Chart.js 4.4.x |
| Machine Learning | scikit-learn |
| Algoritma | Multinomial Naive Bayes dan TF-IDF Vectorizer |
| NLP Bahasa Indonesia | PySastrawi |
| Manipulasi Data ML | pandas dan NumPy |
| Serialisasi Model | joblib |
| Keamanan Password | Werkzeug scrypt |
| Proteksi CSRF | Flask-WTF |
| Test Runner | pytest |
| Version Control | Git dan GitHub |

Detail konfigurasi dan batasan teknis mengikuti [docs/TECHSTACK.md](docs/TECHSTACK.md).

## 5. Struktur Direktori Proyek

### 5.1 Struktur Workspace Saat Ini (Fase 0 — Dokumentasi)

Saat ini repositori berada pada tahap persiapan spesifikasi teknis dan fondasi tata kelola kerja.

```text
Klasifas/
├── README.md             # Gambaran umum, panduan repositori, dan indeks proyek
├── AGENTS.md             # Instruksi dan aturan kerja AI Coding Agent
└── docs/
    ├── PRD.md            # Product Requirements Document (v1.3)
    ├── TECHSTACK.md      # Spesifikasi arsitektur dan teknologi (v1.3)
    ├── SECURITY.md       # Kebijakan keamanan aplikasi (v1.0)
    ├── DESIGN.md         # Spesifikasi UI/UX dan desain sistem (v1.0)
    ├── TASKS.md          # Implementation Backlog modular 8 fase (v0.1)
    └── SKILLS.md         # Katalog kapabilitas teknis AI Coding Agent
```

### 5.2 Rencana Struktur Implementasi Aplikasi

Struktur berikut merupakan rancangan arsitektur modular yang akan diimplementasikan secara bertahap mulai Fase 1. Struktur dan nama file final mengikuti kebutuhan implementasi serta keputusan teknis yang disetujui.

```text
Klasifas/
├── app/
│   ├── __init__.py           # Application Factory (create_app)
│   ├── config.py             # Konfigurasi environment
│   ├── auth/                 # Autentikasi staf dan session management
│   ├── admin/                # Operasional Sarpras, verifikasi, dan audit
│   ├── reporter/             # Pelaporan dan pelacakan publik
│   ├── technician/           # Antrean dan pembaruan status teknisi
│   ├── dashboard/            # Dasbor analitik manajerial
│   ├── ml/                   # Pipeline NLP dan Naive Bayes
│   ├── models/               # Model database
│   ├── services/             # Logika bisnis dan layanan aplikasi
│   ├── templates/            # Template antarmuka Jinja2
│   └── static/               # Aset CSS dan JavaScript
├── docs/                     # Dokumentasi proyek
├── tests/                    # Pengujian otomatis
├── migrations/               # Migrasi skema database
├── instance/                 # Konfigurasi lokal instance
├── uploads/                  # Penyimpanan foto keluhan non-publik
├── .env.example              # Template variabel lingkungan
├── .gitignore                # Aturan pengecualian Git
├── requirements.txt          # Dependensi Python
├── wsgi.py                   # Entrypoint aplikasi (rencana)
├── AGENTS.md                 # Aturan kerja AI Coding Agent
└── README.md                 # Dokumentasi utama repositori
```

**Catatan:** Struktur di atas merupakan rancangan, bukan kondisi aktual atau struktur final yang sudah dikunci.

## 6. Persyaratan Sistem dan Lingkungan

Persyaratan teknologi yang direncanakan untuk pengembangan lokal:

- Python 3.11.
- PostgreSQL.
- pip sebagai manajer paket Python.
- Virtual environment (`venv`).
- Git untuk pengelolaan versi kode.
- Browser web modern seperti Google Chrome, Mozilla Firefox, atau Microsoft Edge.

Versi detail database dan dependensi mengikuti spesifikasi final [docs/TECHSTACK.md](docs/TECHSTACK.md).

## 7. Panduan Instalasi dan Konfigurasi

> [!WARNING]
> **Status: Belum Dapat Dijalankan — Tahap Implementasi Belum Dimulai**
>
> Kode aplikasi, dependensi, dan skema database belum tersedia di repositori. Urutan instruksi di bawah ini merupakan panduan rencana teknis yang akan dilengkapi setelah Fase 1 implementasi backlog diselesaikan.

Urutan instalasi yang direncanakan:

1. Clone repositori setelah alamat repositori resmi tersedia.
2. Buat dan aktifkan virtual environment Python 3.11.
3. Instal dependensi setelah `requirements.txt` tersedia.
4. Salin `.env.example` menjadi `.env`, kemudian lengkapi konfigurasi yang diperlukan.
5. Konfigurasikan koneksi PostgreSQL.
6. Jalankan migrasi database setelah konfigurasi aplikasi dan migrasi tersedia.
7. Siapkan akun staf melalui mekanisme provisioning yang telah disetujui kelompok.

Contoh perintah berikut merupakan gambaran persiapan environment pada Windows PowerShell, bukan prosedur instalasi aplikasi yang sudah dapat dijalankan:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Perintah instalasi dependensi, migrasi, dan provisioning akan ditambahkan setelah implementasinya tersedia dan diverifikasi.

### 7.1 Provisioning Akun Staf (CLI)

Akun staf (`admin_sarpras`, `teknisi`, `pimpinan`) dibuat melalui perintah CLI lokal, bukan melalui halaman pengelolaan akun. Referensi aturan: `docs/SECURITY.md` §4.4.

```powershell
$env:FLASK_APP = "app"
$env:FLASK_CONFIG = "development"

python -m flask create-staff `
  --username nama.staf `
  --role admin_sarpras `
  --full-name "Nama Lengkap Staf"
```

Ketentuan yang berlaku:

- Password **tidak** dapat diberikan sebagai argumen. Perintah menampilkan prompt tersembunyi dan meminta konfirmasi ulang.
- Panjang password minimal 12 karakter. Password tidak boleh sama dengan username.
- Username wajib huruf kecil dengan format `^[a-z0-9._-]{3,64}$`; input huruf besar otomatis dinormalisasi ke huruf kecil.
- Role yang diterima hanya `admin_sarpras`, `teknisi`, dan `pimpinan`.
- Username duplikat ditolak dan perintah keluar dengan status non-zero.
- Perintah hanya menampilkan `Akun staf dibuat: <username> (role=<role>)`. Password maupun hash tidak pernah dicetak atau dicatat ke log.
- Tidak ada akun default yang dibuat otomatis saat aplikasi start, migrasi, atau impor modul.

Verifikasi cepat setelah pembuatan akun: masuk melalui `/auth/login` dengan akun tersebut.


## 8. Panduan Menjalankan Aplikasi dan Pengujian

> [!WARNING]
> **Status: Belum Tersedia — Tahap Implementasi Belum Dimulai**
>
> Server aplikasi dan pengujian belum dapat dijalankan karena kode sumber belum ditulis.

Setelah modul aplikasi tersedia, bagian ini akan dilengkapi dengan:

- Cara menjalankan server pengembangan Flask secara lokal.
- Konfigurasi database untuk lingkungan pengembangan.
- Cara menjalankan pengujian otomatis menggunakan pytest.
- Penggunaan database PostgreSQL khusus pengujian (`klasifas_test_db`).
- Verifikasi hasil pengujian dan skenario demonstrasi MVP.

Kriteria kesiapan pengujian adalah seluruh skenario pengujian yang telah didefinisikan lulus dengan **100% test pass rate (0 errors dan 0 failures)**. Angka tersebut bukan target code coverage 100%.

## 9. Keamanan dan Batasan Sistem

### 9.1 Ketentuan Keamanan Utama

KlasiFas dirancang dengan mengutamakan prinsip keamanan defensif:

- **Penyimpanan password:** Password staf internal di-hash menggunakan Werkzeug scrypt. Password tidak disimpan dalam bentuk teks biasa.
- **Keamanan token tiket:** Token pelacakan dibuat menggunakan nilai acak kriptografis 128-bit. Hanya hash SHA-256 token yang disimpan pada database. Verifikasi token menggunakan `hmac.compare_digest()`.
- **Larangan kebocoran token:** Token akses rahasia tidak boleh disematkan pada URL, query parameter, atau log server.
- **Otorisasi ketat (RBAC):** Menerapkan prinsip deny-by-default pada endpoint internal melalui pemeriksaan server-side.
- **Proteksi form:** Formulir perubahan data wajib memvalidasi token CSRF.
- **Sanitasi file unggahan:** Validasi foto mencakup ekstensi, MIME type, magic number, dan validitas gambar. File disimpan menggunakan nama acak pada lokasi non-publik.
- **Keamanan model ML:** Artefak serialisasi `.joblib` hanya dimuat secara lokal dari lokasi internal tepercaya.
- **Perlindungan data pribadi (PII):** Dasbor manajerial hanya menyajikan data agregat tanpa membuka identitas personal pelapor.

Pedoman keamanan lengkap merujuk pada [docs/SECURITY.md](docs/SECURITY.md).

### 9.2 Batasan Ruang Lingkup MVP (Out of Scope)

Fitur-fitur berikut berada di luar cakupan MVP:

- Registrasi publik mandiri dan pemulihan password (*Forgot Password*).
- Aplikasi mobile native (Android APK / iOS).
- Integrasi ke SIAKAD, Single Sign-On (SSO), atau API eksternal kampus.
- Klasifikasi citra (*computer vision*) terhadap foto fasilitas.
- Analisis sentimen atau NLP multibahasa di luar Bahasa Indonesia.
- Pengiriman notifikasi melalui SMS/WhatsApp gateway berbayar.
- Penjadwalan teknisi otomatis atau pengelolaan inventaris dan penggajian.
- Deployment cloud publik berskala produksi.

## 10. Status Pengembangan (Roadmap Backlog)

Proyek saat ini berada pada **Fase 0 — Persiapan Spesifikasi dan Fondasi Dokumentasi**. Pengerjaan kode aplikasi akan dilakukan secara modular mengikuti delapan fase pada [docs/TASKS.md](docs/TASKS.md).

- [ ] **Fase 1:** Fondasi Arsitektur, Basis Data, dan Konfigurasi (TSK-F1-01 s.d. F1-05)
- [ ] **Fase 2:** Autentikasi Staf, Keamanan Sesi, dan Otorisasi RBAC (TSK-F2-01 s.d. F2-04)
- [ ] **Fase 3:** Pelaporan Keluhan dan Pelacakan Mandiri Publik (TSK-F3-01 s.d. F3-05)
- [ ] **Fase 4:** Pipeline Natural Language Processing dan Machine Learning (TSK-F4-01 s.d. F4-05)
- [ ] **Fase 5:** Portal Operasional Sarpras — Verifikasi dan Penugasan (TSK-F5-01 s.d. F5-05)
- [ ] **Fase 6:** Portal Lapangan Teknisi dan Pembaruan Status (TSK-F6-01 s.d. F6-03)
- [ ] **Fase 7:** Dasbor Pemantauan Manajerial dan Visualisasi Chart.js (TSK-F7-01 s.d. F7-04)
- [ ] **Fase 8:** Pengujian Sistem, Hardening Keamanan, dan Persiapan Demo (TSK-F8-01 s.d. F8-04)

## 11. Indeks Dokumentasi Proyek

Seluruh rincian perancangan sistem KlasiFas didokumentasikan pada berkas berikut:

| Dokumen | Deskripsi | Tautan |
|---|---|---|
| PRD.md | Tujuan produk, use case, dan kebutuhan FR-01 sampai FR-10. | [docs/PRD.md](docs/PRD.md) |
| TECHSTACK.md | Spesifikasi teknis, arsitektur, stack teknologi, dan konvensi. | [docs/TECHSTACK.md](docs/TECHSTACK.md) |
| SECURITY.md | Kebijakan keamanan data, autentikasi, dan batasan teknis. | [docs/SECURITY.md](docs/SECURITY.md) |
| DESIGN.md | Spesifikasi UI/UX, tata letak layar, dan design tokens. | [docs/DESIGN.md](docs/DESIGN.md) |
| TASKS.md | Work Breakdown Structure dan backlog 35 tugas dalam 8 fase implementasi. | [docs/TASKS.md](docs/TASKS.md) |
| SKILLS.md | Katalog kapabilitas teknis AI Coding Agent. | [docs/SKILLS.md](docs/SKILLS.md) |
| AGENTS.md | Aturan kerja operasional AI Coding Agent. | [AGENTS.md](AGENTS.md) |

---

**KlasiFas — Sistem Klasifikasi Keluhan Fasilitas Kampus**  
Fakultas Teknologi Industri dan Informatika (FTII)  
Universitas Muhammadiyah Prof. Dr. HAMKA (UHAMKA)  
Kelompok 7 — Seminar Capstone Project

**Status dokumen:** Draft v0.1 — Menunggu Review Kelompok.
