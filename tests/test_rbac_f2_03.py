"""Pengujian TSK-F2-03: otorisasi RBAC server-side."""
import pytest
from flask import Blueprint, g
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.user import User
from app.utils.decorators import login_required, role_required

PASSWORD = "Valid-Staff-Pass-123!"
PASSWORD_HASH = generate_password_hash(PASSWORD, method="scrypt")

rbac_test_bp = Blueprint("rbac_test", __name__, url_prefix="/_test")


@rbac_test_bp.get("/public")
def public_route():
    return {"authenticated": g.current_user is not None}


@rbac_test_bp.get("/staff")
@login_required
def staff_route():
    return {"role": g.current_user.role}


@rbac_test_bp.get("/admin")
@role_required("admin_sarpras")
def admin_route():
    return {"role": g.current_user.role}


@rbac_test_bp.get("/technician")
@role_required("teknisi")
def technician_route():
    return {"role": g.current_user.role}


@rbac_test_bp.get("/management")
@role_required("admin_sarpras", "pimpinan")
def management_route():
    return {"role": g.current_user.role}


@rbac_test_bp.get("/audit")
@role_required("admin_sarpras")
def audit_route():
    return {"role": g.current_user.role}


@rbac_test_bp.post("/admin-mutation")
@role_required("admin_sarpras")
def admin_mutation_route():
    return {"updated": True}


@pytest.fixture()
def app():
    """Aplikasi testing dengan transaksi database yang selalu di-rollback."""
    from app import create_app

    test_app = create_app("testing")
    test_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    test_app.register_blueprint(rbac_test_bp)

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


def _create_user(username, role, is_active=True):
    user = User(
        username=username,
        full_name=f"Pengguna {username}",
        password_hash=PASSWORD_HASH,
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


def _login_as(client, role, username=None):
    username = username or f"{role}_user"
    user = _create_user(username, role)
    response = _login(client, username)
    assert response.status_code == 302
    return user


def _set_session(client, user_id, role, permanent=True):
    with client.session_transaction() as session_data:
        session_data["user_id"] = user_id
        session_data["role"] = role
        session_data.permanent = permanent


@pytest.mark.parametrize(
    "path",
    [
        "/_test/staff",
        "/_test/admin",
        "/_test/technician",
        "/_test/management",
        "/_test/audit",
    ],
)
def test_unauthenticated_staff_request_redirects_to_login(client, path):
    response = client.get(path)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/auth/login")


def test_reporter_session_is_rejected(client):
    user = _create_user("reporter_session", "reporter")
    _set_session(client, user.id, "reporter")

    response = client.get("/_test/staff")

    assert response.status_code == 302
    with client.session_transaction() as session_data:
        assert "user_id" not in session_data
        assert "role" not in session_data


def test_invalid_session_user_is_cleared(client):
    _set_session(client, 999999, "admin_sarpras")

    response = client.get("/_test/staff")

    assert response.status_code == 302
    with client.session_transaction() as session_data:
        assert len(session_data) == 0


def test_inactive_user_session_is_cleared(client):
    user = _create_user("inactive_session", "teknisi", is_active=False)
    _set_session(client, user.id, "teknisi")

    response = client.get("/_test/staff")

    assert response.status_code == 302
    with client.session_transaction() as session_data:
        assert len(session_data) == 0


def test_deleted_user_session_is_cleared(client):
    user = _create_user("deleted_session", "pimpinan")
    _set_session(client, user.id, "pimpinan")
    db.session.delete(user)
    db.session.flush()

    response = client.get("/_test/staff")

    assert response.status_code == 302
    with client.session_transaction() as session_data:
        assert len(session_data) == 0


@pytest.mark.parametrize(
    "role,path,expected_status",
    [
        ("admin_sarpras", "/_test/staff", 200),
        ("admin_sarpras", "/_test/admin", 200),
        ("admin_sarpras", "/_test/technician", 403),
        ("admin_sarpras", "/_test/management", 200),
        ("admin_sarpras", "/_test/audit", 200),
        ("teknisi", "/_test/staff", 200),
        ("teknisi", "/_test/admin", 403),
        ("teknisi", "/_test/technician", 200),
        ("teknisi", "/_test/management", 403),
        ("teknisi", "/_test/audit", 403),
        ("pimpinan", "/_test/staff", 200),
        ("pimpinan", "/_test/admin", 403),
        ("pimpinan", "/_test/technician", 403),
        ("pimpinan", "/_test/management", 200),
        ("pimpinan", "/_test/audit", 403),
    ],
)
def test_role_matrix(client, role, path, expected_status):
    _login_as(client, role, username=f"{role}_matrix")

    response = client.get(path)

    assert response.status_code == expected_status


def test_admin_can_use_admin_mutation_route(client):
    _login_as(client, "admin_sarpras", "admin_mutation_user")

    response = client.post("/_test/admin-mutation")

    assert response.status_code == 200
    assert response.get_json() == {"updated": True}


@pytest.mark.parametrize("role", ["teknisi", "pimpinan"])
def test_non_admin_cannot_use_admin_mutation_route(client, role):
    _login_as(client, role, username=f"{role}_mutation_user")

    response = client.post("/_test/admin-mutation")

    assert response.status_code == 403


def test_database_role_change_updates_access_and_session(client):
    user = _login_as(client, "admin_sarpras", "role_change_user")
    assert client.get("/_test/admin").status_code == 200

    user.role = "teknisi"
    db.session.flush()

    assert client.get("/_test/admin").status_code == 403
    assert client.get("/_test/technician").status_code == 200
    with client.session_transaction() as session_data:
        assert session_data["role"] == "teknisi"
        assert session_data.permanent is True


def test_session_role_tampering_does_not_grant_access(client):
    _login_as(client, "teknisi", "role_tamper_user")

    with client.session_transaction() as session_data:
        session_data["role"] = "admin_sarpras"

    response = client.get("/_test/admin")

    assert response.status_code == 403
    with client.session_transaction() as session_data:
        assert session_data["role"] == "teknisi"


def test_role_change_to_reporter_invalidates_session(client):
    user = _login_as(client, "admin_sarpras", "reporter_change_user")

    user.role = "reporter"
    db.session.flush()

    response = client.get("/_test/staff")

    assert response.status_code == 302
    with client.session_transaction() as session_data:
        assert len(session_data) == 0


def test_missing_session_role_is_restored_from_database(client):
    user = _create_user("missing_role_user", "admin_sarpras")
    _set_session(client, user.id, None, permanent=False)

    response = client.get("/_test/admin")

    assert response.status_code == 200
    with client.session_transaction() as session_data:
        assert session_data["role"] == "admin_sarpras"


def test_login_post_clears_stale_session_and_sets_permanent(client):
    user = _create_user("stale_login_user", "admin_sarpras")
    with client.session_transaction() as session_data:
        session_data["user_id"] = 999999
        session_data["role"] = "reporter"
        session_data["stale_key"] = "nilai-lama"

    response = _login(client, "stale_login_user")

    assert response.status_code == 302
    with client.session_transaction() as session_data:
        assert session_data["user_id"] == user.id
        assert session_data["role"] == "admin_sarpras"
        assert session_data.permanent is True
        assert "stale_key" not in session_data


def test_public_route_remains_public_without_login(client):
    response = client.get("/_test/public")

    assert response.status_code == 200
    assert response.get_json() == {"authenticated": False}


def test_public_route_keeps_valid_session(client):
    _login_as(client, "pimpinan", "public_session_user")

    response = client.get("/_test/public")

    assert response.status_code == 200
    assert response.get_json() == {"authenticated": True}


def test_public_route_clears_invalid_session_without_redirect(client):
    _set_session(client, 999999, "admin_sarpras")

    response = client.get("/_test/public")

    assert response.status_code == 200
    with client.session_transaction() as session_data:
        assert len(session_data) == 0


def test_static_request_does_not_mutate_session(client):
    _set_session(client, 999999, "admin_sarpras")

    response = client.get("/static/tidak-ada.css")

    assert response.status_code == 404
    with client.session_transaction() as session_data:
        assert session_data["user_id"] == 999999


def test_logout_requires_authentication(client):
    response = client.post("/auth/logout")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/auth/login")


def test_logout_clears_entire_session(client):
    _login_as(client, "teknisi", "logout_rbac_user")
    with client.session_transaction() as session_data:
        session_data["stale_key"] = "harus-terhapus"

    response = client.post("/auth/logout")

    assert response.status_code == 302
    with client.session_transaction() as session_data:
        assert len(session_data) == 0


def test_role_required_rejects_empty_or_invalid_roles():
    with pytest.raises(ValueError):
        role_required()
    with pytest.raises(ValueError):
        role_required("reporter")
    with pytest.raises(ValueError):
        role_required("role_tidak_ada")
