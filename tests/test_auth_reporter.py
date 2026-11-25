"""Integration tests: login dan logout pelapor."""
import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models.user import User
from app.routes.auth import (
    GENERIC_LOGIN_ERROR,
    login_account_limiter,
    login_ip_limiter,
)

PASSWORD = "Valid-Pelapor-Pass-123!"
_HASH_NOT_PROVIDED = object()


@pytest.fixture()
def app():
    """Aplikasi testing dengan transaksi database yang selalu di-rollback."""
    login_account_limiter.reset()
    login_ip_limiter.reset()
    test_app = create_app("testing")
    test_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    with test_app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        db.session.remove()
        db.session.configure(bind=connection)

        try:
            yield test_app
        finally:
            db.session.remove()
            transaction.rollback()
            connection.close()
            db.session.configure(bind=None)
            login_account_limiter.reset()
            login_ip_limiter.reset()


@pytest.fixture()
def client(app):
    return app.test_client()


def _create_user(
    username,
    role="reporter",
    password=PASSWORD,
    password_hash=_HASH_NOT_PROVIDED,
    is_active=True,
):
    if password_hash is _HASH_NOT_PROVIDED:
        password_hash = (
            generate_password_hash(password, method="scrypt")
            if password is not None
            else None
        )

    user = User(
        username=username,
        full_name=f"Pengguna {username}",
        password_hash=password_hash,
        role=role,
        is_active=is_active,
    )
    db.session.add(user)
    db.session.flush()
    return user


def _login(client, username, password=PASSWORD):
    return client.post(
        "/auth/pelapor/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )


def test_get_reporter_login_page_renders_form(client):
    response = client.get("/auth/pelapor/login")

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Login Pelapor KlasiFas" in body
    assert 'action="/auth/pelapor/login"' in body
    assert 'name="username"' in body
    assert 'name="password"' in body
    assert 'name="csrf_token"' in body
    assert 'action="/auth/login"' not in body


def test_reporter_login_links_to_staff_login(client):
    response = client.get("/auth/pelapor/login")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert '<a id="staff-login-link" href="/auth/login">' in body
    assert "Login sebagai Staf" in body


def test_reporter_login_links_to_public_report_form(client):
    response = client.get("/auth/pelapor/login")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'href="/lapor">Laporkan tanpa login</a>' in body


def test_reporter_login_success_sets_separate_session(client):
    reporter = _create_user("reporter_login")

    response = _login(client, "reporter_login")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/auth/pelapor/login")

    with client.session_transaction() as session_data:
        assert session_data["reporter_id"] == reporter.id
        assert "user_id" not in session_data
        assert session_data.permanent is True
        assert set(session_data.keys()) == {"reporter_id", "_permanent"}


def test_reporter_status_page_after_login(client):
    reporter = _create_user("reporter_status")

    response = client.post(
        "/auth/pelapor/login",
        data={"username": "reporter_status", "password": PASSWORD},
        follow_redirects=True,
    )

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Anda sudah login sebagai" in body
    assert reporter.full_name in body
    assert "(Pelapor)" in body
    assert 'action="/auth/pelapor/logout"' in body
    assert 'name="password"' not in body
    assert "Dasbor" not in body
    assert "Antrean Sarpras" not in body


@pytest.mark.parametrize(
    "username,password,is_active,password_hash,role",
    [
        ("wrong_password_reporter", "password-yang-salah", True, _HASH_NOT_PROVIDED, "reporter"),
        ("missing_reporter", PASSWORD, True, _HASH_NOT_PROVIDED, "reporter"),
        ("inactive_reporter", PASSWORD, False, _HASH_NOT_PROVIDED, "reporter"),
        ("no_hash_reporter", PASSWORD, True, None, "reporter"),
        ("staff_account", PASSWORD, True, _HASH_NOT_PROVIDED, "admin_sarpras"),
    ],
)
def test_reporter_login_failure_is_generic(
    client, username, password, is_active, password_hash, role
):
    if username != "missing_reporter":
        _create_user(
            username,
            role=role,
            is_active=is_active,
            password_hash=password_hash,
        )

    response = _login(client, username, password)

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert GENERIC_LOGIN_ERROR in body
    assert username not in body

    with client.session_transaction() as session_data:
        assert "reporter_id" not in session_data
        assert "user_id" not in session_data


def test_reporter_login_is_rate_limited(client):
    _create_user("rate_limited_reporter")

    for _ in range(5):
        assert _login(client, "rate_limited_reporter", "wrong-password").status_code == 200

    response = _login(client, "rate_limited_reporter", "wrong-password")

    assert response.status_code == 429
    assert response.headers["Retry-After"]
    assert "Terlalu banyak percobaan login" in response.get_data(as_text=True)


def test_reporter_rate_limit_does_not_block_other_account_same_ip(client):
    _create_user("rate_limited_a")
    _create_user("rate_limited_b")

    for _ in range(5):
        assert _login(client, "rate_limited_a", "wrong-password").status_code == 200

    response = _login(client, "rate_limited_b")

    assert response.status_code == 302


def test_reporter_cannot_access_staff_area(client):
    reporter = _create_user("isolated_reporter")

    with client.session_transaction() as session_data:
        session_data["reporter_id"] = reporter.id

    response = client.get("/admin/tiket")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/auth/login")


def test_staff_session_redirects_away_from_reporter_login(client):
    _create_user("staff_redirect", role="teknisi")
    assert client.post(
        "/auth/login",
        data={"username": "staff_redirect", "password": PASSWORD},
    ).status_code == 302

    response = client.get("/auth/pelapor/login")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/auth/login")


def test_report_form_shows_reporter_identity_and_logout(client):
    reporter = _create_user("nav_reporter")
    assert _login(client, "nav_reporter").status_code == 302

    response = client.get("/lapor")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert reporter.full_name in body
    assert "Pelapor" in body
    assert 'method="post" action="/auth/pelapor/logout"' in body
    assert 'name="csrf_token"' in body
    assert "Tanpa login" not in body


def test_report_form_keeps_public_state_for_anonymous(client):
    response = client.get("/lapor")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Tanpa login" in body
    assert 'action="/auth/pelapor/logout"' not in body


def test_reporter_logout_clears_entire_session(client):
    _create_user("logout_reporter")
    assert _login(client, "logout_reporter").status_code == 302

    with client.session_transaction() as session_data:
        session_data["stale_key"] = "harus-terhapus"

    response = client.post("/auth/pelapor/logout")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/auth/pelapor/login")
    with client.session_transaction() as session_data:
        assert len(session_data) == 0


def test_get_reporter_logout_is_rejected(client):
    response = client.get("/auth/pelapor/logout")
    assert response.status_code == 405
