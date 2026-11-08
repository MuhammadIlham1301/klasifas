"""
Pengujian halaman error kustom VQ-21 (403/404/500).

Cakupan:
1. Status HTTP tetap dipertahankan (403, 404, 500).
2. Halaman error dirender dengan layout aplikasi (navbar + footer), bukan default Flask.
3. Tombol kembali menyesuaikan peran pengguna.
4. Tidak ada kebocoran detail internal (traceback, path server, exception message) pada 500.
5. Konsistensi IDOR: 404 tidak membocorkan keberadaan data.
"""
import secrets

import pytest
from sqlalchemy import delete, select
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.ticket import Ticket
from app.models.user import User

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

            with db.engine.begin() as cleanup_connection:
                if baseline_ticket_ids:
                    cleanup_connection.execute(
                        delete(AuditLog).where(
                            AuditLog.ticket_id.notin_(baseline_ticket_ids)
                        )
                    )
                    cleanup_connection.execute(
                        delete(Ticket).where(Ticket.id.notin_(baseline_ticket_ids))
                    )
                else:
                    cleanup_connection.execute(delete(AuditLog))
                    cleanup_connection.execute(delete(Ticket))

                if baseline_user_ids:
                    cleanup_connection.execute(
                        delete(User).where(User.id.notin_(baseline_user_ids))
                    )
                else:
                    cleanup_connection.execute(delete(User))

            db.engine.dispose()


@pytest.fixture()
def client(app):
    return app.test_client()


def _login_as(client, role: str, username: str | None = None) -> User:
    unique_uname = f"{username or role}_{secrets.token_hex(4)}"
    user = User(
        username=unique_uname,
        full_name=f"Pengguna {unique_uname}",
        password_hash=PASSWORD_HASH,
        role=role,
        is_active=True,
    )
    db.session.add(user)
    db.session.flush()
    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["role"] = user.role
        sess.permanent = True
    return user


PUBLIC_MARKERS = ("KlasiFas", "FTII UHAMKA", "Lewati ke konten utama")


# ==============================================================================
# 1. Status HTTP & render layout aplikasi
# ==============================================================================


def test_404_unknown_path_keeps_status_and_uses_app_layout(client):
    resp = client.get("/halaman-yang-tidak-ada-vq21")

    assert resp.status_code == 404
    html = resp.get_data(as_text=True)
    for marker in PUBLIC_MARKERS:
        assert marker in html
    assert "Halaman yang Anda cari tidak tersedia" in html


def test_403_role_denied_keeps_status_and_uses_app_layout(client):
    _login_as(client, "teknisi")
    resp = client.get("/admin/tiket")

    assert resp.status_code == 403
    html = resp.get_data(as_text=True)
    for marker in PUBLIC_MARKERS:
        assert marker in html
    assert "Anda tidak memiliki akses ke halaman ini" in html


def test_500_handler_renders_generic_page_without_internal_details(client, app):
    secret_message = "INTERNAL_DB_PASSWORD_LEAK_SENTINEL"

    @app.get("/__vq21_broken")
    def _broken():
        raise RuntimeError(secret_message)

    app.config["PROPAGATE_EXCEPTIONS"] = False
    resp = client.get("/__vq21_broken")

    assert resp.status_code == 500
    html = resp.get_data(as_text=True)
    assert "Terjadi kesalahan pada sistem" in html
    for marker in PUBLIC_MARKERS:
        assert marker in html
    assert secret_message not in html
    assert "RuntimeError" not in html
    assert "Traceback" not in html


# ==============================================================================
# 2. Tombol kembali sesuai peran
# ==============================================================================


@pytest.mark.parametrize(
    "role,expected_href,expected_label",
    [
        ("admin_sarpras", "/admin/tiket", "Kembali ke Antrean Sarpras"),
        ("teknisi", "/teknisi/tiket", "Kembali ke Papan Tugas"),
        ("pimpinan", "/dashboard/", "Kembali ke Dasbor"),
    ],
)
def test_error_page_back_button_matches_role(
    client, role, expected_href, expected_label
):
    _login_as(client, role)
    resp = client.get("/halaman-tidak-ada-vq21-role")

    assert resp.status_code == 404
    html = resp.get_data(as_text=True)
    assert expected_label in html
    assert f'href="{expected_href}"' in html


def test_error_page_anonymous_has_no_role_back_button(client):
    resp = client.get("/halaman-tidak-ada-vq21-anon")

    assert resp.status_code == 404
    html = resp.get_data(as_text=True)
    assert "Kembali ke Antrean Sarpras" not in html
    assert "Kembali ke Papan Tugas" not in html
    assert "Kembali ke Dasbor" not in html
    assert "Portal Pengaduan Publik" in html


# ==============================================================================
# 3. IDOR tidak membocorkan keberadaan data
# ==============================================================================


def test_idor_404_does_not_leak_existence_of_other_ticket(client):
    tech_a = _login_as(client, "teknisi", "vq21_tech_a")
    tech_b = _login_as(client, "teknisi", "vq21_tech_b")

    ticket = Ticket(
        ticket_code="KF-7829AA",
        access_token_hash=secrets.token_hex(32),
        description="RAHASIA_TIKET_TEKNISI_B_VQ21",
        building_name="Gedung FTII",
        floor_number=2,
        room_name="Lab VQ21",
        status="Terverifikasi",
        assigned_technician_id=tech_b.id,
    )
    db.session.add(ticket)
    db.session.flush()

    with client.session_transaction() as sess:
        sess["user_id"] = tech_a.id
        sess["role"] = tech_a.role

    resp = client.get(f"/teknisi/tiket/{ticket.id}")

    assert resp.status_code == 404
    html = resp.get_data(as_text=True)
    assert "RAHASIA_TIKET_TEKNISI_B_VQ21" not in html
    assert ticket.ticket_code not in html
    assert "Halaman yang Anda cari tidak tersedia" in html
