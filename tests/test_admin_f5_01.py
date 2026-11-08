"""
Pengujian Komprehensif TSK-F5-01:
Antrean Tiket dan Verifikasi Kategori Sarpras (FR-04, FR-09).

Mencakup seluruh kriteria penerimaan (AC-1 s.d. AC-6):
1. AC-1: Otorisasi & RBAC (@role_required("admin_sarpras")).
2. AC-2: Antrean tiket & filter status (default 'Baru', tab status lain).
3. AC-3: Penyajian foto bukti aman (GET /admin/tiket/<id>/foto).
4. AC-4: Verifikasi tiket 'Baru' -> 'Terverifikasi' & unflag manual verification.
5. AC-5: Integritas AuditLog atomik & bebas redundansi (idempoten).
6. Pengujian koreksi kategori pada status 'Terverifikasi', 'Diproses', dan 'Selesai'
   (status tidak boleh mundur atau berubah otomatis).
7. Penanganan tiket fallback manual F4-05.
8. Proteksi CSRF & validasi input kategori K1-K7.
"""
from datetime import datetime, timezone
import hashlib
import os
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
    CategoryValidationError,
    get_ticket_by_id,
    get_verification_queue,
    verify_ticket_category,
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

            # Bersihkan record yang dibuat selama test secara aman
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
    status: str = "Baru",
    needs_manual: bool = False,
    reporter_category_id: int | None = None,
    predicted_category_id: int | None = None,
    official_category_id: int | None = None,
    confidence_score: float | None = None,
    photo_filename: str | None = None,
    photo_mime_type: str | None = None,
) -> Ticket:
    ticket_code = code or generate_ticket_code()
    token_seed = secrets.token_hex(16)
    token_hash = hashlib.sha256(token_seed.encode("ascii")).hexdigest()

    ticket = Ticket(
        ticket_code=ticket_code,
        access_token_hash=token_hash,
        description=f"Keluhan uji coba untuk {ticket_code}",
        building_name="Gedung FTII",
        floor_number=2,
        room_name="Lab 2.1",
        location_detail="Sebelah pintu masuk",
        status=status,
        needs_manual_verification=needs_manual,
        reporter_category_id=reporter_category_id,
        predicted_category_id=predicted_category_id,
        official_category_id=official_category_id,
        confidence_score=confidence_score,
        photo_filename=photo_filename,
        photo_mime_type=photo_mime_type,
        photo_size_bytes=1024 if photo_filename else None,
        photo_uploaded_at=datetime.now(timezone.utc) if photo_filename else None,
    )
    db.session.add(ticket)
    db.session.flush()
    return ticket


# ==============================================================================
# 1. AC-1: Otorisasi & RBAC Ketat
# ==============================================================================


@pytest.mark.parametrize(
    "path",
    [
        "/admin/tiket",
        "/admin/tiket/1/verifikasi",
        "/admin/tiket/1/foto",
    ],
)
def test_unauthenticated_get_requests_redirect_to_login(client, path):
    resp = client.get(path)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/auth/login")


def test_unauthenticated_post_redirects_to_login_with_csrf(client):
    resp_login = client.get("/auth/login")
    csrf_token = _extract_csrf(resp_login)

    resp = client.post(
        "/admin/tiket/1/verifikasi",
        data={"csrf_token": csrf_token, "official_category_id": "1"},
    )
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/auth/login")


@pytest.mark.parametrize("role", ["teknisi", "pimpinan"])
def test_staff_non_admin_receive_403_forbidden(client, role):
    _login_as(client, role)
    resp = client.get("/admin/tiket")
    assert resp.status_code == 403


def test_reporter_role_session_rejected_and_redirects_to_login(client):
    _login_as(client, "reporter")
    resp = client.get("/admin/tiket")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/auth/login")


def test_admin_sarpras_can_access_queue(client):
    _login_as(client, "admin_sarpras")
    resp = client.get("/admin/tiket")
    assert resp.status_code == 200
    assert "Antrean Tiket Sarpras" in resp.get_data(as_text=True)


# ==============================================================================
# 2. AC-2: Antrean Tiket & Filter Status
# ==============================================================================


def test_ticket_queue_filters_by_status(client):
    _login_as(client, "admin_sarpras")
    cat = db.session.scalar(select(Category).where(Category.code == "K1"))

    t_baru = _create_dummy_ticket(status="Baru", reporter_category_id=cat.id)
    t_verif = _create_dummy_ticket(status="Terverifikasi", official_category_id=cat.id)
    t_selesai = _create_dummy_ticket(status="Selesai", official_category_id=cat.id)
    db.session.commit()

    # 1. Default (Baru)
    resp = client.get("/admin/tiket")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert t_baru.ticket_code in html
    assert t_verif.ticket_code not in html
    assert t_selesai.ticket_code not in html

    # 2. Filter Terverifikasi
    resp = client.get("/admin/tiket?status=Terverifikasi")
    html = resp.get_data(as_text=True)
    assert t_baru.ticket_code not in html
    assert t_verif.ticket_code in html
    assert t_selesai.ticket_code not in html

    # 3. Filter Semua Status
    resp = client.get("/admin/tiket?status=all")
    html = resp.get_data(as_text=True)
    assert t_baru.ticket_code in html
    assert t_verif.ticket_code in html
    assert t_selesai.ticket_code in html


def test_ticket_queue_displays_fallback_and_ml_badges(client):
    _login_as(client, "admin_sarpras")
    k5 = db.session.scalar(select(Category).where(Category.code == "K5"))

    # Tiket fallback F4-05 (tanpa prediksi ML, needs_manual=True)
    t_fb = _create_dummy_ticket(status="Baru", needs_manual=True)

    # Tiket dengan prediksi ML normal
    t_ml = _create_dummy_ticket(
        status="Baru",
        predicted_category_id=k5.id,
        confidence_score=0.884,
        needs_manual=False,
    )
    db.session.commit()

    resp = client.get("/admin/tiket")
    html = resp.get_data(as_text=True)
    assert "Verifikasi Manual (Fallback)" in html
    assert t_ml.ticket_code in html
    assert "88.4%" in html


# ==============================================================================
# 3. AC-3: Penyajian Foto Bukti Aman
# ==============================================================================


def test_secure_photo_serving(app, client):
    _login_as(client, "admin_sarpras")

    upload_dir = Path(app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    test_file = upload_dir / "test_photo_sample.jpg"
    test_file.write_bytes(b"\xff\xd8\xff\xe0testjpegcontent")

    t_photo = _create_dummy_ticket(
        status="Baru",
        photo_filename="test_photo_sample.jpg",
        photo_mime_type="image/jpeg",
    )
    t_nophoto = _create_dummy_ticket(status="Baru", photo_filename=None)
    db.session.commit()

    # 1. Akses foto yang ada
    resp = client.get(f"/admin/tiket/{t_photo.id}/foto")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"].startswith("image/jpeg")
    assert resp.data == b"\xff\xd8\xff\xe0testjpegcontent"

    # 2. Akses tiket tanpa foto -> 404
    resp = client.get(f"/admin/tiket/{t_nophoto.id}/foto")
    assert resp.status_code == 404

    # 3. Akses tiket id tidak ada -> 404
    resp = client.get("/admin/tiket/999999/foto")
    assert resp.status_code == 404

    # 4. Path traversal attack dicegah
    t_traversal = _create_dummy_ticket(
        status="Baru",
        photo_filename="../../etc/passwd",
    )
    db.session.commit()
    resp = client.get(f"/admin/tiket/{t_traversal.id}/foto")
    assert resp.status_code == 404


# ==============================================================================
# 4. AC-4: Verifikasi Tiket Baru & Transisi Status
# ==============================================================================


def test_verify_new_ticket_transitions_to_verified_and_unflags_manual(client):
    admin = _login_as(client, "admin_sarpras")
    k3 = db.session.scalar(select(Category).where(Category.code == "K3"))

    ticket = _create_dummy_ticket(
        status="Baru",
        needs_manual=True,
    )
    db.session.commit()

    # Dapatkan CSRF token dari halaman verifikasi
    resp = client.get(f"/admin/tiket/{ticket.id}/verifikasi")
    assert resp.status_code == 200
    csrf_token = _extract_csrf(resp)

    # Submit verifikasi kategori K3
    post_resp = client.post(
        f"/admin/tiket/{ticket.id}/verifikasi",
        data={
            "csrf_token": csrf_token,
            "official_category_id": str(k3.id),
            "note": "Verifikasi awal ke jaringan wifi",
        },
        follow_redirects=True,
    )
    assert post_resp.status_code == 200
    html = post_resp.get_data(as_text=True)
    assert "berhasil diverifikasi (Status: Terverifikasi)" in html

    # Periksa kondisi database
    db.session.refresh(ticket)
    assert ticket.status == "Terverifikasi"
    assert ticket.official_category_id == k3.id
    assert ticket.needs_manual_verification is False

    # Periksa AuditLog
    logs = db.session.scalars(
        select(AuditLog).where(AuditLog.ticket_id == ticket.id).order_by(AuditLog.id)
    ).all()
    assert len(logs) == 2

    cat_log = next(log for log in logs if log.action == "category_changed")
    assert cat_log.old_value is None
    assert cat_log.new_value == str(k3.id)
    assert cat_log.actor_user_id == admin.id
    assert cat_log.actor_role == "admin_sarpras"
    assert cat_log.note == "Verifikasi awal ke jaringan wifi"

    status_log = next(log for log in logs if log.action == "status_changed")
    assert status_log.old_value == "Baru"
    assert status_log.new_value == "Terverifikasi"
    assert status_log.actor_user_id == admin.id
    assert status_log.actor_role == "admin_sarpras"


# ==============================================================================
# 5. AC-5 & Ketentuan Pengguna: Idempotensi AuditLog (Bebas Redundansi)
# ==============================================================================


def test_reverify_same_category_does_not_create_duplicate_audit(client):
    _login_as(client, "admin_sarpras")
    k1 = db.session.scalar(select(Category).where(Category.code == "K1"))

    ticket = _create_dummy_ticket(
        status="Terverifikasi",
        official_category_id=k1.id,
    )
    db.session.commit()

    initial_audit_count = len(
        db.session.scalars(select(AuditLog).where(AuditLog.ticket_id == ticket.id)).all()
    )

    resp = client.get(f"/admin/tiket/{ticket.id}/verifikasi")
    csrf_token = _extract_csrf(resp)

    # Submit kategori yang sama (K1)
    post_resp = client.post(
        f"/admin/tiket/{ticket.id}/verifikasi",
        data={
            "csrf_token": csrf_token,
            "official_category_id": str(k1.id),
            "note": "Tidak ada perubahan",
        },
        follow_redirects=True,
    )
    assert post_resp.status_code == 200
    html = post_resp.get_data(as_text=True)
    assert "tidak mengalami perubahan" in html

    # Pastikan TIDAK ada entri audit baru yang dibuat
    new_audit_count = len(
        db.session.scalars(select(AuditLog).where(AuditLog.ticket_id == ticket.id)).all()
    )
    assert new_audit_count == initial_audit_count


# ==============================================================================
# 6. Pengujian Koreksi Kategori pada Status Terverifikasi, Diproses, dan Selesai
# ==============================================================================


@pytest.mark.parametrize("fixed_status", ["Terverifikasi", "Diproses", "Selesai"])
def test_category_correction_does_not_alter_status(client, fixed_status):
    """Koreksi kategori pada tiket tidak boleh mengubah status tiket operasional."""
    admin = _login_as(client, "admin_sarpras")
    k1 = db.session.scalar(select(Category).where(Category.code == "K1"))
    k2 = db.session.scalar(select(Category).where(Category.code == "K2"))

    ticket = _create_dummy_ticket(
        status=fixed_status,
        official_category_id=k1.id,
    )
    db.session.commit()

    resp = client.get(f"/admin/tiket/{ticket.id}/verifikasi")
    csrf_token = _extract_csrf(resp)

    # Koreksi kategori dari K1 ke K2
    post_resp = client.post(
        f"/admin/tiket/{ticket.id}/verifikasi",
        data={
            "csrf_token": csrf_token,
            "official_category_id": str(k2.id),
            "note": f"Koreksi saat berstatus {fixed_status}",
        },
        follow_redirects=True,
    )
    assert post_resp.status_code == 200

    # Verifikasi status TIDAK mundur dan tetap sama
    db.session.refresh(ticket)
    assert ticket.status == fixed_status
    assert ticket.official_category_id == k2.id

    # Verifikasi hanya ada 1 log audit (category_changed), TANPA status_changed
    logs = db.session.scalars(
        select(AuditLog).where(AuditLog.ticket_id == ticket.id)
    ).all()
    assert len(logs) == 1
    assert logs[0].action == "category_changed"
    assert logs[0].old_value == str(k1.id)
    assert logs[0].new_value == str(k2.id)
    assert logs[0].actor_user_id == admin.id


# ==============================================================================
# 7. AC-6: Penanganan Tiket Fallback Manual F4-05
# ==============================================================================


def test_verify_ticket_from_f4_05_fallback(client):
    """Tiket dari fallback F4-05 (tanpa model) dapat diverifikasi normal."""
    _login_as(client, "admin_sarpras")
    k4 = db.session.scalar(select(Category).where(Category.code == "K4"))

    ticket = _create_dummy_ticket(
        status="Baru",
        needs_manual=True,
        predicted_category_id=None,
        confidence_score=None,
    )
    db.session.commit()

    # Periksa tampilan form
    resp = client.get(f"/admin/tiket/{ticket.id}/verifikasi")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Model belum tersedia (Fallback)" in html
    csrf_token = _extract_csrf(resp)

    # Tetapkan kategori resmi K4
    post_resp = client.post(
        f"/admin/tiket/{ticket.id}/verifikasi",
        data={
            "csrf_token": csrf_token,
            "official_category_id": str(k4.id),
            "note": "Menetapkan kategori sanitasi setelah peninjauan manual",
        },
        follow_redirects=True,
    )
    assert post_resp.status_code == 200

    db.session.refresh(ticket)
    assert ticket.status == "Terverifikasi"
    assert ticket.official_category_id == k4.id
    assert ticket.needs_manual_verification is False


# ==============================================================================
# 8. Proteksi CSRF & Validasi Input Kategori
# ==============================================================================


def test_verify_ticket_without_csrf_is_rejected(client):
    _login_as(client, "admin_sarpras")
    k1 = db.session.scalar(select(Category).where(Category.code == "K1"))
    ticket = _create_dummy_ticket(status="Baru")
    db.session.commit()

    resp = client.post(
        f"/admin/tiket/{ticket.id}/verifikasi",
        data={"official_category_id": str(k1.id)},
    )
    assert resp.status_code == 400


def test_verify_ticket_with_invalid_category_is_rejected(client):
    _login_as(client, "admin_sarpras")
    ticket = _create_dummy_ticket(status="Baru")
    db.session.commit()

    resp = client.get(f"/admin/tiket/{ticket.id}/verifikasi")
    csrf_token = _extract_csrf(resp)

    # Kirim id kategori 9999 (tidak ada)
    post_resp = client.post(
        f"/admin/tiket/{ticket.id}/verifikasi",
        data={"csrf_token": csrf_token, "official_category_id": "9999"},
        follow_redirects=True,
    )
    assert post_resp.status_code == 200
    html = post_resp.get_data(as_text=True)
    assert "Kategori resmi yang dipilih tidak valid" in html

    db.session.refresh(ticket)
    assert ticket.status == "Baru"
    assert ticket.official_category_id is None


# ==============================================================================
# 9. Atomisitas Transaksi & Rollback saat Kegagalan Audit
# ==============================================================================


def test_atomic_rollback_on_audit_failure(app):
    """Kegagalan pencatatan audit log wajib me-rollback seluruh mutasi tiket."""
    with app.app_context():
        admin = _create_user("audit_admin", "admin_sarpras")
        k1 = db.session.scalar(select(Category).where(Category.code == "K1"))
        ticket = _create_dummy_ticket(status="Baru")
        db.session.commit()

        # Simulasikan error pada saat pencatatan audit
        with patch(
            "app.services.complaint_service.log_category_change",
            side_effect=RuntimeError("Simulated audit write failure"),
        ):
            with pytest.raises(RuntimeError, match="Simulated audit write failure"):
                verify_ticket_category(
                    ticket=ticket,
                    new_category_id=k1.id,
                    actor_user=admin,
                )

        # Pastikan tiket TIDAK termutasi di basis data
        db.session.refresh(ticket)
        assert ticket.status == "Baru"
        assert ticket.official_category_id is None
