# Security & Privacy Policy Specification

**KlasiFas — Klasifikasi Keluhan Fasilitas Kampus**

| Metadata | Keterangan |
|---|---|
| Proyek | KlasiFas — Klasifikasi Keluhan Fasilitas Kampus |
| Institusi | FTII UHAMKA |
| Kelompok | 7 |
| Versi | 1.0 |
| Status | Approved Draft — Kelompok 7 Review |
| Dokumen Acuan | PRD.md v1.3 dan TECHSTACK.md v1.3 |

> **Tujuan Dokumen**
>
> Dokumen ini menetapkan prinsip, aturan, dan pedoman keamanan aplikasi KlasiFas. Seluruh implementasi oleh pengembang maupun AI Coding Agent wajib mengikuti ketentuan yang telah disetujui. Setiap rekomendasi yang belum disetujui dan keputusan yang masih TBD tidak boleh dianggap sebagai requirement final.

---

## 1. Landasan Privasi dan Perlindungan Data

### 1.1 Landasan dan Batasan Kepatuhan

KlasiFas dirancang dengan mempertimbangkan prinsip perlindungan data pribadi berdasarkan Undang-Undang Republik Indonesia Nomor 27 Tahun 2022 tentang Pelindungan Data Pribadi (UU PDP).

Penerapan prinsip tersebut menjadi bagian dari pendekatan Privacy-by-Design, khususnya dalam pengumpulan, penyimpanan, penggunaan, dan pemrosesan informasi pelapor.

**Batasan klaim kepatuhan:**

- Dokumen ini merupakan pedoman rancangan keamanan untuk prototipe akademik.
- Penerapan kontrol teknis tidak secara otomatis membuktikan kepatuhan penuh terhadap UU PDP.
- Penetapan dasar pemrosesan, kewajiban pengendali dan prosesor data, masa retensi, serta prosedur pemenuhan hak subjek data masih memerlukan validasi institusi.
- Data pribadi tidak boleh digunakan di luar tujuan operasional dan akademik yang telah disetujui.

### 1.2 Prinsip Minimisasi Data

KlasiFas hanya boleh mengumpulkan informasi yang diperlukan untuk pelaporan dan penanganan keluhan fasilitas kampus.

Ketentuan:

1. Nama dan kontak pelapor bersifat opsional sesuai rancangan PRD.
2. Deskripsi keluhan, lokasi fasilitas, waktu pelaporan, dan foto bukti opsional digunakan sesuai kebutuhan pelaporan.
3. Informasi identitas pribadi tidak boleh ditampilkan pada dashboard manajerial.
4. Data pribadi tidak boleh dicantumkan dalam log aplikasi apabila tidak diperlukan.
5. Data tidak boleh dikumpulkan hanya untuk kemungkinan penggunaan di masa depan tanpa tujuan yang jelas.

### 1.3 Anonimisasi Dataset Machine Learning

Data keluhan yang digunakan untuk pelatihan model Naive Bayes harus melalui proses pembersihan dan anonimisasi sebelum masuk ke dataset pemrosesan ML.

Aturan:

- Dataset pelatihan tidak boleh memuat nama, nomor telepon, alamat email, NIM, atau informasi pribadi lain yang dapat mengidentifikasi pelapor.
- Proses pembersihan dilakukan sebelum teks digunakan untuk pelatihan.
- Pola regex dapat digunakan untuk mendeteksi nomor telepon, email, dan format identitas yang telah diketahui.
- Hasil anonimisasi perlu diperiksa menggunakan sampel untuk mengurangi risiko identitas yang masih tertinggal.
- Data mentah yang mengandung informasi pribadi tidak boleh disalin ke repositori Git.
- Foto bukti tidak digunakan sebagai input klasifikasi Machine Learning.

Pola regex merupakan lapisan awal, bukan jaminan anonimisasi sempurna. Pemeriksaan tambahan tetap diperlukan untuk mendeteksi informasi identitas yang tidak mengikuti pola umum.

### 1.4 Penanganan Hak Subjek Data

Permintaan koreksi, penghapusan, atau anonimisasi data harus ditinjau berdasarkan tujuan pemrosesan, kebutuhan operasional, dan ketentuan yang berlaku.

Prinsip penanganan:

- Identitas pelapor dapat dianonimkan apabila permintaan disetujui dan tidak terdapat dasar yang sah untuk mempertahankannya.
- Foto bukti dapat dihapus sesuai hasil peninjauan.
- Deskripsi dan lokasi tiket hanya dapat dipertahankan apabila masih diperlukan dan memiliki dasar yang sesuai.
- Permintaan harus ditinjau dan dicatat sesuai prosedur yang nantinya disepakati.

**TBD:** Prosedur operasional, pihak yang berwenang menyetujui, dan mekanisme pemenuhan permintaan hak subjek data perlu divalidasi dengan institusi.

---

## 2. Role-Based Access Control (RBAC)

### 2.1 Prinsip Otorisasi

KlasiFas menggunakan empat peran pengguna resmi:

1. Pelapor
2. Admin Sarpras
3. Teknisi
4. Pimpinan/Kaprodi

Setiap permintaan terhadap fitur dan data harus melalui pemeriksaan otorisasi di sisi server.

Prinsip wajib:

- Deny by default: akses ditolak apabila tidak ada izin eksplisit.
- Pemeriksaan peran dilakukan di backend, bukan hanya menyembunyikan menu pada antarmuka.
- Pengguna hanya boleh mengakses data yang sesuai dengan perannya.
- Perubahan hak akses harus dilakukan melalui mekanisme yang terkontrol.
- Identitas pengguna dan peran aktif harus diverifikasi sebelum operasi sensitif dilakukan.

### 2.2 Matriks Hak Akses

| Fitur / Data | Pelapor | Admin Sarpras | Teknisi | Pimpinan/Kaprodi |
|---|---|---|---|---|
| Membuat laporan keluhan (FR-01) | Ya (Formulir Terbuka) | Tidak | Tidak | Tidak |
| Melihat status tiket melalui mekanisme pelacakan | Tiket dengan akses valid | Ya | Tiket yang ditugaskan | Tidak |
| Melihat riwayat tiket | Tiket miliknya | Ya | Tiket yang ditugaskan | Tidak |
| Verifikasi kategori keluhan (FR-04) | Tidak | Ya | Tidak | Tidak |
| Mengubah kategori hasil verifikasi | Tidak | Ya | Tidak | Tidak |
| Menugaskan teknisi (FR-05) | Tidak | Ya | Tidak | Tidak |
| Melihat tiket yang ditugaskan | Tidak | Ya | Ya | Tidak |
| Memperbarui status dan catatan penyelesaian (FR-06) | Tidak | Tidak | Tiket yang ditugaskan | Tidak |
| Dashboard manajerial FR-07 | Tidak | Ya | Tidak | Ya, read-only |
| Membaca audit log FR-09 | Tidak | Ya | Tidak | Tidak |

Keterangan:

- Hak membuat laporan keluhan (FR-01) secara formal diperuntukkan bagi civitas akademika melalui peran Pelapor.
- Admin Sarpras memiliki kewenangan verifikasi, penugasan, dan pemantauan sesuai PRD.
- Teknisi hanya dapat memperbarui status tiket yang secara sah ditugaskan kepadanya.
- Pimpinan/Kaprodi hanya memperoleh akses baca terhadap informasi dashboard agregat.
- Pelapor tidak boleh mengakses tiket milik pengguna lain.
- Hak akses membaca audit log hanya diberikan kepada Admin Sarpras.

### 2.3 Pengamanan Status Tiket

Empat status resmi tiket adalah:

1. Baru
2. Terverifikasi
3. Diproses
4. Selesai

Perubahan status harus dilakukan melalui backend dengan pemeriksaan peran dan aturan transisi.

Ketentuan:

- Status tidak boleh diubah secara langsung melalui manipulasi parameter dari browser.
- Teknisi hanya dapat memperbarui status tiket yang ditugaskan kepadanya.
- Setiap perubahan status harus dicatat dalam audit log.
- Flag `needs_manual_verification` bukan status tiket, melainkan penanda bahwa tiket membutuhkan pemeriksaan manual.

### 2.4 Isolasi Audit Log dan Dashboard

**Audit log FR-09:**

- Hanya Admin Sarpras yang dapat membaca audit log.
- Teknisi dapat tercatat sebagai aktor yang melakukan perubahan, tetapi tidak memperoleh hak membaca keseluruhan audit log.
- Catatan audit harus memuat informasi perubahan yang relevan tanpa menyimpan password, token, atau secret.

**Dashboard FR-07:**

- Hanya Admin Sarpras dan Pimpinan/Kaprodi yang dapat mengakses dashboard manajerial.
- Pimpinan/Kaprodi memiliki akses read-only.
- Dashboard menggunakan data agregat berdasarkan kategori, lokasi, status, dan periode.
- Identitas pribadi pelapor tidak boleh ditampilkan.

### 2.5 Penegakan Otorisasi

Implementasi backend disarankan menggunakan decorator atau middleware pemeriksaan peran, misalnya `@role_required`.

Setiap endpoint harus melakukan pemeriksaan:

1. Apakah sesi pengguna valid?
2. Apakah pengguna memiliki peran yang diizinkan?
3. Apakah objek tiket termasuk dalam cakupan akses pengguna?
4. Apakah operasi yang diminta diizinkan untuk status tiket saat ini?

Kegagalan otorisasi harus menghasilkan respons yang sesuai tanpa membocorkan informasi internal.

---

## 3. Pengamanan Pelacakan Tiket Tanpa Login

### 3.1 Pemisahan Kode Referensi dan Token Akses

KlasiFas menggunakan dua komponen berbeda:

**A. Kode referensi tiket**

Format: `KF-XXXXXX`

- Prefix tetap `KF-`.
- Diikuti enam karakter kapital alfanumerik non-ambigu.
- Dibuat menggunakan modul kriptografis Python `secrets`.
- Digunakan sebagai identitas atau referensi tiket umum.
- Bukan kredensial keamanan untuk membuka detail tiket.

**B. Token akses rahasia**

Token akses merupakan kredensial terpisah yang digunakan untuk membuktikan hak akses terhadap detail tiket melalui mekanisme pelacakan tanpa login.

Aturan:

- Token harus memiliki entropi minimal 128 bit.
- Token dibuat menggunakan generator kriptografis yang aman, seperti `secrets.token_urlsafe(16)` atau mekanisme setara dengan entropi yang memenuhi persyaratan.
- Token asli tidak boleh disimpan dalam database.
- Database hanya menyimpan hash token.
- Perbandingan token harus dilakukan terhadap hash yang tersimpan dengan metode perbandingan constant-time menggunakan `hmac.compare_digest()` guna mencegah serangan *timing attack*.
- Token tidak boleh ditulis ke application log, URL analytics, atau pesan error.
- Token tidak boleh ditampilkan kembali setelah proses penerbitan kecuali melalui mekanisme penyampaian yang disetujui.

Contoh pembuatan dan verifikasi token yang aman:

```python
from flask import abort, request
from app.utils.ticket_identity import generate_access_token, verify_access_token

# 1. Saat tiket pertama kali dibuat: buat token dan simpan hash-nya di database.
# Token asli hanya ditampilkan sekali pada respons POST /lapor.
access_token, token_hash = generate_access_token()
# Simpan token_hash ke kolom database ticket.access_token_hash.

# 2. Saat pelapor mengirim formulir pelacakan melalui POST /lacak:
submitted_token = (request.form.get("access_token") or "").strip()

is_valid_access = verify_access_token(submitted_token, ticket.access_token_hash)

if not is_valid_access:
    # Tolak akses tanpa membocorkan status keberadaan kode tiket.
    abort(404)
```

Hash SHA-256 digunakan karena token memiliki entropi tinggi dan dihasilkan secara acak. Token asli hanya digunakan sesuai kebutuhan proses penerbitan dan validasi akses.

**Keputusan distribusi:** Token ditampilkan satu kali pada respons POST `/lapor` dengan header `Cache-Control: no-store`. Token asli tidak disimpan di database, session, URL, query parameter, flash, log, atau header. Masa berlaku token dan prosedur penerbitan ulang tetap TBD; utility rotasi hash tersedia tanpa endpoint reissue.

### 3.2 Perlindungan terhadap Enumeration dan Brute Force

Endpoint pelacakan harus dilindungi dari percobaan pencarian kode tiket dan token secara berulang.

Kontrol yang direkomendasikan:

- Rate limiting berdasarkan alamat IP.
- Pembatasan frekuensi permintaan pada endpoint `/lacak`.
- Respons generik untuk kegagalan kode atau token agar tidak membocorkan keberadaan tiket.
- Pencatatan percobaan akses mencurigakan tanpa menyimpan token asli.
- Pembatasan akses terhadap data tiket setelah kredensial berhasil diverifikasi.

**Usulan awal:** Maksimum 15 request per menit per IP untuk endpoint `/lacak`.

Angka tersebut masih perlu diuji dan disetujui kelompok. Rate limiting tidak boleh dianggap sebagai pengganti token rahasia yang kuat.

---

## 4. Autentikasi, Kredensial, dan Keamanan Sesi

### 4.1 Hashing Password

Password pengguna internal wajib disimpan dalam bentuk hash, bukan plaintext.

Ketentuan:

- Gunakan `generate_password_hash` dan `check_password_hash` dari Werkzeug.
- Gunakan algoritma scrypt sesuai keputusan TECHSTACK.
- Password asli tidak boleh dicatat pada log.
- Password tidak boleh dikirimkan melalui URL atau disimpan pada browser dalam bentuk plaintext.
- Proses autentikasi harus menggunakan pesan kesalahan generik.

Contoh:

```python
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

password_hash = generate_password_hash(
    password,
    method="scrypt"
)

is_valid = check_password_hash(
    password_hash,
    submitted_password
)
```

### 4.2 Keamanan Cookie dan Sesi

Konfigurasi cookie sesi wajib mengikuti prinsip keamanan berikut:

| Atribut | Ketentuan |
|---|---|
| HttpOnly | True |
| SameSite | Lax |
| Secure | True pada lingkungan produksi HTTPS |
| Session lifetime | Rekomendasi awal 2 jam |

Ketentuan tambahan:

- Sesi harus dihapus setelah logout.
- Sesi tidak boleh berisi password atau token akses tiket.
- Aplikasi harus melindungi sesi dari akses JavaScript melalui `HttpOnly`.
- `SESSION_COOKIE_SECURE` harus aktif pada produksi yang menggunakan HTTPS.
- Lingkungan development lokal dapat menggunakan HTTP sesuai konfigurasi TECHSTACK.

**Usulan:** Batas sesi dua jam perlu divalidasi berdasarkan kebutuhan operasional dan pengujian.

### 4.3 Pembatasan Percobaan Login

Endpoint login staf dan pelapor dilindungi dari brute-force dan credential stuffing.

Ketentuan saat ini:

- Maksimum lima percobaan login per lima menit untuk setiap kombinasi akun dan alamat IP.
- Maksimum 50 percobaan login per lima menit untuk setiap alamat IP sebagai perlindungan tambahan terhadap penyemprotan akun.
- Bucket staf dan pelapor dipisahkan agar percobaan pada satu portal tidak memblokir portal lain.
- Pesan kesalahan tidak boleh mengungkap apakah username atau password yang salah.
- Aktivitas login mencurigakan dapat dicatat tanpa merekam kredensial.
- Rate limiter bersifat in-memory per proses; batas multi-worker dan restart dicatat pada utilitas rate limiter.

Pembatasan global per akun lintas alamat IP masih menjadi backlog dan angka di atas masih perlu diuji dengan beban nyata.

### 4.4 Provisioning dan Pengelolaan Akun Staf serta Pelapor

Provisioning akun staf dan pelapor dilakukan melalui CLI lokal, bukan melalui halaman manajemen akun.

Ketentuan:

- CLI menyediakan `create-staff` untuk akun staf dan `create-reporter` untuk akun pelapor.
- Perubahan role, penonaktifan akun, dan reset password belum tersedia melalui CLI dan dicatat sebagai backlog pengembangan lanjutan.
- Password dimasukkan secara interaktif. Password tidak boleh diberikan melalui argumen command, dicatat pada log, atau disimpan dalam bentuk plaintext.
- Password disimpan menggunakan `generate_password_hash` dengan algoritma scrypt sesuai Bagian 4.1.
- Role staf yang didukung `create-staff` hanya `admin_sarpras`, `teknisi`, dan `pimpinan`.
- Akun `reporter` hanya dibuat melalui `create-reporter`; login pelapor mewajibkan password hash yang valid.
- Tidak ada registrasi publik.
- Tidak ada halaman manajemen akun dalam MVP.
- CLI hanya dijalankan oleh operator lokal yang berwenang dengan konfigurasi lingkungan yang sesuai.

---

## 5. Validasi Input dan Pertahanan Aplikasi Web

### 5.1 Validasi Sisi Server

Semua data yang diterima aplikasi harus divalidasi di sisi server.

Ketentuan:

- Jangan mempercayai validasi HTML atau JavaScript di browser sebagai satu-satunya pengaman.
- Validasi tipe, panjang, format, dan nilai input.
- Terapkan batas panjang teks keluhan.
- Validasi lokasi dan parameter pencarian berdasarkan aturan aplikasi.
- Tolak input yang tidak sesuai dengan skema.
- Lakukan normalisasi teks keluhan sebelum proses klasifikasi sesuai pipeline ML.

Validasi harus mempertahankan informasi lokasi yang diperlukan. Pembersihan angka untuk teks keluhan tidak boleh diterapkan secara membabi buta pada nama gedung, lantai, atau nomor ruangan.

### 5.2 Cross-Site Request Forgery (CSRF)

Formulir dan operasi yang mengubah data wajib dilindungi dari CSRF.

Ketentuan:

- Gunakan Flask-WTF atau mekanisme CSRF yang sesuai.
- Setiap operasi perubahan data harus memvalidasi token CSRF.
- Jangan menonaktifkan perlindungan CSRF hanya untuk mengatasi error implementasi.
- Endpoint yang dikecualikan harus memiliki alasan teknis dan kontrol pengganti yang jelas.

### 5.3 Cross-Site Scripting (XSS)

Untuk mencegah XSS:

- Gunakan auto-escaping bawaan Jinja2.
- Hindari penggunaan `|safe` terhadap input pengguna yang belum disanitasi.
- Jangan menyisipkan input pengguna langsung ke dalam JavaScript atau HTML.
- Lakukan encoding sesuai konteks ketika menampilkan data.
- Batasi penggunaan HTML yang berasal dari input pengguna.

Deskripsi keluhan dan catatan penyelesaian harus dianggap sebagai input tidak tepercaya.

### 5.4 SQL Injection

Seluruh kueri database wajib menggunakan parameter binding melalui SQLAlchemy ORM atau mekanisme parameterized query.

Dilarang:

- Menggabungkan input pengguna secara langsung ke string SQL.
- Membentuk query dinamis menggunakan concatenation input.
- Menggunakan raw SQL yang tidak melakukan parameter binding.

Penggunaan SQL mentah hanya dapat dipertimbangkan apabila parameter binding tetap diterapkan dan terdapat alasan teknis yang jelas.

### 5.5 Penanganan Error

- Jangan menampilkan stack trace kepada pengguna.
- Jangan mengungkap struktur database, konfigurasi internal, atau lokasi file sensitif.
- Catat detail teknis error pada log internal dengan penyaringan informasi sensitif.
- Gunakan pesan error yang aman dan mudah dipahami pengguna.

---

## 6. Keamanan File Unggahan Bukti Foto

### 6.1 Batas Ukuran dan Format File

Foto bukti bersifat opsional dan digunakan sebagai pendukung laporan fasilitas. Foto tidak menjadi input klasifikasi Machine Learning.

**Batas ukuran final:** Maksimum 3 MB per file.

Status: Disetujui kelompok.

Format yang diizinkan:

- `.jpg`
- `.jpeg`
- `.png`

MIME type yang diizinkan: `image/jpeg` dan `image/png`.

Batas dimensi final: maksimum 6000 x 6000 piksel.

Pustaka validasi gambar: Pillow.

Metadata EXIF wajib dihapus melalui re-encode sebelum file disimpan.

### 6.2 Validasi File Berlapis

Validasi dilakukan di sisi server dan tidak boleh hanya mengandalkan nama atau ekstensi file.

Lapisan validasi:

1. Periksa ekstensi terhadap daftar format yang diizinkan.
2. Periksa MIME type.
3. Periksa magic numbers atau signature file.
4. Pastikan file benar-benar dapat dibaca sebagai gambar menggunakan pustaka pemrosesan gambar yang sesuai.
5. Terapkan batas ukuran dan dimensi gambar yang wajar setelah parameter teknisnya ditetapkan.
6. Tolak file yang rusak, tidak sesuai format, atau terindikasi sebagai file berbahaya.

MIME type yang dikirim browser tidak boleh dianggap sebagai bukti validitas file.

### 6.3 Sanitasi Nama dan Pencegahan Path Traversal

Ketentuan:

- Gunakan `secure_filename` dari Werkzeug untuk sanitasi nama file.
- Gunakan nama penyimpanan internal yang acak agar tidak bergantung pada nama asli.
- Jangan menggunakan nama file dari pengguna sebagai path penyimpanan secara langsung.
- Pastikan lokasi file tetap berada di dalam direktori penyimpanan yang ditentukan.
- Tolak path yang mencoba mengakses direktori di luar lokasi penyimpanan.

### 6.4 Isolasi Penyimpanan dan Akses Foto

- Direktori `uploads/` harus berada di luar direktori aset publik seperti `app/static/`.
- File tidak boleh dapat diakses secara langsung melalui URL publik.
- Penampilan atau pengunduhan foto harus melalui route terproteksi.
- Backend harus memeriksa autentikasi, peran, dan hak akses terhadap tiket terkait sebelum memberikan file.
- Jangan menganggap seluruh pengguna internal otomatis berhak melihat semua foto.

### 6.5 Retensi dan Penghapusan Foto

**Usulan awal:** Foto disimpan selama enam bulan setelah tiket berstatus `Selesai`.

Status: Ditunda. Retensi dan penghapusan tidak termasuk TSK-F3-02.

Apabila disetujui, mekanisme pengelolaan meliputi:

- Pencatatan waktu penyelesaian tiket.
- Peninjauan berkala terhadap file yang telah melewati masa retensi.
- Penghapusan file melalui proses terkontrol.
- Pencatatan hasil penghapusan tanpa menyimpan isi file.
- Penanganan kegagalan penghapusan agar file tidak tertinggal tanpa pengawasan.

**TBD:** Jadwal pembersihan, pengecualian retensi, dan mekanisme penghapusan final harus ditentukan setelah persetujuan kelompok.

---

## 7. Keamanan Machine Learning dan Artefak Model

### 7.1 Perlindungan Artefak `.joblib`

KlasiFas menggunakan scikit-learn untuk klasifikasi keluhan dengan algoritma Multinomial Naive Bayes.

File model dan artefak `.joblib` memiliki risiko keamanan karena proses deserialisasi dapat menjalankan kode berbahaya apabila sumber file tidak tepercaya.

Aturan wajib:

- Hanya muat artefak `.joblib` dari pipeline pelatihan internal pengembang yang tepercaya.
- Lokasi artefak model yang diizinkan adalah direktori internal `app/ml/models/` sesuai TECHSTACK.
- Jangan memuat model dari unggahan pengguna, internet, atau sumber eksternal yang tidak diverifikasi.
- Jangan menyediakan fitur unggah model dari pengguna.
- Perubahan artefak model harus melalui proses pengujian dan peninjauan.
- Artefak model dan data mentah tidak boleh masuk repositori Git.

### 7.2 Integritas Dataset Pelatihan

- Dataset harus berasal dari sumber yang diperoleh dan digunakan secara sah.
- Data pribadi harus dianonimkan sebelum digunakan dalam proses pelatihan.
- Data pelatihan dan evaluasi harus dipisahkan sesuai prosedur eksperimen.
- Jangan mencampurkan data pengujian ke dalam proses pelatihan.
- Perubahan dataset harus dicatat agar eksperimen dapat ditelusuri.
- Dataset mentah yang mengandung informasi pribadi harus disimpan secara terbatas dan tidak disebarkan.

### 7.3 Fallback Aman FR-10

Apabila proses klasifikasi gagal atau modul ML tidak tersedia:

- Sistem tetap harus menyimpan laporan keluhan.
- Laporan diberi penanda `needs_manual_verification`.
- Penanganan dilanjutkan melalui proses verifikasi manual oleh Admin Sarpras.
- Kegagalan ML tidak boleh menyebabkan data laporan hilang.
- Detail error teknis tidak boleh ditampilkan kepada pengguna.
- Fallback tidak boleh mengubah empat status resmi tiket.

---

## 8. Secrets Management dan Konfigurasi Lingkungan

### 8.1 Perlindungan Secret dan File Sensitif

File berikut wajib dikecualikan dari Git:

- `.env`
- Data mentah yang mengandung PII.
- Direktori `uploads/`.
- Artefak model `.joblib`.
- File database lokal dan file sementara yang mengandung data sensitif.
- Kredensial dan konfigurasi rahasia lainnya.

Contoh aturan `.gitignore`:

```gitignore
.env
.env.*
!.env.example

uploads/
data/raw/
data/private/

*.joblib
*.sqlite
*.db

__pycache__/
venv/
.venv/
```

File `.env.example` hanya boleh berisi nama variabel dan placeholder, bukan nilai secret asli.

### 8.2 Validasi Variabel Lingkungan

Aplikasi wajib menerapkan mekanisme fail-fast apabila konfigurasi keamanan yang diwajibkan tidak tersedia.

Ketentuan:

- `SECRET_KEY` wajib tersedia.
- `DATABASE_URL` wajib tersedia pada konfigurasi produksi.
- Jangan menggunakan secret default yang diketahui publik.
- Jangan melakukan fallback diam-diam ke konfigurasi produksi yang lebih lemah.
- Nama konfigurasi yang tidak dikenal harus menghasilkan error yang jelas dan menghentikan inisialisasi aplikasi.

Konfigurasi mengikuti pola Development, Testing, dan Production yang ditetapkan pada TECHSTACK.

### 8.3 Penanganan Kebocoran Secret

Apabila secret terindikasi bocor:

1. Hentikan penggunaan secret yang terdampak.
2. Ganti secret melalui mekanisme konfigurasi lingkungan.
3. Evaluasi dampak terhadap sesi dan koneksi terkait.
4. Periksa riwayat repositori serta log untuk memastikan cakupan kebocoran.
5. Dokumentasikan tindakan penanganan tanpa menyalin nilai secret ke laporan.

Secret tidak boleh dikirim melalui chat publik, commit Git, atau dokumentasi yang dapat diakses umum.

---

## 9. Keamanan Jaringan dan HTTP

### 9.1 HTTPS

- Lingkungan produksi yang dapat diakses melalui jaringan harus menggunakan HTTPS.
- Cookie sesi `Secure` harus diaktifkan pada produksi HTTPS.
- Penggunaan HTTP untuk development lokal hanya diperbolehkan sesuai konfigurasi TECHSTACK.
- Secret dan kredensial tidak boleh dikirim melalui koneksi yang tidak aman.

### 9.2 HTTP Security Headers

Aplikasi disarankan menerapkan HTTP security headers melalui mekanisme Flask response hook atau konfigurasi setara.

Header yang direkomendasikan:

| Header | Nilai Rekomendasi | Tujuan |
|---|---|---|
| X-Content-Type-Options | `nosniff` | Mencegah MIME type sniffing |
| X-Frame-Options | `SAMEORIGIN` | Membatasi clickjacking |
| Referrer-Policy | `strict-origin-when-cross-origin` | Membatasi informasi referrer |
| Content-Security-Policy | Sesuai kebutuhan aplikasi | Membatasi sumber resource |

Content Security Policy harus disesuaikan dengan penggunaan Bootstrap dan Chart.js. Apabila CDN digunakan, hanya sumber yang benar-benar diperlukan yang boleh diizinkan.

### 9.3 Keamanan Respons dan Log

- Jangan mengembalikan stack trace kepada pengguna.
- Jangan menampilkan nilai secret, password, token, atau informasi database dalam pesan error.
- Log aplikasi harus membatasi informasi pribadi.
- Aktivitas sensitif harus dicatat sesuai kebutuhan audit.
- Log harus memiliki akses terbatas.

---

## 10. Aturan Keamanan untuk AI Coding Agent

Seluruh AI Coding Agent yang digunakan untuk mengembangkan KlasiFas wajib mengikuti aturan berikut:

1. Jangan pernah menuliskan secret, password, token, atau kredensial asli ke source code.
2. Jangan menonaktifkan CSRF, autentikasi, otorisasi, validasi input, atau kontrol keamanan lain hanya untuk menghilangkan error.
3. Jangan mengubah hak akses RBAC tanpa persetujuan dan dokumentasi.
4. Jangan memberikan akses audit log kepada Teknisi, Pelapor, atau Pimpinan/Kaprodi.
5. Jangan mengubah empat status resmi tiket tanpa persetujuan.
6. Jangan memuat file `.joblib` dari sumber eksternal yang tidak tepercaya.
7. Jangan memasukkan data mentah atau PII ke repositori Git.
8. Jangan mengubah konfigurasi produksi menjadi lebih lemah untuk mempermudah pengujian.
9. Jangan menghapus validasi atau penanganan error tanpa alasan teknis yang dapat dipertanggungjawabkan.
10. Setiap perubahan terkait keamanan harus disertai penjelasan dan pengujian yang relevan.
11. Apabila terdapat konflik antara instruksi implementasi dan kebijakan keamanan, hentikan perubahan terkait dan minta klarifikasi.
12. Gunakan dokumen PRD, TECHSTACK, dan SECURITY sebagai acuan, dengan tetap meminta persetujuan untuk keputusan yang masih TBD.

---

## 11. Pre-Deployment Security Checklist

Sebelum demo atau deployment, lakukan pemeriksaan berikut:

- [ ] `SECRET_KEY` tersedia dan tidak menggunakan nilai default.
- [ ] `DATABASE_URL` tersedia pada konfigurasi produksi.
- [ ] File `.env`, data mentah, `uploads/`, dan `.joblib` dikecualikan dari Git.
- [ ] Password disimpan menggunakan hashing scrypt Werkzeug.
- [ ] Cookie sesi menggunakan atribut keamanan yang sesuai.
- [ ] CSRF aktif pada form dan operasi perubahan data.
- [ ] Validasi input dilakukan di sisi server.
- [ ] SQLAlchemy menggunakan parameter binding.
- [ ] Pemeriksaan XSS melalui auto-escaping Jinja2 diterapkan.
- [ ] Pemeriksaan RBAC empat peran telah diuji.
- [ ] Audit log hanya dapat dibaca Admin Sarpras.
- [ ] Dashboard manajerial hanya dapat diakses Admin Sarpras dan Pimpinan/Kaprodi.
- [ ] Kode referensi tiket tidak dapat digunakan sebagai satu-satunya kredensial akses.
- [ ] Token akses tiket disimpan dalam bentuk hash dan tidak dicatat di log.
- [ ] Rate limiting pada endpoint sensitif telah diuji.
- [ ] Validasi file foto telah diuji terhadap file tidak valid.
- [ ] Direktori foto tidak dapat diakses langsung secara publik.
- [ ] Artefak `.joblib` hanya dimuat dari sumber internal tepercaya.
- [ ] Fallback FR-10 tetap menyimpan laporan ketika ML gagal.
- [ ] Error aplikasi tidak membocorkan stack trace atau informasi sensitif.
- [ ] Kebijakan TBD dan usulan yang belum disetujui tidak diterapkan sebagai keputusan final tanpa persetujuan.

---

## 12. Security Incident Reporting

Setiap anggota kelompok yang menemukan indikasi celah keamanan wajib melaporkannya kepada tim pengembang.

Informasi laporan sebaiknya mencakup:

- Deskripsi masalah.
- Bagian aplikasi yang terdampak.
- Langkah reproduksi jika aman dilakukan.
- Dampak potensial.
- Bukti pendukung yang tidak mengandung secret atau data pribadi.

Jangan menyebarkan detail celah keamanan, kredensial, atau data pribadi ke kanal publik.

**Narahubung:** TBD — ditetapkan oleh Kelompok 7.

---

## 13. Open Decisions dan TBD

Daftar berikut harus diselesaikan sebelum kebijakan terkait dianggap final.

| ID | Topik | Status |
|---|---|---|
| SEC-TBD-01 | Batas upload foto 3 MB, format JPEG/PNG, maksimum 6000 x 6000 piksel, EXIF dihapus | Final |
| SEC-TBD-02 | Persetujuan retensi foto enam bulan | Ditunda (di luar F3-02) |
| SEC-TBD-03 | Masa simpan data tiket | TBD |
| SEC-TBD-04 | Mekanisme penyampaian token akses tiket | Final: tampil sekali pada respons POST `/lapor`, tanpa URL/session/log, `Cache-Control: no-store` |
| SEC-TBD-05 | Masa berlaku dan penerbitan ulang token | Sebagian final: utility rotasi hash tersedia; expiry dan endpoint reissue TBD |
| SEC-TBD-06 | Parameter final rate limiting | TBD |
| SEC-TBD-07 | Kebijakan account lockout | TBD |
| SEC-TBD-08 | Prosedur pemenuhan hak subjek data | Perlu validasi institusi |
| SEC-TBD-09 | Jadwal pembersihan file foto | TBD |
| SEC-TBD-10 | Narahubung pelaporan celah keamanan | TBD |

Setiap perubahan terhadap keputusan di atas harus ditinjau dan disetujui sebelum diterapkan pada implementasi.

---

## 14. Change Log

| Versi | Status | Keterangan |
|---|---|---|
| 1.0 | Approved Draft | Penyusunan awal berdasarkan PRD v1.3, TECHSTACK v1.3, integrasi constant-time comparison hmac.compare_digest(), dan penyelarasan matriks RBAC FR-01. |

**Akhir Dokumen — SECURITY.md**
