# UI/UX & Design System Specification

**KlasiFas — Klasifikasi Keluhan Fasilitas Kampus**

| Metadata | Keterangan |
|---|---|
| Proyek | KlasiFas — Klasifikasi Keluhan Fasilitas Kampus |
| Institusi | FTII UHAMKA |
| Kelompok | 7 |
| Versi | 1.2 |
| Status | Approved Draft — Kelompok 7 Review |
| Dokumen Acuan | PRD.md v1.3, TECHSTACK.md v1.3, SECURITY.md v1.0 |

> **Tujuan Dokumen**
>
> Dokumen ini menjadi pedoman rancangan antarmuka, pengalaman pengguna, dan sistem visual KlasiFas. Seluruh rancangan harus mengikuti kebutuhan fungsional PRD, arsitektur teknologi TECHSTACK, dan batasan keamanan SECURITY.
>
> Dokumen ini membedakan kebutuhan yang sudah memiliki dasar, rekomendasi visual sementara, serta keputusan desain yang masih berstatus TBD.

---

## 1. Prinsip Desain dan Identitas Visual

### 1.1 Karakter Visual Produk

KlasiFas dirancang sebagai sistem informasi pengaduan fasilitas kampus yang mengutamakan kemudahan penggunaan, kejelasan informasi, dan efisiensi proses penanganan keluhan.

Karakter desain yang digunakan:

**Akademis dan Formal**
- Menggunakan tampilan profesional yang sesuai dengan lingkungan perguruan tinggi.
- Memiliki struktur halaman yang konsisten dan mudah dipahami.
- Menghindari dekorasi visual yang tidak mendukung fungsi aplikasi.

**Fungsional dan Efisien**
- Menempatkan tindakan utama pada posisi yang mudah ditemukan.
- Menyederhanakan proses pelaporan keluhan.
- Menampilkan informasi berdasarkan kebutuhan setiap peran pengguna.
- Mengutamakan keterbacaan tabel, formulir, dan ringkasan informasi.

**Informatif dan Transparan**
- Menampilkan status penanganan tiket secara jelas.
- Menggunakan istilah yang mudah dipahami pengguna nonteknis.
- Memperlihatkan informasi penanganan sesuai hak akses pengguna.
- Memisahkan rekomendasi Machine Learning dari keputusan verifikasi Admin Sarpras.

### 1.2 Prinsip Pengalaman Pengguna

Rancangan UI/UX mengikuti prinsip berikut:

1. **Consistency:** komponen dan pola navigasi memiliki tampilan serta perilaku yang konsisten.
2. **Clarity:** informasi penting, status tiket, dan tindakan pengguna ditampilkan dengan jelas.
3. **Efficiency:** jumlah langkah untuk melakukan tindakan utama dibuat sesederhana mungkin.
4. **Accessibility:** teks, tombol, warna, dan elemen interaktif harus mudah digunakan.
5. **Responsive:** tampilan menyesuaikan ukuran layar desktop, tablet, dan ponsel.
6. **Privacy and Security:** antarmuka hanya menampilkan informasi yang boleh diakses oleh peran pengguna.

### 1.3 Target Kebergunaan

Evaluasi kebergunaan menggunakan instrumen System Usability Scale (SUS).

**Target proyek:**
- Skor SUS minimal 68.
- Pengujian dilakukan kepada responden yang mewakili pengguna sistem.
- Hasil evaluasi digunakan untuk mengidentifikasi kesulitan navigasi, keterbacaan informasi, dan kemudahan penggunaan.

Nilai 68 merupakan target evaluasi proyek, bukan hasil pengujian yang sudah dicapai.

---

## 2. Palet Warna dan Identitas Visual

### 2.1 Warna Primer dan Sekunder

Palet warna berikut merupakan keputusan final dan selaras dengan token CSS aktual di `app/static/css/klasifas.css` (direkonsiliasi pada VQ-11).

| Elemen | Nama Warna | Kode Hex | Token CSS | Penggunaan |
|---|---|---|---|---|
| Primary | Deep Navy Blue | #0C356A | `--kf-primary` | Navigasi, tombol utama, dan identitas visual |
| Primary Dark | Navy Shade | #082245 | `--kf-primary-dark` | Status hover/pressed tombol utama |
| Primary Soft | Navy Tint | #E6EEF9 | `--kf-primary-soft` | Latar badge/aksen lembut |
| Secondary | Warm Gold | #FFC436 | `--kf-secondary` | Aksen dan elemen sorotan |
| Secondary Dark | Gold Shade | #D4A017 | `--kf-secondary-dark` | Status hover/pressed aksen |
| Secondary Soft | Gold Tint | #FFF6DD | `--kf-secondary-soft` | Latar aksen lembut |
| Background | Off-white | #F6F8FA | `--kf-background` | Latar belakang halaman |
| Surface | Pure White | #FFFFFF | `--kf-surface` | Kartu, formulir, dan kontainer |
| Surface Subtle | Cool Gray Tint | #F1F4F9 | `--kf-surface-subtle` | Header tabel, footer kartu, metadata sekunder |
| Primary Text | Slate 800 | #1F2937 | `--kf-text` | Teks utama |
| Secondary Text | Slate 600 | #4B5563 | `--kf-text-muted` | Label, keterangan, dan metadata |
| Border | Neutral Border | #E5E7EB | `--kf-border` | Perimeter kartu, pemisah, garis tabel |
| Border Strong | Neutral Border Strong | #D1D5DB | `--kf-border-strong` | Batas input/bidang nonaktif |
| Success | Emerald | #059669 | `--kf-success` | Status `Selesai` dan konfirmasi |
| Warning | Amber | #D97706 | `--kf-warning` | Status `Terverifikasi` dan peringatan |
| Danger | Red | #DC2626 | `--kf-danger` | Kesalahan dan aksi destruktif |
| Info | Sky Blue | #0284C7 | `--kf-info` | Status `Baru` dan metadata informatif |

**Status:** Final — dikunci dan divalidasi pada implementasi (VQ-04 sampai VQ-11).

Catatan implementasi:
- Warna navy memerlukan aturan CSS khusus atau penyesuaian variabel Bootstrap.
- Kelas default Bootstrap `bg-primary` menggunakan warna biru standar Bootstrap, bukan otomatis warna navy yang direkomendasikan.
- Seluruh pemilihan warna harus memperhatikan kontras dan keterbacaan.
- Hex alternatif `#003366` (primary) dan `#D4A017` (secondary) merupakan usulan lama; `#D4A017` kini dipakai sebagai `--kf-secondary-dark`. Semua nilai token merujuk pada tabel di atas.
- Referensi visual Stitch (`docs/ui-ux-reference/stitch/`) bersifat panduan visual saja; token warna resmi adalah tabel ini dan `app/static/css/klasifas.css`.

### 2.2 Warna Semantik Status Tiket

KlasiFas hanya menggunakan empat status tiket resmi:

| Status | Rekomendasi Kelas Bootstrap | Representasi Visual | Makna |
|---|---|---|---|
| Baru | `badge bg-info text-dark` | Biru muda / cyan | Keluhan tersimpan dan menunggu verifikasi Admin Sarpras |
| Terverifikasi | `badge bg-warning text-dark` | Kuning / oranye | Kategori keluhan telah diverifikasi Admin Sarpras |
| Diproses | `badge bg-primary` | Biru standar Bootstrap | Proses perbaikan sedang berlangsung |
| Selesai | `badge bg-success` | Hijau | Perbaikan telah diselesaikan |

Ketentuan:
- Label teks status wajib selalu ditampilkan bersama warna.
- Warna tidak boleh menjadi satu-satunya indikator status.
- Penggunaan kelas warna dapat disesuaikan melalui CSS selama makna visual tetap konsisten.
- Penugasan teknisi merupakan atribut penanggung jawab yang terpisah, bukan status tiket tambahan.

### 2.3 Penanda Khusus Verifikasi Manual

Penanda `Perlu Verifikasi Manual` menggunakan rekomendasi tampilan:

`badge bg-secondary`

Penanda ini bukan status tiket resmi.

Penanda ditampilkan pada antrean Admin Sarpras apabila:
- Proses inferensi Machine Learning gagal.
- Model ML tidak tersedia atau tidak dapat digunakan sehingga sistem menjalankan fallback FR-10.

Nilai confidence rendah tidak boleh secara otomatis memunculkan penanda tersebut sebelum threshold resmi disepakati berdasarkan evaluasi model.

### 2.4 Warna Kategori Fasilitas

KlasiFas memiliki tujuh kategori fasilitas:

1. Ruang kelas dan perabot.
2. Laboratorium dan perangkat.
3. Jaringan dan internet.
4. Kebersihan dan sanitasi.
5. Listrik, AC, dan penerangan.
6. Keamanan, parkir, dan akses.
7. Lainnya.

**Rekomendasi sementara:** gunakan badge netral atau outline badge untuk kategori agar tidak bertabrakan dengan warna semantik status tiket.

Skema warna definitif setiap kategori masih TBD.

---

## 3. Tipografi, Spacing, dan Aset Grafis

### 3.1 Keluarga Font

Tipografi menggunakan **Public Sans** yang disimpan lokal di `app/static/fonts/public-sans/` agar sesuai referensi Stitch dan tetap berjalan offline. Aset memiliki lisensi SIL Open Font License 1.1 (`OFL.txt`). Bobot yang tersedia: 400, 500, 600, dan 700. Fallback ke system stack bila font gagal dimuat.

Tidak memakai CDN; CSP `font-src 'self'` sudah membatasi pemuatan font ke aset lokal.

```css
font-family:
    "Public Sans",
    system-ui,
    -apple-system,
    "Segoe UI",
    Roboto,
    "Helvetica Neue",
    Arial,
    sans-serif;
```

### 3.2 Skala Tipografi

Rekomendasi hierarki teks:

| Elemen | Ukuran | Ketebalan | Penggunaan |
|---|---:|---|---|
| H1 | 2rem / 32px | Semi-bold | Judul utama halaman |
| H2 | 1.5rem / 24px | Semi-bold | Judul bagian dan kartu |
| H3 | 1.25rem / 20px | Medium | Subjudul dan metrik |
| Body | 1rem / 16px | Regular | Isi konten |
| Caption | 0.875rem / 14px | Regular | Metadata dan keterangan |

Gunakan hierarki tipografi secara konsisten agar informasi dapat dipindai dengan mudah.

Ukuran di atas merupakan rekomendasi awal dan dapat disesuaikan melalui pengujian antarmuka.

### 3.3 Spacing dan Layout

Gunakan sistem spacing Bootstrap 5 agar jarak antar elemen konsisten.

Pedoman:
- Gunakan utility spacing Bootstrap seperti `mt-*`, `mb-*`, `p-*`, dan `gap-*`.
- Berikan jarak yang cukup antara label, input, tombol, dan pesan validasi.
- Hindari tampilan yang terlalu padat pada tabel operasional.
- Kelompokkan informasi berdasarkan fungsi dan prioritas.
- Gunakan kontainer responsif Bootstrap untuk menjaga proporsi konten.

Lebar kontainer standar (VQ-06):
- Kontainer konten standar memakai `.kf-container` dengan `max-width: 1200px` (token `--kf-container-max`) mulai viewport `>= 1200 px`. Kelas ini diterapkan pada container navbar, `main`, dan footer melalui `base.html`.
- Workspace padat yang membutuhkan lebar lebih besar (board/antrean teknisi sesuai referensi Stitch) memakai `.kf-container--wide` dengan `max-width: 1440px` (token `--kf-container-wide-max`). Kelas wide hanya diterapkan pada halaman teknisi (`Papan Tugas Teknisi` dan `Rincian Tugas`), bukan pada halaman publik, admin, dashboard, maupun autentikasi.
- Di bawah `1200 px`, lebar kontainer mengikuti breakpoint bawaan Bootstrap sehingga perilaku mobile dan tablet tidak berubah.

### 3.4 Logo dan Aset Institusi

Logo resmi FTII UHAMKA belum dinyatakan tersedia dalam aset workspace.

Ketentuan:
- Gunakan placeholder teks `KlasiFas FTII UHAMKA` selama logo resmi belum dikonfirmasi.
- Jangan menggunakan logo hasil pencarian yang tidak memiliki sumber atau izin penggunaan yang jelas.
- Apabila tim telah memperoleh aset resmi, gunakan format grafis yang sesuai, seperti PNG atau SVG.
- Ukuran dan posisi logo harus menjaga keseimbangan navbar dan identitas sistem.
- Favicon (VQ-10) memakai aset lokal `app/static/favicon.svg` berupa monogram `K` bernuansa navy/gold sesuai token warna. Favicon bukan logo resmi FTII dan hanya berfungsi sebagai ikon tab browser.
- Favicon wajib disajikan dari aset lokal (`self`), tanpa CDN. `<link rel="icon">` di `base.html` menunjuk `/static/favicon.svg`, dan permintaan root `/favicon.ico` dialihkan (redirect) ke aset tersebut sehingga tidak menghasilkan HTTP 404.

**Status:** TBD — menunggu ketersediaan aset resmi dari tim.

---

## 4. Komponen Antarmuka Standar

### 4.1 Tombol

Tombol harus menampilkan fungsi secara jelas melalui label dan hierarki visual.

Jenis tombol:

| Jenis | Penggunaan |
|---|---|
| Primary | Tindakan utama seperti Kirim Laporan atau Simpan Perubahan |
| Secondary | Tindakan pendamping |
| Outline | Aksi alternatif atau navigasi sekunder |
| Danger | Tindakan yang berpotensi menghapus atau membatalkan data |
| Disabled | Menandai tindakan yang belum dapat dilakukan |

Ketentuan:
- Gunakan label tindakan yang jelas.
- Hindari label ambigu seperti "Klik di sini".
- Berikan indikator visual ketika tombol sedang memproses permintaan.
- Cegah pengiriman formulir berulang ketika proses masih berlangsung.
- Pastikan ukuran tombol nyaman digunakan pada layar sentuh.

### 4.2 Formulir dan Input

Formulir harus memiliki label yang menjelaskan data yang diminta.

Komponen yang digunakan antara lain:
- Text input.
- Textarea.
- Select atau dropdown.
- File input.
- Password input.
- Tombol submit.

Aturan tampilan:
- Label harus jelas dan selalu terkait dengan input.
- Tampilkan keterangan untuk kolom opsional.
- Tampilkan pesan validasi dekat dengan input yang bermasalah.
- Pertahankan data formulir yang aman ketika terjadi kesalahan validasi.
- Tampilkan kondisi loading ketika formulir sedang dikirim.
- Kesalahan validasi harus menggunakan bahasa yang mudah dipahami.

Ukuran input publik (VQ-07 & VQ-09):
- Input teks dan select (`.form-control`, `.form-select`) memiliki tinggi minimal `44px` dan padding `10px 14px`, memakai token `--kf-input-height`, `--kf-input-padding-y`, dan `--kf-input-padding-x`.
- Aturan ini berlaku seragam pada formulir pelaporan, pelacakan tiket, dan login staf; tidak ada ukuran input khusus per halaman.
- Textarea memakai padding `10px 14px` namun tidak dipaksa tinggi minimal `44px`; tingginya mengikuti jumlah baris (`rows`).

Validasi sisi server tetap menjadi pengaman utama, sebagaimana ditentukan dalam SECURITY.md.

### 4.3 Kartu Konten

Card Bootstrap digunakan untuk mengelompokkan informasi berdasarkan fungsi.

Contoh penggunaan:
- Ringkasan tiket.
- Informasi status.
- Rekomendasi klasifikasi Naive Bayes.
- Kartu metrik dashboard.
- Daftar pekerjaan teknisi.

Setiap kartu harus memiliki:
- Judul atau identitas informasi.
- Isi utama yang relevan.
- Metadata atau keterangan jika dibutuhkan.
- Aksi yang jelas apabila terdapat interaksi.

Hindari terlalu banyak dekorasi dan bayangan yang mengganggu hierarki konten.

Ketentuan visual dasar kartu (VQ-04):
- Seluruh `.card` menggunakan background putih (`--kf-surface`), border `1px` solid (`--kf-border`), dan radius `8px` (`--kf-radius-lg`). Nilai ini diambil dari design token CSS, bukan nilai hardcoded.
- Accent `3px` di sisi atas kartu hanya digunakan pada empat jenis kartu berikut dan tidak pada kartu konten biasa:
  - Kartu formulir (`.kf-form-card`).
  - Kartu sidebar (`.kf-sidebar-card`).
  - Kartu receipt/konfirmasi (`.kf-receipt-card`).
  - Kartu KPI (`.kf-kpi`).
- Kartu konten lainnya memakai border netral tanpa accent agar hierarki tetap bersih dan konsisten.

### 4.4 Badge dan Tabel

Badge digunakan untuk menampilkan:
- Empat status resmi tiket.
- Peran pengguna.
- Kategori fasilitas.
- Penanda `Perlu Verifikasi Manual` jika fallback FR-10 aktif.

Tabel digunakan untuk menyajikan daftar tiket dan log audit.

Ketentuan:
- Tabel harus memiliki heading kolom yang jelas.
- Informasi utama ditempatkan pada kolom awal.
- Tabel operasional harus mendukung pembacaan pada layar kecil melalui responsivitas, scrolling horizontal, atau pola penyajian alternatif yang sesuai.
- Informasi sensitif tidak boleh ditampilkan hanya karena dapat dimuat ke dalam tabel.
- Aksi pada tabel harus mengikuti otorisasi RBAC.

### 4.5 Dialog dan Konfirmasi Aksi

Bootstrap Modal dapat digunakan untuk aksi operasional yang membutuhkan konfirmasi atau input tambahan.

Contoh:
- Verifikasi dan koreksi kategori.
- Penugasan teknisi.
- Pembaruan status atau catatan tindakan.

Modal harus:
- Menyampaikan tindakan yang akan dilakukan.
- Memiliki tombol konfirmasi dan pembatalan yang jelas.
- Tidak menyembunyikan informasi penting.
- Mengikuti validasi dan otorisasi backend.

---

## 5. Arsitektur Antarmuka Berdasarkan Peran Pengguna (RBAC)

### 5.1 Gambaran Sepuluh Halaman/Layar Utama

KlasiFas memiliki sepuluh halaman atau layar utama:

| No. | Halaman | Rute | Requirement | Pengguna |
|---:|---|---|---|---|
| 1 | Beranda Publik (redirect) | `/` → `/lapor` | Navigasi ke formulir pelaporan | Publik |
| 2 | Formulir Pelaporan | `/lapor` | FR-01 | Pelapor |
| 3 | Konfirmasi Pengiriman | `/lapor/sukses` | FR-01, FR-02 | Pelapor |
| 4 | Pelacakan Tiket | `/lacak` | FR-02 | Pelapor |
| 5 | Login Pengguna Internal | `/auth/login` | Autentikasi | Pengguna internal |
| 6 | Antrean Verifikasi dan Penugasan | `/admin/tiket` | FR-04, FR-05, FR-10 | Admin Sarpras |
| 7 | Pencarian dan Filter Operasional | `/admin/filter` | FR-08 | Admin Sarpras |
| 8 | Riwayat Log Audit | `/admin/audit-log` | FR-09 | Admin Sarpras |
| 9 | Papan Antrean Kerja Teknisi | `/teknisi/tiket` | FR-06 | Teknisi |
| 10 | Dashboard Pemantauan Manajerial | `/dashboard` | FR-07 | Admin Sarpras dan Pimpinan/Kaprodi |

Rute `/` adalah alias publik yang mengalihkan ke `/lapor` dengan HTTP 302; tidak ada halaman beranda terpisah.

Rute `/lapor/sukses` merupakan usulan rute antarmuka dan belum dianggap sebagai keputusan final jika belum dikunci pada rancangan arsitektur.

Seluruh akses halaman wajib divalidasi oleh backend.

### 5.2 Antarmuka Pelapor

Pelapor menggunakan antarmuka publik untuk mengirim laporan dan memantau perkembangan tiket.

**Beranda Publik**
- Informasi singkat mengenai tujuan KlasiFas.
- Tombol utama Lapor Keluhan.
- Tombol Lacak Tiket.
- Penjelasan singkat alur penanganan keluhan fasilitas kampus.
- Navigasi ke halaman login petugas.

**Formulir Pelaporan — FR-01**

Elemen utama:
- Input deskripsi keluhan.
- Pemilihan lokasi gedung, lantai, dan ruang.
- Pemilihan kategori oleh pelapor apabila tersedia, sebagai informasi awal.
- Upload foto bukti opsional.
- Tombol Kirim Laporan.

Ketentuan:
- Kategori awal dari pelapor bukan pengganti hasil klasifikasi atau verifikasi Admin Sarpras.
- Foto merupakan bukti pendukung dan bukan input klasifikasi ML.
- Batas ukuran foto mengikuti keputusan SECURITY.md yang telah disetujui.

**Implementasi B2 — Formulir Pelaporan**

Status: selesai dan tervalidasi.

- Layout desktop menggunakan grid Bootstrap 12 kolom dengan pembagian 8/4: formulir `col-lg-8` dan sidebar `col-lg-4`. Pada viewport tablet dan mobile, kedua kolom ditumpuk menjadi satu kolom penuh.
- Formulir memiliki empat section bernomor: `1` Lokasi Fasilitas, `2` Informasi & Rincian, `3` Foto Bukti, dan `4` Data Pelapor.
- Gedung ditampilkan sebagai field statis `Gedung FTII` dengan badge `Terpilih Otomatis`; nilai gedung dikirim melalui hidden input dan tidak dapat diubah pelapor.
- Deskripsi memiliki counter karakter dengan batas 2.000 karakter. Counter menampilkan format `0 / 2.000 karakter` dan diperbarui oleh `portal.js` dengan `aria-live="polite"`.
- Foto menggunakan dropzone bergaris putus-putus yang dapat diklik atau menerima drag-and-drop. Dropzone menampilkan nama file, menerima JPG/JPEG/PNG, dan menampilkan batas 3 MB serta dimensi maksimum 6000 x 6000 piksel.
- Sidebar `Alur Penanganan Sarpras` berisi empat langkah: Verifikasi Admin Sarpras, Disposisi & Jadwal Teknisi, Tindakan Perbaikan Fisik, dan Laporan Selesai & Ditutup.
- Foto tetap opsional, tidak digunakan untuk klasifikasi ML, dan metadata EXIF dibersihkan sebelum penyimpanan.
- Sidebar tidak menampilkan kontak, hotline, atau statistik yang belum terverifikasi.

Validasi visual B2:

| Viewport | Hasil |
|---:|---|
| 1440 px | Formulir 800 px dan sidebar 400 px pada satu baris (container standar 1200 px); rasio 8/4 sesuai. |
| 768 px | Formulir dan sidebar masing-masing 720 px; ditumpuk satu kolom tanpa overflow horizontal. |
| 390 px | Formulir dan sidebar selebar viewport; ditumpuk satu kolom tanpa overflow horizontal. |

Validasi perilaku dan pengujian: counter, dropzone, badge, empat section, dan sidebar diperiksa pada ketiga viewport. Sebanyak 47 targeted tests untuk `tests/test_report_f3_01.py` dan `tests/test_report_f3_02.py` lulus pada database sementara `klasifas_test_b2_audit_20261106_025322`. Database lama `klasifas_test_db` tidak digunakan untuk validasi B2.

Batas upload final mengikuti keputusan SECURITY.md dan TASKS.md: 3 MB per file, JPEG/PNG, maksimum 6000 x 6000 piksel, dan EXIF dihapus.

**Konfirmasi Pengiriman**

Halaman konfirmasi menampilkan informasi keberhasilan penyimpanan laporan dan kode referensi tiket.

Komponen yang direncanakan:
- Pesan bahwa laporan berhasil disimpan.
- Kode referensi `KF-XXXXXX`.
- Area token akses rahasia yang ditampilkan satu kali pada respons POST.
- Instruksi untuk menjaga kerahasiaan token.

Distribusi token final: tampil sekali pada respons POST `/lapor` dengan `Cache-Control: no-store`. Masa berlaku dan reissue tetap TBD.

Token tidak boleh disisipkan ke URL, query parameter, session, flash, log, atau header.

**Pelacakan Mandiri — FR-02**

Elemen utama:
- Form input kode referensi tiket.
- Form input token akses rahasia.
- Ringkasan status tiket.
- Riwayat perubahan atau penanganan yang boleh ditampilkan kepada pelapor.
- Catatan tindakan teknisi jika tersedia dan diizinkan.

Pelapor hanya boleh melihat tiket yang aksesnya berhasil diverifikasi.

**Implementasi B4 — Pelacakan Mandiri**

Status: selesai dan tervalidasi.

- Stepper progres penanganan menampilkan empat status resmi (`Baru`, `Terverifikasi`, `Diproses`, `Selesai`) berdasarkan status tiket aktual. Tahap yang sudah dilewati ditandai selesai, tahap aktif memakai `aria-current="step"`, dan tahap berikutnya ditandai belum tercapai. Stepper tidak menampilkan timestamp atau riwayat; data waktu yang tersedia hanya `Waktu Laporan` dan `Waktu Selesai` (khusus status `Selesai`).
- Field token akses tetap bertipe `password` dan dilengkapi tombol tampil/sembunyikan aksesibel (`aria-pressed`, `aria-controls`, ikon `bi-eye`/`bi-eye-slash`) yang ditangani `portal.js`. Pengiriman token tetap melalui POST dengan CSRF dan rate limiting; token tidak ditempatkan pada URL atau query parameter.
- Konten mockup Stitch 02 yang tidak memiliki sumber data terverifikasi (narasi contoh, foto contoh, log teknisi, lokasi dukungan) tidak ditampilkan. Data publik dibatasi pada hasil sanitasi `ticket_tracking.py`.
- Stepper dirender sebagai grid empat kolom dengan indikator dan label yang diperkecil pada viewport < 576 px; tidak ada lebar tetap yang memicu overflow horizontal.

Validasi perilaku dan pengujian B4: 22 targeted tests untuk `tests/test_track_f3_04.py` dan `tests/test_tracking_e2e_f3_05.py` lulus. Pemeriksaan render memastikan stepper menandai tahap yang benar untuk keempat status serta atribut aksesibilitas tombol token hadir. Validasi viewport 390/768/1440 px dilakukan berbasis analisis CSS (grid responsif, `minmax(0, 1fr)`, `overflow-wrap`); tidak tersedia tooling browser otomatis di lingkungan ini, sehingga validasi visual browser dicatat sebagai belum diverifikasi.

### 5.3 Antarmuka Admin Sarpras

Admin Sarpras memiliki antarmuka operasional untuk mengelola proses verifikasi dan pemantauan.

**Antrean Verifikasi dan Penugasan — FR-04, FR-05**

Elemen:
- Tabel laporan yang perlu ditinjau.
- Status resmi tiket.
- Deskripsi dan lokasi keluhan.
- Kategori rekomendasi Naive Bayes.
- Informasi hasil klasifikasi dan confidence score jika tersedia.
- Penanda `Perlu Verifikasi Manual` apabila fallback FR-10 aktif.
- Aksi verifikasi atau koreksi kategori.
- Form penugasan teknisi.

Rekomendasi ML merupakan informasi pendukung. Keputusan kategori resmi ditetapkan melalui proses verifikasi Admin Sarpras.

Bentuk visual confidence score masih TBD.

**Implementasi C1 — Admin Workspace (Antrean)**

Status: selesai dan tervalidasi.

- Strip KPI lima kartu (Total, Baru, Terverifikasi, Diproses, Selesai) di atas antrean; angka dihitung dari agregat basis data nyata melalui `get_ticket_status_counts()` (`app/services/complaint_service.py`), bukan data sampel mockup.
- Tabel antrean menambah kolom `Keluhan` berupa ringkasan deskripsi dua baris (`kf-text-clamp-2`) dengan tooltip teks penuh.
- Penanda `Perlu Verifikasi Manual` memakai macro `manual_verification_badge`; kasus fallback tanpa prediksi ML tetap menampilkan label `Verifikasi Manual (Fallback)` agar dapat dibedakan.
- Aksi per status: `Baru` → `Verifikasi`, `Terverifikasi` → `Disposisi`, `Diproses`/`Selesai` → `Detail`.
- Empty state eksplisit dengan ikon, judul, dan tombol `Kembalikan Filter Default`.
- Tabel memakai `.table-responsive` (horizontal scroll pada layar sempit); kolom memakai `kf-table-col-min-*`.
- Filter tetap inline pada `/admin/tiket`; tidak ada rute `/admin/filter` baru. RBAC, CSRF, dan batas PII tidak diubah.

Validasi C1: 104 targeted tests F5 (`test_admin_f5_01/02/03`, `test_audit_f5_04/05`) lulus; pemeriksaan render memastikan KPI, kolom deskripsi, aksi per status, dan empty state tampil benar. Validasi visual browser tidak tersedia di lingkungan ini.

**Implementasi C2 — Verifikasi Tiket dan Log Audit**

Status: selesai dan tervalidasi (perapian UI; alur bisnis tidak berubah).

- Halaman verifikasi (`admin/verify.html`) memakai macro badge yang tersedia: `manual_verification_badge` untuk penanda verifikasi manual, `category_badge` untuk pilihan pelapor dan kategori resmi, `role_badge` untuk peran aktor pada riwayat audit, serta `status_badge` untuk status. Teks yang diuji (`Model belum tersedia (Fallback)`, `Akun Nonaktif`, pesan flash) dipertahankan.
- Riwayat audit per-tiket dirapikan: nama aktor + badge peran, label aksi yang dapat dibaca, dan nilai lama → baru; nilai kosong ditampilkan `-`, bukan `None`. Catatan audit dan waktu tetap ditampilkan.
- Halaman log audit (`admin/audit_log.html`) mengganti literal `None` menjadi `-` pada rincian perubahan, dan menambahkan empty state dengan ikon, judul, dan tombol `Kembalikan Filter Default`.
- Confidence score tetap ditampilkan sebagai teks biasa sesuai keputusan TBD.
- Service, route, RBAC, CSRF, dan alur penugasan tidak diubah.

Validasi C2: 104 targeted tests F5 lulus tanpa perubahan perilaku. Validasi visual browser tidak tersedia di lingkungan ini.

**Pencarian dan Filter Operasional — FR-08**

Elemen:
- Input pencarian kata kunci.
- Filter kategori K1–K7.
- Filter lokasi.
- Filter rentang tanggal.
- Filter status tiket.
- Tabel hasil pencarian tiket.

Fitur ini khusus untuk Admin Sarpras.

Pimpinan/Kaprodi tidak diberikan akses terhadap daftar tiket operasional melalui halaman ini.

**Log Audit — FR-09**

Elemen:
- Waktu perubahan.
- Aktor yang melakukan perubahan.
- Entitas yang berubah.
- Informasi perubahan sebelum dan sesudah apabila sesuai kebijakan pencatatan.

Hanya Admin Sarpras yang memiliki hak membaca log audit.

Informasi sensitif seperti password, token, dan secret tidak boleh ditampilkan dalam log audit.

**Dashboard Manajerial — FR-07**

Admin Sarpras dapat menggunakan dashboard untuk melihat data agregat dan ringkasan kondisi fasilitas kampus.

Dashboard tidak boleh menampilkan identitas pribadi pelapor.

**Implementasi C3 — Dashboard Manajerial**

Status: selesai dan tervalidasi (perapian UI; alur data tidak berubah).

- Empat pill status resmi menampilkan jumlah dan persentase terhadap total tiket. Persentase dihitung di klien dari `status_counts` yang sudah disediakan API; tidak ada angka mockup Stitch.
- Stacked progress bar di bawah pill memvisualisasikan proporsi keempat status memakai token warna status yang ada (`.kf-status-progress`, `.kf-status-progress__seg--*`).
- Kondisi total tiket 0 ditangani eksplisit: semua persentase dan lebar segmen menjadi 0 tanpa pembagian nol.
- Badge privasi "Data agregat anonim — tanpa identitas pelapor" ditambahkan pada header untuk menegaskan batas PII.
- Tiga canvas (`trendChart`, `categoryChart`, `locationChart`) memiliki `role="img"` dan `aria-label` deskriptif.
- Layout grid, ID KPI/chart, route `/dashboard`, endpoint `/dashboard/api/chart-data`, dan service agregat tidak diubah. Top rooms tetap berupa daftar; kolom lantai dan status dominan ala Stitch tidak ditambahkan karena payload API belum menyediakannya.

Validasi C3: 48 test pada 4 file dashboard (`test_dashboard_f7_01`..`_04`) dan 104 test regresi F5 lulus pada database sementara `klasifas_test_c3_20261106_audit`. `klasifas_test_db` tidak digunakan dan data lama tidak dihapus. Validasi visual browser tidak tersedia di lingkungan ini.

**Implementasi D1 — Dashboard Hardening**

Status: selesai dan tervalidasi (tambahan aditif; layout dan kontrak lama dipertahankan).

- Payload `category_chart` menambah `percentages` (aditif) dari distribusi kategori; tooltip kategori menampilkan `jumlah (persen%)` tanpa mengubah `datasets`, `labels`, atau `category_names`.
- Kartu kategori menampilkan `Terverifikasi` (dari `total_verified`) di samping badge `Unverified`.
- Kartu lokasi menampilkan catatan `Tiket di luar Lantai 1–4` hanya saat `other_floors_count > 0`; nilai `0` menyembunyikan catatan.
- Ringkasan teks grafik `#dashboard-chart-summary` (`.visually-hidden`, `aria-live="polite"`) terhubung ke tiga canvas melalui `aria-describedby`; `#dashboard-main-content` memakai `aria-busy` selama fetch.
- Respons `/dashboard`, `/dashboard/api/chart-data` (200 dan 400) memakai `Cache-Control: no-store`.
- Layout, ID chart/KPI, bentuk `top_rooms`, bucketing tanggal, RBAC, filter, dan service agregat lain tidak diubah.

Validasi D1: 48 test F7 dan 104 test regresi F5 lulus pada database sementara `klasifas_test_d1_20261106_audit`; smoke test mengonfirmasi `percentages` (7 kategori), `other_floors_count`, ringkasan/aria, dan `no-store` pada HTML, JSON 200, dan JSON 400. `klasifas_test_db` tidak digunakan dan data lama tidak dihapus. Validasi visual browser tidak tersedia di lingkungan ini.

### 5.4 Antarmuka Teknisi

Teknisi menggunakan Papan Antrean Kerja untuk melihat tiket yang ditugaskan kepadanya.

**Papan Antrean Teknisi — FR-06**

Komponen:
- Daftar tiket yang menjadi tanggung jawab teknisi login.
- Deskripsi dan lokasi pekerjaan.
- Kategori keluhan yang telah diverifikasi.
- Status resmi tiket.
- Aksi pembaruan status.
- Input catatan tindakan perbaikan.

Ketentuan:
- Teknisi hanya dapat melihat tiket yang ditugaskan kepadanya.
- Teknisi hanya dapat memperbarui tiket dalam cakupan penugasannya.
- Catatan penyelesaian wajib mengikuti mekanisme yang ditentukan aplikasi.
- Teknisi tidak memiliki akses ke dashboard manajerial maupun log audit.

**Implementasi C4 — Papan Tugas Teknisi**

Status: selesai dan tervalidasi (perapian UI; alur bisnis tidak berubah).

- Strip KPI antrean teknisi memakai pola `.kf-kpi*` yang sama dengan C1: Total Tugas, Terverifikasi, Diproses, dan Selesai; nilai tetap berasal dari `counts` basis data nyata.
- Deskripsi keluhan memakai `.kf-text-clamp-2` dua baris dengan tooltip teks penuh.
- Empty state memakai ikon, judul, penjelasan filter, dan tombol `Kembalikan Filter Default`; teks `Belum ada tiket yang ditugaskan kepada Anda.` dipertahankan karena diuji.
- Paginasi nonaktif memakai `<span>` alih-alih tautan `href="#"`.
- Rincian tugas memakai badge status resmi (`status_badge`), bukan label turunan seperti "Siap Dikerjakan". Nilai `resolution_note` kosong ditampilkan `-`, bukan kalimat pengganti.
- Alert statis memakai `role="status"`, ikon dekoratif `aria-hidden="true"`, dan help text textarea terhubung melalui `aria-describedby`.
- Route, service, RBAC, kepemilikan tiket, CSRF, dan alur transisi status tidak diubah.

Validasi C4: 46 test pada `test_technician_f6_01`, `test_technician_f6_02`, dan `test_audit_f6_03` lulus; 104 test regresi F5 dan 48 test F7 juga lulus pada database sementara `klasifas_test_c4_20261106_audit`. `klasifas_test_db` tidak digunakan dan data lama tidak dihapus. Validasi visual browser tidak tersedia di lingkungan ini.

### 5.5 Antarmuka Pimpinan/Kaprodi

Pimpinan/Kaprodi menggunakan dashboard pemantauan manajerial dengan hak akses read-only.

Komponen:
- Ringkasan jumlah keluhan.
- Distribusi status tiket.
- Distribusi kategori fasilitas.
- Tren laporan berdasarkan periode.
- Ringkasan lokasi fasilitas yang sering mengalami gangguan.
- Filter agregat grafik.

Ketentuan:
- Tidak tersedia aksi untuk membuat atau mengubah tiket.
- Tidak tersedia pencarian data tiket individual FR-08.
- Tidak tersedia akses ke log audit FR-09.
- Tidak menampilkan nama, NIM, nomor telepon, atau kontak pelapor.

---

## 6. Spesifikasi Visual Komponen Khusus KlasiFas

### 6.1 Kode Referensi dan Token Akses

Tampilan identitas tiket harus membedakan:

**Kode Referensi**
- Format `KF-XXXXXX`.
- Digunakan untuk identifikasi tiket.

**Token Akses Rahasia**
- Merupakan kredensial terpisah.
- Digunakan untuk membuktikan hak akses terhadap detail tiket.
- Tidak boleh ditampilkan pada URL atau query parameter.
- Tidak boleh dicatat dalam log.
- Tidak boleh diperlakukan sebagai kode referensi publik.

Mekanisme distribusi final: token ditampilkan sekali pada respons POST; expiry/reissue tetap TBD.

Antarmuka tidak boleh mengasumsikan bahwa kode referensi saja dapat membuka detail tiket.

### 6.2 Rekomendasi Klasifikasi Machine Learning

Panel verifikasi dapat menampilkan:
- Kategori hasil prediksi Naive Bayes.
- Informasi confidence score jika tersedia.
- Kategori awal dari pelapor apabila diberikan.
- Aksi verifikasi atau koreksi kategori oleh Admin Sarpras.

Confidence score merupakan informasi pendukung dan tidak menggantikan keputusan verifikasi manusia.

Format visual berupa persentase teks atau progress bar masih TBD.

### 6.3 Banner Fallback FR-10

Ketika inferensi ML gagal atau model tidak tersedia, antrean Admin Sarpras dapat menampilkan badge:

`Perlu Verifikasi Manual`

Ketentuan:
- Badge merupakan penanda proses, bukan status tiket baru.
- Status resmi tetap mengikuti empat status tiket.
- Laporan yang gagal diklasifikasikan tetap tersimpan.
- Admin Sarpras melanjutkan penanganan melalui proses manual.

Threshold confidence belum boleh digunakan sebagai pemicu otomatis sebelum nilai final dievaluasi dan disetujui kelompok.

### 6.4 Visualisasi Dashboard Chart.js

Dashboard menggunakan Chart.js sesuai TECHSTACK.

Komponen visual yang direkomendasikan:

**Ringkasan Metrik**
- Total keluhan.
- Jumlah tiket berdasarkan empat status resmi.

**Distribusi Kategori**
- Diagram batang untuk tujuh kategori fasilitas.

**Tren Keluhan**
- Diagram garis berdasarkan periode waktu.

**Distribusi Lokasi**
- Visualisasi lokasi gedung atau lantai dengan jumlah keluhan.

Visualisasi harus menggunakan data agregat dan tidak menampilkan identitas pribadi pelapor.

#### Filter Agregat Dashboard

Filter dashboard dapat menggunakan dimensi:
- Kategori fasilitas K1–K7.
- Lokasi fisik seperti gedung dan lantai.
- Status tiket.
- Periode waktu, seperti harian, mingguan, dan bulanan.

Filter tersebut hanya mengubah tampilan agregat dashboard dan bukan pencarian tiket individual FR-08.

Dimensi dan detail akhir mengikuti kebutuhan FR-07 yang telah disetujui.

---

## 7. Panduan Responsivitas Layar

### 7.1 Prinsip Mobile-First

KlasiFas dirancang agar dapat digunakan melalui browser desktop maupun perangkat mobile.

Rekomendasi breakpoint Bootstrap:

| Breakpoint | Ukuran | Penggunaan |
|---|---|---|
| Mobile | ≤576 px | Tampilan satu kolom dan navigasi ringkas |
| Tablet | 577–991 px | Tata letak adaptif |
| Desktop | ≥992 px | Grid multi-kolom dan tabel operasional |

Ketentuan navbar dan grid lokasi (VQ-05):
- Navbar tampil horizontal (logo dan tautan navigasi sejajar) mulai lebar tablet `768 px` ke atas. Tombol hamburger hanya digunakan di bawah `768 px`.
- Grid lokasi pada formulir pelaporan: field Gedung tampil selebar penuh, sedangkan field Lantai dan Nama/nomor ruang disusun dua kolom (`50%`/`50%`) pada tablet dan desktop. Pada mobile, seluruh field tetap satu kolom penuh.
- Navbar maupun grid tidak boleh wrap tak terkendali atau menimbulkan overflow horizontal pada rentang `390 px`, `768 px`, dan `1440 px`.

### 7.2 Tampilan Mobile

Halaman publik dan halaman yang digunakan pelapor harus mengutamakan kemudahan penggunaan pada ponsel.

Prioritas:
- Beranda publik.
- Formulir pelaporan.
- Halaman konfirmasi.
- Pelacakan tiket.
- Login internal.

Ketentuan:
- Formulir menggunakan layout satu kolom.
- Formulir pelaporan B2 divalidasi pada viewport 390 px, 768 px, dan 1440 px. Pada 768 px dan 390 px, formulir serta sidebar ditumpuk tanpa overflow horizontal.
- Input memiliki ukuran yang nyaman disentuh.
- Tombol utama mudah dijangkau.
- Tabel atau informasi padat diubah menjadi pola yang lebih mudah dibaca.
- Hindari kebutuhan scrolling horizontal yang tidak diperlukan.
- Target ukuran area sentuh tombol direkomendasikan minimal 44 px.
- Tombol hamburger navbar memiliki area sentuh minimal `44 x 44 px` (VQ-08). Tombol hanya tampil di bawah `768 px`, sehingga navbar tablet dan desktop tidak terpengaruh. Ikon hamburger tetap terpusat dan navbar tidak boleh overflow horizontal.

### 7.3 Tampilan Desktop

Halaman operasional dan manajerial dapat memanfaatkan sistem grid Bootstrap 12 kolom.

Prioritas:
- Antrean verifikasi Admin Sarpras.
- Pencarian dan filter operasional.
- Log audit.
- Papan antrean teknisi.
- Dashboard manajerial.

Ketentuan:
- Tabel memanfaatkan lebar layar secara proporsional.
- Filter dapat ditempatkan pada panel terpisah.
- Grafik disusun dalam grid agar mudah dibandingkan.
- Informasi penting tidak boleh terpotong saat ukuran layar berubah.

---

## 8. Voice and Tone in UI

### 8.1 Karakter Bahasa Antarmuka

Bahasa antarmuka menggunakan Bahasa Indonesia yang:
- Formal tetapi mudah dipahami.
- Singkat dan langsung pada tujuan.
- Konsisten dalam menyebut istilah sistem.
- Tidak menggunakan jargon teknis yang tidak diperlukan pengguna.

Contoh istilah:
- Lapor Keluhan.
- Lacak Tiket.
- Kode Referensi.
- Status Penanganan.
- Perlu Verifikasi Manual.
- Catatan Penyelesaian.

### 8.2 Notifikasi dan Umpan Balik

Notifikasi harus memberikan informasi mengenai hasil tindakan pengguna.

Contoh:

| Kondisi | Contoh Pesan |
|---|---|
| Berhasil mengirim laporan | Laporan keluhan berhasil dikirim. Simpan kode referensi tiket Anda. |
| Berhasil memperbarui status | Status tiket berhasil diperbarui. |
| Gagal mengirim laporan | Laporan belum dapat dikirim. Periksa kembali data yang dimasukkan. |
| Foto tidak valid | Format atau ukuran file foto tidak sesuai ketentuan. |
| Akses ditolak | Anda tidak memiliki izin untuk mengakses halaman ini. |
| Token pelacakan tidak valid | Data pelacakan tidak dapat diverifikasi. Periksa kembali informasi yang dimasukkan. |
| Fallback ML aktif | Klasifikasi otomatis tidak tersedia. Laporan akan diperiksa secara manual oleh Admin Sarpras. |

Pesan di atas merupakan contoh microcopy dan dapat disesuaikan setelah pengujian antarmuka.

### 8.3 Pesan Kesalahan Aman

Pesan error harus mudah dipahami tanpa mengungkap detail internal aplikasi.

Ketentuan:
- Jangan menampilkan stack trace.
- Jangan menampilkan detail konfigurasi database.
- Jangan mengungkap keberadaan tiket melalui pesan kegagalan autentikasi atau pelacakan.
- Jangan menampilkan password, token, atau secret.
- Detail teknis kesalahan dicatat secara terbatas pada log internal.

---

## 9. Open Design Decisions dan TBD

Parameter berikut belum menjadi keputusan final dan memerlukan persetujuan Kelompok 7 atau validasi pihak terkait.

| ID | Parameter | Status | Rekomendasi |
|---|---|---|---|
| DES-TBD-01 | Batas maksimal upload foto | Menunggu persetujuan | Maksimum 3 MB per file |
| DES-TBD-02 | Mekanisme distribusi dan tampilan token | Final distribusi; expiry TBD | Tampil sekali pada respons POST; tanpa token pada URL/session/log |
| DES-TBD-03 | Warna primer institusi | Final (VQ-11) | Dikunci ke #0C356A (`--kf-primary`), divalidasi pada implementasi |
| DES-TBD-04 | Format visual confidence score | TBD | Persentase teks numerik pada tabel admin |
| DES-TBD-05 | Komponen visual pelacakan tiket | TBD | Timeline list sederhana dan responsif |
| DES-TBD-06 | Warna badge kategori K1–K7 | TBD | Badge netral atau outline |
| DES-TBD-07 | Ketersediaan logo resmi FTII UHAMKA | TBD | Placeholder teks identitas sistem |

Keputusan desain baru dapat dianggap final setelah mendapatkan persetujuan yang diperlukan.

---

## 10. Change Log

| Versi | Status | Keterangan |
|---|---|---|
| 1.0 | Approved Draft | Penyusunan awal pedoman UI/UX KlasiFas berdasarkan PRD v1.3, TECHSTACK v1.3, dan SECURITY v1.0, memetakan 10 layar utama, penegakan RBAC, larangan token pada URL, dan pemisahan filter agregat dasbor. |
| 1.1 | Approved Draft | Menambahkan implementasi dan validasi B2 untuk formulir pelaporan: layout 8/4, empat section, sidebar empat langkah, badge Gedung FTII, counter, dropzone, responsivitas tiga viewport, dan 47 targeted tests pada database sementara. |
| 1.2 | Approved Draft | Rekonsiliasi design system VQ-04 sampai VQ-11: kartu dasar (putih, border 1px, radius 8px), accent 3px terbatas, typografi Public Sans lokal, responsivitas navbar/grid tablet, container standar 1200px dan workspace wide 1440px, standarisasi input 44px, touch target hamburger 44x44px, favicon lokal, serta finalisasi token warna (§2.1) dan penutupan DES-TBD-03 ke #0C356A. Referensi Stitch ditetapkan sebagai panduan visual saja melalui `docs/ui-ux-reference/stitch/README.md`. |

**Akhir Dokumen — DESIGN.md**
