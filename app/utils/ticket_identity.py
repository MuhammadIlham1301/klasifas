"""Pembuatan kode referensi dan hash token akses tiket."""
import hashlib
import hmac
import secrets

TICKET_CODE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
TICKET_CODE_LENGTH = 6
ACCESS_TOKEN_BYTES = 16


def generate_ticket_code() -> str:
    """Buat kode referensi acak berformat KF-XXXXXX."""
    suffix = "".join(
        secrets.choice(TICKET_CODE_ALPHABET) for _ in range(TICKET_CODE_LENGTH)
    )
    return f"KF-{suffix}"


def hash_access_token(token: str) -> str:
    """Hitung hash SHA-256 dari token akses."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_access_token() -> tuple[str, str]:
    """Buat token akses 128-bit dan kembalikan token asli serta hash-nya."""
    token = secrets.token_urlsafe(ACCESS_TOKEN_BYTES)
    return token, hash_access_token(token)


def generate_access_token_hash() -> str:
    """Buat token akses 128-bit dan kembalikan hash-nya saja."""
    _, token_hash = generate_access_token()
    return token_hash


def verify_access_token(token: str, stored_hash: str) -> bool:
    """Verifikasi token terhadap hash tersimpan secara constant-time."""
    if not token or not stored_hash:
        return False
    return hmac.compare_digest(hash_access_token(token), stored_hash)
