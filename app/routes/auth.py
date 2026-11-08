"""Autentikasi staf internal: login dan logout."""
from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import select

from app.extensions import db
from app.models.user import User
from app.utils.decorators import STAFF_ROLES, login_required
from app.utils.password import verify_password

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

GENERIC_LOGIN_ERROR = "Username atau password salah."


@auth_bp.before_app_request
def load_logged_in_user():
    """Muat ulang staf dari session dan jadikan role database sumber otorisasi."""
    g.current_user = None

    if request.endpoint == "static":
        return
    if request.endpoint == "auth.login" and request.method == "POST":
        return

    user_id = session.get("user_id")
    if user_id is None:
        return

    if isinstance(user_id, bool) or not isinstance(user_id, int):
        session.clear()
        return

    user = db.session.get(User, user_id)
    if user is None or not user.is_active or user.role not in STAFF_ROLES:
        session.clear()
        return

    g.current_user = user
    if session.get("role") != user.role:
        session["role"] = user.role


def _authenticate_staff(username, password):
    """Kembalikan user staf yang valid atau None tanpa membedakan penyebab gagal."""
    if not username or not password:
        return None

    user = db.session.scalar(select(User).where(User.username == username))
    if user is None or not user.password_hash:
        return None
    if not user.is_active:
        return None
    if user.role not in STAFF_ROLES:
        return None

    return user if verify_password(user.password_hash, password) else None


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Tampilkan form login atau status sesi staf yang sedang aktif."""
    if request.method == "POST":
        # Setiap percobaan login dimulai tanpa sesi lama, termasuk saat gagal.
        session.clear()

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = _authenticate_staff(username, password)
        if user is None:
            flash(GENERIC_LOGIN_ERROR, "error")
            return render_template("auth/login.html", current_user=None), 200

        session.permanent = True
        session["user_id"] = user.id
        session["role"] = user.role
        return redirect(url_for("auth.login"))

    return render_template("auth/login.html", current_user=g.current_user)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """Akhiri sesi staf dan kembalikan ke halaman login."""
    session.clear()
    return redirect(url_for("auth.login"))
