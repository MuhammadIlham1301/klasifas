# Tech Stack & Architectural Specification
# KlasiFas — Klasifikasi Keluhan Fasilitas Kampus

**Judul Proyek:** Rancang Bangun Sistem Klasifikasi Keluhan dan Dasbor Pemantauan Fasilitas Kampus Menggunakan Algoritma Naive Bayes  
**Institusi:** Universitas Muhammadiyah Prof. Dr. HAMKA (UHAMKA)  
**Fakultas:** Fakultas Teknologi Industri dan Informatika (FTII)  
**Kelompok:** 7  
**Status Dokumen:** Approved Draft — Kelompok 7 Review (v1.3)  
**Dokumen Acuan:** `docs/PRD.md` v1.3, Proposal Seminar Capstone Pertemuan 5, Laporan Seminar Capstone Pertemuan 6  

---

## 1. Arsitektur Sistem Global

KlasiFas mengadopsi arsitektur **Modular Monolith** berbasis web multi-tier yang dirancang untuk skala prototipe operasional kampus FTII UHAMKA. Seluruh modul aplikasi (antarmuka, kontrol bisnis, inferensi Machine Learning, dan akses basis data) berjalan dalam satu kesatuan proses aplikasi terpadu (*in-process*) guna meminimalkan latensi jaringan, menyederhanakan konfigurasi deployment, serta memudahkan pemeliharaan kode oleh tim pengembang.

```
+-----------------------------------------------------------------------+
|                           CLIENT TIER                                 |
|  - Web Browser (Desktop & Mobile Responsive)                          |
|  - HTML5, CSS3, Vanilla JavaScript (ES6+), Bootstrap 5, Chart.js      |
+-----------------------------------▲-----------------------------------+
                                    │ HTTP / HTTPS (Form & JSON)
+-----------------------------------▼-----------------------------------+
|                        APPLICATION SERVER TIER                        |
|  WSGI Web Server (Gunicorn / Waitress / Werkzeug dev)                 |
|  Python 3.11 Runtime + Flask Framework                               |
|                                                                       |
|  [Presentation Layer - app/routes/]                                   |
|   ├── main.py (Beranda & Pelacakan Mandiri FR-02)                     |
|   ├── complaints.py (Formulir Pelaporan Keluhan & Upload Foto FR-01)  |
|   ├── auth.py (Login, Logout, Session Guard RBAC)                     |
|   ├── admin.py (Verifikasi Tiket FR-04, Penugasan FR-05, Log FR-09)   |
|   ├── technician.py (Papan Tugas & Pembaruan Status Kerja FR-06)      |
|   └── dashboard.py (Visualisasi Analitik Manajerial FR-07, Filter FR-08)|
|                                                                       |
|  [Business Logic & Service Layer - app/services/]                     |
|   ├── complaint_service.py (Validasi Transisi Status 4 Tahap, Kode)   |
|   ├── audit_service.py (Pencatatan Riwayat Aktivitas & Perubahan)     |
|   └── classification_service.py (Pra-pemrosesan Teks & Fallback FR-10)|
|                                                                       |
|  [In-Process Machine Learning Pipeline - app/ml/]                     |
|   ├── preprocessor.py (Case Folding, Regex Cleaning, PySastrawi)      |
|   ├── classifier.py (TF-IDF Vectorizer + MultinomialNB .joblib)       |
|   └── Fallback Handler (Penanda Flag Verifikasi Manual)               |
+-----------------------------------▲-----------------------------------+
                                    │ SQLAlchemy 2.0 (Parameterized Queries)
+-----------------------------------▼-----------------------------------+
|                            DATA TIER                                  |
|  - PostgreSQL 15+ (Relational Database)                               |
|  - Local File System Storage (Bukti Foto Terbatas, .joblib Model)     |
+-----------------------------------------------------------------------+
```

### Karakteristik Arsitektur Utama
1. **In-Process Inference:** Model Machine Learning dimuat langsung ke memori proses Flask saat server *bootstrap* (*startup*). Inferensi teks berlangsung secara lokal tanpa overhead pemanggilan jaringan mikroservis.
2. **Layered Separation of Concerns:** Pemisahan tegas antara rute pengontrol HTTP (`app/routes/`), logika transaksi bisnis (`app/services/`), representasi entitas relasional (`app/models/`), dan pengolahan teks/ML (`app/ml/`).
3. **Graceful Fallback (FR-10):** Sistem tetap beroperasi penuh menerima pelaporan tiket apabila modul inferensi ML tidak tersedia atau mendeteksi kegagalan pemuatan artefak.

---

## 2. Pemetaan Komponen Teknologi

| Komponen Sistem | Teknologi Terpilih | Versi Rekomendasi Awal | Peran & Justifikasi Teknis |
| :--- | :--- | :--- | :--- |
| **Language Runtime** | Python | 3.11.x | Bahasa pemrograman terpadu untuk backend web dan ekosistem Machine Learning / NLP. |
| **Backend Framework** | Flask | ^3.0.0 | *Microframework* yang ringan, eksplisit, modular (*Blueprints*), dan efisien untuk arsitektur monolitik terintegrasi. |
| **Relational Database** | PostgreSQL | 15.x / 16.x | RDBMS utama dengan keandalan integritas relasional, kepatuhan ACID, indeks performa tinggi, dan konsistensi dialek pengujian. |
| **Database Driver** | psycopg2-binary | ^2.9.9 | Driver PostgreSQL berbasis C untuk Python dengan performa tinggi dan kompatibilitas penuh terhadap SQLAlchemy. |
| **ORM & Migrations** | Flask-SQLAlchemy, Flask-Migrate | ^3.1.1 (SQLAlchemy 2.0+), ^4.0.5 (Alembic) | Abstraksi relasional objek dengan *parameterized queries* bawaan serta pelacakan skema basis data terkontrol versi. |
| **UI Framework & Style**| Bootstrap | 5.3.x | Framework antarmuka responsif ramah peramban seluler, sistem *grid* teruji, dan komponen antarmuka siap pakai. |
| **Visualisasi Dasbor** | Chart.js | 4.4.x | Pustaka JavaScript sisi klien untuk merender grafik distribusi kategori, tren keluhan, dan perbandingan status secara interaktif. |
| **Frontend Scripting** | Vanilla JavaScript | ES6+ | Menangani interaktivitas DOM, validasi sisi klien, kalkulasi panjang karakter, dan komunikasi asinkron tanpa kerumitan *build tools*. |
| **ML Classifier** | scikit-learn | ^1.3.0 | Implementasi algoritma `MultinomialNB` dengan *Laplace smoothing* ($ \alpha = 1.0 $) dan ekstraksi fitur `TfidfVectorizer`. |
| **NLP Stemmer** | PySastrawi (Sastrawi) | ^1.2.0 | Ekstraksi kata dasar berbahasa Indonesia (*Nazief & Adriani stemming*) untuk mereduksi variasi morfologi teks keluhan. |
| **Data Manipulation** | pandas, numpy | ^2.1.0, ^1.26.0 | Manajemen struktur data tabular saat pelatihan model *offline*, kalkulasi matriks evaluasi, dan persiapan korpus teks. |
| **Model Persistence** | joblib | ^1.3.0 | Serialisasi dan deserialisasi pipa model scikit-learn secara efisien ke dalam format biner `.joblib`. |
| **Keamanan & Autentikasi** | Werkzeug Security, Flask-WTF | bawaan Flask, ^1.2.1 | Hashing kredensial dengan fungsi kriptografi `scrypt` dan proteksi serangan *Cross-Site Request Forgery* (CSRF). |
| **Pengujian Perangkat Lunak** | pytest, pytest-cov | ^7.4.0, ^4.1.0 | Kerangka pengujian unit dan integrasi otomatis dengan pelaporan cakupan baris kode (*coverage report*). |
| **Version Control** | Git & GitHub | Standar | Manajemen riwayat revisi kode sumber, dokumentasi repositori, dan koordinasi pengembangan tim. |

---

## 3. Spesifikasi Modul Backend & Interaksi Data

### 3.1 Arsitektur Modul Rute (`app/routes/`)
Sesuai rancangan modular yang disepakati, kontrol rute HTTP diorganisasikan ke dalam modul blueprint pada direktori `app/routes/`:

1. **`main.py` (Portal Publik & Pelacakan Mandiri):**
   - Menangani beranda informasi sistem (`/`).
   - Melayani pelacakan status tiket publik berbasis kode pelaporan unik secara aman tanpa proses login yang rumit (`/lacak`) (FR-02).
2. **`complaints.py` (Formulir Pelaporan Keluhan):**
   - Menangani formulir pelaporan keluhan fasilitas kampus (`/lapor`) (FR-01).
   - Validasi input teks deskripsi, pemilihan lokasi (gedung, lantai, ruang), isian kategori opsional pelapor, dan unggahan bukti foto opsional.
3. **`auth.py` (Autentikasi Staf Internal):**
   - Menangani login dan logout untuk Admin Sarpras, Teknisi, dan Pimpinan/Kaprodi (`/auth/login`, `/auth/logout`).
   - Mengelola sesi aman berbasis *cookie* dengan pembatasan hak akses berbasis peran (RBAC).
4. **`admin.py` (Operasional Sarpras):**
   - Daftar antrean tiket keluhan terverifikasi dan belum terverifikasi (`/admin/tiket`).
   - Verifikasi atau koreksi kategori hasil inferensi Machine Learning (`/admin/tiket/<id>/verifikasi`) (FR-04).
   - Penugasan nama teknisi/unit penanggung jawab ke tiket (`/admin/tiket/<id>/assign`) (FR-05).
   - Pencarian dan penyaringan data laporan multi-kriteria (`/admin/filter`) (FR-08).
   - Akses eksklusif pembacaan log audit riwayat aktivitas sistem (`/admin/audit-log`) (FR-09).
5. **`technician.py` (Papan Tugas Teknisi):**
   - Daftar tiket yang ditugaskan kepada teknisi login (`/teknisi/tiket`).
   - Formulir pembaruan status pengerjaan tiket sesuai kewenangan transisi resmi dan penambahan catatan tindakan perbaikan fisik (`/teknisi/tiket/<id>/update-status`) (FR-06).
6. **`dashboard.py` (Dasbor Pemantauan Manajerial):**
   - Visualisasi analitik internal untuk **Admin Sarpras** dan **Pimpinan/Kaprodi** (`/dashboard`) (FR-07).
   - Penyajian data statistik volume keluhan, distribusi 7 kategori fasilitas, tren waktu, dan lokasi sering rusak.
   - Endpoint internal data JSON untuk rendering Chart.js (`/dashboard/api/chart-data`).
   - *Catatan:* Dasbor difokuskan secara murni pada visualisasi agregat dan filter data (FR-07 dan FR-08).

### 3.2 Alur Transisi Status Resmi Tiket
Sistem secara ketat hanya memberlakukan **empat status resmi** sesuai PRD Bagian 5.2.E:

$$\mathbf{Baru} \longrightarrow \mathbf{Terverifikasi} \longrightarrow \mathbf{Diproses} \longrightarrow \mathbf{Selesai}$$

- **`Baru`:** Tiket berhasil dibuat oleh pelapor melalui formulir web (FR-01) dan telah melalui proses klasifikasi otomatis atau penandaan *fallback*.
- **`Terverifikasi`:** Kategori operasional tiket telah diperiksa, dikonfirmasi, atau dikoreksi oleh Admin Sarpras (FR-04), dan informasi penanggung jawab teknisi telah disematkan (FR-05).
- **`Diproses`:** Teknisi yang ditugaskan telah menerima penugasan dan mulai melaksanakan tindakan perbaikan fisik di lapangan (FR-06).
- **`Selesai`:** Tindakan perbaikan telah tuntas dilaksanakan oleh teknisi, disertai catatan ringkasan penanganan dan stempel waktu selesai (FR-06).

> [!IMPORTANT]
> **Integritas Status Operasional:**  
> Sistem **tidak menambahkan status di luar empat status resmi** di atas. Penugasan teknisi dicatat sebagai atribut relasional penanggung jawab pada entitas tiket (FR-05), bukan sebagai status baru. Pembatalan atau kendala operasional dicatat pada catatan log audit dan ringkasan tindak lanjut tanpa merusak konsistensi empat status utama.

### 3.3 Penanganan Kondisi "Perlu Verifikasi Manual" (Flag Proses, Bukan Status Tiket)
Apabila model Machine Learning mengalami kegagalan proses/artefak tidak tersedia (FR-10), atau skor keyakinan prediksi berada di bawah ambang batas evaluasi (*low confidence score*):
- Status tiket **tetap berstatus resmi `Baru`**.
- Sistem menyematkan penanda proses klasifikasi internal: `needs_manual_verification = True`.
- Rekomendasi kategori diberi label penanda khusus `Perlu Verifikasi Manual` pada antrean Admin Sarpras agar menjadi prioritas pemeriksaan manusia sebelum tiket diverifikasi menjadi `Terverifikasi`.

### 3.4 Keamanan Kueri Basis Data & Parameter Binding
Interaksi basis data menggunakan **Flask-SQLAlchemy** (SQLAlchemy 2.0). 
- Seluruh kueri yang dieksekusi melalui SQLAlchemy ORM secara otomatis menggunakan **parameter binding / parameterized queries** untuk memitigasi risiko *SQL Injection*.
- Apabila terdapat kueri berbasis *raw SQL* untuk kebutuhan agregasi analitik dasbor, pengembang diwajibkan menggunakan konstruksi `db.session.execute(text("..."), params)` dengan parameter binding eksplisit.

### 3.5 Spesifikasi Format Kode Tiket
- **Format:** Prefix **`KF-`** diikuti **6 karakter acak alfanumerik kapital** (contoh: `KF-8X9B2M`).
- **Panjang Karakter:** Tepat 8 karakter alfanumerik (di luar tanda hubung `-`).
- **Keamanan:** Dibuat menggunakan modul kriptografis `secrets` (alfabet non-ambigu seperti `23456789ABCDEFGHJKLMNPQRSTUVWXYZ` tanpa karakter yang mudah tertukar seperti `0/O` atau `1/I`) guna mencegah serangan tebakan nomor urut (*sequential enumeration attack*). Endpoint pelacakan publik dilindungi pembatasan frekuensi pencarian (*rate limiting*).

---

## 4. Pipeline Machine Learning & Pengolahan Teks (FR-03)

### 4.1 Tahapan Pra-pemrosesan Teks & Klasifikasi
Proses klasifikasi teks keluhan berlangsung secara lokal (*in-process*) di memori aplikasi pada saat pelapor mengirimkan keluhan (FR-03):

```
Teks Keluhan Mentah (Deskripsi)
        │
        ▼
[1. Case Folding] ─── Mengubah seluruh teks deskripsi menjadi huruf kecil (lowercase).
        │
        ▼
[2. Regex Cleaning] ─ Menghapus URL, tanda baca, simbol, spasi berlebih, dan angka.
                      *Penegasan Khusus: Pembersihan angka HANYA diterapkan pada teks deskripsi
                       keluhan dan SAMA SEKALI TIDAK MENGUBAH data angka lokasi (Gedung, Lantai, Ruang).
        │
        ▼
[3. Stopwords Removal] Menghapus kata umum non-substantif menggunakan daftar stopword Indonesia.
        │
        ▼
[4. Sastrawi Stemming] Meretensi kata dasar bahasa Indonesia (PySastrawi: Nazief & Adriani).
        │
        ▼
[5. TF-IDF Vectorizer] Transformasi teks bersih ke bobot fitur unigram/bigram (.joblib artifact).
        │
        ▼
[6. Multinomial Naive Bayes] Komputasi probabilitas posterior tiap kelas K1–K7 (.joblib artifact).
        │
        ├── Kategori Prediksi Rekomendasi (Probabilitas Terbesar)
        └── Nilai Confidence Score (Data pendukung telaah Admin Sarpras)
```

### 4.2 Siklus Hidup dan Keamanan Artefak Model (.joblib)
1. **Pelatihan & Evaluasi Offline:**
   - Pelatihan dan pengujian model scikit-learn dilakukan secara *offline* di lingkungan pengembangan lokal (`scripts/train_model.py`) setelah dataset penelitian (target perencanaan 600 sampel) selesai dihimpun, memperoleh izin institusi, dan dianomimkan dari data pribadi (*PII*).
   - Evaluasi menghasilkan metrik performa formal (Akurasi, Macro-F1, Recall per kelas).
2. **Penyalinan Terkontrol ke Direktori Aplikasi:**
   - Artefak yang telah lolos verifikasi performa (`model.joblib` dan `vectorizer.joblib`) disalin secara terkontrol ke direktori `app/ml/models/`.
3. **Aturan Keamanan Deserialisasi:**
   - **Prinsip Keamanan Mutlak:** Aplikasi **hanya diizinkan memuat** file biner `.joblib` yang bersumber langsung dari pipa pelatihan internal pengembang tepercaya. Aplikasi dilarang keras memuat atau mengeksekusi file `.joblib` dari masukan pengguna, pihak ketiga, atau jaringan eksternal untuk mencegah celah eksekusi kode sembarang (*Arbitrary Code Execution*).
4. **Fallback Handler (FR-10):**
   - Modul `classification_service.py` membungkus pemuatan model dan inferensi dalam blok penanganan eksepsi (`try-except`).
   - Apabila artefak `.joblib` belum tersedia atau terjadi galat komputasi, sistem secara otomatis menandai tiket dengan flag `needs_manual_verification = True` tanpa menggagalkan proses penyimpanan laporan pelapor ke basis data.

---

## 5. Struktur Direktori Proyek

Struktur folder mengimplementasikan pola Modular Monolith yang terstruktur rapi, mempertahankan konsistensi `app/config.py` dan `app/routes/`:

```
klasifas/
├── app/                            # Paket Utama Aplikasi Flask
│   ├── __init__.py                 # Application Factory (create_app) & Inisialisasi Ekstensi
│   ├── config.py                   # Konfigurasi Kelas Aplikasi & Hook Validasi Lingkungan
│   ├── models/                     # Deklarasi Entitas Basis Data (Flask-SQLAlchemy)
│   │   ├── __init__.py
│   │   ├── user.py                 # Entitas Pengguna (Admin Sarpras, Teknisi, Pimpinan/Kaprodi)
│   │   ├── ticket.py               # Entitas Tiket Keluhan & Log 4 Status Resmi
│   │   ├── category.py             # Entitas Referensi 7 Kategori Fasilitas (K1–K7)
│   │   └── audit_log.py            # Entitas Riwayat Audit Perubahan Sistem (FR-09)
│   ├── routes/                     # Modul Blueprint Pengontrol HTTP
│   │   ├── __init__.py
│   │   ├── main.py                 # Beranda & Pelacakan Mandiri Publik (FR-02)
│   │   ├── complaints.py           # Formulir Pelaporan & Upload Foto (FR-01)
│   │   ├── auth.py                 # Login, Logout, & Session Guard Internal
│   │   ├── admin.py                # Verifikasi Kategori, Penugasan, Filter, Log Audit
│   │   ├── technician.py           # Papan Tugas Teknisi & Pembaruan Status (FR-06)
│   │   └── dashboard.py            # Dasbor Pemantauan Manajerial & API Grafik (FR-07)
│   ├── services/                   # Lapisan Logika Bisnis (Business Logic Layer)
│   │   ├── __init__.py
│   │   ├── complaint_service.py    # Logika Tiket, Validasi Transisi 4 Status, Generator Kode
│   │   ├── audit_service.py        # Pencatatan Audit Trail Perubahan Status/Kategori
│   │   └── classification_service.py # Orkestrasi NLP, Inferensi Model, & Fallback (FR-10)
│   ├── ml/                         # Paket Machine Learning & NLP (In-Process)
│   │   ├── __init__.py
│   │   ├── preprocessor.py         # Case Folding, Regex Cleaning, Sastrawi Stemming
│   │   ├── classifier.py           # Deserialisasi .joblib & Komputasi Probabilitas
│   │   └── models/                 # Direktori Artefak Biner (.gitignored)
│   │       ├── .gitkeep
│   │       ├── model.joblib        # [Artefak Terkontrol] Trained Naive Bayes
│   │       └── vectorizer.joblib   # [Artefak Terkontrol] Trained TF-IDF
│   ├── static/                     # Aset Statis Web
│   │   ├── css/
│   │   │   └── style.css           # Kustomisasi Tampilan & Penyesuaian Antarmuka
│   │   ├── js/
│   │   │   ├── main.js             # Validasi Form, Interaksi DOM, Modal Konfirmasi
│   │   │   └── dashboard.js        # Inisialisasi & Rendering Grafik Chart.js
│   │   └── img/                    # Logo Resmi UHAMKA, FTII, & Ikon Fasilitas
│   ├── templates/                  # Template Jinja2 (HTML5 Responsif)
│   │   ├── base.html               # Layout Induk (Navigasi, Notifikasi Flash, Footer)
│   │   ├── public/                 # Tampilan Beranda & Pelacakan Tiket Mandiri
│   │   ├── complaints/             # Tampilan Formulir Pelaporan Keluhan
│   │   ├── auth/                   # Tampilan Form Login Staf Internal
│   │   ├── admin/                  # Antrean Verifikasi Tiket, Penugasan, & Log Audit
│   │   ├── technician/             # Antrean Kerja & Form Pembaruan Status Teknisi
│   │   └── dashboard/              # Dasbor Analitik Manajerial & Grafik Statistik
│   └── utils/                      # Helper & Fungsi Pembantu
│       ├── __init__.py
│       ├── decorators.py           # Dekorator Pembatasan Akses RBAC (@role_required)
│       └── security_helpers.py     # Generator Token Acak Tiket & Sanitasi File
├── migrations/                     # Direktori Migrasi Skema Basis Data (Flask-Migrate/Alembic)
├── scripts/                        # Skrip Utilitas Offline & Otomasi
│   ├── train_model.py              # Pelatihan Offline Model & Serialisasi .joblib
│   ├── evaluate_model.py           # Kalkulasi Metrik Evaluasi & Confusion Matrix
│   └── seed_users.py               # Inisialisasi Data Master Pengguna Awal
├── tests/                          # Paket Pengujian Perangkat Lunak (pytest)
│   ├── conftest.py                 # Fixture Pengujian & Koneksi Database Test
│   ├── test_preprocessing.py       # Unit Test Case Folding, Stopwords, Stemming, Regex
│   ├── test_classifier.py          # Unit Test Inferensi Model ML & Fallback FR-10
│   ├── test_complaint_flow.py      # Integration Test Alur 4 Status Tiket & Transisi
│   └── test_rbac_security.py       # Security Test Sesi, Hak Akses, & Audit Log
├── uploads/                        # Direktori Penyimpanan Foto Bukti Keluhan (.gitignored)
├── .env.example                    # Template Variabel Lingkungan
├── .gitignore                      # Aturan Pengecualian Berkas Repositori
├── requirements.txt                # Daftar Dependensi Pustaka Python Resmi
├── README.md                       # Dokumentasi Utama Repositori
└── run.py                          # Titik Masuk Eksekusi Aplikasi Flask (Entry Point)
```

---

## 6. Spesifikasi Dependensi (`requirements.txt`)

Versi pustaka yang dicantumkan merupakan **batas versi rekomendasi awal**. Dependensi dibatasi secara ketat hanya pada pustaka yang benar-benar dibutuhkan oleh sistem. Pengujian kompatibilitas aktual dilakukan saat penyiapan lingkungan pengembangan, dan versi final akan dikunci (*pinned*) setelah seluruh pengujian lulus:

```text
# Web Framework & Core Extensions
Flask>=3.0.0,<3.1.0
Flask-SQLAlchemy>=3.1.1,<3.2.0
Flask-Migrate>=4.0.5,<4.1.0
Flask-WTF>=1.2.1,<1.3.0
WTForms>=3.1.1,<3.2.0

# Database Driver
psycopg2-binary>=2.9.9,<3.0.0

# Machine Learning & Natural Language Processing
scikit-learn>=1.3.0,<1.4.0
PySastrawi>=1.2.0,<1.3.0
pandas>=2.1.0,<2.2.0
numpy>=1.26.0,<1.27.0
joblib>=1.3.0,<1.4.0

# Security & Utilities
Werkzeug>=3.0.1,<3.1.0
python-dotenv>=1.0.0,<1.1.0

# Testing & Code Quality
pytest>=7.4.0,<8.0.0
pytest-cov>=4.1.0,<5.0.0
flake8>=6.1.0,<7.0.0
```

---

## 7. Konfigurasi Lingkungan (`app/config.py` & `.env`)

### 7.1 Pemuatan dan Validasi Konfigurasi Terisolasi
Modul `app/config.py` memuat berkas `.env` menggunakan `python-dotenv` sebelum kelas konfigurasi dievaluasi. Validasi spesifik lingkungan dipisahkan ke dalam metode kelas `init_app(app)` agar evaluasi variabel yang bersifat eksklusif (seperti `DATABASE_URL` pada produksi) **hanya dieksekusi ketika kelas konfigurasi tersebut benar-benar diaktifkan** oleh *Application Factory* (`create_app`), sehingga tidak mengganggu `DevelopmentConfig` maupun `TestingConfig`:

```python
import os
from datetime import timedelta
from dotenv import load_dotenv

# Pemuatan .env secara eksplisit sebelum pembacaan os.environ
load_dotenv()

class Config:
    """Konfigurasi dasar umum (Base Configuration)."""
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Batas ukuran upload berkas (Rekomendasi awal 5 MB; parameter sementara yang difinalisasi pada docs/SECURITY.md)
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    
    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    ML_MODEL_PATH = os.path.join(BASE_DIR, 'app', 'ml', 'models', 'model.joblib')
    ML_VECTORIZER_PATH = os.path.join(BASE_DIR, 'app', 'ml', 'models', 'vectorizer.joblib')
    
    # Placeholder ambang batas keyakinan (dievaluasi setelah model selesai dilatih)
    ML_CONFIDENCE_THRESHOLD = float(os.environ.get('ML_CONFIDENCE_THRESHOLD', '0.60'))

    @classmethod
    def init_app(cls, app):
        """Validasi umum saat inisialisasi aplikasi."""
        if not cls.SECRET_KEY:
            raise ValueError(
                "CRITICAL: Variabel lingkungan 'SECRET_KEY' belum disetel. "
                "Aplikasi dihentikan demi keamanan sesi."
            )

class DevelopmentConfig(Config):
    """Konfigurasi khusus lingkungan pengembangan lokal."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DEV_DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5432/klasifas_dev_db'
    )
    # Mendukung pengujian dan demonstrasi lokal berbasis protokol HTTP
    SESSION_COOKIE_SECURE = False

    @classmethod
    def init_app(cls, app):
        super().init_app(app)

class TestingConfig(Config):
    """Konfigurasi khusus pengujian otomatis (pytest)."""
    TESTING = True
    DEBUG = False
    WTF_CSRF_ENABLED = False  # Dinonaktifkan khusus untuk kemudahan automated testing form
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'TEST_DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5432/klasifas_test_db'
    )
    SESSION_COOKIE_SECURE = False

    @classmethod
    def init_app(cls, app):
        super().init_app(app)

class ProductionConfig(Config):
    """Konfigurasi khusus lingkungan produksi/deployment resmi."""
    DEBUG = False
    TESTING = False
    
    # Membaca variabel DATABASE_URL tanpa memicu error saat modul config diimpor
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    # Keamanan Cookie Sesi:
    # Wajib bernilai True pada deployment resmi untuk memastikan transmisi cookie hanya melalui HTTPS
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

    @classmethod
    def init_app(cls, app):
        super().init_app(app)
        
        # Validasi Ketat Khusus Produksi:
        # Hanya dieksekusi ketika ProductionConfig dipilih saat runtime
        if not os.environ.get('DATABASE_URL'):
            raise ValueError(
                "CRITICAL: Variabel lingkungan 'DATABASE_URL' wajib disetel saat menggunakan ProductionConfig. "
                "Aplikasi dihentikan karena basis data produksi tidak terdefinisi."
            )

config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig
}
```

### Pola Penerapan pada Application Factory (`app/__init__.py`)
Saat aplikasi diinisialisasi, fungsi pabrik (*factory*) memvalidasi nama konfigurasi secara ketat (*fail-fast*) tanpa *silent fallback* guna mencegah kesalahan penulisan lingkungan operasional:

```python
import os
from flask import Flask
from app.config import config_by_name

def create_app(config_name=None):
    """
    Application Factory KlasiFas.
    Menginisialisasi instance Flask dengan validasi konfigurasi yang aman dan ketat.
    """
    # 1. Jika konfigurasi tidak ditentukan di argumen maupun environment, gunakan 'development' secara eksplisit
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'development')
    
    # 2. Validasi fail-fast: Mencegah silent fallback jika terjadi salah ketik (misal: 'prodution')
    if config_name not in config_by_name:
        valid_keys = ', '.join([f"'{k}'" for k in config_by_name.keys()])
        raise ValueError(
            f"CRITICAL: Lingkungan konfigurasi '{config_name}' tidak dikenali. "
            f"Pilihan valid adalah: {valid_keys}. "
            "Aplikasi dihentikan demi keamanan untuk mencegah pengalihan mode tanpa izin."
        )

    # 3. Ambil kelas konfigurasi yang valid secara eksplisit
    config_class = config_by_name[config_name]
    
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # 4. Eksekusi validasi spesifik lingkungan (SECRET_KEY untuk semua, DATABASE_URL untuk produksi)
    config_class.init_app(app)
    
    # Inisialisasi ekstensi (db, migrate, csrf) dan registrasi blueprints (app/routes/)...
    # ...
    
    return app
```

### 7.2 Panduan Variabel Lingkungan (`.env.example`)
Template variabel lingkungan disediakan tanpa menyertakan kredensial riil:

```bash
# Mode Konfigurasi: development | testing | production
# PERINGATAN: Lingkungan server deployment resmi WAJIB menyetel FLASK_CONFIG=production
FLASK_CONFIG=development

# Kunci Rahasia Sesi Kriptografis (Wajib di-generate unik, misal: python -c "import secrets; print(secrets.token_hex(32))")
SECRET_KEY=

# Koneksi Database PostgreSQL Utama (Wajib diisi HANYA jika FLASK_CONFIG=production)
DATABASE_URL=postgresql://klasifas_user:password_rahasia@localhost:5432/klasifas_db
DEV_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/klasifas_dev_db
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/klasifas_test_db

# Konfigurasi Machine Learning (Placeholder nilai ambang keyakinan)
ML_CONFIDENCE_THRESHOLD=0.60
```

---

## 8. Strategi Pengujian & Penjaminan Mutu

1. **Konsistensi Lingkungan Basis Data Pengujian:**
   - Seluruh pengujian otomatis (`pytest`) dieksekusi menggunakan basis data PostgreSQL pengujian khusus (`klasifas_test_db`) untuk menjaga konsistensi dialek SQL, integritas *foreign key*, dan perilaku transaksi relasional yang identik dengan lingkungan operasional.
2. **Cakupan Pengujian Terfokus:**
   - **Unit Testing Preprocessing (FR-03):** Memvalidasi fungsi *regex cleaning* secara presisi membersihkan teks deskripsi tanpa mengubah angka pada entitas lokasi gedung/lantai/ruang, serta memverifikasi hasil *stemming* Sastrawi.
   - **Unit Testing Klasifikasi & Fallback (FR-03, FR-10):** Menguji akurasi inferensi saat model valid tersedia, serta memastikan flag `needs_manual_verification = True` terpasang saat model tidak tersedia.
   - **Integration Testing Alur Tiket (FR-01, FR-04, FR-05, FR-06):** Memvalidasi transisi status tiket yang ketat (hanya `Baru` $\rightarrow$ `Terverifikasi` $\rightarrow$ `Diproses` $\rightarrow$ `Selesai`) dan mencatat stempel waktu serta penanggung jawab dengan benar.
   - **Security Testing (FR-09):** Memverifikasi bahwa hanya Admin Sarpras yang dapat membaca log audit, memvalidasi enkripsi hash password (`scrypt`), menguji batas ukuran berkas unggahan, dan memastikan pembatasan hak akses peran (*RBAC*).

---

## 9. Prinsip Keamanan & Integritas Repositori

1. **Proteksi Kredensial & Privasi Data:**
   - Berkas konfigurasi `.env`, data mentah berisi identitas pribadi (*PII*) pelapor, direktori bukti foto tiket (`uploads/`), artefak biner model (`.joblib`), dan direktori virtual environment (`venv/`) dilarang diunggah ke repositori Git melalui konfigurasi `.gitignore`.
2. **Penyimpanan Password Pengguna Internal:**
   - Kredensial seluruh akun staf internal (Admin Sarpras, Teknisi, Pimpinan/Kaprodi) disimpan dalam bentuk *hash* kriptografis menggunakan algoritma `scrypt` bawaan Werkzeug.
3. **Validasi File Bukti Unggahan (Parameter Sementara):**
   - Foto bukti keluhan diperiksa ekstensi berkasnya (`.jpg`, `.jpeg`, `.png`), nama berkas diamankan menggunakan `werkzeug.utils.secure_filename`, dan ukuran berkas dibatasi sementara dengan rekomendasi awal maksimum 5 MB (`MAX_CONTENT_LENGTH = 5 MB`), yang akan difinalisasi dalam rentang 2–5 MB pada dokumen `docs/SECURITY.md`.
4. **Pencegahan SQL Injection:**
   - Seluruh operasi basis data wajib memanfaatkan mekanisme *parameter binding* bawaan SQLAlchemy. Kueri mentah dengan metode penggabungan string (*string formatting/concatenation*) dilarang keras.
5. **Pembatasan Hak Akses Khusus:**
   - Dasbor analitik (FR-07) hanya dapat diakses oleh **Admin Sarpras** dan **Pimpinan/Kaprodi**. Teknisi dan pelapor tidak memiliki akses ke dasbor ini.
   - Log audit operasional (FR-09) hanya dapat dibaca oleh **Admin Sarpras**.

---

## Ringkasan Perubahan Minor (Changelog v1.3 Refinement)

1. **Isolasi Validasi `DATABASE_URL` (Bagian 7.1):**
   - Memindahkan pemeriksaan variabel `DATABASE_URL` dari *body* kelas `ProductionConfig` ke dalam metode kelas `init_app(app)`.
   - Validasi ini sekarang **hanya dieksekusi ketika `ProductionConfig` dipilih** saat *runtime*. Mengimpor modul `app.config` di lingkungan `DevelopmentConfig` (yang menggunakan `DEV_DATABASE_URL`) atau `TestingConfig` (yang menggunakan `TEST_DATABASE_URL`) tidak akan memicu galat palsu akibat ketiadaan `DATABASE_URL`.
2. **Eliminasi Silent Fallback pada Application Factory (Bagian 7.1):**
   - Mengganti penggunaan `config_by_name.get(config_name, config_by_name['default'])` dengan validasi eksplisit `if config_name not in config_by_name: raise ValueError(...)`.
   - Mencegah salah ketik konfigurasi produksi beralih secara diam-diam ke konfigurasi *development*.
3. **Penegasan Status Parameter Unggah Berkas (Bagian 7.1 & 9.3):**
   - Menandai batas ukuran 5 MB pada `MAX_CONTENT_LENGTH` dan validasi foto sebagai **parameter rekomendasi awal / sementara**, selaras dengan PRD v1.3 yang menetapkan bahwa kebijakan ukuran berkas (rentang 2–5 MB) akan difinalisasi pada dokumen `docs/SECURITY.md`.
4. **Pembersihan Dependensi & Format Rute (Bagian 2, 5, & 6):**
   - Menghapus pustaka `email-validator` dari daftar dependensi.
   - Mempertahankan struktur rute modular `app/routes/` dan konfigurasi `app/config.py`.

---

### Keputusan Teknis Terbuka (TBD) untuk Tahap Selanjutnya:
1. **Target Lingkungan Hosting Demonstrasi Prototipe:** Menentukan apakah demonstrasi capstone akan dijalankan pada mesin lokal tim pengembang atau pada VPS berbasis Linux (akan difinalkan saat menyusun `docs/TASKS.md` dan `README.md`).
2. **Nilai Ambang Batas Keyakinan Model (`ML_CONFIDENCE_THRESHOLD`):** Menentukan nilai definitif ambang probabilitas untuk flag verifikasi manual setelah model selesai dilatih dan dievaluasi menggunakan dataset teranotasi.
3. **Kebijakan Batas Retensi & Finalisasi Ukuran File Bukti Foto:** Menentukan masa simpan file foto keluhan pada direktori `uploads/` dan menetapkan batas pasti ukuran berkas dalam rentang 2–5 MB (akan diatur mendalam pada `docs/SECURITY.md`).
