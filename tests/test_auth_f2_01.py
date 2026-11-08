"""Integration tests TSK-F2-01: login dan logout staf internal."""
import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models.user import User
from app.routes.auth import GENERIC_LOGIN_ERROR

PASSWORD = "Valid-Staff-Pass-123!"
_HASH_NOT_PROVIDED = object()


@pytest.fixture()
def app():
    """Aplikasi testing dengan transaksi database yang selalu di-rollback."""
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


@pytest.fixture()
def client(app):
    return app.test_client()


def _create_user(
    username,
    role,
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
        "/auth/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )


# --- GET halaman login ---
def test_get_login_page_renders_form(client):
    response = client.get("/auth/login")

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Login Staf KlasiFas" in body
    assert 'name="username"' in body
    assert 'name="password"' in body
    assert 'name="csrf_token"' in body
    assert "register" not in body.lower()


# --- Login berhasil untuk tiga role staf ---
@pytest.mark.parametrize("role", ["admin_sarpras", "teknisi", "pimpinan"])
def test_login_success_for_staff_roles(client, role):
    user = _create_user(f"{role}_user", role)

    response = _login(client, f"{role}_user")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/auth/login")

    with client.session_transaction() as session_data:
        assert session_data["user_id"] == user.id
        assert session_data["role"] == role
        assert session_data.permanent is True
        assert set(session_data.keys()) == {"user_id", "role", "_permanent"}
        assert "password" not in session_data
        assert "password_hash" not in session_data


# --- Password salah dan username tidak ditemukan ---
@pytest.mark.parametrize(
    "username,password",
    [
        ("wrong_password_user", "password-yang-salah"),
        ("username_tidak_ada", PASSWORD),
    ],
)
def test_login_failure_is_generic(client, username, password):
    if username == "wrong_password_user":
        _create_user(username, "admin_sarpras")

    response = _login(client, username, password)

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert GENERIC_LOGIN_ERROR in body
    assert "wrong_password_user" not in body
    assert "username_tidak_ada" not in body

    with client.session_transaction() as session_data:
        assert "user_id" not in session_data
        assert "role" not in session_data


# --- Login gagal membersihkan sesi lama ---
def test_failed_login_clears_previous_session(client):
    _create_user("failed_login_user", "admin_sarpras")

    with client.session_transaction() as session_data:
        session_data["user_id"] = 999999
        session_data["role"] = "reporter"
        session_data["stale_key"] = "nilai-lama"

    response = _login(client, "failed_login_user", "password-yang-salah")

    assert response.status_code == 200
    assert GENERIC_LOGIN_ERROR in response.get_data(as_text=True)
    with client.session_transaction() as session_data:
        assert "user_id" not in session_data
        assert "role" not in session_data
        assert "stale_key" not in session_data


# --- Username kosong atau whitespace ditolak ---
@pytest.mark.parametrize("username", ["", " ", "   ", "\t\n"])
def test_login_rejects_empty_or_whitespace_username(client, username):
    _create_user("blank_username_user", "teknisi")

    response = _login(client, username)

    assert response.status_code == 200
    assert GENERIC_LOGIN_ERROR in response.get_data(as_text=True)
    with client.session_transaction() as session_data:
        assert "user_id" not in session_data
        assert "role" not in session_data


# --- Password kosong ditolak ---
def test_login_rejects_empty_password(client):
    _create_user("empty_password_user", "pimpinan")

    response = _login(client, "empty_password_user", "")

    assert response.status_code == 200
    assert GENERIC_LOGIN_ERROR in response.get_data(as_text=True)
    with client.session_transaction() as session_data:
        assert "user_id" not in session_data
        assert "role" not in session_data


# --- Akun nonaktif ditolak ---
def test_login_rejects_inactive_staff(client):
    _create_user("inactive_user", "teknisi", is_active=False)

    response = _login(client, "inactive_user")

    assert response.status_code == 200
    assert GENERIC_LOGIN_ERROR in response.get_data(as_text=True)
    with client.session_transaction() as session_data:
        assert "user_id" not in session_data


# --- Akun tanpa password hash ditolak ---
def test_login_rejects_account_without_password_hash(client):
    _create_user("no_hash_user", "reporter", password=None)

    response = _login(client, "no_hash_user", "apa-saja")

    assert response.status_code == 200
    assert GENERIC_LOGIN_ERROR in response.get_data(as_text=True)
    with client.session_transaction() as session_data:
        assert "user_id" not in session_data


# --- Role reporter ditolak ---
def test_login_rejects_reporter_role(client):
    _create_user("reporter_user", "reporter")

    response = _login(client, "reporter_user")

    assert response.status_code == 200
    assert GENERIC_LOGIN_ERROR in response.get_data(as_text=True)
    with client.session_transaction() as session_data:
        assert "user_id" not in session_data


# --- Sesi lama dibersihkan sebelum sesi login baru ---
def test_login_clears_previous_session(client):
    user = _create_user("session_reset_user", "pimpinan")

    with client.session_transaction() as session_data:
        session_data["user_id"] = 999999
        session_data["role"] = "reporter"
        session_data["stale_key"] = "nilai-lama"

    response = _login(client, "session_reset_user")
    assert response.status_code == 302

    with client.session_transaction() as session_data:
        assert session_data["user_id"] == user.id
        assert session_data["role"] == "pimpinan"
        assert "stale_key" not in session_data
        assert session_data.permanent is True
        assert set(session_data.keys()) == {"user_id", "role", "_permanent"}


# --- Halaman status tampil setelah login ---
def test_status_page_after_login(client):
    user = _create_user("status_user", "admin_sarpras")

    response = client.post(
        "/auth/login",
        data={"username": "status_user", "password": PASSWORD},
        follow_redirects=True,
    )

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Anda sudah login sebagai" in body
    assert user.full_name in body
    assert "(admin_sarpras)" in body
    assert 'action="/auth/logout"' in body
    assert 'name="password"' not in body


# --- Logout membersihkan seluruh sesi ---
def test_logout_clears_entire_session(client):
    _create_user("logout_user", "teknisi")
    assert _login(client, "logout_user").status_code == 302

    with client.session_transaction() as session_data:
        session_data["stale_key"] = "harus-terhapus"

    response = client.post("/auth/logout")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/auth/login")
    with client.session_transaction() as session_data:
        assert len(session_data) == 0


# --- Logout hanya menerima POST ---
def test_get_logout_is_rejected(client):
    response = client.get("/auth/logout")
    assert response.status_code == 405


# --- Tidak tersedia route registrasi publik ---
def test_registration_route_is_not_available(client):
    assert client.get("/auth/register").status_code == 404
    assert client.post("/auth/register").status_code == 404
