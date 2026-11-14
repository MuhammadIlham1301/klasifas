# KlasiFas — Consolidated Design Audit

**Status:** audit konsolidasi selesai direkonsiliasi dan diverifikasi penuh terhadap working tree Flask, skema PostgreSQL, decorator RBAC, dan test suite proyek (252 unit tests passed).

## 1. Inventaris desain yang dikonsolidasikan

| Area | Sumber desain yang diperiksa | Cakupan yang teridentifikasi | Status konsolidasi |
|---|---|---|---|
| Pimpinan/Kaprodi | Paket executive dashboard Stitch (arsip visual) | Dashboard agregat/read-only, KPI, tren, distribusi kategori/lantai | Dipertahankan; klaim angka/semester/identitas mockup wajib diganti data ilustratif atau data aktual terverifikasi |
| Admin Sarpras | Paket admin queue, verification, audit log (arsip visual) | Antrean, verifikasi/penugasan, Audit Log | Dipertahankan; hapus SLA, akurasi model, data personel, IP/node, hash ledger, dan metrik yang belum dibuktikan |
| Login Staf | Paket login desktop/mobile (arsip visual) | Login internal Admin, Teknisi, Pimpinan | Dipertahankan; mekanisme field/validasi wajib mengikuti Flask Auth yang ada |
| Teknisi | Paket dashboard tugas dan detail/progres desktop/mobile (arsip visual) | Tiket penugasan, detail, catatan progres, foto opsional | Dipertahankan; tanpa SLA/PBM/inventaris; kategori read-only; Audit Log dilarang |
| Pelapor | Paket form, receipt, tracking desktop/mobile (arsip visual) | Pelaporan, tanda terima, pelacakan dua kredensial | Dipertahankan; lokasi/field/kategori/token harus mengikuti aturan kanonis dan backend |
| Global motion | Paket Motion & Interaction System | Motion tokens, navigasi, komponen, state, reduced motion | Menjadi spesifikasi global, diimplementasikan pada `app/static/js/motion.js` |

## 2. Matriks akses lintas role

| Kapabilitas | Pelapor | Admin Sarpras | Teknisi | Pimpinan/Kaprodi |
|---|---|---|---|---|
| Membuat laporan publik | Ya | Tidak sebagai fungsi role | Tidak sebagai fungsi role | Tidak sebagai fungsi role |
| Melacak tiket dengan kode + token | Tiket miliknya saja | Sesuai akses operasional aplikasi; bukan fungsi publik | Tiket penugasan saja | Tidak membuka detail identitas |
| Melihat antrean seluruh tiket | Tidak | Ya | Tidak | Hanya agregat |
| Verifikasi/koreksi kategori | Tidak | Ya | Tidak | Tidak |
| Menetapkan teknisi | Tidak | Ya | Tidak | Tidak |
| Update progres tiket | Tidak | Operasional sesuai kewenangan aktual | Tiket yang ditugaskan | Tidak |
| Membaca Audit Log operasional | Tidak | Ya | Tidak | Tidak |
| Dashboard agregat anonim | Tidak wajib | Sesuai modul aktual | Ringkasan tugas pribadi | Ya, read-only |

> Tabel ini menyatakan batas desain yang disepakati. Detail permission endpoint tetap harus diverifikasi terhadap decorator/authorization backend.

## 3. Temuan prioritas

### P0 — wajib dipenuhi sebelum implementasi halaman terkait

1. Satu status flow: Baru → Terverifikasi → Diproses → Selesai; tidak ada status kelima “Ditugaskan”.
2. RBAC: Admin satu-satunya pembaca Audit Log; Teknisi hanya tiket assigned dan kategori read-only; Pimpinan read-only agregat; Pelapor hanya ticket+token yang valid.
3. Pelapor: Gedung FTII saja, lantai 1–4, ruang free-text, detail lokasi dan foto opsional, token 128-bit (`token_urlsafe(16)`, ~22 karakter URL-safe base64; hash SHA-256 64-hex disimpan di DB), kategori awal informasional.
4. Tidak menampilkan data personal pelapor pada halaman tracking/dashboard pimpinan.
5. Tidak menampilkan SLA, prioritas PBM, sparepart/inventaris, persentase akurasi/ confidence ML, dataset size, kontak, atau integrasi yang belum diverifikasi.
6. Tidak ada placeholder href, tombol simulasi, atau menu yang tidak memiliki route/aksi produksi.

### P1 — konsistensi desain dan implementasi

1. Satu logo resmi UHAMKA lokal.
2. Satu set warna dan typography dari DESIGN.md kanonis.
3. Desktop/mobile konsisten dalam field, kategori, label, status, dan data contoh.
4. Sidebar 250px / 72px; topbar 64px; mobile header 56px; bottom nav 64px hanya untuk role/page yang benar-benar memerlukannya.
5. `prefers-reduced-motion`, focus-visible, keyboard navigation, loading/error/empty/success states.
6. Tidak ada dependensi CDN pada produksi; prototipe Stitch hanya referensi visual.

### P2 — polish saat implementasi

1. Konsistensi ikon, spacing, border, radius, hover, pressed, toast, skeleton, chart animation.
2. Verifikasi overflow tabel, form, chart, timeline dan drawer pada viewport 390px.
3. Perbaiki teks panjang, truncation, dan hierarchy pada layar kecil.

## 4. Konten mockup yang tidak boleh dianggap fakta

Dari HTML Stitch ditemukan contoh data/teks yang berpotensi tampak seperti fakta: semester/tahun akademik, nama pejabat/personel, nama teknisi, email/ekstensi kontak, alamat/node/IP, target SLA, response time, angka akurasi/F1-score, jumlah dataset, persentase confidence, klaim SHA/hash ledger, SOP/MEP/LOTO, prioritas PBM, dan sparepart. Seluruhnya harus dihapus atau diberi status ilustratif dan hanya dipertahankan bila diverifikasi dari sumber proyek/implementasi.

## 5. Status Verifikasi dan Arsip

- **Verifikasi Repositori**: Verifikasi langsung pada working tree `D:\Project Capstone\Klasifas` telah selesai dilakukan pada 14 November 2026. Seluruh path template, route Flask, selector CSS di `klasifas.css`, controller JS (`sidebar.js`, `portal.js`, `motion.js`), serta permission decorator RBAC telah terbukti lulus 100% pada 252 unit test tanpa regresi.
- **Status Artefak Stitch**: Seluruh berkas di `docs/ui-ux-reference/stitch/` (termasuk 5 berkas `DESIGN.md` duplikat dan berkas prototipe `code.html`) dinyatakan sebagai **arsip visual historis**, bukan spesifikasi teknis kanonis.
- **Kategori Fasilitas Resmi**: Seluruh antarmuka dikunci pada 7 kategori resmi K1–K7 sesuai `PRD.md` dan tabel basis data PostgreSQL (`Ruang kelas dan perabot`, `Laboratorium dan perangkat`, `Jaringan dan internet`, `Kebersihan dan sanitasi`, `Listrik, AC, dan penerangan`, `Keamanan, parkir, dan akses`, `Lainnya`).
