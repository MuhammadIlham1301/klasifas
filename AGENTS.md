# AGENTS.md — KlasiFas

Aturan kerja permanen untuk AI Coding Agent yang membantu proyek KlasiFas. Dokumen ini berlaku untuk Antigravity Agent, OpenCode, dan agent lain yang digunakan pada workspace proyek.
## 1. Project Overview

**KlasiFas — Klasifikasi Keluhan Fasilitas Kampus** adalah rancangan sistem informasi berbasis web untuk pelaporan, klasifikasi, pemantauan, dan tindak lanjut keluhan fasilitas kampus FTII UHAMKA. Sistem menggunakan preprocessing NLP Bahasa Indonesia dan algoritma Multinomial Naive Bayes untuk memberikan rekomendasi kategori keluhan yang diverifikasi oleh Admin Sarpras.

Proyek ini merupakan MVP/prototipe akademik lokal, bukan sistem produksi kampus. Data telemetry, integrasi drone, atau fitur di luar PRD tidak termasuk dalam proyek ini.
## 2. Peran AI Agent dan Pembagian Tugas

- **Antigravity IDE / Agent:** perencanaan, analisis, penyusunan dokumentasi, pemeriksaan konsistensi, dan review.
- **OpenCode:** implementasi kode, pengujian, debugging, refactoring, dan pekerjaan engineering.
- Tetapkan satu agent sebagai pelaksana utama untuk satu task. Jangan biarkan dua agent mengedit file yang sama secara bersamaan.
- Agent harus menyebutkan batas kemampuan atau aksesnya. Jangan mengklaim telah memeriksa, menjalankan, mengubah, atau menguji sesuatu jika tindakan tersebut belum benar-benar dilakukan.
## 3. Source of Truth

Sebelum mengerjakan task, baca dokumen yang relevan. Jika terdapat konflik, gunakan urutan acuan berikut:

1. `AGENTS.md` — tata kelola dan aturan operasional agent.
2. `docs/SECURITY.md` — ketentuan keamanan yang wajib dipatuhi.
3. `docs/PRD.md` — tujuan produk, ruang lingkup, aktor, dan kebutuhan fungsional.
4. `docs/TECHSTACK.md` — arsitektur dan teknologi yang disetujui.
5. `docs/DESIGN.md` — UI/UX, layar, komponen, dan design tokens.
6. `docs/TASKS.md` — urutan implementasi, dependensi, dan acceptance criteria.
7. `docs/SKILLS.md` — katalog skill dan panduan penggunaan kemampuan tambahan.
8. `README.md` — ringkasan proyek dan navigasi dokumentasi.

Ketentuan keamanan dalam `SECURITY.md`, ruang lingkup dalam `PRD.md`, dan keputusan teknologi dalam `TECHSTACK.md` tidak boleh dilanggar oleh instruksi skill, contoh kode, atau preferensi agent. Jika konflik tidak dapat diselesaikan dari dokumen, hentikan bagian yang terdampak dan minta keputusan kelompok.
## 4. Project Technology

Detail teknis wajib mengikuti `docs/TECHSTACK.md`. Ringkasannya:

- **Language/runtime:** Python 3.11.
- **Backend:** Flask dengan arsitektur Modular Monolith dan Application Factory.
- **Database:** PostgreSQL dengan SQLAlchemy 2.0 dan mekanisme migrasi yang ditetapkan di TECHSTACK.
- **Frontend:** HTML5, CSS3, Jinja2, Bootstrap 5, dan JavaScript.
- **Dashboard charts:** Chart.js.
- **NLP/ML:** PySastrawi, scikit-learn, TF-IDF, dan Multinomial Naive Bayes.
- **Data processing/model artifact:** pandas, NumPy, dan joblib.
- **Testing:** pytest dengan database PostgreSQL pengujian yang terisolasi.

Jangan mengganti, menambah, atau menaikkan versi teknologi tanpa persetujuan sesuai workflow proyek dan pembaruan dokumen terkait.
## 5. Commands and Current Project State

**Status saat dokumen ini dibuat:** proyek berada pada tahap persiapan spesifikasi dan dokumentasi. Kode aplikasi, konfigurasi runtime, dan perintah operasional belum boleh dianggap tersedia sebelum diverifikasi pada workspace.

Karena itu:
- Jangan mengarang perintah `npm`, `flask`, migrasi, build, lint, atau test yang belum tersedia.
- Sebelum menjalankan command, periksa file konfigurasi dan instruksi aktual proyek.
- Setelah implementasi tersedia, gunakan command yang benar-benar didefinisikan oleh proyek dan `TECHSTACK.md`.
- Pengujian harus menggunakan database khusus testing, bukan database development atau operasional.
- Jangan menjalankan perintah yang menghapus data atau mengubah skema database tanpa persetujuan eksplisit.
## 6. Workflow Rules

1. Baca task yang dituju dalam `docs/TASKS.md` dan dokumen acuannya.
2. Buat implementation plan yang menyebut tujuan, file terdampak, pendekatan, dependensi, risiko, dan cara verifikasi.
3. **Tunggu persetujuan pengguna sebelum menulis atau mengubah kode.**
4. Kerjakan satu task backlog dalam satu sesi. Jangan melompat ke task lain tanpa arahan.
5. Jangan mengerjakan task yang masih terhalang dependensi atau keputusan TBD.
6. Jangan memperluas scope di luar acceptance criteria task.
7. Setelah implementasi, jalankan pemeriksaan dan test yang relevan. Laporkan hasil aktual, termasuk test yang gagal atau tidak dapat dijalankan.
8. Perbarui status task hanya setelah acceptance criteria benar-benar diverifikasi. Jangan menandai task selesai berdasarkan rencana atau kode yang belum diuji.
9. Perbarui dokumentasi yang terdampak bila perubahan yang disetujui mengubah keputusan atau perilaku sistem.
10. Laporkan file yang diubah, ringkasan perubahan, command yang dijalankan, hasil pengujian, dan pekerjaan yang masih tertunda.

Untuk pekerjaan dokumentasi, jelaskan dokumen dan bagian yang akan diubah terlebih dahulu. Jangan mengubah kode aplikasi sebagai bagian dari task dokumentasi.
## 7. Core Product Rules

- Pertahankan sepuluh kebutuhan fungsional FR-01 sampai FR-10 sesuai `docs/PRD.md`.
- Gunakan tujuh kategori resmi: ruang kelas dan perabot; laboratorium dan perangkat; jaringan dan internet; kebersihan dan sanitasi; listrik, AC, dan penerangan; keamanan, parkir, dan akses; serta lainnya.
- Status tiket resmi hanya: `Baru`, `Terverifikasi`, `Diproses`, dan `Selesai`.
- Penugasan teknisi merupakan atribut penugasan, bukan status tiket.
- Admin Sarpras memverifikasi atau mengoreksi kategori dan menugaskan teknisi.
- Teknisi hanya mengelola tugas yang ditugaskan kepadanya sesuai otorisasi.
- Pimpinan/Kaprodi mengakses informasi agregat secara read-only.
- Foto merupakan bukti pendukung opsional; foto tidak digunakan untuk klasifikasi computer vision.
- Jika model ML tidak tersedia atau inferensi gagal, laporan tetap harus dapat disimpan dan diproses melalui fallback/verifikasi manual sesuai FR-10.
- Jangan menganggap target metrik, target jumlah dataset, atau rekomendasi sebagai hasil aktual atau keputusan final.
## 8. Code and Engineering Rules

- Gunakan nama variabel, fungsi, class, dan identifier dalam bahasa Inggris.
- Ikuti struktur Modular Monolith, Application Factory, dan pemisahan tanggung jawab sesuai TECHSTACK.
- Hindari duplikasi logika; gunakan modul/service yang sudah ada sebelum membuat abstraksi baru.
- Gunakan SQLAlchemy dan parameter binding untuk akses database. Jangan menyusun query SQL dari input pengguna.
- Validasi input di sisi server; jangan mengandalkan validasi browser sebagai kontrol keamanan.
- Jangan menaruh secret, password, token, atau data pribadi ke source code, dokumentasi publik, screenshot, atau log.
- Jangan menonaktifkan kontrol keamanan untuk mempermudah demo.
- Ikuti `DESIGN.md` untuk warna, tipografi, spacing, komponen, dan responsivitas; jangan hardcode nilai desain yang sudah memiliki token.
- Jangan memperkenalkan React, TypeScript, Node.js, Zod, Supabase, atau framework lain yang tidak disetujui dalam TECHSTACK.
- Jangan menambahkan dependency baru sebelum menjelaskan kebutuhan, alternatif, dampak, dan meminta persetujuan.
## 9. Security Rules

- Terapkan RBAC dan prinsip deny-by-default pada sisi server untuk seluruh endpoint internal.
- Password staf harus diproses sesuai kebijakan hashing pada `SECURITY.md`; jangan pernah menyimpan password plaintext.
- Token pelacakan rahasia harus dipisahkan dari kode referensi tiket. Jangan menempatkan token pada URL, query parameter, atau log.
- Gunakan proteksi CSRF pada form yang relevan dan output escaping sesuai framework.
- Validasi file unggahan mengikuti `SECURITY.md`, termasuk ekstensi, MIME type, magic number, dan validitas gambar. Simpan file pada lokasi non-publik dengan nama penyimpanan yang aman.
- Jangan mengasumsikan batas ukuran upload atau masa retensi yang masih berstatus rekomendasi/TBD sebagai keputusan final.
- Batasi data dashboard manajerial pada agregat yang diizinkan; jangan membocorkan PII pelapor.
- Muat artefak joblib hanya dari lokasi internal tepercaya.
- Akses audit log dan data tiket harus mengikuti matriks izin di `SECURITY.md`.
## 10. Data and Machine Learning Rules

- Gunakan hanya data yang penggunaan dan pemrosesannya telah diizinkan.
- Anonimkan atau minimalkan PII sebelum data digunakan untuk pelatihan maupun evaluasi.
- Jangan mengarang dataset, label, hasil training, confusion matrix, metrik, atau hasil eksperimen.
- Bedakan dataset target dari dataset yang benar-benar tersedia.
- Terapkan preprocessing yang sama secara konsisten pada data latih dan inferensi.
- Pertahankan label tujuh kategori resmi; perubahan label atau penggabungan kategori harus divalidasi dan disetujui.
- Evaluasi mengikuti pembagian data dan metrik pada PRD/TECHSTACK. Target evaluasi bukan klaim keberhasilan.
- Pastikan fallback FR-10 tetap bekerja ketika model atau pipeline ML gagal.
## 11. Do Not

- Jangan mengedit `.env`, secret, kredensial, atau file konfigurasi sensitif tanpa izin eksplisit.
- Jangan mengubah file migrasi atau menjalankan migrasi yang mengubah/menghapus data tanpa review dan persetujuan eksplisit.
- Jangan menjalankan perintah destruktif seperti penghapusan massal, `DROP TABLE`, reset database, atau force push tanpa konfirmasi eksplisit.
- Jangan commit, push, merge, atau mengubah branch tanpa arahan pengguna.
- Jangan mengubah file di luar scope task yang disetujui.
- Jangan membuat fitur Out of Scope, termasuk payment gateway, aplikasi mobile native, computer vision, dan deployment cloud publik produksi.
- Jangan membuat atau memasang skill baru tanpa persetujuan.
- Jangan mengklaim task, audit, test, atau deployment berhasil jika belum diverifikasi.
## 12. Definition of Done

Sebuah task baru dapat dinyatakan selesai jika:

- [ ] Implementasi sesuai tujuan dan acceptance criteria task di `docs/TASKS.md`.
- [ ] Tidak bertentangan dengan PRD, TECHSTACK, SECURITY, dan DESIGN.
- [ ] Otorisasi, validasi input, privasi, serta kontrol keamanan yang relevan sudah diperiksa.
- [ ] Test yang relevan telah dijalankan pada lingkungan yang benar dan hasilnya dilaporkan.
- [ ] Tidak ada regression atau error yang diketahui dan disembunyikan.
- [ ] Dokumentasi dan status backlog diperbarui bila memang terdampak.
- [ ] Pengguna menerima ringkasan file berubah, hasil verifikasi, dan sisa pekerjaan.

Jika suatu pemeriksaan tidak dapat dilakukan, tandai sebagai belum diverifikasi; jangan mencentangnya seolah-olah lulus.
## 13. Notes and Open Decisions

- KlasiFas adalah MVP akademik lokal untuk FTII UHAMKA, bukan deployment produksi.
- Nama file, endpoint, modul, dan struktur implementasi pada dokumen desain dapat berupa usulan sampai dikunci oleh keputusan proyek.
- Keputusan yang berstatus TBD harus tetap dianggap terbuka sampai kelompok menyetujuinya dan dokumen acuan diperbarui.
- Untuk daftar keputusan TBD dan dependensi task terbaru, periksa `docs/TASKS.md`.
- Jika instruksi pengguna tidak jelas atau berpotensi mengubah keputusan penting, berhenti pada bagian yang terdampak dan minta klarifikasi.

---

**KlasiFas — Kelompok 7**  
Fakultas Teknologi Industri dan Informatika (FTII)  
Universitas Muhammadiyah Prof. Dr. HAMKA (UHAMKA)

**Status dokumen:** Draft — Menunggu Review Kelompok.
