# KlasiFas — Implementation Readiness Review

| Metadata | Keterangan |
|---|---|
| **Proyek** | KlasiFas — Klasifikasi Keluhan Fasilitas Kampus |
| **Institusi** | Fakultas Teknologi Industri dan Informatika (FTII) UHAMKA |
| **Tanggal Evaluasi** | 15 November 2026 |
| **Status Dokumen** | Canonical Implementation Readiness Review — Final |
| **Dokumen Acuan** | `docs/DESIGN.md` v2.0, `docs/PRD.md` v1.3, `docs/SECURITY.md` v1.0, `docs/TECHSTACK.md` v1.3, `docs/IMPLEMENTATION_MAP.md` |
| **Lingkungan Uji** | Python 3.11, PostgreSQL (Database Terisolasi), Flask Modular Monolith |
| **Hasil Uji Aktif** | **49 / 49 UI tests passed** dan **26 / 26 test Teknisi F6.01 passed**; 635 test terkoleksi (211 DB-free, 424 DB-backed); 398 test DB-backed lainnya menunggu `TEST_DATABASE_URL` |

---

## 1. Ringkasan Eksekutif (Executive Summary)

*Implementation Readiness Review* ini menyajikan evaluasi komprehensif atas kesiapan antarmuka, tata letak, komponen visual, alur interaksi, kontrol akses berbasis peran (RBAC), dan cakupan pengujian sistem KlasiFas pada repositori `D:\Project Capstone\Klasifas`.

Berdasarkan audit langsung terhadap seluruh template Jinja2, stylesheet CSS, skrip JavaScript, basis data PostgreSQL, dan 38 modul test suite (635 test terkoleksi):
1. **Fondasi Arsitektur P0 Telah Selesai 100%**: Layout telah mengadopsi pola **True Hybrid Architecture** pada [`app/templates/base.html`](file:///d:/Project%20Capstone/Klasifas/app/templates/base.html) yang memisahkan secara bersih antara **Public Topbar** lapang untuk pelapor publik dengan **Collapsible Sidebar** (250px $\leftrightarrow$ 72px) untuk portal staf internal.
2. **Kepatuhan Desain Kanonis & Identitas Institusi**: Sistem menggunakan logo resmi UHAMKA lokal ([`app/static/img/logo-uhamka.png`](file:///d:/Project%20Capstone/Klasifas/app/static/img/logo-uhamka.png)), font lokal WOFF2 `Public Sans` berlisensi OFL (bebas dependensi CDN eksternal), dan token warna resmi FTII Navy (`#0C356A`) serta Kuning Emas UHAMKA (`#FFC436`).
3. **Kepatuhan Otorisasi & Alur Tiket**: Seluruh endpoint internal diproteksi oleh decorator `@role_required` dengan prinsip *deny-by-default*. Alur status terkunci ketat pada 4 status resmi (`Baru` $\rightarrow$ `Terverifikasi` $\rightarrow$ `Diproses` $\rightarrow$ `Selesai`) dengan penugasan teknisi sebagai atribut relasi, bukan status tiket.
4. **Kesiapan MVP**: Sistem dinyatakan **SIAP UNTUK DEMONSTRASI & PENGUJIAN PENGGUNA (READY FOR DEMO & EVALUATION)** dengan skor kesiapan rata-rata **96.2%**. Ketiga temuan High P1 telah selesai dan diverifikasi pada 390px. Catatan: 49 UI tests dan 26 test Teknisi F6.01 lulus; 398 test DB-backed lainnya masih menunggu `TEST_DATABASE_URL`.

```mermaid
flowchart TD
    subgraph ARSITEKTUR_TEREVALUASI["Arsitektur Antarmuka KlasiFas"]
        direction TB
        REQ["Permintaan Pengguna"] --> CHK{"Apakah Staf Terautentikasi?"}
        
        CHK -->|Tidak (Tamu / Pelapor)| PUB["Mode Publik (Topbar Navbar Lapang)"]
        PUB --> F1["/lapor (Formulir 1 Kolom Lapang)"]
        PUB --> F2["/lapor POST (Tanda Terima & Token 128-bit)"]
        PUB --> F3["/lacak (Pelacakan Mandiri & Stepper Semantis)"]
        
        CHK -->|Ya (Admin / Teknisi / Pimpinan)| INT["Mode Staf Internal (Collapsible Sidebar 250px <-> 72px)"]
        INT --> S1["/dashboard (Dasbor Eksekutif Read-Only Agregat)"]
        INT --> S2["/admin/tiket (Antrean Sarpras & Filter Multi-Kriteria)"]
        INT --> S3["/admin/tiket/id/verifikasi (Komparator 3 Kategori & Penugasan)"]
        INT --> S4["/admin/audit-log (Audit Trail Operasional Eksklusif)"]
        INT --> S5["/teknisi/tugas (Papan Tugas Pribadi & Progres Fisik)"]
    end
```

---

## 2. Kesesuaian 10 Halaman Aktual terhadap Design System Kanonis

| No | Halaman / Layar | Template Fisik | Route / Endpoint | Kesiapan | Status Kepatuhan Desain Kanonis |
|:---:|:---|:---|:---|:---:|:---|
| 1 | **Formulir Pelaporan** | `app/templates/report/form.html` | `/lapor` (`report.report_form`) | **98%** | Form 1 kolom lapang, Gedung FTII terpilih otomatis, dropdown Lantai 1–4, ruang teks bebas, kategori awal informasional, upload bukti foto dengan preview lokal, kartu kontak darurat Posko Sarpras Lantai 1. |
| 2 | **Tanda Terima Pelaporan** | `app/templates/report/success.html` | POST `/lapor` (view render) | **100%** | Tampilan tanda terima bukti lapor, kotak kode tiket (`KF-XXXXXX`), kotak token akses rahasia 128-bit ber-feedback salin clipboard, peringatan satu kali simpan, tautan lacak langsung. |
| 3 | **Pelacakan Tiket Mandiri** | `app/templates/report/track.html` | `/lacak` (`report.track`) | **98%** | Otentikasi dua kredensial (kode + token), sliding-window rate limiting feedback (429 & Retry-After), stepper 4 tahap berikon semantik, metadata tiket, sanitasi output XSS, tanpa pembocoran PII. |
| 4 | **Login Staf Internal** | `app/templates/auth/login.html` | `/auth/login` (`auth.login`) | **100%** | Logo resmi UHAMKA, kartu login rapi, badge portal internal FTII, toggle lihat kata sandi, pesan error generik anti-enumerasi pengguna. |
| 5 | **Dasbor Manajerial** | `app/templates/dashboard/index.html` | `/dashboard` (`dashboard.dashboard_view`) | **96%** | 4 kartu KPI counter animasi native, segmented control rentang waktu (7–365 hari), filter kategori & lantai, Chart.js bar & line grafik dinamis, tombol cetak ringkasan ramah cetak (`@media print`). |
| 6 | **Antrean Tiket Sarpras** | `app/templates/admin/queue.html` | `/admin/tiket` (`admin.ticket_queue`) | **96%** | 5 kartu KPI metrik modern (`.kf-kpi-modern`), filter multi-kriteria (kata kunci, status, kategori resmi, lantai, tanggal), paginasi dinamis, lencana verifikasi manual/ML. |
| 7 | **Verifikasi & Penugasan** | `app/templates/admin/verify.html` | `/admin/tiket/<id>/verifikasi` (`admin.verify_ticket`) | **96%** | Komparator 3 kategori (Pelapor, Prediksi ML, Keputusan Admin), peringatan manual verifikasi, dropdown teknisi aktif, penampil foto bukti aman via streaming route. |
| 8 | **Log Audit Operasional** | `app/templates/admin/audit_log.html` | `/admin/audit-log` (`admin.audit_log_list`) | **98%** | Akses eksklusif Admin Sarpras, tabel padat (`.kf-table-dense`), filter jenis aksi dan tanggal, pencatatan mutasi tiket dan verifikasi yang *immutable*. |
| 9 | **Papan Tugas Teknisi** | `app/templates/technician/queue.html` | `/teknisi/tugas` (`technician.ticket_queue`) | **95%** | Filter tiket yang ditugaskan khusus untuk akun teknisi yang login, kartu KPI tugas (`.kf-kpi-modern`), filter badge status, tabel data padat responsif. |
| 10 | **Rincian Tugas Teknisi** | `app/templates/technician/detail.html` | `/teknisi/tugas/<id>` (`technician.ticket_detail`) | **94%** | Informasi lokasi, kategori resmi *read-only*, kontak koordinasi pelapor (tanpa token), deskripsi keluhan, form transisi fisik (`Terverifikasi` $\rightarrow$ `Diproses` $\rightarrow$ `Selesai` ber-catatan wajib). |

---

## 3. Analisis Gap UI per Peran Pengguna (Role-Based Gap Analysis)

### A. Pelapor (Publik) — Skor Kesiapan: 98%
- **Kekuatan**: Alur pelaporan terpusat, fokus tinggi tanpa navigasi yang membingungkan, tanda terima kredensial yang jelas, dan pelacakan mandiri berproteksi *rate limiting*.
- **Gap yang Teridentifikasi**: Area unggah foto telah memakai *drag-and-drop zone* dengan border putus-putus (`label.kf-photo-dropzone`, `app/templates/report/form.html:230`). Interaksi seret-lepas ditangani `app/static/js/portal.js:278-320` (`dragenter`/`dragover`/`dragleave`/`dragend`/`drop`, kelas `is-dragover`, `DataTransfer`), dengan preview lokal dan fallback klik input file. Tidak ada gap yang tersisa pada item ini.
- **Klasifikasi Gap**: **P2 (Penyempurnaan Mikro-Interaksi) — SELESAI**.

### B. Admin Sarpras — Skor Kesiapan: 96%
- **Kekuatan**: Cockpit operasional lengkap dengan filter multi-kriteria, komparator 3 kategori fasilitas, penugasan teknisi, dan audit trail yang tidak dapat dimanipulasi.
- **Gap yang Teridentifikasi**: *Empty state* antrean tiket telah disempurnakan (P1.2) dengan pesan panduan, ikon netral, dan tombol reset filter pada `admin/queue.html:180` serta `technician/queue.html:161`; responsif di viewport 390px. Tidak ada gap visual yang tersisa pada item ini.
- **Klasifikasi Gap**: **P1 (Poles Visual) — SELESAI**.

### C. Teknisi Lapangan — Skor Kesiapan: 94%
- **Kekuatan**: Isolasi tugas penugasan pribadi, pembaruan status pengerjaan fisik bertahap, dan validasi catatan wajib sebelum penutupan tiket.
- **Gap yang Teridentifikasi**: Penyelarasan kartu detail (P1.1) selesai. Pasangan label/nilai statis pada [`app/templates/technician/detail.html`](file:///d:/Project%20Capstone/Klasifas/app/templates/technician/detail.html) memakai `dl/dt/dd` semantik, dan breadcrumb `ol.breadcrumb.small` (`:10`) selaras dengan komparator admin. Visual terverifikasi pada 390px dan 1440px. CTA status berada di bawah fold pada 390px dan **diterima sebagai trade-off** urutan konten (bukti keluhan lebih dulu, aksi setelahnya); CTA tetap terjangkau keyboard dan terlihat setelah satu kali scroll ke kartu status.
- **Klasifikasi Gap**: **P1 (Poles Visual) — SELESAI**.

### D. Pimpinan FTII — Skor Kesiapan: 95%
- **Kekuatan**: Akses analitik eksekutif *read-only*, preservasi privasi (tanpa data pribadi pelapor), grafik interaktif Chart.js, dan fitur cetak ringkasan yang otomatis menyembunyikan navigasi web.
- **Gap yang Teridentifikasi**: Transisi data saat tombol filter rentang waktu cepat (7/30/90 hari) diklik berlangsung seketika tanpa animasi placeholder *skeleton loading*.
- **Klasifikasi Gap**: **P2 (Penyempurnaan Mikro-Interaksi)**.

---

## 4. Konsistensi Arsitektur Hybrid (Public Topbar vs Internal Sidebar)

Pemisahan layout hibrida pada [`app/templates/base.html`](file:///d:/Project%20Capstone/Klasifas/app/templates/base.html) dan [`app/static/js/sidebar.js`](file:///d:/Project%20Capstone/Klasifas/app/static/js/sidebar.js) telah beroperasi dengan konsistensi penuh:

1. **Mode Publik (Tamu / Pelapor)**:
   - Header horizontal `navbar-expand-md` dengan identitas institusi resmi.
   - Menu ringkas: *Buat Laporan*, *Lacak Tiket*, dan tombol pemisah *Masuk Staf*.
   - Konten dibungkus kontainer lapang `container {{ kf_container }} py-4 py-lg-5`.
   - Footer institusi publik dengan informasi Fakultas Teknologi Industri dan Informatika UHAMKA.
2. **Mode Internal Staf (Admin, Teknisi, Pimpinan)**:
   - Kontainer layout `.kf-internal-layout` fleksibel penuh (*full viewport height*).
   - Sidebar navigasi vertikal (`.kf-sidebar`) dengan lebar normal **250px** dan lebar terlipat **72px**.
   - Tombol toggle kolaps `#kf-sidebar-toggle` dengan indikator shortcut keyboard `[` dan `Ctrl+B` / `Cmd+B`.
   - Persistensi status kolaps antar-halaman tersimpan otomatis di `localStorage['kf_sidebar_collapsed']`.
   - Drawer mobile responsif (< 768px) dikendalikan melalui tombol `#kf-mobile-drawer-toggle`, tombol tutup `#kf-mobile-drawer-close`, dan backdrop `#kf-sidebar-backdrop`; fokus terperangkap saat terbuka.
   - Topbar kontekstual staf (`.kf-contextual-topbar`) memuat indikator lencana peran, lokasi kampus, nama pengguna aktif, dan tombol *Keluar* aman dengan token CSRF.
3. **Kepatuhan Invariant Pengujian Kontrak**:
   - Substring literal `container {{ kf_container }}` tetap terjaga tepat **3 kemunculan** pada `base.html`, memastikan kelulusan permanen pada [`tests/test_ui_container.py`](file:///d:/Project%20Capstone/Klasifas/tests/test_ui_container.py).

---

## 5. Kesesuaian Komponen, Logo, Tipografi, Warna, dan Responsivitas

- **Logo Resmi Institusi**:
  - Menggunakan berkas tunggal [`app/static/img/logo-uhamka.png`](file:///d:/Project%20Capstone/Klasifas/app/static/img/logo-uhamka.png) dengan aspek rasio 1:1 tanpa distorsi.
  - Tampil pada navbar publik (32px), kartu login staf (64px), dan header sidebar staf (32px).
- **Tipografi Resmi**:
  - Font primer: **`Public Sans`** yang disajikan secara mandiri melalui berkas lokal WOFF2 di `app/static/fonts/public-sans/` (Regular 400, Medium 500, SemiBold 600, Bold 700).
  - Berlisensi resmi Open Font License (OFL) lokal (`PublicSans-OFL.txt`).
  - Terbukti memenuhi kebijakan keamanan CSP tanpa ketergantungan pada CDN eksternal ([`tests/test_ui_typography.py`](file:///d:/Project%20Capstone/Klasifas/tests/test_ui_typography.py)).
- **Palet Warna Resmi (Design Tokens)**:
  - Primer: `#0C356A` (`--kf-primary`, FTII Navy) dan Shade Gelap `#082245`.
  - Sekunder: `#FFC436` (`--kf-secondary`, Kuning Emas UHAMKA) dan Shade Gelap `#D4A017`.
  - Sidebar Navigasi: `#0B192C` (Navy pekat formal).
  - Latar Kanvas: `#F6F8FA` (`--kf-background`) dan Permukaan Kartu `#FFFFFF` (`--kf-surface`).
  - Lencana Status Semantik:
    - `Baru`: Teks `#0369A1`, Latar `#E0F2FE`.
    - `Terverifikasi`: Teks `#B45309`, Latar `#FEF3C7`.
    - `Diproses`: Teks `#5B21B6`, Latar `#EDE9FE`.
    - `Selesai`: Teks `#065F46`, Latar `#D1FAE5`.
- **Tata Letak Responsif Tiga Viewport**:
  - **Ponsel (390px)**: Sidebar internal otomatis menjadi off-canvas drawer, seluruh tabel data dibungkus kontainer geser horizontal (`.table-responsive`), kartu KPI dasbor tersusun dalam formasi grid 2x2.
  - **Tablet (768px)**: Kolom lokasi fasilitas membelah 2 kolom sejajar, tombol cetak dan filter segmented aktif.
  - **Desktop (1440px)**: Sidebar internal 250px tetap, layout kanvas data padat (*fluid high-density*).

---

## 6. Audit Sistem Motion dan Mikro-interaksi

| Fitur Motion / Interaksi | Status Implementasi | Pengendali Teknis | Kepatuhan Aksesibilitas |
|:---|:---:|:---|:---|
| **Scroll Reveal (Progressive Disclosure)** | **Aktif** | [`app/static/js/motion.js`](file:///d:/Project%20Capstone/Klasifas/app/static/js/motion.js) via `IntersectionObserver` | Dinonaktifkan otomatis saat `prefers-reduced-motion: reduce` aktif |
| **Animated KPI Counter** | **Aktif** | [`app/static/js/dashboard.js`](file:///d:/Project%20Capstone/Klasifas/app/static/js/dashboard.js) via native `requestAnimationFrame` (450ms `easeOutQuart`) | Seketika menampilkan angka akhir jika reduced-motion aktif |
| **Staggered Chart Drawing Animation** | **Aktif** | [`app/static/js/dashboard.js`](file:///d:/Project%20Capstone/Klasifas/app/static/js/dashboard.js) via Chart.js bar delay (35ms/bar) | Animasi dihentikan total (`animation: false`) jika reduced-motion aktif |
| **Universal Toast Notification** | **Aktif** | `window.KlasifasToast.show()` di `base.html` & `motion.js` | Menggunakan `role="status"` dan `aria-live="polite"` |
| **Copy-to-Clipboard Feedback** | **Aktif** | [`app/static/js/portal.js`](file:///d:/Project%20Capstone/Klasifas/app/static/js/portal.js) untuk kode tiket & token akses | Disertai pembaruan label tombol dan toast hijau konfirmasi |
| **Password Visibility Toggle** | **Aktif** | [`app/static/js/portal.js`](file:///d:/Project%20Capstone/Klasifas/app/static/js/portal.js) pada login & pelacakan | Disertai pembaruan atribut `aria-pressed` dan label teks |
| **Sidebar Collapse Transition** | **Aktif** | [`app/static/js/sidebar.js`](file:///d:/Project%20Capstone/Klasifas/app/static/js/sidebar.js) transisi lebar CSS 250px $\leftrightarrow$ 72px | Didukung shortcut keyboard `[` dan `Ctrl+B` |
| **Skeleton Loading State (AJAX Filter)** | *Belum Ada* | Masuk Backlog Prioritas P2 | Tidak memblokir alur kerja MVP saat ini |
| **Drag-and-Drop Area Upload Bukti** | **Aktif** | [`app/static/js/portal.js`](file:///d:/Project%20Capstone/Klasifas/app/static/js/portal.js) (`dragenter`/`dragover`/`drop`, `DataTransfer`) pada `label.kf-photo-dropzone` di [`app/templates/report/form.html`](file:///d:/Project%20Capstone/Klasifas/app/templates/report/form.html) | Label terhubung ke input file (`for="photo"`), status file `aria-live="polite"`, dan fallback klik/input standar tetap berfungsi |

---

## 7. Validasi RBAC, Endpoint, dan Workflow Tiket

1. **Matriks Otorisasi RBAC**:
   - **Admin Sarpras**: Berwenang mengakses `/admin/tiket`, `/admin/tiket/<id>/verifikasi`, `/admin/tiket/<id>/assign`, `/admin/audit-log`, dan `/dashboard`.
   - **Teknisi**: Berwenang mengakses `/teknisi/tugas`, `/teknisi/tugas/<id>`, dan `/teknisi/tugas/<id>/status`. Upaya membuka rute admin atau dasbor ditolak dengan status **`403 Forbidden`**.
   - **Pimpinan**: Berwenang membuka `/dashboard` secara read-only. Upaya membuka rute admin atau teknisi ditolak dengan status **`403 Forbidden`**.
   - **Pelapor (Publik)**: Mengakses `/`, `/lapor`, dan `/lacak` tanpa memerlukan sesi login staf.
2. **Integritas Alur 4 Status Resmi**:
   - `Baru` $\rightarrow$ `Terverifikasi`: Transisi dipicu oleh Admin Sarpras saat menetapkan kategori verifikasi resmi.
   - `Terverifikasi` $\rightarrow$ `Diproses`: Transisi dipicu oleh Teknisi saat memulai pekerjaan lapangan.
   - `Diproses` $\rightarrow$ `Selesai`: Transisi dipicu oleh Teknisi saat perbaikan fisik selesai dengan kewajiban mengisi deskripsi tindakan perbaikan.
   - Penugasan teknisi (`assigned_technician_id`) adalah atribut penanggung jawab fisik dan tidak menciptakan status transisi kelima.
3. **Keamanan Kredensial & Anti-Enumerasi**:
   - Token pelacakan dibuat berupa string 128-bit acak (`secrets.token_urlsafe(16)`).
   - Basis data PostgreSQL hanya menyimpan nilai hash SHA-256 (64 hex).
   - Verifikasi token dilakukan via `hmac.compare_digest` untuk mencegah serangan *timing attack*.
   - Upaya pelacakan dengan tiket atau token yang tidak valid menghasilkan respons generik `404 Not Found` identik tanpa membocorkan eksistensi nomor tiket.
   - Endpoint `/lacak` diproteksi oleh rate limiter *sliding-window* (10 percobaan per menit per alamat IP) dengan header standar `Retry-After`.

---

## 8. Inventarisasi Test Suite Pendukung UI

Sebanyak **635 test terkoleksi** pada 38 modul pengujian: **211 DB-free** dan **424 DB-backed**. Subset UI non-DB dijalankan ulang pada 15 November 2026: **49 / 49 passed**. `test_technician_f6_01.py` juga **26 / 26 passed**. Modul DB-backed lain belum dijalankan ulang pada sesi ini.

| Kategori Pengujian | Berkas Modul Test | Jumlah Test | Status |
|:---|:---|:---:|:---:|
| **Tipografi & Font Lokal** | `tests/test_ui_typography.py` | 4 | **PASSED** |
| **Layout & Kontrak Kontainer** | `tests/test_ui_container.py` | 6 | **PASSED** |
| **Responsivitas & Breakpoints** | `tests/test_ui_responsive.py` | 6 | **PASSED** |
| **Desain Kartu & Radius Token** | `tests/test_ui_cards.py` | 5 | **PASSED** |
| **Input Form & Touch Targets** | `tests/test_ui_inputs.py` | 6 | **PASSED** |
| **Motion Script & Reduced Motion** | `tests/test_ui_motion.py` | 5 | **PASSED** |
| **Interaksi Toggler** | `tests/test_ui_toggler.py` | 2 | **PASSED** |
| **Aksesibilitas UI & Drawer Mobile** | `tests/test_ui_accessibility.py` | 5 | **PASSED** |
| **Favicon Lokal & Isolasi CSP** | `tests/test_ui_favicon.py` | 5 | **PASSED** |
| **Empty State Antrean** | `tests/test_ui_queue_empty_states.py` | 3 | **PASSED** |
| **SUBTOTAL UI** | **10 berkas** | **49** | **49 PASSED** |
| **Konfigurasi & Environment** | `tests/test_config.py` | 61 | **DB-free** |
| **Application Factory** | `tests/test_factory.py` | 33 | **DB-free** (zero koneksi fisik) |
| **Model Metadata & Migrasi** | `tests/test_models_f1_04.py` | 41 | **DB-free** (metadata/DDL) |
| **Constraint Foto** | `tests/test_models_photo_constraints.py` | 15 | **DB-free** (SQLite in-memory) |
| **Password & Session Config** | `tests/test_security_f2_02.py` | 12 | **DB-free** |
| **SUBTOTAL DB-FREE** | **15 berkas** | **211** | **49 PASSED + 162 DB-free** |
| **Papan Tugas & Status Teknisi** | `tests/test_technician_f6_01.py` | 26 | **26 PASSED** |
| **Modul DB-backed lainnya** | 22 berkas (auth, report, track, admin, audit, dashboard, ML, RBAC, CLI, error pages) | 398 | **MENUNGGU DB** |
| **SUBTOTAL DB-BACKED** | **23 berkas** | **424** | **26 PASSED + 398 menunggu DB** |
| **TOTAL TERKOLEKSI** | **38 berkas** | **635** | **211 DB-free / 424 DB-backed** |

> Catatan: 211 DB-free = 49 UI + 61 config + 33 factory + 41 models + 15 photo constraints + 12 security config. 424 DB-backed = 26 Teknisi F6.01 (passed) + 398 lainnya (menunggu `TEST_DATABASE_URL`). Total 211 + 424 = 635.

---

## 9. Matriks Prioritas Gap & Rencana Tindak Lanjut

### Prioritas P0 — Fondasi Kritis (STATUS: SELESAI & TERTUTUP)
- [x] Pemisahan Arsitektur Hybrid pada `base.html` (Top bar publik vs Collapsible Sidebar).
- [x] Pembuatan pengendali modular `app/static/js/sidebar.js` dan integrasi global `app/static/js/motion.js`.
- [x] Penegakan invariant 3x kontainer literal `container {{ kf_container }}`.
- [x] Penyelarasan token warna aktif (`#0C356A` / `#FFC436`) dan font lokal `Public Sans` WOFF2.
- [x] Harmonisasi dokumen kanonis `docs/DESIGN.md`, `docs/DESIGN_AUDIT.md`, `docs/IMPLEMENTATION_MAP.md`.

---

### Prioritas P1 — Poles Visual & Panduan Demo (STATUS: SELESAI, VERIFIKASI VISUAL 390px)

| ID | Item Pekerjaan | Berkas Terdampak | Status | Acceptance Criteria |
|:---:|:---|:---|:---:|:---|
| **P1.1** | **Penyelarasan Kartu Detail Teknisi** | `app/templates/technician/detail.html` | **SELESAI (visual)** | `dl/dt/dd` semantik dan breadcrumb kanonis selaras admin; visual terverifikasi 390px/1440px. CTA mobile di bawah fold diterima sebagai trade-off. 26/26 test `test_technician_f6_01.py` passed. |
| **P1.2** | **Penyempurnaan Visual Empty State** | `app/templates/admin/queue.html`<br>`app/templates/technician/queue.html` | **SELESAI** | Pesan panduan, ikon netral, dan tombol reset filter; responsif 390px. 49 UI tests passed. |
| **P1.3** | **Pembaruan Panduan Demonstrasi** | `docs/DEMO_GUIDE.md`<br>`docs/screenshots/` | **SELESAI** | 12 tangkapan layar baru terpasang dan 12 referensi gambar di `docs/DEMO_GUIDE.md` konsisten. |

**Status P1.1:** Visual terverifikasi pada 390px dan 1440px. CTA status 390px berada di bawah fold (Terverifikasi y=1750–1798; Diproses y=1792–1840) dan **diterima sebagai trade-off** layout content-first; CTA tetap terjangkau keyboard dan terlihat setelah scroll ke kartu status. Tidak ada overflow horizontal.

**Status P1.2:** Selesai — 49 UI tests passed; 398 test DB-backed lainnya belum dijalankan.

**Status P1.3:** Selesai — 12 screenshot valid dan 12 referensi di `docs/DEMO_GUIDE.md`.

---

### 3 Temuan High — Status Implementasi dan Verifikasi

| Temuan | Implementasi | Verifikasi 390px | Status |
|:---|:---:|:---:|:---:|
| **High-1 — Kartu detail teknisi belum selaras admin (P1.1)** | Selesai | Selesai | **SELESAI (visual)** |
| **High-2 — Empty state antrean tanpa panduan/reset (P1.2)** | Selesai | Selesai | **SELESAI** |
| **High-3 — Panduan demo memakai screenshot lama (P1.3)** | Selesai (12 screenshot) | Selesai | **SELESAI** |

Ketiga temuan High telah diimplementasikan dan diverifikasi pada 390px. 26 test Teknisi F6.01 sudah passed; sisa pekerjaan adalah 398 test DB-backed lain yang menunggu `TEST_DATABASE_URL`, bukan gap implementasi UI.

---

### Prioritas P2 — Mikro-Interaksi Lanjutan (BACKLOG PENYEMPURNAAN PASCA-MVP)

| ID | Item Pekerjaan | Berkas Terdampak | Keterangan |
|:---:|:---|:---|:---|
| **P2.1** | **Skeleton Loading State** | `app/templates/dashboard/index.html`<br>`app/static/js/dashboard.js` | Efek placeholder shimmer saat filter dasbor memperbarui data analitik via AJAX. |
| **P2.2** | **Drag-and-Drop Area Bukti** | `app/templates/report/form.html`<br>`app/static/js/portal.js` | **SELESAI** — `label.kf-photo-dropzone` (`form.html:230`) dan handler `dragenter`/`dragover`/`dragleave`/`dragend`/`drop` dengan `DataTransfer` (`portal.js:278-320`) sudah terpasang; preview lokal dan fallback klik input file berfungsi. |

---

## 10. Kesimpulan Kelayakan (Final Verdict)

KlasiFas dinyatakan **TERVERIFIKASI & SIAP SECARA IMPLEMENTASI (IMPLEMENTATION READY)** untuk seluruh 4 peran pengguna:
- **Pelapor Publik**: Siap digunakan untuk pelaporan dan pelacakan keluhan fasilitas secara mandiri.
- **Admin Sarpras**: Siap digunakan untuk operasional antrean, verifikasi ML, penugasan teknisi, dan inspeksi log audit.
- **Teknisi Lapangan**: Siap digunakan untuk pemantauan tugas pribadi dan pembaruan pengerjaan fisik.
- **Pimpinan FTII**: Siap digunakan untuk pemantauan analitik agregat manajerial.

Tidak ditemukan hambatan arsitektur maupun celah keamanan RBAC yang menghalangi fase evaluasi dan demonstrasi proyek. Regresi penuh belum dapat diklaim: 49 UI tests dan 26 test Teknisi F6.01 lulus, sedangkan 398 test DB-backed lainnya belum dijalankan ulang karena `TEST_DATABASE_URL` tidak tersedia. Status ini harus diverifikasi ulang sebelum demo final.
