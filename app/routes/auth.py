"""Autentikasi staf internal dan pelapor: login dan logout."""
from flask import (
    Blueprint,
    flash,
    g,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import select

from app.extensions import db
from app.models.user import User
from app.utils.decorators import (
    REPORTER_ROLE,
    STAFF_ROLES,
    login_required,
    reporter_required,
)
from app.utils.password import verify_password
from app.utils.rate_limiter import SlidingWindowRateLimiter, get_client_ip

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

GENERIC_LOGIN_ERROR = "Username atau password salah."
LOGIN_ACCOUNT_RATE_LIMIT = 5
LOGIN_IP_RATE_LIMIT = 50
LOGIN_RATE_WINDOW_SECONDS = 300
login_account_limiter = SlidingWindowRateLimiter(
    limit=LOGIN_ACCOUNT_RATE_LIMIT,
    window_seconds=LOGIN_RATE_WINDOW_SECONDS,
)
login_ip_limiter = SlidingWindowRateLimiter(
    limit=LOGIN_IP_RATE_LIMIT,
    window_seconds=LOGIN_RATE_WINDOW_SECONDS,
)


@auth_bp.before_app_request
def load_logged_in_user():
    """Muat ulang staf dan pelapor dari session terpisah."""
    g.current_user = None
    g.reporter = None

    if request.endpoint == "static":
        return
    if request.method == "POST" and request.endpoint in {
        "auth.login",
        "auth.reporter_login",
    }:
        return

    _load_staff_session()
    _load_reporter_session()


def _load_staff_session():
    """Pulihkan sesi staf; role database tetap menjadi sumber otorisasi."""
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


def _load_reporter_session():
    """Pulihkan sesi pelapor tanpa mencampurnya dengan sesi staf."""
    if g.current_user is not None:
        session.pop("reporter_id", None)
        return

    reporter_id = session.get("reporter_id")
    if reporter_id is None:
        return

    if isinstance(reporter_id, bool) or not isinstance(reporter_id, int):
        session.pop("reporter_id", None)
        return

    reporter = db.session.get(User, reporter_id)
    if (
        reporter is None
        or not reporter.is_active
        or reporter.role != REPORTER_ROLE
    ):
        session.pop("reporter_id", None)
        return

    g.reporter = reporter


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


def _authenticate_reporter(username, password):
    """Kembalikan pelapor yang valid atau None tanpa membedakan penyebab gagal."""
    if not username or not password:
        return None

    user = db.session.scalar(select(User).where(User.username == username))
    if user is None or not user.password_hash:
        return None
    if not user.is_active:
        return None
    if user.role != REPORTER_ROLE:
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
        client_ip = get_client_ip(request)
        account_key = f"staff:{client_ip}:{username.lower()[:128]}"
        ip_key = f"staff-ip:{client_ip}"
        account_allowed, account_retry = login_account_limiter.hit(account_key)
        ip_allowed, ip_retry = login_ip_limiter.hit(ip_key)
        if not (account_allowed and ip_allowed):
            retry_after = max(account_retry, ip_retry)
            flash(
                "Terlalu banyak percobaan login. Silakan coba beberapa saat lagi.",
                "error",
            )
            response = make_response(
                render_template("auth/login.html", current_user=None),
                429,
            )
            response.headers["Retry-After"] = str(retry_after)
            return response

        user = _authenticate_staff(username, password)
        if user is None:
            flash(GENERIC_LOGIN_ERROR, "error")
            return render_template("auth/login.html", current_user=None), 200

        login_account_limiter.clear(account_key)
        session.permanent = True
        session["user_id"] = user.id
        session["role"] = user.role
        return redirect(url_for("auth.login"))

    return render_template("auth/login.html", current_user=g.current_user)


@auth_bp.route("/pelapor/login", methods=["GET", "POST"])
def reporter_login():
    """Tampilkan form login atau status sesi pelapor yang sedang aktif."""
    if g.current_user is not None:
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        # Setiap percobaan login dimulai tanpa sesi lama, termasuk saat gagal.
        session.clear()

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        client_ip = get_client_ip(request)
        account_key = f"reporter:{client_ip}:{username.lower()[:128]}"
        ip_key = f"reporter-ip:{client_ip}"
        account_allowed, account_retry = login_account_limiter.hit(account_key)
        ip_allowed, ip_retry = login_ip_limiter.hit(ip_key)
        if not (account_allowed and ip_allowed):
            retry_after = max(account_retry, ip_retry)
            flash(
                "Terlalu banyak percobaan login. Silakan coba beberapa saat lagi.",
                "error",
            )
            response = make_response(
                render_template("auth/reporter_login.html", reporter=None),
                429,
            )
            response.headers["Retry-After"] = str(retry_after)
            return response

        reporter = _authenticate_reporter(username, password)
        if reporter is None:
            flash(GENERIC_LOGIN_ERROR, "error")
            return (
                render_template("auth/reporter_login.html", reporter=None),
                200,
            )

        login_account_limiter.clear(account_key)
        session.permanent = True
        session["reporter_id"] = reporter.id
        return redirect(url_for("auth.reporter_login"))

    return render_template("auth/reporter_login.html", reporter=g.reporter)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """Akhiri sesi staf dan kembalikan ke halaman login."""
    session.clear()
    return redirect(url_for("auth.login"))


@auth_bp.route("/pelapor/logout", methods=["POST"])
@reporter_required
def reporter_logout():
    """Akhiri sesi pelapor dan kembalikan ke halaman login pelapor."""
    session.clear()
    return redirect(url_for("auth.reporter_login"))
