
# Product Requirements Document (PRD)
# KlasiFas — Klasifikasi Keluhan Fasilitas Kampus

**Judul Proyek:** Rancang Bangun Sistem Klasifikasi Keluhan dan Dasbor Pemantauan Fasilitas Kampus Menggunakan Algoritma Naive Bayes  
**Institusi:** Universitas Muhammadiyah Prof. Dr. HAMKA (UHAMKA)  
**Fakultas:** Fakultas Teknologi Industri dan Informatika (FTII)  
**Kelompok:** 7  
**Status:** Approved Draft — Kelompok 7 Review  
**Versi:** 1.3  

---

## 1. Product Name

**KlasiFas (Klasifikasi Keluhan Fasilitas Kampus)** merupakan sistem informasi berbasis web yang dirancang untuk membantu pengelolaan keluhan fasilitas kampus melalui pelaporan terpusat, klasifikasi teks otomatis menggunakan algoritma Multinomial Naive Bayes, verifikasi berbasis manusia (*human-in-the-loop*), pengelolaan alur tindak lanjut, dan dasbor pemantauan internal.

Studi kasus pengembangan sistem difokuskan pada lingkungan Fakultas Teknologi Industri dan Informatika (FTII), Universitas Muhammadiyah Prof. Dr. HAMKA (UHAMKA).

---

## 2. Product Goal

Tujuan utama KlasiFas adalah menyediakan sistem pengelolaan keluhan fasilitas kampus yang terintegrasi agar proses pelaporan, pengelompokan, pemantauan, dan evaluasi penanganan keluhan dapat dilakukan secara lebih terstruktur dan transparan.

Tujuan khusus:

1. Menyediakan kanal pelaporan keluhan fasilitas kampus secara terpusat berbasis formulir web.
2. Mengotomatisasi klasifikasi teks keluhan ke dalam tujuh kategori fasilitas menggunakan algoritma Multinomial Naive Bayes.
3. Membantu Admin Sarpras memverifikasi dan mengoreksi hasil klasifikasi otomatis sebelum penugasan perbaikan.
4. Memfasilitasi penerusan dan penetapan penugasan keluhan kepada unit teknis atau petugas yang bertanggung jawab.
5. Menyediakan mekanisme pelacakan status dan riwayat penanganan keluhan bagi pelapor secara mandiri dan aman.
6. Menyajikan ringkasan visual dan agregasi data keluhan melalui dasbor internal untuk mendukung pemantauan dan pengambilan keputusan pimpinan fakultas serta pengelola sarana prasarana.
7. Mengevaluasi kinerja model klasifikasi teks dan tingkat kebergunaan (*usability*) sistem berdasarkan target perencanaan yang terukur.

---

## 3. Target Users

| Pengguna / Stakeholder | Peran dan Kebutuhan |
|---|---|
| Mahasiswa FTII | Melaporkan gangguan fasilitas secara mudah dan melacak kepastian status penanganan menggunakan kode laporan yang aman. |
| Dosen | Melaporkan kerusakan fasilitas ruang kelas atau laboratorium yang mengganggu kelancaran kegiatan belajar-mengajar. |
| Tenaga Kependidikan | Menyampaikan keluhan fasilitas kerja atau membantu perantara pencatatan laporan. |
| Admin Sarpras/Umum | Memeriksa laporan, memvalidasi kategori prediksi, melakukan koreksi, menugaskan teknisi, mengelola data master, membaca log audit, dan memantau dasbor. |
| Teknisi / Petugas Pemeliharaan | Menerima rincian penugasan perbaikan fisik yang ditugaskan kepadanya dan memperbarui status pengerjaan sesuai aturan transisi yang divalidasi beserta catatan tindakan. |
| Dekan / Wakil Dekan | Memantau ringkasan kondisi fasilitas, tren keluhan, dan evaluasi waktu penyelesaian melalui dasbor pemantauan internal untuk perencanaan perawatan fasilitas. |
| Ketua Program Studi | Memantau ringkasan keluhan fasilitas yang relevan dengan ruang perkuliahan dan laboratorium di lingkungan program studinya. |
| Unit TI / Sistem Informasi | Memberikan pertimbangan teknis terkait infrastruktur jaringan, hosting, dan integrasi sistem. |

Dosen pembimbing dan penguji berperan sebagai evaluator akademik terhadap kelayakan metodologi, kualitas implementasi perangkat lunak, dan capaian evaluasi proyek.

---

## 4. Problem Statement

Pengelolaan keluhan fasilitas di lingkungan kampus saat ini berpotensi menghadapi kendala operasional yang disebabkan oleh belum terintegrasinya media pelaporan:

1. **Pelaporan Tersebar:** Keluhan masuk melalui banyak kanal non-resmi (lisan, WhatsApp, email) sehingga data tercecer dan sulit dilacak perkembangannya.
2. **Informasi Tidak Lengkap:** Laporan teks bebas sering kali tidak memuat lokasi spesifik (gedung/lantai/ruang) atau waktu kejadian yang jelas.
3. **Kategorisasi Manual:** Pengelompokan jenis masalah dan penentuan unit penanggung jawab dilakukan secara manual oleh petugas, sehingga memakan waktu dan berpotensi tidak konsisten antarpetugas.
4. **Penugasan Informal:** Koordinasi dengan petugas pemeliharaan masih melalui pesan percakapan informal sehingga penugasan dan bukti penyelesaian tidak tercatat secara sistematis.
5. **Status Tidak Transparan:** Pelapor tidak memiliki media terpadu untuk memantau apakah keluhannya telah diterima, sedang diproses, atau selesai dikerjakan.
6. **Data Belum Terdokumentasi Terpusat:** Riwayat keluhan belum tersimpan di basis data terstruktur sehingga sulit mengidentifikasi masalah berulang dan lokasi yang rawan mengalami gangguan.
7. **Ketiadaan Dasbor Pemantauan:** Belum tersedia media visual terpadu bagi pimpinan fakultas untuk melihat statistik jumlah keluhan, tren, dan kinerja penanganan secara berbasis data.
8. **Karakteristik Teks Bebas Bahasa Indonesia:** Keluhan ditulis menggunakan bahasa santai, kata singkatan, dan rentan kesalahan ketik (*typo*), menuntut adanya tahapan pra-pemrosesan teks yang teruji sebelum diklasifikasikan.

> *Catatan:* Seluruh poin di atas merupakan identifikasi masalah dari analisis proses bisnis awal dan tetap perlu divalidasi dengan kondisi operasional aktual melalui wawancara dan observasi lapangan.

---

## 5. Core Features

### 5.1 Tabel Kebutuhan Fungsional Definitif (FR-01 s.d. FR-10)

Mengacu langsung pada dokumen resmi Pertemuan 6 (Halaman 4) dengan penegasan operasional:

| ID | Kebutuhan Fungsional | Aktor Terkait | Kriteria Penerimaan Awal (Dapat Diuji) |
|:---:|:---|:---:|:---|
| **FR-01** | Sistem menerima keluhan berisi deskripsi, kategori/lokasi fasilitas yang relevan, dan waktu laporan. | Pelapor | Data keluhan tervalidasi tersimpan di basis data dan memperoleh nomor/kode laporan unik yang aman; isian kategori oleh pelapor berstatus opsional/informasi tambahan, sedangkan kategori operasional resmi ditentukan oleh klasifikasi dan verifikasi Admin Sarpras. |
| **FR-02** | Sistem menyimpan dan menampilkan riwayat keluhan serta statusnya kepada pelapor yang berwenang. | Pelapor | Status dan riwayat yang ditampilkan sesuai dengan data terakhir yang tercatat di sistem (dilindungi mekanisme kode laporan). |
| **FR-03** | Sistem melakukan pra-pemrosesan teks dan menghasilkan prediksi kategori menggunakan Multinomial Naive Bayes. | Sistem | Kategori prediksi dan skor probabilitas/keyakinan tersimpan bersama waktu proses klasifikasi ($\le 2$ detik); hasil dapat diperiksa. |
| **FR-04** | Admin dapat memverifikasi, menerima, atau mengoreksi kategori hasil klasifikasi. | Admin Sarpras | Perubahan kategori tercatat, tersimpan log koreksinya, dan menjadi kategori operasional resmi laporan. |
| **FR-05** | Admin dapat menugaskan atau meneruskan keluhan kepada unit/petugas yang sesuai. | Admin Sarpras | Laporan terhubung dengan identitas penanggung jawab teknisi/unit definitif tanpa menambah status baru di luar empat status resmi. |
| **FR-06** | Teknisi dapat memperbarui status tindak lanjut dan menambahkan catatan penyelesaian. | Teknisi | Pembaruan status dan penambahan catatan perbaikan hanya dapat dilakukan oleh teknisi yang ditugaskan, mengikuti aturan transisi yang divalidasi, serta tersimpan beserta stempel waktu. |
| **FR-07** | Sistem menyediakan dasbor jumlah keluhan menurut kategori, lokasi, status, dan periode. | Admin Sarpras, Pimpinan Fakultas, Kaprodi | Visualisasi agregat dihitung dinamis dari data tersimpan di basis data dan dapat difilter; hak akses terbatas pada peran manajerial (tidak dapat diakses oleh teknisi atau publik). |
| **FR-08** | Sistem menyediakan pencarian/filter riwayat dan ringkasan laporan. | Admin Sarpras, Pimpinan | Hasil pencarian kata kunci dan penyaringan data laporan tampil presisi sesuai kriteria filter yang dipilih (terpisah dari fitur ekspor). |
| **FR-09** | Sistem mencatat perubahan penting pada kategori dan status untuk mendukung penelusuran. | Admin Sarpras (Pembaca Hak Akses), Teknisi (Aktor Tercatat) | Riwayat perubahan (siapa pengguna, waktu perubahan, nilai sebelum dan sesudah) tersimpan dalam log audit operasional; hanya Admin Sarpras yang memiliki hak akses membaca log audit tersebut. |
| **FR-10** | Sistem menampilkan pesan yang sesuai jika model tidak tersedia atau prediksi tidak dapat dihasilkan. | Admin Sarpras, Pelapor | Laporan tetap tersimpan utuh di basis data dan dapat diproses verifikasinya secara manual tanpa kehilangan data keluhan. |

---

### 5.2 Rincian Fitur Utama

#### A. Pelaporan Keluhan (FR-01)
* Formulir web responsif untuk mencatat teks deskripsi keluhan dalam bahasa Indonesia, pemilihan lokasi gedung/ruang, dan waktu laporan otomatis.
* **Status Kategori Isian Pelapor:** Isian pemilihan kategori fasilitas oleh pelapor pada formulir bersifat **opsional / informasi awal tambahan**. Kategori operasional resmi yang digunakan untuk tindak lanjut **hanya ditentukan** melalui klasifikasi Naive Bayes yang diverifikasi dan disetujui oleh Admin Sarpras.
* **Lampiran Bukti Foto (Opsional):** Berkas foto murni berfungsi sebagai bukti visual pendukung pengerjaan perbaikan fisik, **bukan** sebagai data masukan klasifikasi Machine Learning.
* **Mekanisme Kode Laporan `[Perlu Divalidasi]`:** Setiap laporan yang berhasil disimpan akan memperoleh nomor/kode laporan unik. Mekanisme pembuatan kode laporan harus dirancang secara aman (misalnya pengacakan non-sekuensial atau kombinasi token acak) agar pelapor dapat melacak statusnya secara mandiri tanpa risiko pembacaan data keluhan lain oleh pihak yang tidak berwenang.

#### B. Pra-pemrosesan Teks & Klasifikasi Naive Bayes (FR-03)
Tahapan pipeline NLP teks keluhan:
1. *Case folding* (penyeragaman huruf kecil pada teks deskripsi).
2. *Cleaning* (penghapusan karakter non-huruf, tanda baca, simbol, dan angka).  
   > [!IMPORTANT]
   > **Penegasan Pembersihan Angka:** Pembersihan angka (*cleaning digits*) **hanya diterapkan secara khusus pada teks deskripsi keluhan** untuk kebutuhan vektorisasi kosakata model ML. Pembersihan ini **sama sekali tidak mengubah, menghapus, atau memengaruhi** data entitas lokasi gedung, nomor lantai, maupun nomor ruangan (misalnya: "Ruang 3.2", "Lantai 2") yang disimpan pada kolom/atribut terpisah di basis data.
3. *Normalisasi singkatan dan kata slang* berbasis kamus kata baku.
4. *Tokenisasi* (pemisahan teks deskripsi menjadi deretan token kata).
5. *Stopword removal* menggunakan pustaka Sastrawi.
6. *Stemming* menggunakan algoritma Nazief-Adriani melalui pustaka Sastrawi.
7. *Ekstraksi fitur:* Pembobotan TF-IDF (*Term Frequency-Inverse Document Frequency*) dengan skema *unigram* dan *bigram*.
8. *Klasifikasi:* Multinomial Naive Bayes dengan Laplace smoothing ($\alpha = 1$).
* *Keluaran Model:* Menghasilkan label kategori prediksi dan skor keyakinan (*confidence score* / probabilitas posterior). Hasil ini merupakan rekomendasi awal (*decision support*) dan tidak menggantikan keputusan manusia.

#### C. Tujuh Kategori Klasifikasi Fasilitas (Sesuai Proposal P-5 Hal. 11)
| Kode | Kategori Fasilitas | Cakupan Fasilitas Kampus | Unit Penanggung Jawab (Rancangan Awal) |
|:---:|:---|:---|:---|
| **K1** | Ruang kelas dan perabot | Kursi kuliah, meja, papan tulis, proyektor kelas, kebersihan kelas. | Sarana-prasarana |
| **K2** | Laboratorium dan perangkat | Komputer laboratorium, perangkat keras praktikum, software lab. | Pengelola Lab / Unit TI |
| **K3** | Jaringan dan internet | Akses Wi-Fi lambat/putus, kendala login portal internet kampus. | Unit TI |
| **K4** | Kebersihan dan sanitasi | Toilet kotor/rusak, air bersih tidak mengalir, tempat sampah penuh. | Kebersihan / Sarpras |
| **K5** | Listrik, AC, dan penerangan | AC tidak dingin/bocor/mati, lampu padam, saklar atau stop kontak rusak. | Sarana-prasarana |
| **K6** | Keamanan, parkir, dan akses | Area parkir kendaraan, pintu gerbang, lift gedung, fasilitas keamanan. | Keamanan / Bagian Umum |
| **K7** | Lainnya | Keluhan fasilitas di luar enam kategori di atas (memerlukan tinjauan manual). | Admin Sarpras |

> *Catatan:* Pemetaan unit penanggung jawab di atas merupakan rancangan awal yang akan divalidasi bersama pihak Sarpras FTII UHAMKA.

#### D. Verifikasi & Koreksi Kategori (FR-04)
* Admin Sarpras memeriksa hasil prediksi kategori.
* Keluhan dengan probabilitas di bawah ambang keyakinan tertentu `[Perlu Divalidasi Nilai Ambangnya]` ditandai khusus untuk diverifikasi.
* Admin menetapkan kategori operasional resmi yang digunakan untuk penugasan.

#### E. Penugasan & Alur Status Penanganan (FR-05, FR-06)
* Admin Sarpras meneruskan laporan kepada teknisi atau unit penanggung jawab terkait dengan menyematkan informasi penanggung jawab pada data tiket (penugasan bukan merupakan status terpisah).
* Alur resmi transisi status dibatasi secara tegas pada empat status:
  $$\text{Baru} \longrightarrow \text{Terverifikasi} \longrightarrow \text{Diproses} \longrightarrow \text{Selesai}$$
* **Kewenangan dan Aturan Transisi Teknisi:** Teknisi **hanya berwenang** memperbarui status pada tiket yang secara sah ditugaskan kepadanya, mengikuti aturan transisi yang divalidasi (yaitu memperbarui dari status *Terverifikasi* ke *Diproses*, lalu ke *Selesai* disertai catatan tindakan perbaikan). Teknisi tidak memiliki kewenangan mengubah kategori fasilitas atau melompati alur status tanpa persetujuan Admin Sarpras.
* **Validasi Transisi `[Perlu Divalidasi]`:** Aturan rinci mengenai transisi status (termasuk kondisi pembatalan laporan atau kendala suku cadang) merupakan rancangan awal yang akan diselaraskan dengan hasil validasi operasional Sarpras.

#### F. Pelacakan Status & Riwayat Mandiri (FR-02)
* Pelapor memeriksa perkembangan penanganan secara mandiri dengan memasukkan nomor/kode laporan pada portal web.
* **Pengamanan Pelacakan Tiket:** Karena pelacakan dirancang tanpa proses login akun yang rumit, sistem harus menerapkan mekanisme pengamanan (seperti format kode laporan acak unik yang tidak mudah ditebak dan pembatasan frekuensi pencarian/*rate limiting*) guna mencegah pihak yang tidak berwenang melihat isi keluhan orang lain secara acak (*enumeration/guessing attack*).

#### G. Dasbor Pemantauan Internal (FR-07)
* Dasbor bersifat **internal** dan hak aksesnya dibatasi secara ketat hanya untuk peran manajerial yang berwenang: **Admin Sarpras, Pimpinan Fakultas (Dekan/Wakil Dekan), dan Ketua Program Studi (Kaprodi)**. Teknisi lapangan dan pelapor tidak memiliki akses ke dasbor analitik ini.
* Visualisasi agregat menggunakan **Chart.js**:
  1. Kartu ringkasan total keluhan dan status penanganan.
  2. Diagram batang sebaran keluhan per kategori fasilitas.
  3. Diagram garis tren keluhan (harian, mingguan, bulanan).
  4. Peringkat lokasi/gedung yang sering mengalami kerusakan.
* **Perlindungan Privasi:** Dasbor hanya menyajikan data statistik agregat dan **tidak pernah menampilkan identitas pribadi pelapor** (nama/kontak).
* **Integritas Analisis:** Dasbor menyajikan data apa adanya dari basis data; dilarang membuat kesimpulan tren apabila volume data belum mencukupi.

#### H. Pencarian dan Filter Laporan Terpusat (FR-08)
* Sistem menyediakan panel pencarian berbasis kata kunci dan filter multi-kriteria (kategori fasilitas, lokasi gedung, rentang tanggal, dan status penanganan).
* Fitur ini murni ditujukan untuk penelusuran data operasional dan ringkasan keluhan di lingkungan antarmuka sistem oleh Admin Sarpras dan Pimpinan.

#### I. Ekspor Ringkasan Laporan — PDF dan CSV (Fitur Opsional / Could Have)
* Terpisah dari fungsi pencarian/filter utama, sistem merencanakan fitur pengunduhan data ringkasan laporan yang tersaring ke dalam format **PDF dan CSV**.
* Fitur ini berstatus *Could Have* (opsional) dan akan diimplementasikan setelah seluruh kebutuhan fungsional utama (Must-Have dan Should-Have) selesai dan teruji.

#### J. Audit Trail Operasional (FR-09)
* Mencatat riwayat log perubahan data penting: waktu perubahan, aktor yang melakukan perubahan, nilai lama, nilai baru, dan catatan tindak lanjut.
* **Pembatasan Hak Baca Log Audit:** Log audit hanya dapat dibaca dan diakses oleh **Admin Sarpras** untuk menjaga akuntabilitas penanganan fasilitas. Teknisi tercatat sebagai pelaku perubahan (*actor of change*) ketika memperbarui status, namun **tidak memiliki hak akses** untuk membuka atau membaca log audit sistem.

#### K. Fallback Layanan Klasifikasi (FR-10)
* Jika modul Machine Learning mengalami kegagalan proses atau service tidak aktif, sistem tetap menyimpan data laporan secara aman di basis data.
* Sistem menampilkan pesan informatif kepada pengguna dan laporan dialihkan ke antrean verifikasi manual oleh Admin Sarpras tanpa ada data yang hilang.

---

## 6. Out of Scope

Fitur dan batasan berikut **secara tegas tidak termasuk** dalam ruang lingkup proyek KlasiFas:

1. **Aplikasi Mobile Native:** Tidak membangun aplikasi Android/iOS native (sistem berbasis web peramban responsif).
2. **Integrasi Eksternal SIAKAD / Single Sign-On (SSO):** Sistem tidak terhubung ke API sistem akademik universitas.
3. **Computer Vision / Klasifikasi Gambar:** Foto hanya berupa bukti lampiran visual opsional dan **tidak dianalisis** oleh algoritma Machine Learning.
4. **Analisis Sentimen & Deteksi Emosi/Sarkasme:** Fokus klasifikasi murni pada penentuan kategori fasilitas fisik dan unit penanggung jawab.
5. **Notifikasi Otomatis Berbayar:** Tidak menyediakan notifikasi SMS atau WhatsApp Gateway berbayar (pelacakan dilakukan mandiri via web menggunakan kode laporan).
6. **Penjadwalan Otomatis & Inventaris Aset:** Tidak mencakup pengaturan jadwal shift kerja teknisi, manajemen stok suku cadang, maupun anggaran pengadaan sarpras.
7. **Sistem Penggajian Teknisi:** Tidak mengelola kompensasi atau sistem penggajian teknisi.
8. **Pemrosesan Teks Bahasa Daerah atau Bahasa Asing:** Model klasifikasi hanya dirancang untuk teks keluhan dalam bahasa Indonesia.
9. **Operasional Produksi Penuh Pasca-Capstone:** Sistem dikembangkan sebagai purwarupa (*pilot project*) teruji di lingkup FTII UHAMKA.

---

## 7. Success Metrics (Target Perencanaan)

> [!NOTE]
> Seluruh indikator di bawah ini merupakan **target perencanaan akademis** yang dirumuskan pada dokumen Pertemuan 4 dan Pertemuan 5, **bukan** klaim hasil implementasi atau capaian aktual yang telah selesai.

### 7.1 Target Evaluasi Model Machine Learning
| Indikator Evaluasi | Target Perencanaan | Metode Pengukuran |
|---|:---:|---|
| **Akurasi Global** | $\ge 80\%$ | Pengujian pada data uji terpisah (*hold-out*). |
| **Macro-F1 Score** | $\ge 75\%$ | Rata-rata F1 seluruh kelas tanpa pembobotan untuk memitigasi risiko ketidakseimbangan kelas (*class imbalance*). |
| **Recall Minimum per Kategori** | $\ge 60\%$ | Memastikan performa deteksi pada kategori minoritas tetap dapat dipertanggungjawabkan. |
| **Kesepakatan Anotator (Cohen's Kappa)** | $\ge 0{,}60$ | Pengukuran konsistensi pelabelan data antara minimal dua anotator independen. |

*Komponen evaluasi model lengkap mencakup:* Confusion Matrix, Precision, Recall, F1 per kelas, analisis kesalahan klasifikasi (*misclassification analysis*), serta perbandingan dengan *baseline* Logistic Regression dan Linear SVM.

### 7.2 Target Dataset dan Validasi `[Target Perencanaan]`
* **Target Volume Data:** Minimal 600 sampel keluhan berlabel ($\pm 80\text{--}100$ sampel per kategori).
* **Anotasi Data:** Pelabelan oleh minimal dua anotator independen berpedoman pada panduan tertulis.
* **Skema Validasi:** *Stratified train-test split* 80:20 dan 5-fold *cross-validation* pada data latih.
* *Status Data:* Dataset riil **belum dinyatakan tersedia**; data akan dikumpulkan, dianonimkan, dan divalidasi setelah izin penggunaan data disetujui pihak sarpras.

### 7.3 Target Kinerja Sistem & Kebergunaan
| Indikator Kinerja | Target Perencanaan | Keterangan & Pengukuran |
|---|:---:|---|
| **Waktu Inferensi Model** | $\le 2$ detik / keluhan | Diukur saat proses inferensi teks keluhan tunggal. |
| **Waktu Pemuatan Dasbor** | $\le 3$ detik | Diuji pada beban data uji $\pm 1.000$ baris data keluhan di basis data. |
| **Kelulusan Uji Fungsional** | $100\%$ | Seluruh skenario pengujian *black-box* fungsi utama (FR-01 s.d. FR-10) lulus uji. |
| **Skor Kebergunaan (SUS)** | $\ge 68$ (*Above Average*) | Pengujian System Usability Scale (kuesioner 10 butir) kepada minimal 10 responden perwakilan (pelapor dan staf sarpras). |

---

## 8. Security & Privacy Requirements

### 8.1 Perlindungan Data Pribadi (Kepatuhan UU No. 27/2022 tentang PDP)
* **Prinsip Minimisasi Data:** Data identitas pelapor (nama, kontak) bersifat opsional saat pengisian formulir keluhan.
* **Anonimisasi Dataset Latih:** Identitas pribadi pelapor wajib disamarkan atau dihapus secara permanen sebelum data keluhan digunakan sebagai dataset pelatihan model Machine Learning.
* **Perlindungan Akses Dasbor:** Dasbor bersifat internal bagi pengguna manajerial berwenang dan **tidak menampilkan identitas pribadi pelapor** dalam visualisasi ringkasan.

### 8.2 Autentikasi, Pembatasan Hak Akses (RBAC), dan Pengamanan Pelacakan Tiket
* Pembatasan hak akses berbasis peran secara tegas di sisi server:
  * *Pelapor:* Mengisi formulir pelaporan dan memantau status laporannya sendiri via nomor/kode laporan.
  * *Admin Sarpras:* Akses penuh verifikasi kategori, penugasan teknisi, manajemen data master, pencarian/filter, membaca log audit (FR-09), dan ekspor ringkasan laporan.
  * *Teknisi:* Akses terbatas hanya pada daftar tugas penanganan yang diberikan kepadanya dan pembaruan status pengerjaan sesuai aturan transisi yang divalidasi. Teknisi **tidak memiliki hak akses** ke dasbor analitik eksekutif dan **tidak memiliki hak akses** membaca log audit sistem.
  * *Pimpinan Fakultas / Kaprodi:* Akses baca (*read-only*) terhadap statistik agregat dasbor pemantauan internal dan ringkasan laporan.
* **Pengamanan Akses Tiket Tanpa Login:** Sistem pelacakan mandiri tanpa login wajib diamankan dengan kode laporan acak unik (*cryptographically secure/unguessable token*) dan perlindungan pembatasan frekuensi percobaan (*rate limiting*) untuk mencegah serangan penelusuran tiket (*brute-force enumeration*) oleh pihak luar.
* **Penyimpanan Kredensial:** Kata sandi pengguna terdaftar (Admin, Teknisi, Pimpinan) wajib disimpan dalam bentuk nilai *hash* yang aman (misalnya bcrypt) dan dilarang disimpan dalam bentuk teks biasa (*plain text*).

### 8.3 Integritas Data & Validasi Input
* Seluruh input teks keluhan divalidasi dan disanitasi di sisi server untuk mencegah serangan *Cross-Site Scripting* (XSS).
* Kueri basis data wajib menggunakan *parameterized query* atau ORM teruji untuk mencegah *SQL Injection*.
* Unggahan bukti foto divalidasi ketat di sisi server (pemeriksaan tipe MIME citra, pembatasan ekstensi `.jpg`/`.jpeg`/`.png`, batas ukuran file maksimum 2–5 MB sebagai parameter teknis yang diatur lebih lanjut pada `SECURITY.md`, dan sanitasi nama berkas guna mencegah *directory traversal*).
* Kredensial, kunci rahasia (*secrets*), dan konfigurasi sensitif tidak boleh ditulis langsung di dalam kode sumber (*source code*).

### 8.4 Tanggung Jawab & Etika Penggunaan AI
* Hasil klasifikasi Naive Bayes diposisikan sebagai rekomendasi pendukung keputusan; Admin Sarpras tetap menjadi penentu akhir keputusan operasional (*human-in-the-loop*).
* Seluruh performa model dan keterbatasan data dilaporkan secara transparan dan jujur tanpa manipulasi angka.

---

## 9. Constraints, Assumptions & Dependencies

### 9.1 Technical Constraints
Tumpukan teknologi mengacu pada proposal resmi:

| Komponen | Pilihan Teknologi Utama | Catatan Teknis |
|---|---|---|
| **Bahasa Pemrograman** | Python 3.11 | Bahasa pemrograman terpadu untuk backend web dan machine learning. |
| **Backend Framework** | Flask | Kerangka kerja web utama untuk routing, API endpoint, dan manajemen sesi. |
| **Basis Data Relasional** | **PostgreSQL** | **Basis data utama** untuk penyimpanan data relasional dan agregasi dasbor. *(Catatan: SQLite hanya alternatif historis yang pernah dipertimbangkan pada pengujian awal, bukan target kebutuhan implementasi).* |
| **Frontend & UI** | HTML5, CSS3, JavaScript, Bootstrap | Tampilan antarmuka web responsif (desktop dan mobile browser). |
| **Dasbor Visualisasi** | Chart.js | Pustaka rendering grafik agregat di sisi klien. |
| **Pustaka Machine Learning** | scikit-learn | Implementasi MultinomialNB, TfidfVectorizer, dan metrik evaluasi. |
| **Pustaka NLP Indonesia** | Sastrawi | Stopword removal dan stemming bahasa Indonesia. |
| **Manipulasi Data** | pandas, numpy | Pra-pemrosesan dataset dan analisis data. |
| **Penyimpanan Model** | joblib | Serialisasi artefak model terlatih (`.joblib`). |
| **Alat Desain & Kolaborasi** | Git, GitHub, Figma, draw.io | Pelacakan versi dan perancangan diagram sistem. |

### 9.2 Project Assumptions `[Perlu Divalidasi]`
1. Pengguna kampus dapat menyampaikan keluhan secara memadai dalam bahasa Indonesia.
2. Setiap laporan keluhan memuat deskripsi permasalahan dan kejelasan lokasi fasilitas yang relevan.
3. Ketersediaan dan izin pembagian dataset keluhan historis dari bagian Sarpras FTII UHAMKA dapat diperoleh.
4. Jika data riil belum mencukupi target 600 sampel, data simulasi kuesioner terbuka dapat digunakan dengan penandaan sumber yang jujur dan transparan.
5. Admin Sarpras bersedia berperan aktif dalam alur verifikasi kategori dan pengujian kegunaan sistem.
6. Pemetaan 7 kategori fasilitas awal cukup representatif untuk menampung mayoritas kerusakan fasilitas di FTII UHAMKA.

### 9.3 Dependencies
Kelancaran penyelesaian proyek bergantung pada:
* Izin resmi penggunaan data keluhan fasilitas kampus dari pihak universitas/fakultas.
* Partisipasi minimal dua anotator independen dalam pelabelan dataset.
* Ketersediaan lingkungan runtime Python 3.11 dan dependensi pustaka terkait.
* Ketersediaan instalasi basis data PostgreSQL.
* Ketersediaan responden uji (minimal 10 orang) untuk pelaksanaan pengujian SUS.
* Koordinasi dan pembagian tugas yang solid antaranggota Kelompok 7 (Egi, Adrian, Ilham).

### 9.4 Project Risks & Mitigasi
| Risiko | Peluang / Dampak | Rencana Mitigasi |
|---|:---:|---|
| Data keluhan riil sulit diperoleh atau jumlahnya minim | Sedang / Tinggi | Ajukan permohonan izin lebih awal; sebar kuesioner keluhan terbuka kepada mahasiswa; tandai data simulasi secara transparan. |
| Distribusi kategori keluhan tidak seimbang (*imbalance*) | Tinggi / Sedang | Terapkan *stratified split*, jadikan Macro-F1 sebagai metrik utama, prioritaskan penambahan data latih, evaluasi sebaran kelas, serta perbaikan pra-pemrosesan teks. Penggabungan kategori minoritas ke kategori 'Lainnya' bukan mitigasi otomatis dan hanya dapat dipertimbangkan setelah melalui validasi serta persetujuan tertulis pihak Sarpras. |
| Performa klasifikasi model di bawah target | Sedang / Sedang | Evaluasi perbaikan pra-pemrosesan teks, normalisasi kata tidak baku, uji n-gram, dan andalkan verifikasi manual oleh Admin Sarpras. |
| Layanan klasifikasi Machine Learning mengalami galat | Rendah / Sedang | Terapkan mekanisme *fallback* (FR-10) agar laporan tetap tersimpan di basis data dan dialihkan ke penanganan manual. |
| Akses tidak sah atau kebocoran data tiket pelapor | Rendah / Tinggi | Terapkan kode laporan acak aman, *rate limiting* pada endpoint pelacakan, dan pembatasan hak akses berbasis peran (RBAC). |
| Keterlambatan validasi stakeholder | Sedang / Sedang | Jadwalkan wawancara dan survei sejak awal masa pengerjaan proyek. |
| Keterbatasan waktu pengerjaan proyek | Sedang / Sedang | Disiplin menerapkan skala prioritas MoSCoW (*Must-Have* diselesaikan terlebih dahulu). |

---

## 10. Notes

### 10.1 Prioritas Fitur (Pendekatan MoSCoW)
Berdasarkan dokumen Pertemuan 4 (Tabel 4.1) dan Pertemuan 6 (FR-01 s.d. FR-10):

* **Must Have (Prioritas Utama — Wajib Selesai):**
  * FR-01: Formulir pelaporan keluhan terstruktur (lokasi, deskripsi, foto opsional; isian kategori pelapor opsional).
  * FR-02: Pelacakan status dan riwayat keluhan bagi pelapor secara aman.
  * FR-03: Pra-pemrosesan teks dan klasifikasi 7 kategori Multinomial Naive Bayes.
  * FR-04: Verifikasi dan koreksi kategori oleh Admin Sarpras.
  * FR-05: Penugasan keluhan kepada unit/petugas penanggung jawab.
  * FR-06: Papan pembaruan status pengerjaan oleh teknisi sesuai kewenangan dan aturan transisi.
  * FR-07: Dasbor pemantauan internal (agregasi jumlah, kategori, tren, lokasi) untuk peran manajerial.
  * FR-10: Fallback pesan dan penanganan manual saat model ML gagal.
  * Pembatasan hak akses berbasis peran (RBAC) dan keamanan kata sandi hash.

* **Should Have (Prioritas Tambahan — Sangat Dianjurkan):**
  * FR-08: Pencarian dan filter laporan multi-kriteria secara terpusat.
  * FR-09: Pencatatan log riwayat perubahan kategori dan status (*audit trail* operasional; hak baca dibatasi untuk Admin Sarpras).
  * Penandaan khusus (*flagging*) terhadap keluhan dengan probabilitas di bawah ambang keyakinan.
  * Penandaan prioritas keluhan berdasarkan kata kunci darurat (misal: "korsleting", "bocor", "padam").

* **Could Have (Prioritas Opsional — Jika Waktu Mencukupi):**
  * Ekspor ringkasan laporan ke berkas **PDF dan CSV** (terpisah dari fungsi pencarian FR-08).
  * Modul pengelolaan data latih tambahan dari hasil koreksi admin untuk pelatihan ulang model (*retraining*).

### 10.2 Metodologi Pengembangan
* **Jalur Rekayasa Perangkat Lunak:** Menggunakan pendekatan *Iterative Prototyping* (analisis kebutuhan $\rightarrow$ rancangan arsitektur/wireframe $\rightarrow$ implementasi prototipe $\rightarrow$ evaluasi pengguna $\rightarrow$ penyempurnaan).
* **Jalur Machine Learning:** Mengikuti alur CRISP-DM (*Business Understanding* $\rightarrow$ *Data Understanding* $\rightarrow$ *Data Preparation* $\rightarrow$ *Modeling* $\rightarrow$ *Evaluation* $\rightarrow$ *Deployment/Integration*).

### 10.3 Integrasi Nilai Al-Islam Kemuhammadiyahan (AIK)
* **Amanah:** Mengelola informasi dan keluhan civitas secara bertanggung jawab hanya untuk peningkatan fasilitas kampus; menjaga kerahasiaan identitas pelapor.
* **Kejujuran:** Melaporkan hasil evaluasi model, akurasi, dan keterbatasan data apa adanya tanpa rekayasa angka.
* **Keadilan:** Menjaga evaluasi kinerja model pada seluruh kategori fasilitas (termasuk kelas minoritas) serta menempatkan manusia sebagai pengambil keputusan akhir.
* **Tanggung Jawab:** Setiap tindakan verifikasi dan pembaruan status tercatat dalam log audit operasional.
* **Kemanfaatan:** Menghasilkan solusi terapan yang secara konkret mempercepat penanganan fasilitas di FTII UHAMKA.

### 10.4 Hal-Hal yang Masih Perlu Divalidasi Lapangan `[Perlu Divalidasi]`
1. Format dan mekanisme pengamanan kode laporan acak untuk pelacakan tiket tanpa login.
2. Aturan rinci transisi status penanganan dan batasan kewenangan teknisi lapangan.
3. Izin resmi akses dan ketersediaan data keluhan historis bagian Sarpras FTII UHAMKA.
4. Validasi akhir daftar 7 kategori fasilitas dan unit kerja penanggung jawab bersama pimpinan sarpras.
5. Nilai ambang batas probabilitas (*confidence threshold*) untuk penandaan laporan yang wajib diverifikasi manual oleh admin.
6. Ketersediaan dan jadwal responden (minimal 10 orang) untuk pelaksanaan pengujian System Usability Scale (SUS).

### 10.5 Referensi Dokumen Sumber
1. *Seminar Capstone Project Pertemuan 1:* Karakteristik Masalah, Identifikasi Masalah, dan Identifikasi Stakeholder.
2. *Seminar Capstone Project Pertemuan 2:* Konsep PjBL, Karakteristik Capstone, dan Pembagian Peran Tim.
3. *Laporan Tugas Kelompok Pertemuan 3 (2):* Analisis Proses Bisnis AS-IS, 12 Aktivitas, dan Analisis Kebutuhan Sistem.
4. *Produk Pertemuan 4:* Dokumen Perencanaan Awal Capstone Project (MELATI).
5. *Proposal Capstone Project Pertemuan 5:* Rancang Bangun Sistem KlasiFas (Kajian Teori, Dataset, & Arsitektur).
6. *Laporan Tugas Kelompok Pertemuan 6:* Rancangan Arsitektur Berlapis, Use Case Diagram, DFD Level 0/1, Matriks Keterlacakan FR-01 s.d. FR-10, serta Analisis Keamanan dan AIK.

---

> **Pernyataan Batasan Dokumen:**  
> Dokumen PRD Revisi v1.3 ini merupakan spesifikasi kebutuhan dan panduan perancangan sistem. Dokumen ini **tidak menyatakan** bahwa sistem aplikasi, dataset keluhan, model Machine Learning, maupun pengujian telah selesai diimplementasikan.
