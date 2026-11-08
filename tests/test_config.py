import importlib
import os
import re
import subprocess
import sys
import pytest
import dotenv


@pytest.fixture(autouse=True)
def isolate_environment(monkeypatch):
    """
    Fixture isolasi hermetik:
    1. Mematikan pembacaan disk oleh load_dotenv.
    2. Menyetel PYTHON_DOTENV_DISABLED=true.
    3. Membersihkan environment dari variabel sebelumnya.
    4. Teardown: membersihkan sys.modules['app.config'] dan atribut package 'app'.
    """
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "true")
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: False)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("FLASK_CONFIG", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DEV_DATABASE_URL", raising=False)
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)

    yield

    # Teardown: pastikan tidak ada state modul atau mock yang tertinggal
    if 'app' in sys.modules:
        if hasattr(sys.modules['app'], 'config'):
            delattr(sys.modules['app'], 'config')
        sys.modules.pop('app', None)
    sys.modules.pop('app.config', None)


def get_isolated_config():
    """Helper untuk memuat modul app.config di bawah lingkungan monkeypatch aktif."""
    import app.config
    return importlib.reload(app.config)


# --- Skenario 1: Penolakan None, Kosong, dan Whitespace Tanpa Strip ---
@pytest.mark.parametrize("invalid_secret", [
    None,
    "",
    "   ",
    "\t\n",
    " " + ("0123456789abcdef" * 4),   # 64 hex diawali spasi
    ("0123456789abcdef" * 4) + " ",   # 64 hex diakhiri spasi
    ("0123456789abcdef" * 2) + "  " + ("0123456789abcdef" * 2),  # spasi di tengah
])
def test_secret_key_empty_or_whitespace_fails(monkeypatch, invalid_secret):
    if invalid_secret is not None:
        monkeypatch.setenv("SECRET_KEY", invalid_secret)
    else:
        monkeypatch.delenv("SECRET_KEY", raising=False)

    cfg = get_isolated_config()
    with pytest.raises(ValueError) as exc_info:
        cfg.Config.init_app()

    err_msg = str(exc_info.value)
    assert "CRITICAL:" in err_msg
    if invalid_secret:
        assert invalid_secret not in err_msg


# --- Skenario 2: Penolakan Panjang Bukan Tepat 64 Karakter Hex ---
@pytest.mark.parametrize("invalid_length", [
    "a" * 32,      # 32 karakter
    "a" * 63,      # 63 karakter
    "a" * 65,      # 65 karakter
    "short-secret"
])
def test_secret_key_invalid_length_fails(monkeypatch, invalid_length):
    monkeypatch.setenv("SECRET_KEY", invalid_length)
    cfg = get_isolated_config()
    with pytest.raises(ValueError, match="wajib tepat 64 karakter heksadesimal"):
        cfg.Config.init_app()


# --- Skenario 3: Penolakan Karakter Non-Hexadecimal ---
def test_secret_key_non_hex_fails(monkeypatch):
    non_hex_secret = ("0123456789abcdef" * 3) + "0123456789abcdeg"  # 'g' bukan hex
    monkeypatch.setenv("SECRET_KEY", non_hex_secret)
    cfg = get_isolated_config()
    with pytest.raises(ValueError, match="wajib tepat 64 karakter heksadesimal"):
        cfg.Config.init_app()


# --- Skenario 4: Token Valid 64 Karakter Hex Lolos ---
@pytest.mark.parametrize("valid_secret", [
    "0123456789abcdef" * 4,
    "0123456789ABCDEF" * 4,
    "0a1B2c3D4e5F6a7B8c9D0e1F2a3B4c5D6e7F8a9B0c1D2e3F4a5B6c7D8e9F0a1B"
])
def test_secret_key_valid_passes(monkeypatch, valid_secret):
    monkeypatch.setenv("SECRET_KEY", valid_secret)
    cfg = get_isolated_config()
    cfg.Config.init_app()  # Tidak melempar exception


# --- Skenario 5: Konsistensi Konfigurasi Efektif (cls.SECRET_KEY vs app.config) ---
def test_effective_config_validation(monkeypatch):
    valid_secret = "0123456789abcdef" * 4
    monkeypatch.setenv("SECRET_KEY", valid_secret)
    cfg = get_isolated_config()

    class MockFlask:
        def __init__(self):
            self.config = {'SECRET_KEY': valid_secret}

    mock_app = MockFlask()
    cfg.Config.init_app(mock_app)  # Lolos

    # Jika app.config memiliki nilai yang tidak valid meskipun os.environ valid
    mock_app.config['SECRET_KEY'] = 'invalid_in_app_config'
    with pytest.raises(ValueError, match="wajib tepat 64 karakter heksadesimal"):
        cfg.Config.init_app(mock_app)


# --- Skenario 6: Eliminasi Silent Fallback FLASK_CONFIG ---
@pytest.mark.parametrize("invalid_cfg", [None, "", "   ", "prodution", "staging"])
def test_no_silent_fallback(monkeypatch, invalid_cfg):
    if invalid_cfg is not None:
        monkeypatch.setenv("FLASK_CONFIG", invalid_cfg)
    else:
        monkeypatch.delenv("FLASK_CONFIG", raising=False)

    cfg = get_isolated_config()
    with pytest.raises(ValueError, match="Silent fallback dilarang"):
        cfg.get_config_class()


def test_flask_config_valid_resolution(monkeypatch):
    cfg = get_isolated_config()
    assert cfg.get_config_class('development') == cfg.DevelopmentConfig
    assert cfg.get_config_class('testing') == cfg.TestingConfig
    assert cfg.get_config_class('production') == cfg.ProductionConfig


# --- Skenario 7: Validasi Nilai Efektif ProductionConfig SQLALCHEMY_DATABASE_URI ---
def test_production_database_uri_validation(monkeypatch):
    valid_secret = "0123456789abcdef" * 4
    monkeypatch.setenv("SECRET_KEY", valid_secret)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    cfg = get_isolated_config()

    class MockFlask:
        def __init__(self, db_uri=None):
            self.config = {'SECRET_KEY': valid_secret}
            if db_uri is not None:
                self.config['SQLALCHEMY_DATABASE_URI'] = db_uri

    # 1. Tanpa DATABASE_URL dan tanpa app.config['SQLALCHEMY_DATABASE_URI'] -> ValueError
    mock_app_empty = MockFlask()
    with pytest.raises(ValueError, match="Konfigurasi basis data produksi 'SQLALCHEMY_DATABASE_URI'"):
        cfg.ProductionConfig.init_app(mock_app_empty)

    # 2. Standalone tanpa DATABASE_URL -> ValueError
    with pytest.raises(ValueError, match="Konfigurasi basis data produksi 'SQLALCHEMY_DATABASE_URI'"):
        cfg.ProductionConfig.init_app()

    # 3. app.config['SQLALCHEMY_DATABASE_URI'] terisi -> Lolos tanpa koneksi ke DB
    mock_app_valid = MockFlask(db_uri="postgresql+psycopg2://user:pass@localhost:5432/prod_db")
    cfg.ProductionConfig.init_app(mock_app_valid)

    # 4. app.config['SQLALCHEMY_DATABASE_URI'] bernilai kosong padahal os.environ terisi -> Tetap ditolak (prioritas efektif)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://user:pass@localhost:5432/env_db")
    mock_app_override_empty = MockFlask(db_uri="")
    with pytest.raises(ValueError, match="Konfigurasi basis data produksi 'SQLALCHEMY_DATABASE_URI'"):
        cfg.ProductionConfig.init_app(mock_app_override_empty)


# --- Skenario 8: Isolasi Subprocess Mandiri (Hermetik dari .env fisik) ---
def test_subprocess_isolation_fail_fast():
    sub_env = os.environ.copy()
    sub_env['PYTHON_DOTENV_DISABLED'] = 'true'
    sub_env.pop('SECRET_KEY', None)

    code = (
        "from app.config import Config;"
        "Config.init_app()"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=sub_env,
        capture_output=True,
        text=True
    )
    assert result.returncode != 0
    assert "CRITICAL: Konfigurasi 'SECRET_KEY' belum disetel" in result.stderr


# --- Skenario 9: Pemeriksaan Keberadaan Berkas dan Proteksi Secret ---
def test_configuration_files_and_git_protection():
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    env_example_path = os.path.join(base_dir, ".env.example")
    env_path = os.path.join(base_dir, ".env")
    gitignore_path = os.path.join(base_dir, ".gitignore")

    # 1. Pastikan .env dan .env.example ada di disk
    assert os.path.isfile(env_example_path), ".env.example wajib ada di root proyek"
    assert os.path.isfile(env_path), ".env wajib ada di root proyek"
    assert os.path.isfile(gitignore_path), ".gitignore wajib ada di root proyek"

    # 2. Pastikan .env.example tidak memuat secret nyata
    with open(env_example_path, "r", encoding="utf-8") as f:
        example_content = f.read()
    assert re.search(r"^SECRET_KEY=\s*$", example_content, re.MULTILINE), (
        "SECRET_KEY pada .env.example wajib kosong!"
    )

    # 3. Pastikan .gitignore memuat aturan proteksi .env
    with open(gitignore_path, "r", encoding="utf-8") as f:
        gitignore_content = f.read()
    assert ".env" in gitignore_content
    assert "!.env.example" in gitignore_content

