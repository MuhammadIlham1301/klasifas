import importlib
import os
import sys
from datetime import timedelta
from unittest.mock import patch
import pytest
import dotenv


@pytest.fixture(autouse=True)
def isolate_factory_environment(monkeypatch):
    """
    Fixture isolasi hermetik factory:
    1. Mematikan pembacaan disk oleh load_dotenv.
    2. Menyetel PYTHON_DOTENV_DISABLED=true.
    3. Menyetel SECRET_KEY valid secara default untuk pengujian factory.
    4. Menyetel DEV_DATABASE_URL dan TEST_DATABASE_URL sesuai placeholder standar.
    5. Membersihkan FLASK_CONFIG dan DATABASE_URL.
    6. Teardown: membersihkan sys.modules['app.config'] dan sys.modules['app'].
    """
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "true")
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: False)

    # Kunci default 64 hex yang valid untuk pengujian fungsionalitas factory
    valid_key = "0123456789abcdef" * 4
    monkeypatch.setenv("SECRET_KEY", valid_key)

    # Default database placeholders untuk mode development dan testing
    monkeypatch.setenv("DEV_DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/klasifas_dev_db")
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/klasifas_test_db")

    # Pastikan FLASK_CONFIG dan DATABASE_URL bersih
    monkeypatch.delenv("FLASK_CONFIG", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    yield

    # Teardown: pastikan package 'app' dan modul 'app.config' dibersihkan
    if 'app' in sys.modules:
        if hasattr(sys.modules['app'], 'config'):
            delattr(sys.modules['app'], 'config')
        sys.modules.pop('app', None)
    sys.modules.pop('app.config', None)


def get_isolated_factory():
    """
    Helper reload terkoordinasi:
    1. Memuat ulang app.config di bawah kondisi environment terbaru.
    2. Memuat ulang package app sehingga create_app mengikat modul konfigurasi mutakhir.
    3. Mengembalikan modul app bersih tanpa stale configuration.
    """
    import app.config
    importlib.reload(app.config)
    import app
    return importlib.reload(app)


# --- 1. Development Configuration ---
def test_create_app_development():
    factory_mod = get_isolated_factory()
    app = factory_mod.create_app('development')

    assert app.config['DEBUG'] is True
    assert app.config['TESTING'] is False
    assert app.config['SESSION_COOKIE_SECURE'] is False
    # Verifikasi ekstensi terdaftar di app.extensions
    assert 'csrf' in app.extensions
    assert 'sqlalchemy' in app.extensions
    assert 'migrate' in app.extensions


# --- 2. Testing Configuration ---
def test_create_app_testing():
    factory_mod = get_isolated_factory()
    app = factory_mod.create_app('testing')

    assert app.config['TESTING'] is True
    assert app.config['DEBUG'] is False
    assert app.config['WTF_CSRF_ENABLED'] is False
    assert app.config['SESSION_COOKIE_SECURE'] is False


# --- 2b. Testing Configuration: URI Terisolasi Valid ---
def test_create_app_testing_uses_isolated_database_uri():
    factory_mod = get_isolated_factory()
    app = factory_mod.create_app('testing')

    assert app.config['SQLALCHEMY_DATABASE_URI'] == os.environ['TEST_DATABASE_URL']


# --- 2c. Testing Fail-Fast Ketika TEST_DATABASE_URL Tidak Tersedia, Kosong, atau Whitespace ---
@pytest.mark.parametrize("empty_db_url", [None, "", "   ", "\t\n"])
def test_create_app_testing_missing_database_url_fails(monkeypatch, empty_db_url):
    if empty_db_url is not None:
        monkeypatch.setenv("TEST_DATABASE_URL", empty_db_url)
    else:
        monkeypatch.delenv("TEST_DATABASE_URL", raising=False)

    factory_mod = get_isolated_factory()
    with pytest.raises(ValueError, match="Konfigurasi basis data pengujian 'SQLALCHEMY_DATABASE_URI'"):
        factory_mod.create_app('testing')


# --- 2d. Testing Menolak URI yang Sama dengan DEV_DATABASE_URL ---
def test_create_app_testing_rejects_dev_database_url(monkeypatch):
    dev_uri = os.environ["DEV_DATABASE_URL"]
    monkeypatch.setenv("TEST_DATABASE_URL", dev_uri)

    factory_mod = get_isolated_factory()
    with pytest.raises(ValueError, match="tidak boleh sama dengan 'DEV_DATABASE_URL'"):
        factory_mod.create_app('testing')


# --- 2e. Testing Menolak URI yang Sama dengan DATABASE_URL ---
def test_create_app_testing_rejects_production_database_url(monkeypatch):
    test_uri = os.environ["TEST_DATABASE_URL"]
    monkeypatch.setenv("DATABASE_URL", test_uri)

    factory_mod = get_isolated_factory()
    with pytest.raises(ValueError, match="tidak boleh sama dengan 'DATABASE_URL'"):
        factory_mod.create_app('testing')


# --- 2f. Testing Memvalidasi URI Efektif dari app.config ---
def test_create_app_testing_rejects_effective_empty_override(monkeypatch):
    factory_mod = get_isolated_factory()
    import app.config

    monkeypatch.setattr(app.config.TestingConfig, 'SQLALCHEMY_DATABASE_URI', "")

    with pytest.raises(ValueError, match="Konfigurasi basis data pengujian 'SQLALCHEMY_DATABASE_URI'"):
        factory_mod.create_app('testing')


def test_create_app_testing_rejects_effective_override_equal_dev(monkeypatch):
    factory_mod = get_isolated_factory()
    import app.config

    dev_uri = os.environ["DEV_DATABASE_URL"]
    monkeypatch.setattr(app.config.TestingConfig, 'SQLALCHEMY_DATABASE_URI', dev_uri)

    with pytest.raises(ValueError, match="tidak boleh sama dengan 'DEV_DATABASE_URL'"):
        factory_mod.create_app('testing')


# --- 3. Production Configuration dengan DATABASE_URL Valid ---
def test_create_app_production_valid(monkeypatch):
    prod_uri = "postgresql+psycopg2://prod_user:secret_pass@localhost:5432/klasifas_prod_db"
    monkeypatch.setenv("DATABASE_URL", prod_uri)

    factory_mod = get_isolated_factory()
    app = factory_mod.create_app('production')

    assert app.config['DEBUG'] is False
    assert app.config['TESTING'] is False
    assert app.config['SESSION_COOKIE_SECURE'] is True
    assert app.config['SESSION_COOKIE_HTTPONLY'] is True
    assert app.config['SESSION_COOKIE_SAMESITE'] == 'Lax'
    assert app.config['PERMANENT_SESSION_LIFETIME'] == timedelta(hours=2)
    assert app.config['SQLALCHEMY_DATABASE_URI'] == prod_uri


# --- 4. Production Fail-Fast Ketika DATABASE_URL Tidak Tersedia, Kosong, atau Whitespace ---
@pytest.mark.parametrize("empty_db_url", [None, "", "   ", "\t\n"])
def test_create_app_production_missing_database_url_fails(monkeypatch, empty_db_url):
    if empty_db_url is not None:
        monkeypatch.setenv("DATABASE_URL", empty_db_url)
    else:
        monkeypatch.delenv("DATABASE_URL", raising=False)

    factory_mod = get_isolated_factory()
    with pytest.raises(ValueError, match="Konfigurasi basis data produksi 'SQLALCHEMY_DATABASE_URI'"):
        factory_mod.create_app('production')


# --- 5. Resolusi FLASK_CONFIG dari Environment ---
@pytest.mark.parametrize("env_config, expected_debug, expected_testing", [
    ("development", True, False),
    ("testing", False, True),
])
def test_create_app_from_flask_config_env(monkeypatch, env_config, expected_debug, expected_testing):
    monkeypatch.setenv("FLASK_CONFIG", env_config)
    factory_mod = get_isolated_factory()
    app = factory_mod.create_app()

    assert app.config['DEBUG'] is expected_debug
    assert app.config['TESTING'] is expected_testing


# --- 6. Penolakan Konfigurasi Tidak Dikenal dan Tanpa Silent Fallback ---
@pytest.mark.parametrize("unknown_cfg", [
    "prodution",  # Typo umum
    "staging",
    "local",
    "invalid_mode",
])
def test_create_app_unknown_config_fails(unknown_cfg):
    factory_mod = get_isolated_factory()
    with pytest.raises(ValueError, match="tidak valid atau belum disetel"):
        factory_mod.create_app(unknown_cfg)


@pytest.mark.parametrize("empty_flask_config", [None, "", "   ", "\t\n"])
def test_create_app_no_silent_fallback(monkeypatch, empty_flask_config):
    if empty_flask_config is not None:
        monkeypatch.setenv("FLASK_CONFIG", empty_flask_config)
    else:
        monkeypatch.delenv("FLASK_CONFIG", raising=False)

    factory_mod = get_isolated_factory()
    with pytest.raises(ValueError, match="Silent fallback dilarang"):
        factory_mod.create_app()


# --- 7. Fail-Fast SECRET_KEY Tidak Valid pada Runtime Factory ---
@pytest.mark.parametrize("invalid_secret", [
    None,
    "",
    "short-key",
    "0123456789abcdef" * 3 + "0123456789abcdeg",  # Karakter 'g' non-hex
])
def test_create_app_invalid_secret_key_fails(monkeypatch, invalid_secret):
    if invalid_secret is not None:
        monkeypatch.setenv("SECRET_KEY", invalid_secret)
    else:
        monkeypatch.delenv("SECRET_KEY", raising=False)

    factory_mod = get_isolated_factory()
    with pytest.raises(ValueError) as exc_info:
        factory_mod.create_app('testing')

    assert "CRITICAL:" in str(exc_info.value)
    if invalid_secret:
        assert invalid_secret not in str(exc_info.value)


# --- 8. Class-Level Override ProductionConfig ---
def test_create_app_production_class_override(monkeypatch):
    factory_mod = get_isolated_factory()
    import app.config

    override_uri = "postgresql+psycopg2://override_user:pass@localhost:5432/override_db"
    monkeypatch.setattr(app.config.ProductionConfig, 'SQLALCHEMY_DATABASE_URI', override_uri)

    app = factory_mod.create_app('production')
    assert app.config['SQLALCHEMY_DATABASE_URI'] == override_uri


# --- 9. Reload Konfigurasi Mencegah Stale Configuration ---
def test_configuration_reload_prevents_stale_config(monkeypatch):
    # Tahap A: Set URI Pertama
    uri_alpha = "postgresql+psycopg2://user_a:pass@localhost:5432/db_alpha"
    monkeypatch.setenv("DATABASE_URL", uri_alpha)
    factory_a = get_isolated_factory()
    app_a = factory_a.create_app('production')
    assert app_a.config['SQLALCHEMY_DATABASE_URI'] == uri_alpha

    # Tahap B: Ganti dengan URI Kedua (harus ter-update, bukan menggunakan URI_A lama)
    uri_beta = "postgresql+psycopg2://user_b:pass@localhost:5432/db_beta"
    monkeypatch.setenv("DATABASE_URL", uri_beta)
    factory_b = get_isolated_factory()
    app_b = factory_b.create_app('production')
    assert app_b.config['SQLALCHEMY_DATABASE_URI'] == uri_beta

    # Tahap C: Hapus DATABASE_URL (harus fail-fast, bukan mempertahankan URI_B)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    factory_c = get_isolated_factory()
    with pytest.raises(ValueError, match="Konfigurasi basis data produksi 'SQLALCHEMY_DATABASE_URI'"):
        factory_c.create_app('production')


# --- 10. Verifikasi Zero Physical Connection ke PostgreSQL ---
def test_create_app_zero_physical_database_connection(monkeypatch):
    """
    Memverifikasi secara ketat bahwa psycopg2.connect TIDAK PERNAH dipanggil
    selama eksekusi create_app() (lazy binding).
    """
    prod_uri = "postgresql+psycopg2://dummy_user:dummy_pass@localhost:5432/dummy_db"
    monkeypatch.setenv("DATABASE_URL", prod_uri)

    factory_mod = get_isolated_factory()

    with patch("psycopg2.connect") as mock_psycopg2_connect:
        app = factory_mod.create_app('production')

        # Membuktikan psycopg2.connect sama sekali tidak dipanggil
        assert mock_psycopg2_connect.call_count == 0, (
            "psycopg2.connect terpanggil selama create_app! Koneksi database wajib bersifat lazy."
        )
        assert app is not None
