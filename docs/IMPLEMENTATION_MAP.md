# KlasiFas — Design-to-Flask Implementation Map

**Tujuan:** peta kerja kanonis untuk penerapan dan pemeliharaan antarmuka desain pada sistem Flask tanpa mengubah backend, skema basis data, atau business logic.

**Status:** Terverifikasi 100% pada working tree repositori `D:\Project Capstone\Klasifas`. Seluruh path berkas, template Jinja2, controller JavaScript, file CSS, route Flask, dan permission decorator RBAC telah dicocokkan langsung dan divalidasi melalui 252 unit test.

## 1. Global foundation

| Komponen Desain | Path Berkas Aktual | Status & Catatan Implementasi |
|---|---|---|
| Global layout / public + internal shell | `app/templates/base.html` | Terverifikasi: Arsitektur Hybrid (Public Topbar vs Internal Collapsible Sidebar), mematuhi invariant 3x `container {{ kf_container }}` |
| Global CSS tokens/components | `app/static/css/klasifas.css` | Terverifikasi: Berisi token warna resmi (`#0C356A`, `#FFC436`), tata letak responsif, dan styling kartu modern |
| Sidebar controller | `app/static/js/sidebar.js` | Terverifikasi: Pengendali modular toggle sidebar, shortcut keyboard (`[` / `Ctrl+B`), drawer mobile, dan sinkronisasi `localStorage` |
| Public form controller | `app/static/js/portal.js` | Terverifikasi: Pengendali formulir pelaporan publik dan upload preview |
| Motion & Interaction controller | `app/static/js/motion.js` | Terverifikasi: Pengendali global animasi scroll reveal dan fallback `prefers-reduced-motion` |
| Shared status/card macros | `app/templates/components/_macros.html` | Terverifikasi: Makro `status_badge` untuk empat status resmi |
| Official institutional logo | `app/static/img/logo-uhamka.png` | Terverifikasi: Logo resmi UHAMKA disajikan dari aset lokal statis (bebas CDN) |
| Local fonts | `app/static/fonts/public-sans/` | Terverifikasi: Font lokal Public Sans WOFF2 (Regular, Medium, SemiBold, Bold) berlisensi OFL |
| Local icons & vendor assets | `app/static/vendor/` | Terverifikasi: Bootstrap 5.3 bundle & Bootstrap Icons lokal (bebas CDN) |

## 2. Page mapping by role

| Role / Screen | Template Fisik Terverifikasi | Route & Endpoint | JS/CSS Terkait | Backend Contract yang Dipertahankan |
|---|---|---|---|---|
| **Login Staf** | `app/templates/auth/login.html` | `/auth/login` (`auth.login`) | `klasifas.css` | Endpoint login, session staf, password hashing scrypt, role redirect, CSRF, generic error |
| **Dashboard Pimpinan** | `app/templates/dashboard/index.html` | `/dashboard` (`dashboard.dashboard_view`) | `dashboard.js`, Chart.js, `sidebar.js` | Data agregat, filter periode/kategori/lantai, read-only Pimpinan & Admin, tanpa eksposur PII |
| **Admin — Antrean** | `app/templates/admin/queue.html` | `/admin/tiket` (`admin.ticket_queue`) | `sidebar.js`, `klasifas.css` | Filter multi-kriteria, pagination, detail link, permission `@role_required("admin_sarpras")` |
| **Admin — Verifikasi** | `app/templates/admin/verify.html` | `/admin/tiket/<id>/verifikasi` (`admin.verify_ticket`) | `sidebar.js`, `klasifas.css` | Rekomendasi ML, keputusan kategori Admin, assignment teknisi, transisi `Baru` $\rightarrow$ `Terverifikasi` |
| **Admin — Audit Log** | `app/templates/admin/audit_log.html` | `/admin/audit-log` (`admin.audit_log_view`) | `sidebar.js`, `klasifas.css` | Akses baca eksklusif Admin Sarpras; immutable audit log trail |
| **Teknisi — Antrean** | `app/templates/technician/queue.html` | `/teknisi/tugas` (`technician.ticket_queue`) | `sidebar.js`, `klasifas.css` | Filter tiket yang ditugaskan khusus untuk akun teknisi yang sedang login |
| **Teknisi — Detail** | `app/templates/technician/detail.html` | `/teknisi/tugas/<id>` (`technician.ticket_detail`) | `sidebar.js`, `klasifas.css` | Catatan tindakan lapangan wajib, foto opsional, kategori read-only, transisi status fisik |
| **Pelapor — Form** | `app/templates/report/form.html` | `/lapor` (`report.report_form`) | `portal.js`, `klasifas.css` | Gedung FTII, lantai 1–4, ruang teks bebas, detail opsional, foto opsional, kategori awal informasional |
| **Pelapor — Receipt** | `app/templates/report/success.html` | POST `/lapor` (view render) | `portal.js`, `klasifas.css` | Kode tiket (`KF-XXXXXX`) + token rahasia 128-bit (`token_urlsafe(16)`); hash SHA-256 64-hex disimpan di DB |
| **Pelapor — Tracking** | `app/templates/report/track.html` | `/lacak` (`report.track`) | `portal.js`, `klasifas.css` | Pasangan kredensial kode + token; anti-enumeration generic 404; sliding-window rate limiting |

## 3. Implementasi bertahap & Status Verifikasi

### Tahap A — Baseline dan Kontrak [SELESAI]
- Seluruh dokumen acuan (`AGENTS.md`, `PRD.md`, `SECURITY.md`, `TECHSTACK.md`, `DESIGN.md`) telah disinkronkan.
- Seluruh path dan endpoint pada tabel di atas telah terverifikasi 100% pada repositori fisik.
- Tidak ada perubahan pada backend, schema, migrasi, endpoint, atau business logic.

### Tahap B — Global Design Foundation [SELESAI]
- Variabel CSS token disatukan pada `klasifas.css` (`--kf-primary: #0c356a`, `--kf-secondary: #ffc436`).
- Template `base.html` menerapkan Arsitektur Hybrid (Public Topbar vs Internal Collapsible Sidebar 250px $\rightarrow$ 72px) dengan invariant 3x `container {{ kf_container }}`.
- Logo resmi UHAMKA disajikan secara lokal di `app/static/img/logo-uhamka.png`.
- Reduced-motion, transisi interaktif, dan navigasi keyboard terverifikasi via `test_ui_motion.py`.

### Tahap C — Halaman per Role [SELESAI]
- **Login Staf**: Terverifikasi pada `app/templates/auth/login.html` dengan logo institusi resmi.
- **Pelapor**: Formulir, tanda terima kode/token 128-bit, dan pelacakan tiket mandiri terverifikasi pada `form.html`, `success.html`, dan `track.html`.
- **Admin Sarpras**: Antrean tiket, verifikasi/rekomendasi ML, penugasan teknisi, dan Audit Log terverifikasi pada `queue.html`, `verify.html`, dan `audit_log.html`.
- **Teknisi**: Papan tugas pribadi dan rincian pengerjaan fisik terverifikasi pada `queue.html` dan `detail.html`.
- **Pimpinan**: Dashboard eksekutif agregat read-only terverifikasi pada `dashboard/index.html`.

### Tahap D — Verifikasi Menyeluruh [SELESAI]
- Seluruh 252 unit test pada 18 file pengujian lulus 100% tanpa regresi (`pytest`).
- Kontrak tipografi lokal Public Sans WOFF2 diverifikasi lulus via `test_ui_typography.py`.
- Uji 4 role dan akses negatif (RBAC) terbukti menolak akses ilegal (`403 Forbidden`).
- Pelacakan tiket dengan rate limiting sliding-window dan proteksi token konstan terverifikasi via `test_track_f3_04.py`.

## 4. Definition of Done

- Dokumen `docs/DESIGN.md` menjadi **Satu-satunya Acuan Desain Kanonis**.
- Direktori `docs/ui-ux-reference/stitch/` berstatus **Arsip Visual Historis** dan tidak menjadi acuan teknis.
- Semua halaman memakai design tokens kanonis resmi FTII UHAMKA.
- Semua role mematuhi matriks RBAC dan prinsip deny-by-default.
- Tidak ada placeholder link/button atau data mockup yang tampil sebagai data produksi.
- Tidak ada klaim SLA, ML performance fiktif, kontak personal, integrasi, SOP, atau inventaris yang belum diverifikasi.
- Seluruh 252 pengujian unit test lulus 100%.
- Tidak ada perubahan backend, endpoint, maupun database yang tidak disetujui.
