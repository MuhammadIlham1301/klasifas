"""Dekorator otorisasi RBAC untuk area staf internal."""
from functools import wraps

from flask import abort, g, redirect, url_for

from app.models.user import USER_ROLES

STAFF_ROLES = frozenset(USER_ROLES) - {"reporter"}


def _validate_staff_roles(allowed_roles):
    """Validasi daftar role agar hanya role staf resmi yang dapat dipakai."""
    allowed = frozenset(allowed_roles)

    if not allowed:
        raise ValueError("role_required membutuhkan minimal satu role staf.")

    unknown_roles = allowed - STAFF_ROLES
    if unknown_roles:
        raise ValueError(
            f"Role tidak valid untuk akses staf: {', '.join(sorted(unknown_roles))}."
        )

    return allowed


def login_required(view):
    """Pastikan request memiliki sesi staf yang sudah divalidasi loader."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if getattr(g, "current_user", None) is None:
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped


def role_required(*allowed_roles):
    """Batasi akses ke role staf yang diizinkan menggunakan login_required."""
    allowed = _validate_staff_roles(allowed_roles)

    def decorator(view):
        @wraps(view)
        def role_checked(*args, **kwargs):
            if g.current_user.role not in allowed:
                abort(403)
            return view(*args, **kwargs)

        return login_required(role_checked)

    return decorator
