---
name: KlasiFas Design System
version: 2.0.0
canonical: true
status: consolidated-design-handoff
product: KlasiFas
institution: FTII UHAMKA
device_targets:
  desktop: 1440px
  mobile: 390px
---

# KlasiFas — Canonical Design System

Dokumen ini menjadi satu acuan desain kanonis tunggal untuk seluruh role KlasiFas yang disintesis dari kebutuhan antarmuka FTII UHAMKA. Aturan role di bawah disusun terpisah agar batasan RBAC satu role tidak tertukar dengan role lain.

**Cakupan produk:** sistem akademik MVP untuk pelaporan, klasifikasi, pemantauan, verifikasi, penugasan, dan tindak lanjut keluhan fasilitas di Gedung FTII UHAMKA, Lantai 1–4. Dokumen ini adalah spesifikasi desain, bukan bukti bahwa seluruh fitur, data, model ML, SLA, integrasi, atau infrastruktur sudah berjalan.

## 1. Prinsip kanonis

1. Satu identitas produk: **KlasiFas — FTII UHAMKA**.
2. Gunakan satu logo resmi UHAMKA saja (`logo-uhamka.png` dari aset lokal proyek); jangan menumpuk logo atau menggunakan placeholder/URL eksternal.
3. Satu gedung: **Gedung FTII**. Pilihan lantai hanya **Lantai 1–4**.
4. Empat status tiket resmi: **Baru → Terverifikasi → Diproses → Selesai**. Penugasan teknisi bukan status kelima.
5. Kategori yang dipilih pelapor adalah informasi awal opsional. Kategori operasional berasal dari rekomendasi Naive Bayes dan verifikasi/koreksi Admin Sarpras.
6. Dashboard Pimpinan bersifat read-only dan hanya menampilkan agregat yang menjaga privasi.
7. Teknisi hanya dapat mengakses tiket yang ditugaskan kepadanya; tidak dapat mengubah kategori terverifikasi atau membaca Audit Log operasional.
8. Admin Sarpras adalah satu-satunya role yang memiliki akses baca ke Audit Log operasional.
9. Jangan menampilkan metrik, SLA, akurasi model, confidence, kontak, integrasi, SOP, atau klaim keamanan yang belum dibuktikan oleh implementasi/dokumen proyek.
10. Seluruh data pada mockup harus diberi label **Data Sampel Ilustratif MVP**. Jangan menganggap angka mockup sebagai data aktual.
11. Direktori referensi desain `docs/ui-ux-reference/stitch/` berstatus **arsip visual historis**, bukan spesifikasi implementasi kanonis. Seluruh implementasi antarmuka wajib mengacu pada dokumen ini dan token lokal proyek.

## 2. Visual tokens

### 2.1 Warna

Nilai warna disinkronkan secara presisi dengan variabel CSS aktif pada [`app/static/css/klasifas.css`](file:///d:/Project%20Capstone/Klasifas/app/static/css/klasifas.css):

| Token | Nilai Hex | Variabel CSS | Penggunaan |
|---|---|---|---|
| Primary | `#0C356A` | `--kf-primary` | Warna primer FTII Navy, tombol utama, tautan aktif |
| Primary dark | `#082245` | `--kf-primary-dark` | State hover/pressed tombol primer |
| Primary soft | `#E6EEF9` | `--kf-primary-soft` | Background aksen primer lembut |
| Secondary | `#FFC436` | `--kf-secondary` | Warna sekunder Kuning Emas UHAMKA, aksen sorotan |
| Secondary dark | `#D4A017` | `--kf-secondary-dark` | State hover/aksen sekunder gelap |
| Secondary soft | `#FFF6DD` | `--kf-secondary-soft` | Background aksen sekunder lembut |
| Internal sidebar | `#0B192C` | `--kf-sidebar-bg` | Navigasi sidebar internal staf |
| Background | `#F6F8FA` | `--kf-background` | Latar kanvas aplikasi utama |
| Surface | `#FFFFFF` | `--kf-surface` | Kartu putih, form panel, modal surface |
| Surface subtle | `#F1F4F9` | `--kf-surface-subtle` | Surface panel dan area sekunder |
| Text primary | `#1F2937` | `--kf-text` | Teks utama berkontras tinggi |
| Text muted | `#4B5563` | `--kf-text-muted` | Teks sekunder, label pembantu, deskripsi |
| Border default | `#E5E7EB` | `--kf-border` | Garis pembatas kartu dan kontainer default |
| Border strong | `#D1D5DB` | `--kf-border-strong` | Border form kontrol dan penegas batas |
| Focus ring | `rgba(12, 53, 106, 0.15)` | `--kf-focus-ring` | Aksen cincin fokus aksesibilitas keyboard |

### 2.2 Status tiket

| Status | Teks / Aksen | Latar Badge | Variabel Token | Makna Operasional |
|---|---|---|---|---|
| Baru | `#0369A1` / `#64748B` | `#E0F2FE` | `--kf-status-baru-bg/text` | Laporan baru diterima sistem |
| Terverifikasi | `#B45309` / `#D97706` | `#FEF3C7` | `--kf-status-verif-bg/text` | Kategori diverifikasi Admin Sarpras |
| Diproses | `#5B21B6` / `#2563EB` | `#EDE9FE` | `--kf-status-proses-bg/text` | Pekerjaan fisik ditangani Teknisi |
| Selesai | `#065F46` / `#059669` | `#D1FAE5` | `--kf-status-selesai-bg/text` | Tindakan tuntas dan tiket ditutup |

Warna status harus konsisten di badge, timeline, tabel, kartu, chart legend, dan mobile view. Jangan menciptakan status tambahan seperti “Ditugaskan”.

### 2.3 Tipografi

- Font utama: **`Public Sans`** (tersedia lokal dalam format WOFF2 di `app/static/fonts/public-sans/` dengan lisensi OFL lokal), fallback `system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif`.
- Bobot font yang tersedia: Regular (400), Medium (500), SemiBold (600), dan Bold (700).
- Font monospace: `SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace` (tersedia via token `--kf-font-monospace`), khusus untuk kode tiket dan token akses bila membantu keterbacaan.
- H1: 28px / 1.25 / 700.
- H2: 22px / 1.3 / 700.
- H3: 18px / 1.35 / 600.
- Body: 14px / 1.5 / 400.
- Small: 12px / 1.4 / 500.
- Caption: 11px / 1.3 / 600.

### 2.4 Layout dan komponen

| Elemen | Desktop | Mobile |
|---|---:|---:|
| Target viewport | 1440px | 390px |
| Sidebar expanded | 250px | Tidak digunakan sebagai sidebar permanen |
| Sidebar collapsed | 72px | Drawer/menu responsif |
| Topbar internal | 64px | Header 56px |
| Bottom navigation | — | 64px bila sesuai pola role |
| Minimum touch target | — | 48px |

- Gunakan light content area dengan dark navy internal navigation (Premium Modern + Hybrid).
- Gunakan radius, spacing, shadow, dan komponen bersama secara konsisten; hindari dekorasi berlebihan.
- Layout desktop dan mobile harus memiliki field, label, kategori, status, serta aturan bisnis yang sama.
- Jangan menambahkan menu mobile yang tidak memiliki halaman/aksi aktual.

## 3. Motion & Interaction

Motion & Interaction adalah spesifikasi lintas halaman, bukan halaman/fitur produk tersendiri.

- Navigasi sidebar: transisi lebar 250px ↔ 72px; mobile drawer hanya saat diperlukan.
- Button: hover, focus-visible, pressed, disabled, dan loading.
- Form: focus, validation, upload preview, submission, success, dan error.
- KPI/chart: animasi singkat dan tidak menghalangi pembacaan data.
- Toast/dialog: feedback jelas, dapat diakses keyboard, dan tidak menutupi aksi penting.
- Skeleton hanya saat data benar-benar sedang dimuat; jangan gunakan sebagai dekorasi permanen.
- Terapkan `prefers-reduced-motion`: nonaktifkan animasi non-esensial, looping shimmer, scaling, dan perpindahan spasial; informasi tetap tersedia tanpa animasi.
- Jangan menyalin prototipe HTML Stitch langsung ke Flask. Implementasi menggunakan CSS/JS lokal proyek, bukan CDN eksternal.

## 4. Arsitektur role dan batas akses

### 4.1 Pelapor (publik)

**Halaman:** Form Pelaporan, Tanda Terima, Pelacakan Tiket.

- Tidak memerlukan login staf.
- Mengirim laporan untuk Gedung FTII; lantai dropdown Lantai 1–4; nama ruang free-text; detail lokasi tambahan opsional.
- Kategori pilihan pelapor bersifat opsional dan informasional.
- Foto bukti opsional.
- Setelah laporan berhasil, tampilkan kode tiket resmi (format `KF-XXXXXX`) dan token rahasia 128-bit (`token_urlsafe(16)`, sekitar 22 karakter URL-safe base64). Nilai hash SHA-256 (64 karakter heksadesimal) disimpan di basis data, sedangkan token asli hanya diperlihatkan satu kali pada tanda terima konfirmasi.
- Pelacakan memerlukan kombinasi kode tiket + token rahasia yang valid.
- Hanya tampilkan tiket yang cocok dengan kedua kredensial tersebut. Jangan bocorkan nama/identitas pelapor, tiket orang lain, atau informasi internal.
- Jangan tampilkan tombol simulasi/testing pada UI produksi.

### 4.2 Admin Sarpras

**Halaman:** Antrean Tiket, Verifikasi & Penugasan, Audit Log.

- Memantau antrean laporan.
- Meninjau deskripsi dan rekomendasi kategori Naive Bayes.
- Memverifikasi atau mengoreksi kategori resmi.
- Menetapkan teknisi/responsible person.
- Memantau perubahan status dan tindak lanjut.
- Memiliki akses baca Audit Log operasional.
- Hanya gunakan filter, kategori, prioritas, SLA, ekspor, atau metrik jika benar-benar didukung PRD/backend. Jangan mengarang angka, target SLA, atau akurasi model.

### 4.3 Teknisi

**Halaman:** Dashboard Tugas, Detail Tiket/Pembaruan Progres.

- Hanya melihat tiket yang ditugaskan kepada akun teknisi tersebut.
- Kategori resmi read-only; tidak dapat memverifikasi atau mengubah kategori.
- Tidak dapat membuka Audit Log operasional.
- Catatan tindakan lapangan wajib diisi, tanpa batas minimum karakter arbitrer.
- Foto dokumentasi hasil pekerjaan opsional.
- Aksi progres yang ditampilkan mengikuti workflow aktual; desain saat ini membedakan “Tetap Diproses” dan “Selesaikan Pekerjaan”.
- Penugasan teknisi adalah atribut penanggung jawab, bukan status tiket.
- Jangan menambahkan SLA countdown, prioritas PBM, inventaris/suku cadang, SOP khusus, atau metrik performa yang belum didukung proyek.

### 4.4 Pimpinan/Kaprodi

**Halaman:** Dashboard Pemantauan Manajerial.

- Read-only; tidak ada aksi edit, verifikasi, penugasan, atau perubahan status.
- Menampilkan agregat jumlah tiket, distribusi status, tren, kategori, dan lantai hanya jika datanya tersedia dan definisinya jelas.
- Menjaga privasi: jangan menampilkan identitas atau deskripsi yang dapat mengidentifikasi pelapor.
- Hindari angka contoh yang tampak seperti data produksi; labeli data sampel dengan jelas.
- Tidak mengakses detail identitas atau Audit Log operasional.

### 4.5 Login Staf

- Satu halaman autentikasi untuk Admin Sarpras, Teknisi, dan Pimpinan/Kaprodi.
- Pelapor publik tidak diarahkan ke login staf.
- Field dan aturan validasi harus mengikuti mekanisme autentikasi Flask yang sudah ada.
- Jangan menambahkan SSO, integrasi direktori, registrasi, reset password, MFA, atau aturan password baru jika belum ada di proyek.
- Pesan gagal login tidak boleh membocorkan apakah username terdaftar.

## 5. Workflow tiket

Alur status resmi:

`Baru → Terverifikasi → Diproses → Selesai`

- Baru: laporan diterima.
- Terverifikasi: kategori telah diproses melalui rekomendasi model dan diverifikasi Admin.
- Diproses: penanganan teknisi berlangsung.
- Selesai: pekerjaan ditutup sesuai aturan aplikasi.

Detail transisi, siapa yang dapat memicu perubahan, dan syarat penutupan harus mengikuti PRD serta service/route aktual. Dokumen desain tidak boleh menciptakan transisi atau aktor baru.

## 6. Aturan data, konten, dan klaim

- Gedung: hanya Gedung FTII; lantai 1–4.
- Nama ruang: teks bebas, bukan dropdown daftar ruangan tetap.
- Kategori resmi: gunakan daftar K1–K7 yang sudah disahkan di PRD/backend; jangan menyalin daftar kategori mockup yang belum tervalidasi.
- Kode tiket: ikuti format yang sudah diimplementasikan; jangan menetapkan format baru dari mockup.
- Token pelacakan: token rahasia pengguna dibuat menggunakan `secrets.token_urlsafe(16)` (sekitar 22 karakter base64url, 128-bit entropi). Basis data PostgreSQL hanya menyimpan nilai hash SHA-256 (64 karakter heksadesimal). Verifikasi dilakukan dengan pencocokan hash *constant-time* via `hmac.compare_digest`.
- Jangan menampilkan email, nomor ekstensi, alamat helpdesk, nama pejabat, server/node, SLA, jam layanan, response-time, akurasi/F1-score, confidence, dataset size, atau klaim integrasi tanpa sumber yang sah.
- Semua identitas dan angka pada mockup harus diberi label data ilustratif.

## 7. Aset dan implementasi

- Gunakan aset logo lokal `app/static/img/logo-uhamka.png` (nama/path diverifikasi tersedia di repo).
- Gunakan CSS, JavaScript, ikon, dan font lokal yang sudah tersedia atau disetujui proyek. Jangan menambahkan CDN sebagai dependensi runtime.
- Folder `docs/ui-ux-reference/stitch/` merupakan arsip artefak eksplorasi visual awal, bukan acuan teknis kanonis. Pengembang dilarang menggunakan utilitas Tailwind atau CDN eksternal dari folder tersebut.
- Jangan mengubah endpoint, model, skema database, autentikasi, RBAC, atau business logic hanya untuk menyesuaikan mockup.
- Jika desain tidak sesuai perilaku backend yang ada, tandai sebagai gap untuk keputusan; jangan diam-diam mengubah backend.

## 8. Checklist penerimaan desain

- [ ] Branding KlasiFas — FTII UHAMKA konsisten; satu logo resmi.
- [ ] Warna, tipografi, spacing, radius, sidebar dan topbar mengikuti token kanonis.
- [ ] Desktop dan mobile memiliki field serta business rules yang identik.
- [ ] Empat status resmi saja.
- [ ] Pelapor hanya dapat melacak dengan kode tiket + token valid.
- [ ] Kategori pilihan pelapor tidak dianggap kategori final.
- [ ] Admin dapat verifikasi/koreksi kategori dan mengelola penugasan sesuai hak akses.
- [ ] Audit Log hanya dapat dibaca Admin Sarpras.
- [ ] Teknisi hanya melihat tiket penugasannya; kategori read-only.
- [ ] Pimpinan hanya melihat agregat anonim dan read-only.
- [ ] Tidak ada SLA, angka model, kontak, integrasi, atau SOP fiktif.
- [ ] Tidak ada menu, tautan, atau tombol placeholder.
- [ ] Reduced-motion dan keyboard focus tersedia.
- [ ] Prototipe Stitch tidak disalin mentah ke produksi.
