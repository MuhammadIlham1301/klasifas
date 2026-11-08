"""
Pengujian perintah CLI `flask create-staff` (SECURITY.md §4.4).

Cakupan:
1. Pembuatan akun untuk setiap role staf yang valid.
2. Penolakan username duplikat, format username tidak valid, dan role reporter.
3. Penolakan password pendek, password tidak cocok saat konfirmasi, dan password == username.
4. Tidak ada kebocoran password maupun hash pada output perintah.
5. Tidak ada akun default yang tercipta otomatis.
"""
import secrets

import pytest
from sqlalchemy import delete, select

from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.ticket import Ticket
from app.models.user import User
from app.utils.password import verify_password

VALID_PASSWORD = "RahasiaStaf-2026!"


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
def runner(app):
    return app.test_cli_runner()


def _unique_username(prefix: str = "cli") -> str:
    return f"{prefix}_{secrets.token_hex(4)}"


def _find_user(username: str) -> User | None:
    return db.session.scalar(select(User).where(User.username == username))


def _invoke(runner, username, role, full_name, password_inputs):
    return runner.invoke(
        args=[
            "create-staff",
            "--username",
            username,
            "--role",
            role,
            "--full-name",
            full_name,
        ],
        input="\n".join(password_inputs) + "\n",
    )


# ==============================================================================
# 1. Pembuatan akun per role
# ==============================================================================


@pytest.mark.parametrize("role", ["admin_sarpras", "teknisi", "pimpinan"])
def test_create_staff_succeeds_for_each_staff_role(runner, app, role):
    username = _unique_username(role)

    result = _invoke(runner, username, role, "Nama Staf Uji", [VALID_PASSWORD, VALID_PASSWORD])

    assert result.exit_code == 0, result.output
    user = _find_user(username)
    assert user is not None
    assert user.role == role
    assert user.full_name == "Nama Staf Uji"
    assert user.is_active is True
    assert user.password_hash
    assert verify_password(user.password_hash, VALID_PASSWORD)
    assert f"Akun staf dibuat: {username}" in result.output


def test_created_staff_can_complete_login_flow(runner, app):
    username = _unique_username("logincheck")
    result = _invoke(runner, username, "teknisi", "Teknisi Login", [VALID_PASSWORD, VALID_PASSWORD])
    assert result.exit_code == 0, result.output

    client = app.test_client()
    login = client.post(
        "/auth/login",
        data={"username": username, "password": VALID_PASSWORD},
    )
    assert login.status_code == 302

    with client.session_transaction() as sess:
        assert sess.get("user_id") is not None


# ==============================================================================
# 2. Penolakan input tidak valid
# ==============================================================================


def test_duplicate_username_is_rejected(runner, app):
    username = _unique_username("dup")
    first = _invoke(runner, username, "teknisi", "Pertama", [VALID_PASSWORD, VALID_PASSWORD])
    assert first.exit_code == 0, first.output

    second = _invoke(runner, username, "pimpinan", "Kedua", [VALID_PASSWORD, VALID_PASSWORD])

    assert second.exit_code != 0
    assert "sudah dipakai" in second.output
    assert _find_user(username).role == "teknisi"


@pytest.mark.parametrize(
    "bad_username",
    ["ab", "spasi ada", "tanda!seru", "a" * 65],
)
def test_invalid_username_format_is_rejected(runner, app, bad_username):
    result = _invoke(runner, bad_username, "teknisi", "Nama", [VALID_PASSWORD, VALID_PASSWORD])

    assert result.exit_code != 0
    assert "Username tidak valid" in result.output
    assert _find_user(bad_username.strip().lower()) is None


def test_reporter_role_is_rejected(runner, app):
    username = _unique_username("rep")

    result = _invoke(runner, username, "reporter", "Pelapor", [VALID_PASSWORD, VALID_PASSWORD])

    assert result.exit_code != 0
    assert _find_user(username) is None


def test_short_password_is_rejected(runner, app):
    username = _unique_username("short")

    result = _invoke(runner, username, "teknisi", "Nama", ["Pendek1234", "Pendek1234"])

    assert result.exit_code != 0
    assert "minimal 12 karakter" in result.output
    assert _find_user(username) is None


def test_password_confirmation_mismatch_is_rejected(runner, app):
    username = _unique_username("mismatch")

    result = _invoke(runner, username, "teknisi", "Nama", [VALID_PASSWORD, "BedaPassword-99!"])

    assert result.exit_code != 0
    assert _find_user(username) is None


def test_password_equal_to_username_is_rejected(runner, app):
    username = "abcdefghijklmnop"

    result = _invoke(runner, username, "teknisi", "Nama", [username, username])

    assert result.exit_code != 0
    assert "tidak boleh sama dengan username" in result.output
    assert _find_user(username) is None


def test_empty_full_name_is_rejected(runner, app):
    username = _unique_username("noname")

    result = _invoke(runner, username, "teknisi", "   ", [VALID_PASSWORD, VALID_PASSWORD])

    assert result.exit_code != 0
    assert "Nama lengkap wajib diisi" in result.output
    assert _find_user(username) is None


def test_uppercase_username_is_normalized_to_lowercase(runner, app):
    base = _unique_username("case")
    mixed = base.upper()

    result = _invoke(runner, mixed, "teknisi", "Nama", [VALID_PASSWORD, VALID_PASSWORD])

    assert result.exit_code == 0, result.output
    assert _find_user(base) is not None


# ==============================================================================
# 3. Tidak ada kebocoran kredensial
# ==============================================================================


def test_output_never_contains_password_or_hash(runner, app):
    username = _unique_username("leak")

    result = _invoke(runner, username, "teknisi", "Nama", [VALID_PASSWORD, VALID_PASSWORD])

    assert result.exit_code == 0, result.output
    assert VALID_PASSWORD not in result.output
    assert "scrypt" not in result.output
    user = _find_user(username)
    assert user.password_hash not in result.output


def test_no_default_accounts_are_created_automatically(runner, app):
    baseline_usernames = set(db.session.scalars(select(User.username)).all())

    result = runner.invoke(args=["create-staff", "--help"])
    assert result.exit_code == 0

    after_usernames = set(db.session.scalars(select(User.username)).all())
    assert after_usernames == baseline_usernames
