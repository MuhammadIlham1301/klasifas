"""
Pengujian Komprehensif TSK-F6-02:
Pembaruan Status dan Catatan Penyelesaian (FR-06, FR-09).

Mencakup seluruh kriteria penerimaan (AC-1 s.d. AC-7):
1. Kelompok 1 (RBAC & Otorisasi):
   - Unauthenticated dialihkan ke /auth/login.
   - Non-teknisi (admin_sarpras, pimpinan) ditolak 403.
   - Reporter dialihkan ke /auth/login.
2. Kelompok 2 (Pencegahan IDOR Mutlak):
   - Tiket milik teknisi lain ditolak 404.
   - Tiket belum ditugaskan (unassigned) ditolak 404.
   - Tiket ID tidak ditemukan ditolak 404.
3. Kelompok 3 (Alur Transisi Positif & Audit Atomik):
   - Terverifikasi -> Diproses (catatan opsional, status berubah, AuditLog tercatat, resolved_at/resolution_note None).
   - Diproses -> Selesai (catatan tindakan wajib, resolved_at UTC terisi, resolution_note tersimpan, AuditLog tercatat).
   - Transaksi atomik: kegagalan pencatatan membatalkan seluruh perubahan (rollback).
4. Kelompok 4 (Validasi Transisi Negatif & Anti-Bypass):
   - Melompati alur (Terverifikasi -> Selesai) ditolak dengan flash peringatan.
   - Memundurkan alur (Diproses -> Terverifikasi) ditolak dengan flash peringatan.
   - Tiket Selesai tidak dapat diubah lagi.
   - Nilai status tidak valid ditolak.
5. Kelompok 5 (Validasi Catatan di Service Layer):
   - Transisi ke Selesai menolak note yang None, string kosong (""), atau hanya whitespace.
   - Catatan melebihi 1000 karakter ditolak eksplisit dengan AuditNoteLengthError.
6. Kelompok 6 (Keamanan, Immutability & Integritas Data):
   - CSRF protection aktif (POST tanpa token ditolak 400).
   - HTTP Methods selain POST (GET, PUT, PATCH, DELETE) pada endpoint status ditolak 405.
   - Immutability: field non-status tidak termutasi, Jinja autoescaping melindungi dari serangan XSS.
"""
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
import secrets
from unittest.mock import patch

import pytest
from sqlalchemy import delete, select
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.category import Category
from app.models.ticket import Ticket
from app.models.user import User
from app.services.audit_service import AuditNoteLengthError
from app.services.complaint_service import (
    InvalidTicketStatusError,
    transition_ticket_status,
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
# 1. Kelompok 1: RBAC & Autentikasi (AC-1)
# ==============================================================================


def test_technician_update_status_unauthenticated_redirects_to_login(client):
    """Pengguna tanpa sesi login dialihkan ke halaman login saat mencoba update status."""
    resp = client.post("/teknisi/tiket/1/status", data={"new_status": "Diproses"})
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_technician_update_status_non_technician_roles_forbidden(client):
    """Pengguna dengan peran admin_sarpras atau pimpinan ditolak dengan 403 Forbidden."""
    for role in ["admin_sarpras", "pimpinan"]:
        _login_as(client, role)
        resp = client.post("/teknisi/tiket/1/status", data={"new_status": "Diproses"})
        assert resp.status_code == 403, f"Role {role} harus ditolak 403"


def test_technician_update_status_reporter_redirects_to_login(client):
    """Pengguna dengan peran reporter dialihkan ke halaman login."""
    _login_as(client, "reporter")
    resp = client.post("/teknisi/tiket/1/status", data={"new_status": "Diproses"})
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


# ==============================================================================
# 2. Kelompok 2: IDOR & Perlindungan Penugasan (AC-2)
# ==============================================================================


def test_technician_update_status_idor_other_technician_ticket_returns_404(client):
    """
    IDOR Protection: Teknisi A mencoba memperbarui status tiket milik Teknisi B
    ditolak dengan 404 Not Found (mencegah enumerasi / pembocoran informasi keberadaan tiket).
    """
    tech_a = _login_as(client, "teknisi", "tech_attacker")
    tech_b = _create_user("tech_victim", "teknisi")

    ticket_b = _create_dummy_ticket(
        status="Terverifikasi", assigned_technician_id=tech_b.id
    )
    db.session.commit()

    resp = client.post(
        f"/teknisi/tiket/{ticket_b.id}/status",
        data={"new_status": "Diproses"},
    )
    assert resp.status_code == 404

    # Pastikan status tiket korban tidak termutasi
    db.session.refresh(ticket_b)
    assert ticket_b.status == "Terverifikasi"


def test_technician_update_status_idor_unassigned_ticket_returns_404(client):
    """Percobaan memperbarui tiket yang belum ditugaskan (unassigned) ditolak dengan 404."""
    tech = _login_as(client, "teknisi")
    unassigned_ticket = _create_dummy_ticket(
        status="Terverifikasi", assigned_technician_id=None
    )
    db.session.commit()

    resp = client.post(
        f"/teknisi/tiket/{unassigned_ticket.id}/status",
        data={"new_status": "Diproses"},
    )
    assert resp.status_code == 404

    db.session.refresh(unassigned_ticket)
    assert unassigned_ticket.status == "Terverifikasi"


def test_technician_update_status_nonexistent_ticket_returns_404(client):
    """ID tiket fiktif yang tidak ada di basis data mengembalikan 404 Not Found."""
    _login_as(client, "teknisi")
    resp = client.post(
        "/teknisi/tiket/999999/status",
        data={"new_status": "Diproses"},
    )
    assert resp.status_code == 404


# ==============================================================================
# 3. Kelompok 3: Alur Transisi Positif & Audit Atomik (AC-3, AC-4, AC-5)
# ==============================================================================


def test_technician_transition_terverifikasi_to_diproses_success(client):
    """
    Transisi sah: Terverifikasi -> Diproses oleh teknisi yang ditugaskan.
    - Catatan pengerjaan opsional tercatat dalam audit log.
    - Status tiket berubah menjadi Diproses.
    - resolved_at dan resolution_note tetap None.
    """
    tech = _login_as(client, "teknisi")
    ticket = _create_dummy_ticket(
        status="Terverifikasi", assigned_technician_id=tech.id
    )
    db.session.commit()

    resp = client.post(
        f"/teknisi/tiket/{ticket.id}/status",
        data={
            "new_status": "Diproses",
            "note": "Menyiapkan peralatan dan suku cadang untuk perbaikan.",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "berhasil diperbarui menjadi Diproses" in html

    db.session.refresh(ticket)
    assert ticket.status == "Diproses"
    assert ticket.resolved_at is None
    assert ticket.resolution_note is None

    # Verifikasi entri AuditLog
    audit = db.session.scalar(
        select(AuditLog).where(
            AuditLog.ticket_id == ticket.id,
            AuditLog.action == "status_changed",
        )
    )
    assert audit is not None
    assert audit.old_value == "Terverifikasi"
    assert audit.new_value == "Diproses"
    assert audit.actor_user_id == tech.id
    assert audit.actor_role == "teknisi"
    assert audit.note == "Menyiapkan peralatan dan suku cadang untuk perbaikan."


def test_technician_transition_diproses_to_selesai_success(client):
    """
    Transisi sah: Diproses -> Selesai oleh teknisi yang ditugaskan.
    - Catatan tindakan perbaikan wajib diisi.
    - Status tiket berubah menjadi Selesai.
    - ticket.resolved_at otomatis terisi timestamp UTC.
    - ticket.resolution_note terisi catatan tindakan perbaikan.
    - AuditLog mencatat mutasi status dengan note yang sama secara atomik.
    """
    tech = _login_as(client, "teknisi")
    ticket = _create_dummy_ticket(
        status="Diproses", assigned_technician_id=tech.id
    )
    db.session.commit()

    action_note = "Kabel power supply telah diganti baru dan lampu indikator menyala stabil."
    resp = client.post(
        f"/teknisi/tiket/{ticket.id}/status",
        data={
            "new_status": "Selesai",
            "note": action_note,
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "berhasil diselesaikan dan catatan tindakan perbaikan telah tersimpan" in html

    db.session.refresh(ticket)
    assert ticket.status == "Selesai"
    assert ticket.resolved_at is not None
    assert ticket.resolved_at <= datetime.now(timezone.utc)
    assert ticket.resolution_note == action_note

    # Verifikasi entri AuditLog
    audit = db.session.scalar(
        select(AuditLog).where(
            AuditLog.ticket_id == ticket.id,
            AuditLog.action == "status_changed",
        )
    )
    assert audit is not None
    assert audit.old_value == "Diproses"
    assert audit.new_value == "Selesai"
    assert audit.actor_user_id == tech.id
    assert audit.actor_role == "teknisi"
    assert audit.note == action_note


def test_technician_transition_atomic_transaction_rollback_on_failure(app):
    """
    Atomisitas: Jika terjadi kegagalan sistem saat pencatatan audit,
    seluruh mutasi tiket (status, resolved_at, resolution_note) dibatalkan secara atomik (rollback).
    """
    with app.app_context():
        tech = _create_user("tech_rollback", "teknisi")
        ticket = _create_dummy_ticket(
            status="Diproses", assigned_technician_id=tech.id
        )
        db.session.commit()

        # Simulasikan kegagalan pada fungsi log_status_change
        with patch(
            "app.services.complaint_service.log_status_change",
            side_effect=RuntimeError("Database failure simulation during audit log"),
        ):
            with pytest.raises(RuntimeError):
                transition_ticket_status(
                    ticket=ticket,
                    new_status="Selesai",
                    actor_user=tech,
                    note="Tindakan selesai",
                    commit=True,
                )

        # Pastikan tiket kembali ke kondisi awal (rollback)
        db.session.refresh(ticket)
        assert ticket.status == "Diproses"
        assert ticket.resolved_at is None
        assert ticket.resolution_note is None

        # 0 audit log baru
        audit_count = db.session.scalar(
            select(db.func.count(AuditLog.id)).where(AuditLog.ticket_id == ticket.id)
        )
        assert audit_count == 0


# ==============================================================================
# 4. Kelompok 4: Validasi Alur Transisi Negatif & Anti-Bypass (AC-3)
# ==============================================================================


def test_technician_transition_illegal_skip_terverifikasi_to_selesai_rejected(client):
    """Percobaan melompati alur dari Terverifikasi langsung ke Selesai ditolak secara eksplisit."""
    tech = _login_as(client, "teknisi")
    ticket = _create_dummy_ticket(
        status="Terverifikasi", assigned_technician_id=tech.id
    )
    db.session.commit()

    resp = client.post(
        f"/teknisi/tiket/{ticket.id}/status",
        data={
            "new_status": "Selesai",
            "note": "Mencoba langsung menyelesaikan tanpa proses",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "tidak diizinkan" in html

    db.session.refresh(ticket)
    assert ticket.status == "Terverifikasi"
    assert ticket.resolved_at is None
    assert ticket.resolution_note is None


def test_technician_transition_illegal_backward_diproses_to_terverifikasi_rejected(client):
    """Percobaan memundurkan alur dari Diproses ke Terverifikasi ditolak secara eksplisit."""
    tech = _login_as(client, "teknisi")
    ticket = _create_dummy_ticket(
        status="Diproses", assigned_technician_id=tech.id
    )
    db.session.commit()

    resp = client.post(
        f"/teknisi/tiket/{ticket.id}/status",
        data={
            "new_status": "Terverifikasi",
            "note": "Mencoba memundurkan status",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "tidak diizinkan" in html

    db.session.refresh(ticket)
    assert ticket.status == "Diproses"


def test_technician_transition_from_selesai_rejected(client):
    """Tiket yang telah berstatus Selesai tidak dapat diperbarui lagi ke status apa pun."""
    tech = _login_as(client, "teknisi")
    ticket = _create_dummy_ticket(
        status="Selesai", assigned_technician_id=tech.id
    )
    original_resolved_at = datetime.now(timezone.utc)
    ticket.resolved_at = original_resolved_at
    ticket.resolution_note = "Pekerjaan sebelumnya telah tuntas."
    db.session.commit()

    for invalid_target in ["Diproses", "Terverifikasi", "Baru"]:
        resp = client.post(
            f"/teknisi/tiket/{ticket.id}/status",
            data={"new_status": invalid_target, "note": "Mencoba mengubah tiket selesai"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert ("tidak diizinkan" in html) or ("kewenangan" in html)

        db.session.refresh(ticket)
        assert ticket.status == "Selesai"
        assert ticket.resolution_note == "Pekerjaan sebelumnya telah tuntas."


def test_technician_transition_invalid_status_value_rejected(client):
    """Mengirimkan string status sembarang (tidak resmi) ditolak secara eksplisit."""
    tech = _login_as(client, "teknisi")
    ticket = _create_dummy_ticket(
        status="Terverifikasi", assigned_technician_id=tech.id
    )
    db.session.commit()

    for bad_status in ["Batal", "Tertunda", "InvalidStatus", ""]:
        resp = client.post(
            f"/teknisi/tiket/{ticket.id}/status",
            data={"new_status": bad_status, "note": "Uji status acak"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert ("bukan status resmi" in html) or ("tidak valid" in html)

        db.session.refresh(ticket)
        assert ticket.status == "Terverifikasi"


# ==============================================================================
# 5. Kelompok 5: Validasi Catatan di Service Layer (AC-4, AC-6)
# ==============================================================================


def test_technician_transition_to_selesai_requires_note(client):
    """
    Transisi menuju Selesai menolak catatan yang None, kosong, atau hanya whitespace.
    Validasi terjadi sebelum mutasi data tiket dan sebelum audit log.
    """
    tech = _login_as(client, "teknisi")
    ticket = _create_dummy_ticket(
        status="Diproses", assigned_technician_id=tech.id
    )
    db.session.commit()

    # Uji string kosong dan whitespace
    for empty_note in ["", "   ", "\t\n  "]:
        resp = client.post(
            f"/teknisi/tiket/{ticket.id}/status",
            data={"new_status": "Selesai", "note": empty_note},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "Catatan tindakan perbaikan wajib diisi saat menyelesaikan tiket" in html

        db.session.refresh(ticket)
        assert ticket.status == "Diproses"
        assert ticket.resolved_at is None
        assert ticket.resolution_note is None

    # Pastikan 0 audit log tercipta
    audit_count = db.session.scalar(
        select(db.func.count(AuditLog.id)).where(AuditLog.ticket_id == ticket.id)
    )
    assert audit_count == 0


def test_technician_transition_note_exceeding_max_length_rejected(client):
    """Catatan melebihi batas 1000 karakter ditolak secara eksplisit dengan AuditNoteLengthError."""
    tech = _login_as(client, "teknisi")
    ticket = _create_dummy_ticket(
        status="Diproses", assigned_technician_id=tech.id
    )
    db.session.commit()

    too_long_note = "A" * 1001
    resp = client.post(
        f"/teknisi/tiket/{ticket.id}/status",
        data={"new_status": "Selesai", "note": too_long_note},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "tidak boleh melebihi 1000 karakter" in html

    db.session.refresh(ticket)
    assert ticket.status == "Diproses"
    assert ticket.resolved_at is None
    assert ticket.resolution_note is None


# ==============================================================================
# 6. Kelompok 6: Keamanan, CSRF, HTTP Methods & Immutability (AC-6, AC-7)
# ==============================================================================


def test_technician_update_status_csrf_protection_and_http_methods(app):
    """
    Keamanan:
    - POST tanpa token CSRF valid ditolak (400 Bad Request) saat CSRF diaktifkan.
    - Metode selain POST (GET, PUT, PATCH, DELETE) pada endpoint status ditolak 405 Method Not Allowed.
    """
    with app.test_client() as csrf_client:
        # 1. Aktifkan proteksi CSRF untuk menguji penolakan request tanpa token
        app.config["WTF_CSRF_ENABLED"] = True
        try:
            _login_as(csrf_client, "teknisi")
            # Request POST tanpa token CSRF
            resp = csrf_client.post("/teknisi/tiket/1/status", data={"new_status": "Diproses"})
            assert resp.status_code == 400
        finally:
            app.config["WTF_CSRF_ENABLED"] = False

    # 2. Uji HTTP methods pada endpoint status: selain POST ditolak 405
    with app.test_client() as test_client:
        tech = _login_as(test_client, "teknisi")
        ticket = _create_dummy_ticket(status="Terverifikasi", assigned_technician_id=tech.id)
        db.session.commit()

        for method in ["get", "put", "patch", "delete"]:
            caller = getattr(test_client, method)
            resp = caller(f"/teknisi/tiket/{ticket.id}/status")
            assert resp.status_code == 405, f"Method {method.upper()} harus ditolak 405"


def test_technician_update_status_immutability_of_other_ticket_fields_and_xss_safety(client):
    """
    Integritas & XSS Protection:
    - Seluruh field non-status (ticket_code, token hash, description, lokasi, kategori, pelapor, dsb.)
      tidak berubah saat proses update status.
    - Catatan perbaikan yang mengandung tag script/HTML disanitasi secara aman oleh template autoescape.
    """
    tech = _login_as(client, "teknisi")
    category = db.session.scalar(select(Category).where(Category.is_active.is_(True)))
    original_code = generate_ticket_code()
    token_seed = secrets.token_hex(16)
    original_token_hash = hashlib.sha256(token_seed.encode("ascii")).hexdigest()

    ticket = _create_dummy_ticket(
        code=original_code,
        access_token_hash=original_token_hash,
        description="Keluhan proyektor buram di ruang rapat",
        floor_number=3,
        room_name="Ruang Rapat 301",
        location_detail="Dekat pintu keluar barat",
        official_category_id=category.id,
        status="Diproses",
        assigned_technician_id=tech.id,
    )
    db.session.commit()

    # Payload XSS pada catatan tindakan perbaikan
    xss_note = "<script>alert('XSS_ATTACK_VECTOR')</script><b>Lensa dibersihkan</b>"
    resp = client.post(
        f"/teknisi/tiket/{ticket.id}/status",
        data={"new_status": "Selesai", "note": xss_note},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # Pastikan tag script tidak dirender mentah (escaped)
    assert "<script>alert('XSS_ATTACK_VECTOR')</script>" not in html
    assert "&lt;script&gt;alert(&#39;XSS_ATTACK_VECTOR&#39;)&lt;/script&gt;" in html or \
           "&lt;script&gt;alert('XSS_ATTACK_VECTOR')&lt;/script&gt;" in html

    # Pastikan seluruh field non-status tidak termutasi
    db.session.refresh(ticket)
    assert ticket.ticket_code == original_code
    assert ticket.access_token_hash == original_token_hash
    assert ticket.description == "Keluhan proyektor buram di ruang rapat"
    assert ticket.building_name == "Gedung FTII"
    assert ticket.floor_number == 3
    assert ticket.room_name == "Ruang Rapat 301"
    assert ticket.location_detail == "Dekat pintu keluar barat"
    assert ticket.official_category_id == category.id
    assert ticket.assigned_technician_id == tech.id
    assert ticket.status == "Selesai"
    assert ticket.resolution_note == xss_note

