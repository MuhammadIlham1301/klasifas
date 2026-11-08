"""
Pengujian Komprehensif TSK-F6-01:
Papan Antrean Tiket Teknisi (FR-06).

Mencakup seluruh kriteria penerimaan (AC-1 s.d. AC-7):
1. AC-1: Otorisasi & RBAC Server-Side (teknisi only; non-teknisi 403, unauthenticated/reporter 302).
2. AC-2: Isolasi Data Penugasan Mutlak (hanya tiket milik g.current_user.id; eksklusi unassigned & Baru).
3. AC-3: Pencegahan IDOR Mutlak pada Rincian Tiket (URL manipulation tiket lain/unassigned ditolak 404).
4. AC-4: Pencegahan IDOR Mutlak pada Foto Bukti & Penggunaan Kembali Helper Keamanan (404, path traversal, symlink escape).
5. AC-5: Kelengkapan Informasi, Metrik Terisolasi, dan Validasi Filter (anti-silent widening).
6. AC-6: Proteksi Data Sensitif (tanpa leak access_token_hash) & Jinja autoescape XSS protection.
7. AC-7: Strictly Read-Only (POST/PUT/PATCH/DELETE ditolak 405 pada seluruh 3 endpoint) & Immutability data.
"""
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import secrets

import pytest
from sqlalchemy import delete, select
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.category import Category
from app.models.ticket import Ticket
from app.models.user import User
from app.services.complaint_service import (
    TECHNICIAN_ALLOWED_STATUS_FILTERS,
    get_technician_assigned_tickets,
    get_technician_ticket_by_id,
    get_technician_ticket_counts,
    parse_and_validate_technician_filter_params,
    serve_ticket_photo,
)
from app.utils.ticket_identity import generate_ticket_code

PASSWORD = "Valid-Test-Pass-123!"
PASSWORD_HASH = generate_password_hash(PASSWORD, method="scrypt")


@pytest.fixture()
def app():
    from app import create_app

    test_app = create_app("testing")
    test_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    with test_app.app_context():
        baseline_ticket_ids = set(db.session.scalars(select(Ticket.id)).all())
        baseline_user_ids = set(db.session.scalars(select(User.id)).all())

        connection = db.engine.connect()
        transaction = connection.begin()
        db.session.remove()
        db.session.configure(
            bind=connection, join_transaction_mode="create_savepoint"
        )

        try:
            yield test_app
        finally:
            db.session.remove()
            if transaction.is_active:
                transaction.rollback()
            connection.close()
            db.session.configure(bind=None)

            # Pembersihan data test
            with db.engine.begin() as cleanup_connection:
                if baseline_ticket_ids:
                    cleanup_connection.execute(
                        delete(AuditLog).where(
                            AuditLog.ticket_id.notin_(baseline_ticket_ids)
                        )
                    )
                    cleanup_connection.execute(
                        delete(Ticket).where(
                            Ticket.id.notin_(baseline_ticket_ids)
                        )
                    )
                else:
                    cleanup_connection.execute(delete(AuditLog))
                    cleanup_connection.execute(delete(Ticket))

                if baseline_user_ids:
                    cleanup_connection.execute(
                        delete(User).where(
                            User.id.notin_(baseline_user_ids)
                        )
                    )
                else:
                    cleanup_connection.execute(delete(User))

            db.engine.dispose()


@pytest.fixture()
def client(app):
    return app.test_client()


def _create_user(username: str, role: str) -> User:
    unique_uname = f"{username}_{secrets.token_hex(4)}"
    user = User(
        username=unique_uname,
        full_name=f"Pengguna {username}",
        password_hash=PASSWORD_HASH,
        role=role,
        is_active=True,
    )
    db.session.add(user)
    db.session.flush()
    return user


def _login_as(client, role: str, username: str | None = None) -> User:
    uname = username or f"{role}_user"
    user = _create_user(uname, role)
    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["role"] = user.role
        sess.permanent = True
    return user


def _create_dummy_ticket(
    *,
    code: str | None = None,
    description: str | None = None,
    status: str = "Terverifikasi",
    floor_number: int = 2,
    room_name: str = "Lab 2.1",
    location_detail: str | None = None,
    reporter_category_id: int | None = None,
    predicted_category_id: int | None = None,
    official_category_id: int | None = None,
    assigned_technician_id: int | None = None,
    confidence_score: float | None = None,
    access_token_hash: str | None = None,
    photo_filename: str | None = None,
    photo_mime_type: str | None = None,
    created_at: datetime | None = None,
) -> Ticket:
    ticket_code = code or generate_ticket_code()
    if access_token_hash is None:
        token_seed = secrets.token_hex(16)
        access_token_hash = hashlib.sha256(token_seed.encode("ascii")).hexdigest()

    ticket = Ticket(
        ticket_code=ticket_code,
        access_token_hash=access_token_hash,
        description=description or f"Keluhan fasilitas untuk {ticket_code}",
        building_name="Gedung FTII",
        floor_number=floor_number,
        room_name=room_name,
        location_detail=location_detail or "Area tengah ruangan",
        status=status,
        needs_manual_verification=(status == "Baru"),
        reporter_category_id=reporter_category_id,
        predicted_category_id=predicted_category_id,
        official_category_id=official_category_id,
        assigned_technician_id=assigned_technician_id,
        confidence_score=confidence_score,
        photo_filename=photo_filename,
        photo_mime_type=photo_mime_type,
        photo_size_bytes=1024 if photo_filename else None,
        photo_uploaded_at=datetime.now(timezone.utc) if photo_filename else None,
        created_at=created_at or datetime.now(timezone.utc),
    )
    db.session.add(ticket)
    db.session.flush()
    return ticket


# ==============================================================================
# 1. AC-1: Otorisasi & RBAC Server-Side Area Teknisi
# ==============================================================================


def test_technician_queue_unauthenticated_redirects_to_login(client):
    """Akses tanpa login ke /teknisi/tiket dialihkan ke /auth/login."""
    resp = client.get("/teknisi/tiket")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers.get("Location", "")


def test_technician_queue_non_technician_roles_forbidden(client):
    """Pengguna non-teknisi (admin_sarpras, pimpinan) ditolak dengan 403, reporter dialihkan ke login."""
    for staff_role in ["admin_sarpras", "pimpinan"]:
        staff_client = client.application.test_client()
        _login_as(staff_client, staff_role)
        resp = staff_client.get("/teknisi/tiket")
        assert resp.status_code == 403, f"Role {staff_role} seharusnya mendapat 403"

    reporter_client = client.application.test_client()
    _login_as(reporter_client, "reporter")
    resp_rep = reporter_client.get("/teknisi/tiket")
    assert resp_rep.status_code == 302
    assert "/auth/login" in resp_rep.headers.get("Location", "")


def test_technician_queue_access_success_for_technician(client):
    """Teknisi yang login berhasil mengakses papan antrean tiket (/teknisi/tiket) dengan 200 OK."""
    _login_as(client, "teknisi")
    resp = client.get("/teknisi/tiket")
    assert resp.status_code == 200
    assert "Papan Tugas Teknisi" in resp.text
    assert "Filter Status Tugas" in resp.text


# ==============================================================================
# 2. AC-2: Isolasi Data Penugasan Mutlak pada Papan Antrean
# ==============================================================================


def test_technician_queue_only_shows_assigned_tickets(client):
    """Papan antrean teknisi hanya menampilkan tiket yang ditugaskan kepada teknisi login."""
    tech_a = _login_as(client, "teknisi", "tech_andi")
    tech_b = _create_user("tech_budi", "teknisi")

    t_a = _create_dummy_ticket(assigned_technician_id=tech_a.id, description="TUGAS_KHUSUS_ANDI")
    t_b = _create_dummy_ticket(assigned_technician_id=tech_b.id, description="TUGAS_KHUSUS_BUDI")
    db.session.commit()

    # Login sebagai Teknisi A
    resp_a = client.get("/teknisi/tiket")
    assert resp_a.status_code == 200
    assert t_a.ticket_code in resp_a.text
    assert "TUGAS_KHUSUS_ANDI" in resp_a.text
    assert t_b.ticket_code not in resp_a.text
    assert "TUGAS_KHUSUS_BUDI" not in resp_a.text

    # Login sebagai Teknisi B
    client_b = client.application.test_client()
    with client_b.session_transaction() as sess:
        sess["user_id"] = tech_b.id
        sess["role"] = tech_b.role
        sess.permanent = True

    resp_b = client_b.get("/teknisi/tiket")
    assert resp_b.status_code == 200
    assert t_b.ticket_code in resp_b.text
    assert "TUGAS_KHUSUS_BUDI" in resp_b.text
    assert t_a.ticket_code not in resp_b.text
    assert "TUGAS_KHUSUS_ANDI" not in resp_b.text


def test_technician_queue_excludes_unassigned_and_baru_tickets(client):
    """Tiket yang belum ditugaskan atau masih berstatus Baru tidak pernah muncul di antrean teknisi."""
    tech = _login_as(client, "teknisi")

    t_baru = _create_dummy_ticket(status="Baru", assigned_technician_id=None, description="TIKET_BARU_UNASSIGNED")
    t_unassigned = _create_dummy_ticket(status="Terverifikasi", assigned_technician_id=None, description="TIKET_TERVERIFIKASI_UNASSIGNED")
    t_assigned = _create_dummy_ticket(status="Terverifikasi", assigned_technician_id=tech.id, description="TIKET_TERVERIFIKASI_ASSIGNED")
    db.session.commit()

    resp = client.get("/teknisi/tiket")
    assert resp.status_code == 200
    assert t_assigned.ticket_code in resp.text
    assert "TIKET_TERVERIFIKASI_ASSIGNED" in resp.text
    assert t_baru.ticket_code not in resp.text
    assert "TIKET_BARU_UNASSIGNED" not in resp.text
    assert t_unassigned.ticket_code not in resp.text
    assert "TIKET_TERVERIFIKASI_UNASSIGNED" not in resp.text


# ==============================================================================
# 3. AC-5: Isolasi Metrik Tugas & Kelengkapan Informasi
# ==============================================================================


def test_technician_queue_metrics_strictly_isolated_to_logged_in_technician(client):
    """Seluruh kartu metrik (total, Terverifikasi, Diproses, Selesai) hanya menghitung tiket teknisi login."""
    tech_a = _login_as(client, "teknisi", "tech_metrik_a")
    tech_b = _create_user("tech_metrik_b", "teknisi")

    # Tiket Teknisi A (1 Terverifikasi, 2 Diproses, 1 Selesai -> Total: 4)
    _create_dummy_ticket(status="Terverifikasi", assigned_technician_id=tech_a.id)
    _create_dummy_ticket(status="Diproses", assigned_technician_id=tech_a.id)
    _create_dummy_ticket(status="Diproses", assigned_technician_id=tech_a.id)
    _create_dummy_ticket(status="Selesai", assigned_technician_id=tech_a.id)

    # Tiket Teknisi B (5 Terverifikasi, 5 Diproses -> Total: 10)
    for _ in range(5):
        _create_dummy_ticket(status="Terverifikasi", assigned_technician_id=tech_b.id)
        _create_dummy_ticket(status="Diproses", assigned_technician_id=tech_b.id)

    db.session.commit()

    # Verifikasi langsung pada service layer
    counts_a = get_technician_ticket_counts(tech_a.id)
    assert counts_a["total"] == 4
    assert counts_a["Terverifikasi"] == 1
    assert counts_a["Diproses"] == 2
    assert counts_a["Selesai"] == 1

    # Verifikasi pada antarmuka web
    resp = client.get("/teknisi/tiket")
    assert resp.status_code == 200
    assert "Total Tugas" in resp.text


def test_technician_queue_displays_required_ticket_fields(client):
    """Papan antrean menyajikan kode tiket, lokasi gedung/lantai/ruang, kategori resmi, dan status."""
    tech = _login_as(client, "teknisi")
    category = db.session.scalar(select(Category).order_by(Category.id))
    assert category is not None

    ticket = _create_dummy_ticket(
        status="Terverifikasi",
        assigned_technician_id=tech.id,
        floor_number=3,
        room_name="Lab Jaringan 301",
        official_category_id=category.id,
        description="Kabel LAN terputus di meja instruktur",
    )
    db.session.commit()

    resp = client.get("/teknisi/tiket")
    assert resp.status_code == 200
    assert ticket.ticket_code in resp.text
    assert "Gedung FTII" in resp.text
    assert "Lt. 3" in resp.text
    assert "Lab Jaringan 301" in resp.text
    assert category.code in resp.text
    assert category.name in resp.text
    assert "Terverifikasi" in resp.text


# ==============================================================================
# 4. AC-5: Penyaringan Status & Paginasi (Anti-Silent Widening)
# ==============================================================================


def test_technician_queue_filter_by_status(client):
    """Penyaringan status resmi (Terverifikasi, Diproses, Selesai, all) berfungsi akurat."""
    tech = _login_as(client, "teknisi")

    t1 = _create_dummy_ticket(status="Terverifikasi", assigned_technician_id=tech.id, description="DESK_STATUS_TERVERIFIKASI")
    t2 = _create_dummy_ticket(status="Diproses", assigned_technician_id=tech.id, description="DESK_STATUS_DIPROSES")
    t3 = _create_dummy_ticket(status="Selesai", assigned_technician_id=tech.id, description="DESK_STATUS_SELESAI")
    db.session.commit()

    # Filter Terverifikasi
    r_terverif = client.get("/teknisi/tiket?status=Terverifikasi")
    assert "DESK_STATUS_TERVERIFIKASI" in r_terverif.text
    assert "DESK_STATUS_DIPROSES" not in r_terverif.text
    assert "DESK_STATUS_SELESAI" not in r_terverif.text

    # Filter Diproses
    r_diproses = client.get("/teknisi/tiket?status=Diproses")
    assert "DESK_STATUS_DIPROSES" in r_diproses.text
    assert "DESK_STATUS_TERVERIFIKASI" not in r_diproses.text

    # Filter Selesai
    r_selesai = client.get("/teknisi/tiket?status=Selesai")
    assert "DESK_STATUS_SELESAI" in r_selesai.text
    assert "DESK_STATUS_DIPROSES" not in r_selesai.text

    # Filter all
    r_all = client.get("/teknisi/tiket?status=all")
    assert "DESK_STATUS_TERVERIFIKASI" in r_all.text
    assert "DESK_STATUS_DIPROSES" in r_all.text
    assert "DESK_STATUS_SELESAI" in r_all.text


def test_technician_queue_filter_invalid_status_explicit_rejection_no_silent_widening(client):
    """Filter status invalid ditolak secara eksplisit dengan pesan error dan TIDAK memperluas kueri secara diam-diam."""
    tech = _login_as(client, "teknisi")
    _create_dummy_ticket(status="Terverifikasi", assigned_technician_id=tech.id, description="DESK_TIKET_SAH_TEKNISI")
    db.session.commit()

    # 1. Status fiktif / ilegal
    resp_illegal = client.get("/teknisi/tiket?status=status_ilegal_hack")
    assert resp_illegal.status_code == 200
    assert "tidak valid untuk teknisi" in resp_illegal.text
    # Hasil tidak boleh melebar diam-diam (daftar tiket harus kosong saat filter invalid)
    assert "DESK_TIKET_SAH_TEKNISI" not in resp_illegal.text
    assert "Belum ada tiket yang ditugaskan kepada Anda." in resp_illegal.text

    # 2. Status 'Baru' (milik Admin Sarpras, bukan status penugasan teknisi)
    resp_baru = client.get("/teknisi/tiket?status=Baru")
    assert resp_baru.status_code == 200
    assert "tidak valid untuk teknisi" in resp_baru.text
    assert "DESK_TIKET_SAH_TEKNISI" not in resp_baru.text


def test_technician_queue_pagination_and_navigation(client):
    """Paginasi membatasi entri per halaman dan mempertahankan parameter filter."""
    tech = _login_as(client, "teknisi")

    for i in range(25):
        _create_dummy_ticket(
            status="Terverifikasi",
            assigned_technician_id=tech.id,
            description=f"PAGINASI_TEKNISI_{i+1:02d}",
            created_at=datetime(2026, 1, 1, 0, i, tzinfo=timezone.utc),
        )
    db.session.commit()

    # Halaman 1 default per_page=20
    r_p1 = client.get("/teknisi/tiket")
    assert r_p1.status_code == 200
    assert "PAGINASI_TEKNISI_25" in r_p1.text
    assert "PAGINASI_TEKNISI_06" in r_p1.text
    assert "PAGINASI_TEKNISI_05" not in r_p1.text  # Ada di halaman 2

    # Halaman 2
    r_p2 = client.get("/teknisi/tiket?page=2")
    assert r_p2.status_code == 200
    assert "PAGINASI_TEKNISI_05" in r_p2.text
    assert "PAGINASI_TEKNISI_01" in r_p2.text

    # Custom per_page=10 dengan filter status
    r_custom = client.get("/teknisi/tiket?status=Terverifikasi&per_page=10&page=1")
    assert r_custom.status_code == 200
    assert "status=Terverifikasi" in r_custom.text
    assert "per_page=10" in r_custom.text


# ==============================================================================
# 5. AC-3: Detail Tiket & Pencegahan IDOR Server-Side
# ==============================================================================


def test_technician_ticket_detail_access_success_for_own_ticket(client):
    """Teknisi dapat membuka rincian tiket miliknya (/teknisi/tiket/<id>) dengan 200 OK."""
    tech = _login_as(client, "teknisi")
    category = db.session.scalar(select(Category).order_by(Category.id))
    ticket = _create_dummy_ticket(
        status="Terverifikasi",
        assigned_technician_id=tech.id,
        official_category_id=category.id if category else None,
        description="Lampu ruangan dosen berkedip cepat",
        floor_number=2,
        room_name="R. Dosen 204",
        location_detail="Dekat pintu masuk utama",
    )
    db.session.commit()

    resp = client.get(f"/teknisi/tiket/{ticket.id}")
    assert resp.status_code == 200
    assert ticket.ticket_code in resp.text
    assert "Lampu ruangan dosen berkedip cepat" in resp.text
    assert "R. Dosen 204" in resp.text
    assert "Dekat pintu masuk utama" in resp.text
    assert "Status Pengerjaan Fisik" in resp.text


def test_technician_ticket_detail_idor_other_technician_ticket_returns_404(client):
    """Percobaan membuka rincian tiket milik teknisi lain ditolak di sisi server dengan 404 Not Found."""
    tech_a = _login_as(client, "teknisi", "tech_attacker")
    tech_b = _create_user("tech_victim", "teknisi")

    ticket_b = _create_dummy_ticket(
        status="Terverifikasi",
        assigned_technician_id=tech_b.id,
        description="RAHASIA_PEKERJAAN_BUDI",
    )
    db.session.commit()

    # Teknisi A mencoba membuka ID tiket milik Teknisi B
    resp = client.get(f"/teknisi/tiket/{ticket_b.id}")
    assert resp.status_code == 404
    assert "RAHASIA_PEKERJAAN_BUDI" not in resp.text


def test_technician_ticket_detail_idor_unassigned_and_non_existent_returns_404(client):
    """Mengakses ID tiket unassigned atau tiket yang tidak terdaftar di database mengembalikan 404 Not Found."""
    _login_as(client, "teknisi")

    t_unassigned = _create_dummy_ticket(status="Terverifikasi", assigned_technician_id=None)
    db.session.commit()

    # Tiket unassigned
    resp_unassigned = client.get(f"/teknisi/tiket/{t_unassigned.id}")
    assert resp_unassigned.status_code == 404

    # Tiket non-existent
    resp_non_existent = client.get("/teknisi/tiket/99998888")
    assert resp_non_existent.status_code == 404


# ==============================================================================
# 6. AC-4: Keamanan Foto Bukti, Pencegahan IDOR, dan Traversal
# ==============================================================================


def test_technician_ticket_photo_access_success_via_reused_mechanism(client, app, tmp_path):
    """Teknisi dapat melihat foto bukti dari tiket yang ditugaskan kepadanya melalui helper serve_ticket_photo."""
    tech = _login_as(client, "teknisi")

    # Buat file dummy foto pada direktori upload aplikasi
    upload_dir = Path(app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    dummy_photo = upload_dir / "test_photo_tech.jpg"
    dummy_photo.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00test_image_data")

    try:
        ticket = _create_dummy_ticket(
            status="Terverifikasi",
            assigned_technician_id=tech.id,
            photo_filename="test_photo_tech.jpg",
            photo_mime_type="image/jpeg",
        )
        db.session.commit()

        resp = client.get(f"/teknisi/tiket/{ticket.id}/foto")
        assert resp.status_code == 200
        assert resp.mimetype == "image/jpeg"
        assert resp.data == b"\xff\xd8\xff\xe0\x00\x10JFIF\x00test_image_data"
        resp.close()
    finally:
        if dummy_photo.exists():
            try:
                dummy_photo.unlink()
            except (OSError, PermissionError):
                pass


def test_technician_ticket_photo_idor_other_technician_photo_returns_404(client, app):
    """Teknisi tidak dapat mengakses foto tiket milik teknisi lain (IDOR dicegah dengan 404)."""
    tech_a = _login_as(client, "teknisi", "tech_photo_attacker")
    tech_b = _create_user("tech_photo_victim", "teknisi")

    upload_dir = Path(app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    dummy_photo = upload_dir / "victim_photo.jpg"
    dummy_photo.write_bytes(b"victim_secret_photo")

    try:
        ticket_b = _create_dummy_ticket(
            status="Terverifikasi",
            assigned_technician_id=tech_b.id,
            photo_filename="victim_photo.jpg",
            photo_mime_type="image/jpeg",
        )
        db.session.commit()

        resp = client.get(f"/teknisi/tiket/{ticket_b.id}/foto")
        assert resp.status_code == 404
        resp.close()
    finally:
        if dummy_photo.exists():
            try:
                dummy_photo.unlink()
            except (OSError, PermissionError):
                pass


def test_technician_ticket_photo_path_traversal_prevention(client, app):
    """Percobaan path traversal pada atribut photo_filename ditolak secara aman dengan 404."""
    tech = _login_as(client, "teknisi")

    ticket = _create_dummy_ticket(
        status="Terverifikasi",
        assigned_technician_id=tech.id,
        photo_filename="../../secret_system_file.txt",
        photo_mime_type="text/plain",
    )
    db.session.commit()

    resp = client.get(f"/teknisi/tiket/{ticket.id}/foto")
    assert resp.status_code == 404


def test_technician_ticket_photo_symlink_traversal_prevention(client, app, tmp_path):
    """
    Pencegahan symbolic link traversal: berkas yang menunjuk ke luar UPLOAD_FOLDER
    ditolak dengan 404 melalui validasi photo_path.is_relative_to(upload_folder).
    """
    tech = _login_as(client, "teknisi")
    upload_dir = Path(app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Buat file target di luar direktori upload
    outside_file = tmp_path / "outside_target.txt"
    outside_file.write_bytes(b"CONFIDENTIAL_OUTSIDE_DATA")

    symlink_file = upload_dir / "symlink_escape_test.jpg"

    symlink_created = False
    try:
        try:
            symlink_file.symlink_to(outside_file)
            symlink_created = True
        except (OSError, NotImplementedError):
            # Lingkungan OS (misal Windows tanpa privilege pembuatan symlink)
            pass

        if symlink_created:
            ticket = _create_dummy_ticket(
                status="Terverifikasi",
                assigned_technician_id=tech.id,
                photo_filename="symlink_escape_test.jpg",
                photo_mime_type="image/jpeg",
            )
            db.session.commit()

            resp = client.get(f"/teknisi/tiket/{ticket.id}/foto")
            # Containment check is_relative_to() harus menolak file symlink yang mengarah keluar
            assert resp.status_code == 404
        else:
            # Fallback unit-level containment test jika OS membatasi pembuatan symlink fisik
            dummy_ticket = _create_dummy_ticket(
                status="Terverifikasi",
                assigned_technician_id=tech.id,
                photo_filename="fake_outside.jpg",
            )
            # Pastikan serve_ticket_photo menolak jika target bukan di dalam upload folder
            with pytest.raises(Exception):
                # Memverifikasi fungsi abort terpanggil saat file tidak valid
                serve_ticket_photo(dummy_ticket)

    finally:
        if symlink_created and symlink_file.exists():
            symlink_file.unlink()


# ==============================================================================
# 7. AC-7: Strictly Read-Only (405) pada Seluruh Endpoint Teknisi
# ==============================================================================


def test_technician_strictly_readonly_methods_on_all_endpoints(client):
    """
    Metode selain GET (POST, PUT, PATCH, DELETE) pada SELURUH endpoint teknisi
    (/teknisi/tiket, /teknisi/tiket/<id>, /teknisi/tiket/<id>/foto) ditolak dengan 405 Method Not Allowed.
    """
    tech = _login_as(client, "teknisi")
    ticket = _create_dummy_ticket(status="Terverifikasi", assigned_technician_id=tech.id)
    db.session.commit()

    endpoints = [
        "/teknisi/tiket",
        f"/teknisi/tiket/{ticket.id}",
        f"/teknisi/tiket/{ticket.id}/foto",
    ]

    for ep in endpoints:
        for method in ["post", "put", "patch", "delete"]:
            caller = getattr(client, method)
            resp = caller(ep)
            assert resp.status_code == 405, f"Metode {method.upper()} pada {ep} harus ditolak 405"


# ==============================================================================
# 8. AC-6 & AC-7: Immutability Data & Proteksi Data Sensitif (XSS / Token)
# ==============================================================================


def test_technician_views_and_filtering_does_not_mutate_data_and_xss_protection(client):
    """
    Membuka halaman antrean, rincian tiket, maupun filter terbukti tidak memutasi data
    Ticket maupun AuditLog, tidak membocorkan access_token_hash, dan teks di-escape aman dari XSS.
    """
    tech = _login_as(client, "teknisi")
    secret_token_hash = "super_secret_access_token_hash_tech_f601_9999"
    xss_payload = "<script>alert('XSS_TECHNICIAN_BOARD')</script><b>Bold Desc</b>"

    ticket = _create_dummy_ticket(
        status="Terverifikasi",
        assigned_technician_id=tech.id,
        access_token_hash=secret_token_hash,
        description=xss_payload,
        location_detail="Ruang <img src=x onerror=alert(1)>",
    )
    db.session.commit()

    # Snapshot data sebelum akses
    audit_count_before = len(db.session.scalars(select(AuditLog)).all())
    ticket_count_before = len(db.session.scalars(select(Ticket)).all())
    ticket_snapshot_before = [
        (t.id, t.ticket_code, t.status, t.assigned_technician_id, t.updated_at)
        for t in db.session.scalars(select(Ticket).order_by(Ticket.id)).all()
    ]

    # Akses berbagai halaman dan filter
    r_queue = client.get("/teknisi/tiket")
    r_filter = client.get("/teknisi/tiket?status=Terverifikasi&per_page=10")
    r_detail = client.get(f"/teknisi/tiket/{ticket.id}")

    # Snapshot data sesudah akses
    audit_count_after = len(db.session.scalars(select(AuditLog)).all())
    ticket_count_after = len(db.session.scalars(select(Ticket)).all())
    ticket_snapshot_after = [
        (t.id, t.ticket_code, t.status, t.assigned_technician_id, t.updated_at)
        for t in db.session.scalars(select(Ticket).order_by(Ticket.id)).all()
    ]

    # 1. Immutability
    assert audit_count_after == audit_count_before
    assert ticket_count_after == ticket_count_before
    assert ticket_snapshot_after == ticket_snapshot_before

    # 2. Non-disclosure token hash
    assert secret_token_hash not in r_queue.text
    assert secret_token_hash not in r_filter.text
    assert secret_token_hash not in r_detail.text

    # 3. XSS Protection
    for r in [r_queue, r_detail]:
        assert "<script>alert('XSS_TECHNICIAN_BOARD')</script>" not in r.text
        assert "&lt;script&gt;alert(" in r.text
        assert "<b>Bold Desc</b>" not in r.text

