# AI Technical Skills Catalog

**KlasiFas — Klasifikasi Keluhan Fasilitas Kampus**

Panduan dan tata kelola kemampuan AI Coding Agent untuk proyek KlasiFas.

| Informasi | Keterangan |
|---|---|
| Institusi | Universitas Muhammadiyah Prof. Dr. HAMKA (UHAMKA) |
| Fakultas | Fakultas Teknologi Industri dan Informatika (FTII) |
| Kelompok | 7 |
| Versi Dokumen | 0.1 |
| Status | Draft — Menunggu Review Kelompok |
| Backlog Acuan | 35 tugas dalam 8 fase |

---

## 1. Tujuan dan Prinsip Penggunaan

Dokumen ini menjadi katalog kemampuan dan panduan prosedural bagi AI Coding Agent yang membantu pengembangan KlasiFas. Dokumen ini menjelaskan skill yang tersedia, kapan digunakan, batas penggunaannya, serta skill khusus proyek yang dapat diusulkan untuk mendukung pekerjaan teknis.

**Skill** adalah paket instruksi yang membantu AI menjalankan jenis pekerjaan tertentu secara konsisten. Katalog ini tidak otomatis memasang skill atau menjamin suatu agent memiliki kapabilitas tertentu.

### 1.1 Lingkungan Kerja Agent

- **Antigravity IDE / Agent:** digunakan untuk perencanaan, penyusunan dan pemeriksaan dokumentasi, analisis, serta review.
- **OpenCode:** digunakan sebagai coding agent utama untuk implementasi, pengujian, debugging, refactoring, dan pekerjaan engineering.
- **Skill eksternal:** dapat tersedia secara global atau melalui integrasi agent. Ketersediaan dan kompatibilitasnya harus diperiksa pada lingkungan agent yang sedang digunakan.
- **Skill prosedural KlasiFas:** panduan kerja khusus proyek yang dapat dibuat setelah disetujui. Nama skill yang tercantum sebagai rancangan bukan bukti bahwa paket tersebut sudah terpasang.

### 1.2 Hierarki dan Kepatuhan Dokumen

Sebelum menjalankan tugas, agent wajib membaca `AGENTS.md` dan dokumen proyek yang relevan. Ketentuan proyek tidak boleh dilanggar hanya karena instruksi skill eksternal menyarankan pendekatan berbeda.

Acuan utama:
1. `AGENTS.md` — aturan operasional agent dan alur kerja.
2. `docs/PRD.md` — tujuan, ruang lingkup, aktor, dan kebutuhan fungsional.
3. `docs/TECHSTACK.md` — arsitektur dan teknologi yang disetujui.
4. `docs/SECURITY.md` — ketentuan keamanan.
5. `docs/DESIGN.md` — ketentuan UI/UX.
6. `docs/TASKS.md` — backlog dan kriteria penerimaan.
7. `docs/SKILLS.md` — katalog dan panduan skill.

Jika terdapat konflik, ikuti hierarki dokumen pada `AGENTS.md`. Ketentuan keamanan pada `SECURITY.md`, ruang lingkup pada `PRD.md`, dan keputusan teknologi pada `TECHSTACK.md` tidak boleh diubah oleh skill tanpa persetujuan kelompok.

### 1.3 Protokol Pemanggilan Skill

1. Identifikasi tujuan dan ruang lingkup task.
2. Periksa katalog ini dan ketersediaan skill pada agent yang sedang digunakan.
3. Baca instruksi skill yang relevan sebelum menggunakannya.
4. Gunakan hanya skill yang sesuai dengan task dan kompatibel dengan stack KlasiFas.
5. Jika skill tidak tersedia, jangan berpura-pura telah menjalankannya. Kerjakan berdasarkan dokumen proyek atau laporkan keterbatasannya.
6. Jika instruksi skill bertentangan dengan dokumen proyek, hentikan langkah yang berkonflik dan laporkan.
7. Jangan memasang dependensi, membuat skill baru, atau mengubah arsitektur tanpa persetujuan sesuai `AGENTS.md`.

Satu task dapat membutuhkan lebih dari satu skill. Contohnya, implementasi form pelaporan dapat memerlukan panduan backend, keamanan, UI, dan pengujian.

---

## 2. Inventaris Skill dan Integrasi Eksternal

Daftar berikut mencatat tools/skill eksternal yang pernah dilaporkan terpasang dalam lingkungan kerja. Status aktual perlu diverifikasi kembali pada agent dan mesin yang digunakan sebelum mengandalkannya.

| Nama | Status yang pernah dilaporkan | Peran / penggunaan | Batasan |
|---|---|---|---|
| Caveman | Terpasang secara global di OpenCode | Kumpulan instruksi/skill tambahan untuk membantu pekerjaan agent | Periksa skill spesifik yang tersedia; jangan menganggap semua instruksinya cocok untuk KlasiFas |
| Impeccable | Terpasang | Pendukung kualitas desain dan evaluasi UI | Gunakan hanya untuk pekerjaan antarmuka; ikuti `DESIGN.md` |
| UI UX Pro Max (`ui-ux-pro-max`) | Terpasang | Referensi dan panduan desain UI/UX | Bukan pengganti spesifikasi desain KlasiFas |
| Graphify | Terpasang; pernah dilaporkan versi 0.9.100 | Analisis dan pemetaan relasi/struktur proyek melalui integrasi yang tersedia | Inisialisasi proyek dan kompatibilitas perlu diperiksa; jangan menganggap graph sudah dibuat |
| Context7 | Connected / terhubung | Membantu mengambil dokumentasi library dan framework | Integrasi dokumentasi, bukan skill prosedural proyek |
| Ponytail | Pernah dilaporkan terpasang | Skill tambahan dari setup sebelumnya | Fungsi, cakupan, dan kompatibilitas perlu diverifikasi sebelum digunakan |

**Catatan inventaris:**
- Tabel ini merupakan catatan dari setup sebelumnya, bukan hasil pemeriksaan langsung konfigurasi agent saat ini.
- Agent harus memverifikasi nama, lokasi, versi, dan ketersediaan skill sebelum menyatakan skill aktif.
- RTK dan Taste Skills pernah dilaporkan tidak jadi dipasang.
- AgentMemory pernah dilaporkan dihapus. Jangan menganggapnya masih tersedia.
- Jangan menyimpan token, API key, kredensial, atau data sensitif di dokumen katalog ini.

---

## 3. Skill Prosedural Khusus KlasiFas

Bagian ini mendefinisikan panduan kerja yang dibutuhkan proyek. Nama-nama di bawah adalah **rancangan skill prosedural KlasiFas**, bukan klaim bahwa folder `SKILL.md` masing-masing sudah dibuat atau terpasang.

### 3.1 Skill Inti (Core)

| Nama Skill | Dipakai saat | Jangan dipakai saat |
|---|---|---|
| `flask-modular-builder` | Membuat atau mengubah aplikasi Flask, Application Factory, Blueprint, routing, Jinja2, dan service sesuai `TECHSTACK.md` | Mengubah arsitektur atau menambah framework tanpa persetujuan |
| `sqlalchemy-pg-modeler` | Membuat model dan relasi SQLAlchemy, query PostgreSQL, transaksi, serta migrasi skema | Mengubah skema database tanpa memeriksa kebutuhan dan migrasi yang sudah ada |
| `nlp-indonesian-preprocessor` | Mengembangkan preprocessing teks keluhan Bahasa Indonesia sesuai pipeline yang disetujui | Memproses data pribadi yang belum diizinkan atau mengganti pipeline tanpa evaluasi |
| `naive-bayes-classifier` | Melatih, mengevaluasi, menyimpan, memuat, dan menjalankan inferensi TF-IDF + Multinomial Naive Bayes | Mengklaim target evaluasi sebagai hasil aktual atau mengubah label/kategori tanpa persetujuan |
| `security-hardener` | Menerapkan atau meninjau autentikasi, RBAC, session, token pelacakan, CSRF, validasi upload, dan keamanan data | Mengurangi kontrol keamanan demi kemudahan implementasi atau mengubah kebijakan `SECURITY.md` |
| `pytest-suite-runner` | Membuat dan menjalankan unit test serta integration test, termasuk penggunaan database pengujian terpisah | Menggunakan database pengujian untuk data operasional atau mengklaim code coverage 100% dari test pass rate |

#### Panduan khusus skill inti

**`flask-modular-builder`**
- Ikuti pola Application Factory dan struktur Modular Monolith yang ditetapkan `TECHSTACK.md`.
- Gunakan Blueprint sesuai pembagian tanggung jawab modul.
- Pisahkan routing, logika bisnis, akses data, dan integrasi ML secara terstruktur.
- Gunakan Jinja2 untuk rendering template sesuai stack proyek.
- Jangan membuat REST API terpisah atau microservice tanpa persetujuan.

**`sqlalchemy-pg-modeler`**
- Gunakan SQLAlchemy 2.0 dan PostgreSQL sesuai `TECHSTACK.md`.
- Gunakan parameter binding/parameterized query; jangan merangkai input pengguna menjadi SQL mentah.
- Perubahan skema harus disertai migrasi dan pertimbangan data yang sudah tersimpan.
- Pisahkan konfigurasi database development, testing, dan production.
- Database pengujian harus terisolasi dari database development/operasional.

**`nlp-indonesian-preprocessor`**
- Ikuti urutan preprocessing yang ditetapkan dokumen ML proyek: case folding, pembersihan teks, tokenisasi, stopword removal, dan stemming menggunakan PySastrawi.
- Terapkan preprocessing yang sama secara konsisten pada data latih dan data inferensi.
- Jangan melakukan pembersihan numerik pada field lokasi gedung/lantai/ruang; aturan tersebut berlaku pada deskripsi keluhan sesuai keputusan PRD.
- Perubahan normalisasi slang atau preprocessing harus dicatat dan dievaluasi dampaknya.

**`naive-bayes-classifier`**
- Gunakan TF-IDF unigram/bigram dan MultinomialNB dengan konfigurasi yang ditetapkan dokumen proyek.
- Pertahankan tujuh kategori fasilitas resmi.
- Evaluasi dengan metrik yang ditetapkan, termasuk Accuracy, Macro-F1, dan recall per kelas. Cohen's Kappa digunakan untuk evaluasi kesepakatan anotator jika data anotasi tersedia.
- Bedakan target metrik dari hasil eksperimen aktual.
- Simpan artefak model secara lokal dan hanya muat artefak tepercaya.
- Jika model tidak tersedia atau inferensi gagal, jalankan fallback sesuai FR-10 agar laporan tetap tersimpan dan dapat diverifikasi manual.

**`security-hardener`**
- Ikuti `SECURITY.md` untuk hashing password, session, CSRF, RBAC, token pelacakan, validasi unggahan, dan perlindungan data pribadi.
- Terapkan prinsip deny-by-default dan pemeriksaan otorisasi di sisi server.
- Token pelacakan rahasia tidak boleh ditempatkan pada URL, query parameter, atau log.
- Validasi unggahan harus mengikuti ketentuan ekstensi, MIME type, magic number, dan validitas gambar yang ditetapkan `SECURITY.md`.
- Jangan menambahkan library validasi gambar seperti Pillow/PIL sebagai dependensi wajib kecuali disetujui dan dicatat pada `TECHSTACK.md`.

**`pytest-suite-runner`**
- Gunakan pytest untuk unit test dan integration test.
- Gunakan database PostgreSQL khusus pengujian yang terpisah dari database development dan operasional.
- Uji alur berhasil, input tidak valid, akses tanpa otorisasi, dan kondisi fallback.
- Kriteria 100% test pass rate berarti seluruh test yang didefinisikan lulus tanpa failure/error; bukan code coverage 100%.
- Jangan menjalankan test yang berpotensi menghapus atau mengubah data di database non-testing.

### 3.2 Skill Pendukung (Supporting)

| Nama Skill | Dipakai saat | Jangan dipakai saat |
|---|---|---|
| `bootstrap-ui-stylist` | Membuat atau memperbaiki halaman dan komponen Bootstrap 5 sesuai `DESIGN.md` | Mengubah aturan bisnis, status tiket, atau otorisasi |
| `chartjs-visualizer` | Membuat visualisasi dasbor agregat menggunakan Chart.js sesuai FR-07 | Menampilkan identitas atau data pribadi pelapor pada dasbor manajerial |
| `code-review` | Meninjau perubahan kode sebelum integrasi atau penyelesaian task | Menggantikan pengujian otomatis atau menyetujui perubahan yang belum diverifikasi |
| `documentation-maintainer` | Memperbarui dokumentasi ketika keputusan, implementasi, atau hasil pengujian berubah | Mengubah keputusan proyek tanpa persetujuan |

#### Panduan khusus skill pendukung

**`bootstrap-ui-stylist`**
- Gunakan Bootstrap 5 dan design tokens pada `DESIGN.md`.
- Terapkan responsivitas dan pola komponen yang telah ditentukan.
- Jaga konsistensi dengan spesifikasi layar, navigasi, form, tabel, dan status tiket.
- Jangan menambahkan React, TypeScript, atau framework UI lain tanpa persetujuan.

**`chartjs-visualizer`**
- Gunakan Chart.js sesuai versi dan pola integrasi yang ditetapkan `TECHSTACK.md`.
- Visualisasikan data agregat seperti distribusi kategori, lokasi, status, dan tren waktu.
- Terapkan filter agregat sesuai kebutuhan dasbor.
- Jangan mengirim identitas, deskripsi sensitif, token, atau informasi pribadi pelapor ke tampilan manajerial.

**`code-review`**
- Periksa kesesuaian perubahan terhadap PRD, TECHSTACK, SECURITY, DESIGN, dan TASKS.
- Prioritaskan bug, regresi, celah otorisasi, kebocoran data, dan ketidaksesuaian acceptance criteria.
- Laporkan temuan dengan tingkat risiko dan referensi file/baris bila tersedia.
- Jangan menyatakan kode aman hanya berdasarkan pembacaan tanpa pengujian yang relevan.

**`documentation-maintainer`**
- Perbarui dokumen yang terdampak oleh perubahan yang telah disetujui.
- Bedakan kondisi aktual, rencana, target, hasil pengujian, dan TBD.
- Pertahankan konsistensi istilah, FR, status tiket, kategori, peran, dan struktur proyek.
- Jangan membuat klaim implementasi sudah selesai jika belum diverifikasi.

---

## 4. Skill Ditunda dan Batasan Out of Scope

### 4.1 Ditunda / TBD

| Kapabilitas | Status | Ketentuan |
|---|---|---|
| `dataset-curator` | TBD | Pengumpulan, anonimisasi, kurasi, dan pelabelan dataset bergantung pada ketersediaan data yang sah, izin penggunaan, dan kesepakatan kelompok. Target jumlah sampel bukan bukti dataset sudah tersedia. |
| Otomatisasi deployment | Ditunda | Hanya dipertimbangkan jika kebutuhan deployment disetujui; bukan bagian dari MVP lokal saat ini. |
| Skill tambahan dari pihak ketiga | TBD | Harus dievaluasi manfaat, kompatibilitas, keamanan, dan kebutuhan dependensinya sebelum dipasang. |

### 4.2 Out of Scope MVP

Kapabilitas berikut tidak boleh dikerjakan sebagai bagian MVP tanpa perubahan ruang lingkup yang disetujui:

- Payment gateway atau fitur transaksi/pembayaran.
- Aplikasi mobile native dan mobile API khusus.
- Deployment cloud publik berskala produksi atau cloud auto-scaling.
- Computer vision untuk mengklasifikasikan foto fasilitas.
- Analisis sentimen atau NLP multibahasa di luar ruang lingkup.
- Integrasi SIAKAD/SSO atau layanan eksternal kampus yang belum disetujui.
- Penjadwalan teknisi otomatis, inventaris, pengadaan, dan penggajian.

---

## 5. Aturan Pembuatan dan Pemeliharaan Skill

1. Jangan membuat, memasang, menghapus, atau memperbarui skill tanpa persetujuan sesuai `AGENTS.md`.
2. Sebelum mengusulkan skill baru, jelaskan masalah yang diselesaikan, pemicu penggunaan, batasan, dependensi, dan manfaatnya.
3. Satu skill sebaiknya memiliki satu tanggung jawab utama dan deskripsi pemicu yang spesifik.
4. Instruksi skill harus menyebut dokumen proyek yang wajib dibaca.
5. Skill tidak boleh memperkenalkan stack, dependensi, endpoint, tabel, atau fitur baru tanpa persetujuan.
6. Uji instruksi skill dengan task representatif sebelum menyatakan skill siap digunakan.
7. Catat status skill secara akurat: `Terpasang`, `Tersedia`, `Rancangan`, `TBD`, atau `Tidak Digunakan`.
8. Jangan menyamakan katalog ini dengan folder skill yang benar-benar tersedia pada agent.

Jika kelak skill prosedural proyek dibuat sebagai paket terpisah, gunakan format dan lokasi yang kompatibel dengan agent yang digunakan. Lokasi `.claude/skills/` pada template lama tidak boleh dianggap sebagai lokasi universal untuk OpenCode maupun Antigravity.

---

## 6. Riwayat Perubahan

| Versi | Perubahan |
|---|---|
| 0.1 | Rekonstruksi template generik menjadi katalog skill KlasiFas; membedakan inventaris eksternal, rancangan skill prosedural proyek, dan kapabilitas TBD/out of scope. |

---

**KlasiFas — Sistem Klasifikasi Keluhan Fasilitas Kampus**  
Fakultas Teknologi Industri dan Informatika (FTII)  
Universitas Muhammadiyah Prof. Dr. HAMKA (UHAMKA)  
Kelompok 7 — Seminar Capstone Project

**Status dokumen:** Draft v0.1 — Menunggu Review Kelompok.
