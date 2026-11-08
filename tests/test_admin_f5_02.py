"""
Pengujian Komprehensif TSK-F5-02:
Penugasan Teknisi Lapangan untuk Tiket Terverifikasi (FR-05, FR-09).

Mencakup seluruh kriteria penerimaan dan penegasan pengguna:
1. AC-1: Otorisasi RBAC (@role_required("admin_sarpras")).
2. AC-2: Validasi akun teknisi (wajib terdaftar, is_active=True, role='teknisi').
3. AC-3: Aturan status tiket:
   - 'Terverifikasi': penugasan awal atau penugasan ulang diizinkan.
   - 'Diproses': hanya penugasan ulang yang diizinkan.
   - 'Baru' dan 'Selesai': penugasan ditolak.
4. AC-4: Status tiket tidak berubah saat penugasan (penugasan sebagai atribut relasional).
5. AC-5: AuditLog stabil mencatat old_value & new_value berupa ID teknisi (idempoten).
6. Penanganan teknisi lama yang sudah nonaktif (identitas tetap tampil di detail, tapi tidak ada di dropdown penugasan baru).
7. Penolakan ID teknisi tidak ditemukan.
8. Proteksi CSRF & rollback transaksi atomik pada kegagalan audit.
"""
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
import secrets
from unittest.mock import patch

import pytest
from flask import g
from sqlalchemy import delete, select
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.category import Category
from app.models.ticket import Ticket
from app.models.user import User
from app.services.complaint_service import (
    InvalidTicketStatusError,
    TechnicianValidationError,
    assign_technician_to_ticket,
    get_ticket_by_id,
)
from app.utils.ticket_identity import generate_ticket_code

PASSWORD = "Valid-Admin-Pass-123!"
PASSWORD_HASH = generate_password_hash(PASSWORD, method="scrypt")
CSRF_TOKEN_PATTERN = re.compile(r'name="csrf_token" value="([^"]+)"')


@pytest.fixture()
def app():
    from app import create_app

    test_app = create_app("testing")
    test_app.config.update(TESTING=True, WTF_CSRF_ENABLED=True)

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


def _extract_csrf(response):
    match = CSRF_TOKEN_PATTERN.search(response.get_data(as_text=True))
    assert match is not None, "CSRF token tidak ditemukan pada HTML respons."
    return match.group(1)


def _create_user(username: str, role: str, is_active: bool = True, full_name: str | None = None) -> User:
    unique_uname = f"{username}_{secrets.token_hex(4)}"
    name = full_name or f"Pengguna {username.title()}"
    user = User(
        username=unique_uname,
        full_name=name,
        password_hash=PASSWORD_HASH,
        role=role,
        is_active=is_active,
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
    status: str = "Terverifikasi",
    official_category_id: int | None = None,
    assigned_technician_id: int | None = None,
) -> Ticket:
    ticket_code = generate_ticket_code()
    token_seed = secrets.token_hex(16)
    token_hash = hashlib.sha256(token_seed.encode("ascii")).hexdigest()

    ticket = Ticket(
        ticket_code=ticket_code,
        access_token_hash=token_hash,
        description=f"Keluhan fasilitas untuk penugasan {ticket_code}",
        building_name="Gedung FTII",
        floor_number=2,
        room_name="Lab Jaringan 2.3",
        location_detail="Sebelah rak server",
        status=status,
        official_category_id=official_category_id,
        assigned_technician_id=assigned_technician_id,
        needs_manual_verification=False,
    )
    db.session.add(ticket)
    db.session.flush()
    return ticket


# ==============================================================================
# 1. AC-1: Otorisasi & RBAC Penugasan
# ==============================================================================


def test_unauthenticated_assign_request_redirects_to_login(client):
    resp_login = client.get("/auth/login")
    csrf_token = _extract_csrf(resp_login)

    resp = client.post(
        "/admin/tiket/1/penugasan",
        data={"csrf_token": csrf_token, "technician_id": "1"},
    )
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/auth/login")


@pytest.mark.parametrize("role", ["teknisi", "pimpinan"])
def test_non_admin_staff_cannot_assign_technician(client, role):
    _login_as(client, role)
    resp_login = client.get("/auth/login")
    csrf_token = _extract_csrf(resp_login)

    resp = client.post(
        "/admin/tiket/1/penugasan",
        data={"csrf_token": csrf_token, "technician_id": "1"},
    )
    assert resp.status_code == 403


def test_reporter_role_cannot_assign_technician(client):
    _login_as(client, "reporter")
    resp_login = client.get("/auth/login")
    csrf_token = _extract_csrf(resp_login)

    resp = client.post(
        "/admin/tiket/1/penugasan",
        data={"csrf_token": csrf_token, "technician_id": "1"},
    )
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/auth/login")


# ==============================================================================
# 2. AC-2 & Validasi Akun Teknisi (Non-existent, Inaktif, Role Salah)
# ==============================================================================


def test_assign_technician_not_found_rejected(client):
    """Penugasan ke ID teknisi yang tidak ada ditolak."""
    _login_as(client, "admin_sarpras")
    k1 = db.session.scalar(select(Category).where(Category.code == "K1"))
    ticket = _create_dummy_ticket(status="Terverifikasi", official_category_id=k1.id)
    db.session.commit()

    resp = client.get(f"/admin/tiket/{ticket.id}/verifikasi")
    csrf_token = _extract_csrf(resp)

    post_resp = client.post(
        f"/admin/tiket/{ticket.id}/penugasan",
        data={"csrf_token": csrf_token, "technician_id": "999999"},
        follow_redirects=True,
    )
    assert post_resp.status_code == 200
    html = post_resp.get_data(as_text=True)
    assert "Akun teknisi tidak ditemukan" in html

    db.session.refresh(ticket)
    assert ticket.assigned_technician_id is None


def test_assign_inactive_technician_rejected(client):
    """Penugasan ke teknisi nonaktif ditolak."""
    _login_as(client, "admin_sarpras")
    k1 = db.session.scalar(select(Category).where(Category.code == "K1"))
    inactive_tech = _create_user("tech_nonaktif", role="teknisi", is_active=False)
    ticket = _create_dummy_ticket(status="Terverifikasi", official_category_id=k1.id)
    db.session.commit()

    resp = client.get(f"/admin/tiket/{ticket.id}/verifikasi")
    csrf_token = _extract_csrf(resp)

    post_resp = client.post(
        f"/admin/tiket/{ticket.id}/penugasan",
        data={"csrf_token": csrf_token, "technician_id": str(inactive_tech.id)},
        follow_redirects=True,
    )
    assert post_resp.status_code == 200
    html = post_resp.get_data(as_text=True)
    assert "berstatus nonaktif" in html

    db.session.refresh(ticket)
    assert ticket.assigned_technician_id is None


def test_assign_non_technician_role_rejected(client):
    """Penugasan ke akun dengan role bukan teknisi (misal pimpinan) ditolak."""
    _login_as(client, "admin_sarpras")
    k1 = db.session.scalar(select(Category).where(Category.code == "K1"))
    leader = _create_user("dekan_user", role="pimpinan", is_active=True)
    ticket = _create_dummy_ticket(status="Terverifikasi", official_category_id=k1.id)
    db.session.commit()

    resp = client.get(f"/admin/tiket/{ticket.id}/verifikasi")
    csrf_token = _extract_csrf(resp)

    post_resp = client.post(
        f"/admin/tiket/{ticket.id}/penugasan",
        data={"csrf_token": csrf_token, "technician_id": str(leader.id)},
        follow_redirects=True,
    )
    assert post_resp.status_code == 200
    html = post_resp.get_data(as_text=True)
    assert "tidak memiliki kewenangan sebagai teknisi" in html

    db.session.refresh(ticket)
    assert ticket.assigned_technician_id is None


# ==============================================================================
# 3. AC-3: Aturan Status Tiket untuk Penugasan
# ==============================================================================


def test_assign_technician_rejected_on_new_ticket(client):
    """Tiket berstatus 'Baru' ditolak untuk penugasan teknisi."""
    _login_as(client, "admin_sarpras")
    tech = _create_user("teknisi_1", role="teknisi", is_active=True)
    ticket = _create_dummy_ticket(status="Baru")
    db.session.commit()

    resp = client.get(f"/admin/tiket/{ticket.id}/verifikasi")
    csrf_token = _extract_csrf(resp)

    post_resp = client.post(
        f"/admin/tiket/{ticket.id}/penugasan",
        data={"csrf_token": csrf_token, "technician_id": str(tech.id)},
        follow_redirects=True,
    )
    assert post_resp.status_code == 200
    html = post_resp.get_data(as_text=True)
    assert "harus diverifikasi kategorinya terlebih dahulu" in html

    db.session.refresh(ticket)
    assert ticket.assigned_technician_id is None


def test_assign_technician_rejected_on_done_ticket(client):
    """Tiket berstatus 'Selesai' ditolak untuk penugasan/reassign teknisi."""
    _login_as(client, "admin_sarpras")
    k1 = db.session.scalar(select(Category).where(Category.code == "K1"))
    tech1 = _create_user("tech_done_1", role="teknisi", is_active=True)
    tech2 = _create_user("tech_done_2", role="teknisi", is_active=True)
    ticket = _create_dummy_ticket(
        status="Selesai",
        official_category_id=k1.id,
        assigned_technician_id=tech1.id,
    )
    db.session.commit()

    resp = client.get(f"/admin/tiket/{ticket.id}/verifikasi")
    csrf_token = _extract_csrf(resp)

    post_resp = client.post(
        f"/admin/tiket/{ticket.id}/penugasan",
        data={"csrf_token": csrf_token, "technician_id": str(tech2.id)},
        follow_redirects=True,
    )
    assert post_resp.status_code == 200
    html = post_resp.get_data(as_text=True)
    assert "tidak dapat diubah penugasan teknisinya" in html

    db.session.refresh(ticket)
    assert ticket.assigned_technician_id == tech1.id


def test_assign_technician_rejected_on_in_progress_without_previous_assignment(client):
    """Tiket 'Diproses' tanpa teknisi sebelumnya ditolak (hanya boleh penugasan ulang)."""
    _login_as(client, "admin_sarpras")
    k1 = db.session.scalar(select(Category).where(Category.code == "K1"))
    tech = _create_user("tech_prog", role="teknisi", is_active=True)
    ticket = _create_dummy_ticket(
        status="Diproses",
        official_category_id=k1.id,
        assigned_technician_id=None,
    )
    db.session.commit()

    resp = client.get(f"/admin/tiket/{ticket.id}/verifikasi")
    csrf_token = _extract_csrf(resp)

    post_resp = client.post(
        f"/admin/tiket/{ticket.id}/penugasan",
        data={"csrf_token": csrf_token, "technician_id": str(tech.id)},
        follow_redirects=True,
    )
    assert post_resp.status_code == 200
    html = post_resp.get_data(as_text=True)
    assert "hanya mengizinkan penugasan ulang teknisi" in html

    db.session.refresh(ticket)
    assert ticket.assigned_technician_id is None


# ==============================================================================
# 4. AC-4 & AC-5: Penugasan Sukses, Status Immutability, & AuditLog Stabil
# ==============================================================================


def test_assign_technician_success_on_verified_ticket(client):
    """Penugasan awal pada tiket Terverifikasi berhasil, status tidak berubah, AuditLog tercatat."""
    admin = _login_as(client, "admin_sarpras")
    k1 = db.session.scalar(select(Category).where(Category.code == "K1"))
    tech = _create_user("teknisi_budi", role="teknisi", is_active=True, full_name="Budi Santoso")
    ticket = _create_dummy_ticket(status="Terverifikasi", official_category_id=k1.id)
    db.session.commit()

    resp = client.get(f"/admin/tiket/{ticket.id}/verifikasi")
    csrf_token = _extract_csrf(resp)

    post_resp = client.post(
        f"/admin/tiket/{ticket.id}/penugasan",
        data={
            "csrf_token": csrf_token,
            "technician_id": str(tech.id),
            "note": "Tugaskan perbaikan kursi patah",
        },
        follow_redirects=True,
    )
    assert post_resp.status_code == 200
    html = post_resp.get_data(as_text=True)
    assert "berhasil ditugaskan kepada Budi Santoso" in html

    # Status TIDAK berubah, tetap 'Terverifikasi'
    db.session.refresh(ticket)
    assert ticket.status == "Terverifikasi"
    assert ticket.assigned_technician_id == tech.id

    # AuditLog menyimpan ID teknisi yang stabil (FR-09)
    logs = db.session.scalars(
        select(AuditLog)
        .where(AuditLog.ticket_id == ticket.id, AuditLog.action == "technician_assigned")
    ).all()
    assert len(logs) == 1
    log = logs[0]
    assert log.field_name == "assigned_technician_id"
    assert log.old_value is None
    assert log.new_value == str(tech.id)
    assert log.actor_user_id == admin.id
    assert log.actor_role == "admin_sarpras"
    assert log.note == "Tugaskan perbaikan kursi patah"


def test_reassign_technician_on_in_progress_ticket_preserves_status(client):
    """Penugasan ulang pada tiket Diproses berhasil dan mempertahankan status Diproses."""
    admin = _login_as(client, "admin_sarpras")
    k1 = db.session.scalar(select(Category).where(Category.code == "K1"))
    tech_a = _create_user("tech_a", role="teknisi", is_active=True, full_name="Teknisi Pertama")
    tech_b = _create_user("tech_b", role="teknisi", is_active=True, full_name="Teknisi Pengganti")
    ticket = _create_dummy_ticket(
        status="Diproses",
        official_category_id=k1.id,
        assigned_technician_id=tech_a.id,
    )
    db.session.commit()

    resp = client.get(f"/admin/tiket/{ticket.id}/verifikasi")
    csrf_token = _extract_csrf(resp)

    post_resp = client.post(
        f"/admin/tiket/{ticket.id}/penugasan",
        data={
            "csrf_token": csrf_token,
            "technician_id": str(tech_b.id),
            "note": "Alih tugas karena teknisi A berhalangan",
        },
        follow_redirects=True,
    )
    assert post_resp.status_code == 200
    html = post_resp.get_data(as_text=True)
    assert "berhasil ditugaskan kepada Teknisi Pengganti" in html

    # Status tetap 'Diproses'
    db.session.refresh(ticket)
    assert ticket.status == "Diproses"
    assert ticket.assigned_technician_id == tech_b.id

    # Periksa AuditLog
    logs = db.session.scalars(
        select(AuditLog)
        .where(AuditLog.ticket_id == ticket.id, AuditLog.action == "technician_assigned")
    ).all()
    assert len(logs) == 1
    assert logs[0].old_value == str(tech_a.id)
    assert logs[0].new_value == str(tech_b.id)


def test_reassign_same_technician_is_idempotent(client):
    """Menugaskan teknisi yang sama tidak menambah entri AuditLog (idempoten)."""
    _login_as(client, "admin_sarpras")
    k1 = db.session.scalar(select(Category).where(Category.code == "K1"))
    tech = _create_user("tech_idem", role="teknisi", is_active=True)
    ticket = _create_dummy_ticket(
        status="Terverifikasi",
        official_category_id=k1.id,
        assigned_technician_id=tech.id,
    )
    db.session.commit()

    initial_audit_count = len(
        db.session.scalars(select(AuditLog).where(AuditLog.ticket_id == ticket.id)).all()
    )

    resp = client.get(f"/admin/tiket/{ticket.id}/verifikasi")
    csrf_token = _extract_csrf(resp)

    post_resp = client.post(
        f"/admin/tiket/{ticket.id}/penugasan",
        data={
            "csrf_token": csrf_token,
            "technician_id": str(tech.id),
            "note": "Tidak ada perubahan teknisi",
        },
        follow_redirects=True,
    )
    assert post_resp.status_code == 200
    html = post_resp.get_data(as_text=True)
    assert "tidak mengalami perubahan" in html

    new_audit_count = len(
        db.session.scalars(select(AuditLog).where(AuditLog.ticket_id == ticket.id)).all()
    )
    assert new_audit_count == initial_audit_count


# ==============================================================================
# 5. Penanganan Teknisi Nonaktif pada Detail & Dropdown (Clarification 2 & 4)
# ==============================================================================


def test_assigned_inactive_technician_displayed_but_excluded_from_dropdown(client):
    """
    Jika teknisi yang ditugaskan sudah nonaktif:
    - Identitasnya tetap ditampilkan pada detail tiket.
    - Tetapi tidak muncul sebagai opsi dalam dropdown pilihan penugasan baru.
    """
    _login_as(client, "admin_sarpras")
    k1 = db.session.scalar(select(Category).where(Category.code == "K1"))

    # Buat teknisi aktif dan teknisi nonaktif
    tech_active = _create_user("tech_aktif", role="teknisi", is_active=True, full_name="Teknisi Aktif")
    tech_inactive = _create_user("tech_lama_nonaktif", role="teknisi", is_active=False, full_name="Teknisi Lama Nonaktif")

    # Tiket saat ini sedang ditugaskan ke teknisi yang sudah nonaktif
    ticket = _create_dummy_ticket(
        status="Terverifikasi",
        official_category_id=k1.id,
        assigned_technician_id=tech_inactive.id,
    )
    db.session.commit()

    resp = client.get(f"/admin/tiket/{ticket.id}/verifikasi")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # Identitas teknisi lama tetap tampil di kartu detail
    assert "Teknisi Lama Nonaktif" in html
    assert "Akun Nonaktif" in html

    # Pada form dropdown <select id="technician_id">, hanya teknisi aktif yang muncul
    # Ekstrak opsi select
    select_match = re.search(r'<select[^>]+id="technician_id"[^>]*>(.*?)</select>', html, re.DOTALL)
    assert select_match is not None, "Dropdown technician_id tidak ditemukan pada HTML."
    select_options = select_match.group(1)

    assert "Teknisi Aktif" in select_options
    assert "Teknisi Lama Nonaktif" not in select_options


# ==============================================================================
# 6. Proteksi CSRF & Rollback Atomik
# ==============================================================================


def test_assign_technician_without_csrf_is_rejected(client):
    _login_as(client, "admin_sarpras")
    k1 = db.session.scalar(select(Category).where(Category.code == "K1"))
    tech = _create_user("tech_csrf", role="teknisi", is_active=True)
    ticket = _create_dummy_ticket(status="Terverifikasi", official_category_id=k1.id)
    db.session.commit()

    resp = client.post(
        f"/admin/tiket/{ticket.id}/penugasan",
        data={"technician_id": str(tech.id)},
    )
    assert resp.status_code == 400


def test_assign_technician_atomic_rollback_on_audit_failure(app):
    """Kegagalan saat penulisan audit log wajib me-rollback penugasan tiket."""
    with app.app_context():
        admin = _create_user("audit_admin_f502", role="admin_sarpras")
        k1 = db.session.scalar(select(Category).where(Category.code == "K1"))
        tech = _create_user("tech_rollback", role="teknisi", is_active=True)
        ticket = _create_dummy_ticket(status="Terverifikasi", official_category_id=k1.id)
        db.session.commit()

        with patch(
            "app.services.complaint_service.log_technician_assignment",
            side_effect=RuntimeError("Simulated audit write failure for technician assignment"),
        ):
            with pytest.raises(RuntimeError, match="Simulated audit write failure"):
                assign_technician_to_ticket(
                    ticket=ticket,
                    technician_id=tech.id,
                    actor_user=admin,
                )

        # Verifikasi tiket TIDAK berubah
        db.session.refresh(ticket)
        assert ticket.assigned_technician_id is None
