"""Konfigurasi pytest bersama."""
import pytest

from app.routes.auth import login_account_limiter, login_ip_limiter


@pytest.fixture(autouse=True)
def reset_login_limiter():
    """Isolasi rate limiter login antar pengujian."""
    login_account_limiter.reset()
    login_ip_limiter.reset()
    yield
    login_account_limiter.reset()
    login_ip_limiter.reset()
