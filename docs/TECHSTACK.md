# Tech Stack & Architectural Specification
# KlasiFas — Klasifikasi Keluhan Fasilitas Kampus

**Judul Proyek:** Rancang Bangun Sistem Klasifikasi Keluhan dan Dasbor Pemantauan Fasilitas Kampus Menggunakan Algoritma Naive Bayes  
**Institusi:** Universitas Muhammadiyah Prof. Dr. HAMKA (UHAMKA)  
**Fakultas:** Fakultas Teknologi Industri dan Informatika (FTII)  
**Kelompok:** 7  
**Status Dokumen:** Revisi Verifikasi Implementasi (v1.4)
**Dokumen Acuan:** `docs/PRD.md`, `docs/SECURITY.md`, `README.md`, dan verifikasi source code aktual

---

## 1. Arsitektur Sistem Global

KlasiFas diimplementasikan sebagai **Modular Monolith** berbasis Flask dengan **Application Factory** (`app/__init__.py`). Seluruh komponen aplikasi berjalan dalam satu proses:

- Rute HTTP berbasis blueprint.
- Logika bisnis pada lapisan service.
- Model relasional SQLAlchemy.
- Pemrosesan teks dan inferensi ML in-process.
- Penyimpanan foto pada filesystem lokal non-publik.

```
+-----------------------------------------------------------------------+
|                           CLIENT TIER                                 |
|  Browser Desktop/Mobile: HTML5, CSS3, Jinja2, Bootstrap 5,            |
|  Bootstrap Icons, Chart.js, dan Vanilla JavaScript                    |
+-----------------------------------▲-----------------------------------+
                                    │ HTTP/HTTPS
+-----------------------------------▼-----------------------------------+
|                       APPLICATION SERVER TIER                         |
|  Flask Application Factory (app/__init__.py)                          |
|  Development server: Flask CLI                                        |
|  Production WSGI server belum dikunci di requirements.txt             |
|                                                                       |
|  [Presentation Layer - app/routes/]                                   |
|   ├── report.py    : "/", "/lapor", "/lapor/sukses", "/lacak"         |
|   ├── auth.py      : "/auth/login", "/auth/logout",                   |
|   |                  "/auth/pelapor/login", "/auth/pelapor/logout"     |
|   ├── admin.py     : "/admin/tiket", verifikasi, penugasan, foto,      |
|   |                  "/admin/audit-log"                               |
|   ├── technician.py: "/teknisi/tiket", detail, foto, update status    |
|   └── dashboard.py : "/dashboard", "/dashboard/api/chart-data"        |
|                                                                       |
|  [Business Logic & Service Layer - app/services/]                     |
|   ├── ticket_report.py        : validasi form & pembuatan tiket       |
|   ├── ticket_tracking.py      : sanitasi data pelacakan publik        |
|   ├── ticket_photo.py         : validasi, simpan, hapus foto         |
|   ├── complaint_service.py    : transisi status, filter, penugasan    |
|   ├── audit_service.py        : audit trail                           |
|   ├── classification_service.py: inferensi ML & fallback FR-10        |
|   └── dashboard_service.py    : agregasi dashboard FR-07              |
|                                                                       |
|  [In-Process ML & NLP - app/ml/]                                      |
|   ├── preprocessor.py : case folding, cleaning, slang, stopword,      |
|   |                     stemming PySastrawi                           |
|   ├── dictionary.py   : kamus normalisasi slang/singkatan             |
|   └── classifier.py   : load .joblib, TF-IDF, MultinomialNB           |
+-----------------------------------▲-----------------------------------+
                                    │ SQLAlchemy 2.0 / parameter binding
+-----------------------------------▼-----------------------------------+
|                            DATA TIER                                  |
|  - PostgreSQL melalui psycopg2-binary                                 |
|  - Tabel: users, categories, tickets, audit_logs                      |
|  - Filesystem lokal: uploads/ (foto, non-publik)                      |
|  - Artefak .joblib: app/ml/models/ (belum tersedia saat ini)          |
+-----------------------------------------------------------------------+
```

### Karakteristik Arsitektur Utama

1. **In-Process Inference:** artefak model dimuat dan dipakai langsung di proses Flask. `app/ml/classifier.py` menyediakan cache model thread-safe dan validasi jalur file.
2. **Layered Separation of Concerns:** pemisahan rute (`app/routes/`), service (`app/services/`), model (`app/models/`), ML (`app/ml/`), dan utilitas (`app/utils/`).
3. **Graceful Fallback (FR-10):** bila artefak model tidak tersedia atau inferensi gagal, tiket tetap dibuat dengan `needs_manual_verification = True`.
4. **Tidak ada `run.py`:** aplikasi dijalankan melalui Flask CLI, misalnya `flask --app "app:create_app('development')" run`.
5. **Tidak ada folder `scripts/`:** skrip pelatihan/evaluasi belum tersedia di repositori.

---

## 2. Pemetaan Komponen Teknologi

| Komponen Sistem | Teknologi | Rentang Versi di `requirements.txt` | Peran |
| :--- | :--- | :--- | :--- |
| Language Runtime | Python | 3.11 (lingkungan proyek) | Backend web dan NLP/ML. |
| Backend Framework | Flask | `>=3.0.0,<4.0.0` | Application factory dan blueprint. |
| Environment Loader | python-dotenv | `>=1.0.0,<2.0.0` | Memuat `.env`. |
| Relational Database | PostgreSQL | Tidak dipin di requirements | Basis data utama. |
| Database Driver | psycopg2-binary | `>=2.9.9,<3.0.0` | Driver PostgreSQL. |
| ORM | SQLAlchemy | `>=2.0.0,<3.0.0` | ORM dan query parameter binding. |
| Flask ORM Integration | Flask-SQLAlchemy | `>=3.1.1,<4.0.0` | Integrasi SQLAlchemy dengan Flask. |
| Migrations | Flask-Migrate / Alembic | `>=4.0.5,<5.0.0` | Migrasi skema. |
| Form Security | Flask-WTF | `>=1.2.1,<2.0.0` | Proteksi CSRF. |
| Image Validation | Pillow | `>=10.0.0,<12.0.0` | Validasi, decode, dan re-encode foto. |
| ML Classifier | scikit-learn | `>=1.3.0,<2.0.0` | `TfidfVectorizer` dan `MultinomialNB`. |
| NLP Stemmer/Stopword | PySastrawi | `>=1.2.0,<2.0.0` | Stemming dan stopword Bahasa Indonesia. |
| Data Processing | pandas, numpy | `>=2.1.0,<3.0.0`, `>=1.26.0,<2.0.0` | Pengolahan data dan komputasi model. |
| Model Persistence | joblib | `>=1.3.0,<2.0.0` | Serialisasi artefak model. |
| Testing | pytest | `>=7.4.0,<8.0.0` | Pengujian otomatis. |
| Password Hashing | Werkzeug Security | Dependensi transitif Flask | Hash password `scrypt`. |
| UI Framework | Bootstrap 5 | Aset vendor lokal | Layout dan komponen UI. |
| UI Icons | Bootstrap Icons | Aset vendor lokal | Ikon antarmuka. |
| Dashboard Charts | Chart.js | Aset vendor lokal | Grafik dashboard. |
| Frontend Scripting | Vanilla JavaScript | `app/static/js/` | Interaksi portal dan dashboard. |
| Font | Public Sans | Aset lokal `app/static/fonts/public-sans/` | Tipografi antarmuka. |
| Version Control | Git | Standar | Riwayat revisi. |

Catatan:

- Versi di `requirements.txt` adalah rentang yang diizinkan, bukan hasil `pip freeze`.
- `pytest-cov` dan `flake8` tidak tercantum pada `requirements.txt` saat ini.
- Bootstrap, Bootstrap Icons, dan Chart.js disajikan dari `app/static/vendor/`, bukan CDN.
- Server WSGI produksi (Gunicorn/Waitress) belum ditambahkan sebagai dependensi.

---

## 3. Spesifikasi Modul Backend & Interaksi Data

### 3.1 Arsitektur Modul Rute Aktual (`app/routes/`)

Tidak ada `app/routes/main.py` atau `app/routes/complaints.py`. Rute publik berada di `report.py`.

#### `app/routes/report.py` (FR-01, FR-02)

| Method | Path | Fungsi |
| :--- | :--- | :--- |
| GET | `/` | Redirect ke login pelapor `/auth/pelapor/login`. |
| GET, POST | `/lapor` | Formulir dan penyimpanan laporan. |
| GET | `/lapor/sukses` | Redirect kembali ke formulir pelaporan. |
| GET, POST | `/lacak` | Pelacakan tiket dengan kode dan token akses. |

Endpoint `/lacak` menerapkan rate limiter pada seluruh percobaan `POST`, termasuk input tidak valid.

#### `app/routes/auth.py` (FR-02)

| Method | Path | Fungsi |
| :--- | :--- | :--- |
| GET, POST | `/auth/login` | Login staf internal. |
| POST | `/auth/logout` | Logout staf; dilindungi `login_required`. |
| GET, POST | `/auth/pelapor/login` | Login pelapor; sesi terpisah dari staf. |
| POST | `/auth/pelapor/logout` | Logout pelapor; dilindungi `reporter_required`. |

Blueprint memuat ulang pengguna staf dan pelapor dari session terpisah pada setiap request melalui hook `before_app_request`. Role aktif diambil dari database, bukan hanya dari session. Login staf dan pelapor memakai rate limiter 5 percobaan per 5 menit per kombinasi akun dan alamat IP, ditambah batas 50 percobaan per 5 menit per alamat IP, dengan bucket staf dan pelapor terpisah.

#### `app/routes/admin.py` (FR-04, FR-05, FR-08, FR-09)

| Method | Path | Fungsi |
| :--- | :--- | :--- |
| GET | `/admin/tiket` | Antrean tiket, pencarian, filter, dan paginasi. Filter merupakan query parameter pada endpoint ini. |
| GET, POST | `/admin/tiket/<int:ticket_id>/verifikasi` | Form dan proses verifikasi/koreksi kategori. |
| POST | `/admin/tiket/<int:ticket_id>/penugasan` | Penugasan atau penugasan ulang teknisi. |
| GET | `/admin/tiket/<int:ticket_id>/foto` | Penyajian foto bukti secara terautentikasi. |
| GET | `/admin/audit-log` | Daftar audit log dengan filter dan paginasi. |

Tidak ada endpoint `/admin/filter` dan `/admin/tiket/<id>/assign` pada implementasi aktual.

#### `app/routes/technician.py` (FR-06)

| Method | Path | Fungsi |
| :--- | :--- | :--- |
| GET | `/teknisi/tiket` | Papan tugas teknisi yang sedang login. |
| GET | `/teknisi/tiket/<int:ticket_id>` | Detail tiket milik teknisi login. |
| GET | `/teknisi/tiket/<int:ticket_id>/foto` | Foto bukti tiket milik teknisi login. |
| POST | `/teknisi/tiket/<int:ticket_id>/status` | Pembaruan status dan catatan perbaikan. |

Akses tiket dibatasi pada `assigned_technician_id` milik teknisi login. Tiket milik teknisi lain menghasilkan 404.

#### `app/routes/dashboard.py` (FR-07, FR-08)

| Method | Path | Fungsi |
| :--- | :--- | :--- |
| GET | `/dashboard`, `/dashboard/` | Halaman dashboard untuk `admin_sarpras` dan `pimpinan`. |
| GET | `/dashboard/api/chart-data` | Payload JSON agregat untuk Chart.js. |

Dashboard bersifat read-only dan tidak memuat PII pelapor.

#### Rute dan Handler Tingkat Aplikasi

- `GET /favicon.ico` mengembalikan redirect 308 ke `static/favicon.svg`.
- Handler error kustom tersedia untuk 403, 404, dan 500 di `app/utils/error_handlers.py`.
- Header keamanan dipasang pada setiap respons melalui `after_request`.

### 3.2 Alur Transisi Status Resmi Tiket

Status resmi tetap empat:

$$\mathbf{Baru} \longrightarrow \mathbf{Terverifikasi} \longrightarrow \mathbf{Diproses} \longrightarrow \mathbf{Selesai}$$

Aturan implementasi pada `app/services/complaint_service.py`:

- `Baru` → `Terverifikasi`: hanya `admin_sarpras`.
- `Terverifikasi` → `Diproses`: `teknisi` atau `admin_sarpras`.
- `Diproses` → `Selesai`: `teknisi` atau `admin_sarpras`.
- `Selesai` tidak memiliki transisi keluar.
- Teknisi hanya dapat mengubah tiket yang ditugaskan kepadanya.
- Transisi ke `Selesai` mewajibkan catatan tindakan perbaikan.
- Transisi no-op mengembalikan status tanpa mutasi dan tanpa audit log baru.
- Penugasan teknisi adalah atribut `assigned_technician_id`, bukan status tiket.

### 3.3 Flag "Perlu Verifikasi Manual"

Jika model tidak tersedia, preprocessing gagal, tidak ada token valid, inferensi gagal, kategori hasil prediksi tidak ditemukan, atau skor keyakinan di bawah `ML_CONFIDENCE_THRESHOLD`:

- Status tiket tetap `Baru`.
- `needs_manual_verification` diset `True`.
- Tiket tetap disimpan dan masuk antrean verifikasi Admin Sarpras.

Flag ini adalah penanda proses, bukan status tiket tambahan.

### 3.4 Keamanan Kueri Basis Data

- Seluruh akses data menggunakan SQLAlchemy ORM dan parameter binding.
- Tidak ada penyusunan SQL dari input pengguna.
- Paginasi menggunakan `db.paginate`.
- Relasi many-to-one dimuat dengan `joinedload` pada beberapa query untuk menghindari N+1.

### 3.5 Format Kode Tiket dan Token Pelacakan

- Kode tiket: `KF-` diikuti 6 karakter dari alfabet `23456789ABCDEFGHJKLMNPQRSTUVWXYZ`.
- Panjang total 9 karakter termasuk tanda hubung.
- Pola database dan validasi pelacakan: `^KF-[23456789A-HJ-NP-Z]{6}$`.
- Token akses dibuat dengan `secrets.token_urlsafe(16)` (128 bit).
- Yang disimpan di database hanya hash SHA-256 token (`access_token_hash`), bukan token asli.
- Verifikasi token menggunakan `hmac.compare_digest`.
- Respons pelacakan yang gagal selalu generik (404) untuk mengurangi enumerasi.
- Endpoint `POST /lacak` dilindungi rate limiter.

### 3.6 Modul Service Aktual (`app/services/`)

| Modul | Tanggung Jawab |
| :--- | :--- |
| `ticket_report.py` | Validasi form laporan, validasi kategori aktif, pembuatan kode/token, pembuatan tiket, klasifikasi awal. |
| `ticket_tracking.py` | Validasi kode/token pelacakan dan sanitasi data publik. |
| `ticket_photo.py` | Validasi ekstensi, MIME, magic number, dimensi, decode/re-encode, penyimpanan nama acak, penghapusan file. |
| `complaint_service.py` | State machine status, verifikasi kategori, penugasan teknisi, filter admin, query teknisi, penyajian foto terautentikasi. |
| `audit_service.py` | Sanitasi catatan audit, pencatatan perubahan kategori/status/penugasan, query audit log terpaginasi. |
| `classification_service.py` | Orkestrasi preprocessing, pemuatan model, inferensi, threshold, dan fallback FR-10. |
| `dashboard_service.py` | Agregasi KPI, distribusi kategori, tren waktu, distribusi lokasi, dan payload Chart.js. |

Catatan audit: `VALID_AUDIT_ACTIONS` pada `audit_service.py` mencakup `category_changed`, `status_changed`, dan `technician_assigned`. Konstanta `AUDIT_ACTIONS` pada `app/models/audit_log.py` masih mencantumkan dua aksi dan memiliki komentar bahwa penugasan teknisi belum diputuskan.

### 3.7 Modul Utilitas Aktual (`app/utils/`)

| Modul | Tanggung Jawab |
| :--- | :--- |
| `decorators.py` | `STAFF_ROLES`, `login_required`, `role_required`. |
| `error_handlers.py` | Halaman error 403, 404, 500. |
| `password.py` | Hash dan verifikasi password dengan Werkzeug `scrypt`. |
| `rate_limiter.py` | Sliding-window rate limiter in-memory. |
| `security_headers.py` | Header keamanan respons; tidak termasuk HSTS. |
| `ticket_identity.py` | Generator kode tiket, token akses, hash SHA-256, dan verifikasi constant-time. |

---

## 4. Pipeline Machine Learning & Pengolahan Teks (FR-03)

### 4.1 Tahapan Pra-pemrosesan Aktual

Implementasi berada di `app/ml/preprocessor.py` dengan kamus slang di `app/ml/dictionary.py`.

```
Teks Keluhan Mentah
        │
        ▼
[1. Case Folding]
        │
        ▼
[2. Penghapusan URL]
        │
        ▼
[3. Normalisasi Slang/Singkatan]  ← app/ml/dictionary.py
        │
        ▼
[4. Regex Cleaning]
   Menghapus karakter non-huruf, termasuk angka, dari teks deskripsi.
        │
        ▼
[5. Stopword Removal]             ← PySastrawi
        │
        ▼
[6. Stemming Nazief-Adriani]      ← PySastrawi
        │
        ▼
[TF-IDF Vectorizer]               → vectorizer.joblib (diharapkan)
        │
        ▼
[Multinomial Naive Bayes]         → model.joblib (diharapkan)
        │
        ├── Kode kategori prediksi K1–K7
        └── Confidence score
```

Pembersihan angka hanya berlaku pada teks deskripsi yang dipakai untuk fitur NLP. Nilai numerik lokasi (gedung, lantai, ruang) tidak diubah oleh preprocessor.

### 4.2 Siklus Hidup Artefak Model

1. **Pelatihan dan evaluasi: rencana, belum tersedia.**
   - Tidak ada folder `scripts/`.
   - Tidak ada `train_model.py`, `evaluate_model.py`, dataset, atau artefak model di repositori.
   - Pelatihan dan evaluasi offline masih perlu diselesaikan sebelum model dapat dipakai.
   - Target metrik dan target jumlah dataset bukan hasil aktual.

2. **Lokasi artefak yang diharapkan:**
   - `app/ml/models/model.joblib`
   - `app/ml/models/vectorizer.joblib`
   - Direktori `app/ml/models/` belum ada saat ini.
   - File `*.joblib` masuk `.gitignore`.

3. **Pemuatan artefak:**
   - `app/ml/classifier.py` memvalidasi bahwa path model berada di dalam direktori model yang diizinkan.
   - Model dan vectorizer di-cache di memori secara thread-safe.
   - Aplikasi hanya boleh memuat `.joblib` dari lokasi internal tepercaya.
   - Jika artefak tidak tersedia, `ModelNotAvailableError` ditangani sebagai fallback manual.

4. **Inferensi:**
   - `predict_category()` memanggil `vectorizer.transform()` dan `model.predict_proba()`.
   - Kategori dengan probabilitas tertinggi dipakai sebagai rekomendasi.
   - `ML_CONFIDENCE_THRESHOLD` default `0.60` masih placeholder.

---

## 5. Struktur Direktori Proyek Aktual

```text
Klasifas/
├── app/                                  # Paket utama Flask
│   ├── __init__.py                       # Application Factory & registrasi blueprint
│   ├── cli.py                            # Perintah CLI create-staff, create-reporter
│   ├── config.py                         # Kelas konfigurasi & validasi environment
│   ├── extensions.py                     # db, migrate, csrf
│   ├── models/                           # Model SQLAlchemy
│   │   ├── __init__.py
│   │   ├── base.py                       # Declarative base & naming convention
│   │   ├── user.py                       # User & role RBAC
│   │   ├── category.py                   # Kategori K1–K7
│   │   ├── ticket.py                     # Tiket keluhan
│   │   └── audit_log.py                  # Audit log
│   ├── routes/                           # Blueprint HTTP
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── report.py                     # Rute publik /, /lapor, /lacak
│   │   ├── admin.py
│   │   ├── technician.py
│   │   └── dashboard.py
│   ├── services/                         # Logika bisnis
│   │   ├── __init__.py
│   │   ├── audit_service.py
│   │   ├── classification_service.py
│   │   ├── complaint_service.py
│   │   ├── dashboard_service.py
│   │   ├── ticket_photo.py
│   │   ├── ticket_report.py
│   │   └── ticket_tracking.py
│   ├── ml/                               # NLP & ML in-process
│   │   ├── __init__.py
│   │   ├── classifier.py
│   │   ├── dictionary.py
│   │   └── preprocessor.py
│   │   # app/ml/models/ belum ada; dibuat saat artefak model tersedia
│   ├── static/                           # Aset statis
│   │   ├── css/
│   │   │   └── klasifas.css
│   │   ├── favicon.svg
│   │   ├── fonts/
│   │   │   └── public-sans/
│   │   │       ├── OFL.txt
│   │   │       ├── PublicSans-Bold.woff2
│   │   │       ├── PublicSans-Medium.woff2
│   │   │       ├── PublicSans-Regular.woff2
│   │   │       └── PublicSans-SemiBold.woff2
│   │   ├── js/
│   │   │   ├── dashboard.js
│   │   │   └── portal.js
│   │   └── vendor/
│   │       ├── bootstrap/
│   │       ├── bootstrap-icons/
│   │       └── chartjs/
│   ├── templates/                        # Template Jinja2
│   │   ├── base.html
│   │   ├── components/
│   │   │   ├── _code_box.html
│   │   │   └── _macros.html
│   │   ├── errors/
│   │   │   └── error.html
│   │   ├── report/
│   │   │   ├── form.html
│   │   │   ├── success.html
│   │   │   └── track.html
│   │   ├── auth/
│   │   │   └── login.html
│   │   ├── admin/
│   │   │   ├── audit_log.html
│   │   │   ├── queue.html
│   │   │   └── verify.html
│   │   ├── technician/
│   │   │   ├── detail.html
│   │   │   └── queue.html
│   │   └── dashboard/
│   │       └── index.html
│   └── utils/
│       ├── __init__.py
│       ├── decorators.py
│       ├── error_handlers.py
│       ├── password.py
│       ├── rate_limiter.py
│       ├── security_headers.py
│       └── ticket_identity.py
├── docs/
│   ├── DESIGN.md
│   ├── PRD.md
│   ├── SECURITY.md
│   ├── SKILLS.md
│   ├── TASKS.md
│   ├── TECHSTACK.md
│   └── ui-ux-reference/
├── migrations/                           # Flask-Migrate / Alembic
│   ├── alembic.ini
│   ├── env.py
│   ├── README
│   ├── script.py.mako
│   └── versions/
│       ├── 0001_initial_schema.py
│       └── 0002_seed_categories.py
├── tests/                                # 34 file pengujian pytest
├── uploads/                              # Foto bukti; gitignored
├── .env.example                          # Template environment
├── .gitignore
├── AGENTS.md
├── README.md
├── requirements.txt
└── test-results.txt                      # Artefak baseline pytest lokal
```

Catatan struktur:

- Tidak ada folder `scripts/`.
- Tidak ada `run.py`.
- Tidak ada `app/templates/public/`, `app/templates/complaints/`, atau `app/static/img/` seperti pada rancangan lama.
- Nama file aktual adalah `report.py`, `klasifas.css`, `portal.js`, dan `favicon.svg`.

### 5.1 Provisioning Akun Staf dan Pelapor (CLI)

Akun staf dan pelapor dibuat melalui Flask CLI, bukan halaman registrasi publik:

```powershell
flask --app "app:create_app('development')" create-staff --username <username> --role <role> --full-name "<nama>"
flask --app "app:create_app('development')" create-reporter --username <username> --full-name "<nama>"
```

Ketentuan implementasi `app/cli.py`:

- Perintah didaftarkan melalui `register_cli(app)` di `create_app()`.
- Username dinormalisasi ke huruf kecil dan divalidasi dengan pola `^[a-z0-9._-]{3,64}$`.
- Role staf yang diterima `create-staff`: `admin_sarpras`, `teknisi`, `pimpinan`.
- `create-reporter` hanya membuat role `reporter`.
- Password dimasukkan melalui prompt tersembunyi dengan konfirmasi.
- Password minimal 12 karakter dan tidak boleh sama dengan username.
- Password tidak pernah menjadi argumen CLI dan tidak dicetak.
- Hash password menggunakan `app/utils/password.py` dengan Werkzeug `scrypt`.
- Perintah hanya membuat akun; reset password, penonaktifan, dan perubahan role belum tersedia.
- Tidak ada akun default yang dibuat otomatis.

---

## 6. Spesifikasi Dependensi (`requirements.txt`)

Isi aktual `requirements.txt`:

```text
# --- Web Framework & Core ---
Flask>=3.0.0,<4.0.0
python-dotenv>=1.0.0,<2.0.0

# --- Database & Object-Relational Mapping ---
SQLAlchemy>=2.0.0,<3.0.0
Flask-SQLAlchemy>=3.1.1,<4.0.0
Flask-Migrate>=4.0.5,<5.0.0
psycopg2-binary>=2.9.9,<3.0.0

# --- Form Security ---
Flask-WTF>=1.2.1,<2.0.0

# --- Image Validation ---
Pillow>=10.0.0,<12.0.0

# --- NLP & Machine Learning Ecosystem ---
PySastrawi>=1.2.0,<2.0.0
scikit-learn>=1.3.0,<2.0.0
pandas>=2.1.0,<3.0.0
numpy>=1.26.0,<2.0.0
joblib>=1.3.0,<2.0.0

# --- Automated Testing Suite ---
pytest>=7.4.0,<8.0.0
```

Catatan:

- Tidak ada `pytest-cov`, `flake8`, atau `pytest-flask`.
- Tidak ada dependensi server produksi seperti Gunicorn atau Waitress.
- `Werkzeug` tidak dipin eksplisit; digunakan melalui Flask untuk hashing password.
- `Pillow` digunakan untuk validasi dan pemrosesan ulang foto.

---

## 7. Konfigurasi Lingkungan (`app/config.py` & `.env`)

### 7.1 Pemuatan dan Validasi Konfigurasi

`app/config.py` memuat `.env` menggunakan `python-dotenv`, kecuali `PYTHON_DOTENV_DISABLED=true`.

Prinsip implementasi aktual:

- `FLASK_CONFIG` wajib disetel atau nama konfigurasi harus diberikan eksplisit saat memanggil `create_app()`.
- Tidak ada silent fallback ke `development`.
- `SECRET_KEY` wajib ada dan harus tepat 64 karakter heksadesimal.
- `DevelopmentConfig` dan `TestingConfig` membaca URI database dari environment tanpa nilai default.
- `TestingConfig` mewajibkan `TEST_DATABASE_URL` dan menolak URI yang sama dengan `DEV_DATABASE_URL` atau `DATABASE_URL`.
- `ProductionConfig` mewajibkan `DATABASE_URL`.
- `ProxyFix` hanya dipasang jika `TRUSTED_PROXIES_COUNT > 0`.

Ringkasan kelas konfigurasi:

| Kelas | Karakteristik Aktual |
| :--- | :--- |
| `Config` | `SECRET_KEY`, `SQLALCHEMY_TRACK_MODIFICATIONS=False`, cookie HttpOnly, SameSite `Lax`, path upload/model, batas foto, MIME, threshold ML, `TRUSTED_PROXIES_COUNT`, variabel rate limit (belum dipakai). |
| `DevelopmentConfig` | `DEBUG=True`, URI dari `DEV_DATABASE_URL`, `SESSION_COOKIE_SECURE=False`. |
| `TestingConfig` | `TESTING=True`, `DEBUG=False`, CSRF dinonaktifkan, URI dari `TEST_DATABASE_URL`, validasi isolasi database. |
| `ProductionConfig` | `DEBUG=False`, URI dari `DATABASE_URL`, `SESSION_COOKIE_SECURE=True`, `PERMANENT_SESSION_LIFETIME=2 jam`. |

Nilai batas foto aktual:

- `MAX_PHOTO_SIZE_BYTES = 3 * 1024 * 1024` (3 MB).
- `MAX_PHOTO_DIMENSION = 6000`.
- `MAX_CONTENT_LENGTH = MAX_PHOTO_SIZE_BYTES + 1 MB` (efektif 4 MB).
- Ekstensi diizinkan: `jpg`, `jpeg`, `png`.
- MIME diizinkan: `image/jpeg`, `image/png`.

### 7.2 Panduan Variabel Lingkungan (`.env.example`)

Template aktual memuat:

```bash
# Mode Lingkungan: development | testing | production
FLASK_CONFIG=development

# Kunci Rahasia Sesi Kriptografis
# Wajib 64 karakter heksadesimal (32 bytes).
SECRET_KEY=

# Koneksi PostgreSQL
DATABASE_URL=postgresql+psycopg2://klasifas_user:password_rahasia@localhost:5432/klasifas_db
DEV_DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/klasifas_dev_db
TEST_DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/klasifas_test_db

# Ambang batas keyakinan klasifikasi
ML_CONFIDENCE_THRESHOLD=0.60
```

Catatan:

- `TRUSTED_PROXIES_COUNT`, `TRACK_RATE_LIMIT_PER_MINUTE`, dan `TRACK_RATE_LIMIT_WINDOW_SECONDS` didukung oleh `config.py`, tetapi tidak tercantum di `.env.example`.
- `TRACK_RATE_LIMIT_PER_MINUTE` dan `TRACK_RATE_LIMIT_WINDOW_SECONDS` **belum digunakan** oleh implementasi rate limiter saat ini.

### 7.3 Application Factory

`create_app(config_name=None)`:

1. Menentukan kelas konfigurasi melalui `get_config_class()`.
2. Membuat instance Flask dan memuat konfigurasi.
3. Menjalankan validasi konfigurasi.
4. Menginisialisasi `db`, `migrate`, dan `csrf`.
5. Memasang `ProxyFix` secara kondisional.
6. Mendaftarkan blueprint `auth`, `admin`, `report`, `technician`, dan `dashboard`.
7. Mendaftarkan redirect `/favicon.ico`.
8. Mendaftarkan handler error 403/404/500.
9. Mendaftarkan CLI `create-staff`.
10. Memasang header keamanan melalui `after_request`.

---

## 8. Strategi Pengujian & Penjaminan Mutu

### 8.1 Lingkungan Pengujian

- Kerangka pengujian: `pytest`.
- Database pengujian: PostgreSQL terpisah melalui `TEST_DATABASE_URL`.
- `TestingConfig` menolak URI pengujian yang sama dengan database development atau produksi.
- Tidak ada `tests/conftest.py`; fixture didefinisikan di masing-masing file pengujian.
- Baseline yang tercatat pada `test-results.txt`: **545 passed**.
- Baseline tersebut adalah catatan historis, bukan hasil verifikasi ulang dokumen ini.

### 8.2 Cakupan File Pengujian

Terdapat 34 file pengujian:

| Area | File |
| :--- | :--- |
| Factory & config | `test_factory.py`, `test_config.py` |
| Model & migrasi | `test_models_f1_04.py` |
| Autentikasi & keamanan | `test_auth_f2_01.py`, `test_security_f2_02.py`, `test_rbac_f2_03.py`, `test_security_f2_04.py` |
| Pelaporan & pelacakan | `test_report_f3_01.py`, `test_report_f3_02.py`, `test_ticket_identity_f3_03.py`, `test_track_f3_04.py`, `test_tracking_e2e_f3_05.py` |
| ML & NLP | `test_ml_f4_05.py` |
| Admin | `test_admin_f5_01.py`, `test_admin_f5_02.py`, `test_admin_f5_03.py` |
| Audit | `test_audit_f5_04.py`, `test_audit_f5_05.py`, `test_audit_f6_03.py` |
| Teknisi | `test_technician_f6_01.py`, `test_technician_f6_02.py` |
| Dashboard | `test_dashboard_f7_01.py`, `test_dashboard_f7_02.py`, `test_dashboard_f7_03.py`, `test_dashboard_f7_04.py` |
| CLI | `test_cli_create_staff.py` |
| Error pages | `test_error_pages_vq21.py` |
| UI/aset publik | `test_ui_cards.py`, `test_ui_container.py`, `test_ui_favicon.py`, `test_ui_inputs.py`, `test_ui_responsive.py`, `test_ui_toggler.py`, `test_ui_typography.py` |

### 8.3 Fokus Verifikasi

- Preprocessing: case folding, slang normalization, stopword removal, stemming, dan integritas data lokasi.
- Model loader: validasi path dan fallback saat artefak tidak tersedia.
- Alur tiket: transisi status, verifikasi kategori, penugasan, dan audit log.
- Keamanan: RBAC, session, CSRF, validasi upload, token pelacakan, dan rate limit.
- Dashboard: agregasi, filter, dan sanitasi data.
- UI: struktur halaman, input, responsivitas, dan favicon.

---

## 9. Prinsip Keamanan & Integritas Repositori

### 9.1 Header Keamanan

`app/utils/security_headers.py` memasang header berikut pada seluruh respons:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Content-Security-Policy` dengan `default-src 'self'`, `script-src 'self'`, `style-src 'self'`, `img-src 'self' data:`, dan `font-src 'self'`.

**HSTS tidak tersedia.** Tidak ada header `Strict-Transport-Security` pada implementasi. `tests/test_security_f2_04.py` secara eksplisit memverifikasi bahwa header tersebut tidak ada.

### 9.2 Rate Limiter `/lacak`

Implementasi aktual:

- Singleton `track_limiter = SlidingWindowRateLimiter(limit=15, window_seconds=60)`.
- Batas **hardcoded 15 request per 60 detik per alamat IP**.
- Key menggunakan `request.remote_addr`.
- Berlaku untuk seluruh `POST /lacak`, termasuk percobaan dengan input tidak valid.
- Respons pelanggaran: HTTP 429 dengan header `Retry-After`.
- Penyimpanan riwayat in-memory dan per proses.
- Keterbatasan: pada server multi-worker, kuota efektif dapat menjadi N x limit; restart proses mereset riwayat.
- `TRACK_RATE_LIMIT_PER_MINUTE` dan `TRACK_RATE_LIMIT_WINDOW_SECONDS` di `config.py` belum dihubungkan ke limiter.
- `ProxyFix` hanya aktif jika `TRUSTED_PROXIES_COUNT > 0`.

### 9.3 Autentikasi dan Otorisasi

- Password staf di-hash dengan Werkzeug `scrypt`.
- Login gagal selalu menampilkan pesan generik.
- Role pengguna dimuat ulang dari database pada setiap request.
- `role_required` menerapkan otorisasi server-side dengan prinsip deny-by-default.
- Logout menggunakan `POST` dan dilindungi CSRF.
- Tidak ada registrasi publik atau halaman pengelolaan akun.

### 9.4 Validasi Upload Foto

- Ekstensi: `jpg`, `jpeg`, `png`.
- MIME klien: `image/jpeg` atau `image/png`.
- Magic number diperiksa.
- Gambar di-decode dan di-re-encode dengan Pillow.
- Dimensi maksimum 6000 x 6000 piksel.
- Ukuran maksimum 3 MB; `MAX_CONTENT_LENGTH` efektif 4 MB.
- Nama file disimpan sebagai token heksadesimal acak.
- Lokasi penyimpanan `uploads/` non-publik dan gitignored.
- Penyajian foto hanya melalui endpoint terautentikasi.
- Path traversal dan symlink escape diperiksa saat penyajian.

### 9.5 Perlindungan Data dan Repositori

`.gitignore` mengecualikan:

- `.env` dan turunannya, kecuali `.env.example`.
- `uploads/`.
- `data/raw/` dan `data/private/`.
- `*.joblib`, `*.sqlite`, `*.db`.
- `venv/`, `.venv/`, `__pycache__/`, `.pytest_cache/`, dan artefak coverage.

### 9.6 Pembatasan Akses Data

- Dashboard: `admin_sarpras` dan `pimpinan`.
- Audit log: `admin_sarpras`.
- Verifikasi kategori dan penugasan: `admin_sarpras`.
- Papan tugas dan pembaruan status: `teknisi` dengan pembatasan kepemilikan tiket.
- Data pelacakan publik tidak memuat nama/kontak pelapor, teknisi, hash token, confidence score, atau nama file foto internal.

---

## 10. Batasan Implementasi Aktual dan Pekerjaan Lanjutan

1. **HSTS tidak diterapkan.** Jangan mengklaim HSTS tersedia sampai header ditambahkan dan diuji.
2. **Rate limiter hardcoded.** Nilai 15 request/60 detik belum dapat dikonfigurasi melalui environment.
3. **Variabel rate limit belum digunakan.** `TRACK_RATE_LIMIT_PER_MINUTE` dan `TRACK_RATE_LIMIT_WINDOW_SECONDS` hanya didefinisikan di `config.py`.
4. **Training dan evaluasi ML belum tersedia.** Tidak ada folder `scripts/`, dataset, skrip pelatihan, skrip evaluasi, atau metrik aktual.
5. **Artefak model belum tersedia.** Direktori `app/ml/models/` belum ada; sistem berjalan melalui fallback manual.
6. **Tidak ada `run.py`.** Entry point menggunakan Flask CLI.
7. **Tidak ada `conftest.py`.** Fixture pengujian berada di file masing-masing.
8. **Audit action constant tidak konsisten.** Service memakai tiga aksi, sedangkan konstanta model masih mencantumkan dua aksi.
9. **Server produksi belum dipilih.** Tidak ada dependensi Gunicorn/Waitress pada `requirements.txt`.
10. **Keputusan TBD tetap terbuka:** threshold final `ML_CONFIDENCE_THRESHOLD`, hosting demonstrasi, dan kebijakan retensi/batas final foto.

---

## Ringkasan Revisi v1.4

1. Struktur direktori disesuaikan dengan file aktual: `report.py`, `app/cli.py`, `app/extensions.py`, `dictionary.py`, service tambahan, template `report/`, aset `klasifas.css`/`portal.js`/`favicon.svg`, dan font Public Sans.
2. Folder `scripts/` dihapus dari struktur karena tidak ada di repositori.
3. Rute diperbarui ke endpoint aktual: `/lapor`, `/lacak`, `/admin/tiket`, `/admin/tiket/<id>/penugasan`, `/teknisi/tiket/<id>/status`, dan `/dashboard/api/chart-data`.
4. Rate limiter dijelaskan sebagai hardcoded 15 request/60 detik per IP, in-memory per proses.
5. Variabel `TRACK_RATE_LIMIT_PER_MINUTE` dan `TRACK_RATE_LIMIT_WINDOW_SECONDS` dicatat sebagai belum digunakan.
6. Klaim HSTS dihapus; ditegaskan bahwa HSTS tidak tersedia dan diuji absen.
7. Training dan evaluasi ML dicatat sebagai rencana; tidak ada artefak model atau dataset di repositori.
8. Dependensi disesuaikan dengan `requirements.txt` aktual, termasuk Pillow dan penghapusan `pytest-cov`/`flake8`.
9. Konfigurasi environment disesuaikan dengan `config.py` dan `.env.example`, termasuk validasi `SECRET_KEY` 64 heksadesimal dan isolasi database pengujian.
10. Bagian pengujian diperbarui dengan 34 file aktual dan baseline 545 test lulus.
