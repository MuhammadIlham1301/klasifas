"""Pengujian TSK-F2-02: hashing password dan konfigurasi sesi."""
from datetime import timedelta

import pytest

from app.config import DevelopmentConfig, ProductionConfig, TestingConfig
from app.utils.password import hash_password, verify_password

PASSWORD = "Staff-Pass-123!"


def test_hash_password_uses_scrypt():
    password_hash = hash_password(PASSWORD)

    assert password_hash.startswith("scrypt:")
    assert PASSWORD not in password_hash


def test_verify_password_accepts_correct_password():
    password_hash = hash_password(PASSWORD)

    assert verify_password(password_hash, PASSWORD) is True


def test_verify_password_rejects_wrong_password():
    password_hash = hash_password(PASSWORD)

    assert verify_password(password_hash, "password-yang-salah") is False


@pytest.mark.parametrize("password_hash", [None, "", "bukan-hash-scrypt"])
def test_verify_password_rejects_missing_or_malformed_hash(password_hash):
    assert verify_password(password_hash, PASSWORD) is False


@pytest.mark.parametrize(
    "config_class,expected_secure",
    [
        (DevelopmentConfig, False),
        (TestingConfig, False),
        (ProductionConfig, True),
    ],
)
def test_session_cookie_flags(config_class, expected_secure):
    assert config_class.SESSION_COOKIE_HTTPONLY is True
    assert config_class.SESSION_COOKIE_SAMESITE == "Lax"
    assert config_class.SESSION_COOKIE_SECURE is expected_secure


def test_production_session_lifetime_is_two_hours():
    assert ProductionConfig.PERMANENT_SESSION_LIFETIME == timedelta(hours=2)


@pytest.mark.parametrize("config_class", [DevelopmentConfig, TestingConfig])
def test_non_production_configs_do_not_force_two_hour_lifetime(config_class):
    assert "PERMANENT_SESSION_LIFETIME" not in config_class.__dict__
