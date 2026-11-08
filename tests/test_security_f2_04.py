"""Pengujian TSK-F2-04: proteksi CSRF dan HTTP security headers."""
import re

import pytest
from flask import Blueprint, g
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.user import User
from app.utils.security_headers import CONTENT_SECURITY_POLICY

PASSWORD = "Valid-Staff-Pass-123!"
PASSWORD_HASH = generate_password_hash(PASSWORD, method="scrypt")
CSRF_TOKEN_PATTERN = re.compile(r'name="csrf_token" value="([^"]+)"')

csrf_probe_bp = Blueprint("csrf_probe", __name__, url_prefix="/_test_csrf")


@csrf_probe_bp.route("/mutate", methods=["POST", "PUT", "PATCH", "DELETE"])
def mutate():
    return {"mutated": True}


@pytest.fixture()
def app():
    from app import create_app

    test_app = create_app("testing")
    test_app.config.update(TESTING=True, WTF_CSRF_ENABLED=True)
    test_app.register_blueprint(csrf_probe_bp)

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
            db.engine.dispose()


@pytest.fixture()
def client(app):
    return app.test_client()


def _create_user(username, role="admin_sarpras"):
    user = User(
        username=username,
        full_name=f"Pengguna {username}",
        password_hash=PASSWORD_HASH,
        role=role,
        is_active=True,
    )
    db.session.add(user)
    db.session.flush()
    return user


def _get_csrf_token(client, path="/auth/login"):
    g.pop("csrf_token", None)
    response = client.get(path)
    assert response.status_code == 200
    match = CSRF_TOKEN_PATTERN.search(response.get_data(as_text=True))
    assert match is not None
    return match.group(1)


def _login(client, username, token):
    return client.post(
        "/auth/login",
        data={
            "csrf_token": token,
            "username": username,
            "password": PASSWORD,
        },
        follow_redirects=False,
    )


def _assert_security_headers(response):
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Content-Security-Policy"] == CONTENT_SECURITY_POLICY
    assert "Strict-Transport-Security" not in response.headers


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_unsafe_methods_reject_missing_csrf_token(client, method):
    response = getattr(client, method)("/_test_csrf/mutate")

    assert response.status_code == 400


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_unsafe_methods_reject_invalid_csrf_token(client, method):
    response = getattr(client, method)(
        "/_test_csrf/mutate",
        data={"csrf_token": "token-tidak-valid"},
    )

    assert response.status_code == 400


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_unsafe_methods_accept_valid_csrf_token(client, method):
    token = _get_csrf_token(client)

    response = getattr(client, method)(
        "/_test_csrf/mutate",
        data={"csrf_token": token},
    )

    assert response.status_code == 200
    assert response.get_json() == {"mutated": True}


def test_login_post_rejects_missing_csrf_token(client):
    _create_user("csrf_missing_login")

    response = client.post(
        "/auth/login",
        data={"username": "csrf_missing_login", "password": PASSWORD},
    )

    assert response.status_code == 400
    with client.session_transaction() as session_data:
        assert "user_id" not in session_data


def test_login_post_rejects_invalid_csrf_token(client):
    _create_user("csrf_invalid_login")

    response = client.post(
        "/auth/login",
        data={
            "csrf_token": "token-tidak-valid",
            "username": "csrf_invalid_login",
            "password": PASSWORD,
        },
    )

    assert response.status_code == 400
    with client.session_transaction() as session_data:
        assert "user_id" not in session_data


def test_login_and_logout_accept_valid_csrf_token(client):
    user = _create_user("csrf_valid_login")

    login_token = _get_csrf_token(client)
    response = _login(client, "csrf_valid_login", login_token)

    assert response.status_code == 302
    with client.session_transaction() as session_data:
        assert session_data["user_id"] == user.id
        assert session_data["role"] == "admin_sarpras"

    logout_token = _get_csrf_token(client)
    response = client.post("/auth/logout", data={"csrf_token": logout_token})

    assert response.status_code == 302
    with client.session_transaction() as session_data:
        assert len(session_data) == 0


def test_logout_post_rejects_missing_csrf_token(client):
    user = _create_user("csrf_missing_logout")
    token = _get_csrf_token(client)
    assert _login(client, "csrf_missing_logout", token).status_code == 302

    response = client.post("/auth/logout")

    assert response.status_code == 400
    with client.session_transaction() as session_data:
        assert session_data["user_id"] == user.id


def test_get_requests_are_not_blocked_by_csrf(client):
    assert client.get("/auth/login").status_code == 200
    assert client.get("/auth/logout").status_code == 405
    assert client.get("/_test_csrf/mutate").status_code == 405


def test_login_form_contains_csrf_token(client):
    response = client.get("/auth/login")

    assert response.status_code == 200
    assert CSRF_TOKEN_PATTERN.search(response.get_data(as_text=True)) is not None


def test_security_headers_on_success(client):
    response = client.get("/auth/login")

    assert response.status_code == 200
    _assert_security_headers(response)


def test_security_headers_on_redirect(client):
    _create_user("csrf_redirect_user")
    token = _get_csrf_token(client)

    response = _login(client, "csrf_redirect_user", token)

    assert response.status_code == 302
    _assert_security_headers(response)


def test_security_headers_on_not_found(client):
    response = client.get("/halaman-tidak-ada")

    assert response.status_code == 404
    _assert_security_headers(response)


def test_security_headers_on_csrf_error(client):
    response = client.post("/auth/login", data={"username": "tanpa-token"})

    assert response.status_code == 400
    _assert_security_headers(response)


def test_csp_is_strict_and_compatible_with_planned_assets(client):
    response = client.get("/auth/login")

    csp = response.headers["Content-Security-Policy"]

    assert "default-src 'self'" in csp
    assert "script-src 'self'" in csp
    assert "style-src 'self'" in csp
    assert "img-src 'self' data:" in csp
    assert "connect-src 'self'" in csp
    assert "unsafe-inline" not in csp
    assert "*" not in csp
    assert "http://" not in csp
    assert "https://" not in csp
