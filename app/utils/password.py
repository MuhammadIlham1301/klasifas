"""Hashing dan verifikasi password staf internal."""
from werkzeug.security import check_password_hash, generate_password_hash

HASH_METHOD = "scrypt"


def hash_password(password):
    """Hash password menggunakan algoritma scrypt."""
    return generate_password_hash(password, method=HASH_METHOD)


def verify_password(password_hash, password):
    """Verifikasi password terhadap hash tanpa membocorkan nilai plaintext."""
    if not password_hash or not password:
        return False

    try:
        return check_password_hash(password_hash, password)
    except (TypeError, ValueError):
        return False
