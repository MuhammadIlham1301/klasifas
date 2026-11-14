import math
import os
import re
from datetime import timedelta
from dotenv import load_dotenv

# Pemuatan .env hanya jika tidak dinonaktifkan oleh environment pengujian
if os.environ.get('PYTHON_DOTENV_DISABLED', '').lower() != 'true':
    load_dotenv()

# Pola regex ketat: tepat 64 karakter heksadesimal tanpa spasi/whitespace
SECRET_KEY_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


def _env_number(name: str, default: str, converter):
    raw = os.environ.get(name, default)
    try:
        return converter(raw)
    except (TypeError, ValueError):
        return raw


class Config:
    """Konfigurasi dasar umum (Base Configuration)."""
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_PHOTO_SIZE_BYTES = 3 * 1024 * 1024
    MAX_PHOTO_DIMENSION = 6000
    MAX_CONTENT_LENGTH = MAX_PHOTO_SIZE_BYTES + (1024 * 1024)
    PHOTO_ALLOWED_EXTENSIONS = frozenset({'jpg', 'jpeg', 'png'})
    PHOTO_ALLOWED_MIME_TYPES = frozenset({'image/jpeg', 'image/png'})
    ML_MODEL_PATH = os.path.join(BASE_DIR, 'app', 'ml', 'models', 'model.joblib')
    ML_VECTORIZER_PATH = os.path.join(BASE_DIR, 'app', 'ml', 'models', 'vectorizer.joblib')
    ML_CONFIDENCE_THRESHOLD = _env_number('ML_CONFIDENCE_THRESHOLD', '0.60', float)
    TRUSTED_PROXIES_COUNT = _env_number('TRUSTED_PROXIES_COUNT', '0', int)
    TRACK_RATE_LIMIT_PER_MINUTE = _env_number('TRACK_RATE_LIMIT_PER_MINUTE', '15', int)
    TRACK_RATE_LIMIT_WINDOW_SECONDS = _env_number('TRACK_RATE_LIMIT_WINDOW_SECONDS', '60', int)

    @classmethod
    def init_app(cls, app=None):
        """
        Validasi fail-fast konfigurasi dasar.
        Memeriksa nilai konfigurasi efektif yang digunakan Flask tanpa silent fallback.
        """
        if app is not None and 'SECRET_KEY' in app.config:
            effective_secret = app.config.get('SECRET_KEY')
        elif cls.SECRET_KEY is not None:
            effective_secret = cls.SECRET_KEY
        else:
            effective_secret = os.environ.get('SECRET_KEY')

        if not effective_secret:
            raise ValueError(
                "CRITICAL: Konfigurasi 'SECRET_KEY' belum disetel. "
                "Aplikasi dihentikan demi keamanan sesi."
            )

        if not isinstance(effective_secret, str) or not SECRET_KEY_PATTERN.fullmatch(effective_secret):
            raise ValueError(
                "CRITICAL: Nilai 'SECRET_KEY' tidak memenuhi format valid "
                "(wajib tepat 64 karakter heksadesimal tanpa spasi/whitespace). "
                "Aplikasi dihentikan demi keamanan sesi."
            )

        cls._validate_numeric_config(app)

    @classmethod
    def _effective_config_value(cls, app, key):
        if app is not None and key in app.config:
            return app.config.get(key)
        return getattr(cls, key, None)

    @classmethod
    def _validate_numeric_config(cls, app=None):
        threshold = cls._effective_config_value(app, 'ML_CONFIDENCE_THRESHOLD')
        if (
            isinstance(threshold, bool)
            or not isinstance(threshold, (int, float))
            or not math.isfinite(threshold)
            or not 0.0 <= threshold <= 1.0
        ):
            raise ValueError(
                "CRITICAL: Konfigurasi 'ML_CONFIDENCE_THRESHOLD' harus berupa "
                "angka finite pada rentang 0.0-1.0."
            )

        trusted_proxies = cls._effective_config_value(app, 'TRUSTED_PROXIES_COUNT')
        if (
            isinstance(trusted_proxies, bool)
            or not isinstance(trusted_proxies, int)
            or trusted_proxies < 0
        ):
            raise ValueError(
                "CRITICAL: Konfigurasi 'TRUSTED_PROXIES_COUNT' harus berupa "
                "integer tidak negatif."
            )

        for key in ('TRACK_RATE_LIMIT_PER_MINUTE', 'TRACK_RATE_LIMIT_WINDOW_SECONDS'):
            value = cls._effective_config_value(app, key)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(
                    f"CRITICAL: Konfigurasi '{key}' harus berupa integer minimal 1."
                )


class DevelopmentConfig(Config):
    """Konfigurasi khusus lingkungan pengembangan lokal."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL')
    SESSION_COOKIE_SECURE = False

    @classmethod
    def init_app(cls, app=None):
        """
        Validasi ketat khusus lingkungan pengembangan (Fail-Fast).
        Memeriksa nilai konfigurasi efektif yang benar-benar digunakan Flask
        (app.config['SQLALCHEMY_DATABASE_URI']) tanpa memicu koneksi database.
        """
        super().init_app(app)

        if app is not None and 'SQLALCHEMY_DATABASE_URI' in app.config:
            effective_db_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
        elif cls.SQLALCHEMY_DATABASE_URI is not None:
            effective_db_uri = cls.SQLALCHEMY_DATABASE_URI
        else:
            effective_db_uri = os.environ.get('DEV_DATABASE_URL')

        if not effective_db_uri or not str(effective_db_uri).strip():
            raise ValueError(
                "CRITICAL: Konfigurasi basis data development 'SQLALCHEMY_DATABASE_URI' "
                "(variabel lingkungan 'DEV_DATABASE_URL') wajib disetel saat menggunakan DevelopmentConfig. "
                "Aplikasi dihentikan karena basis data development tidak terdefinisi."
            )


class TestingConfig(Config):
    """Konfigurasi khusus pengujian otomatis (pytest)."""
    TESTING = True
    DEBUG = False
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL')
    SESSION_COOKIE_SECURE = False

    @classmethod
    def init_app(cls, app=None):
        """
        Validasi ketat khusus lingkungan pengujian (Fail-Fast).
        Memeriksa nilai konfigurasi efektif yang benar-benar digunakan Flask
        (app.config['SQLALCHEMY_DATABASE_URI']) tanpa memicu koneksi database.
        """
        super().init_app(app)

        if app is not None and 'SQLALCHEMY_DATABASE_URI' in app.config:
            effective_db_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
        elif cls.SQLALCHEMY_DATABASE_URI is not None:
            effective_db_uri = cls.SQLALCHEMY_DATABASE_URI
        else:
            effective_db_uri = os.environ.get('TEST_DATABASE_URL')

        if not effective_db_uri or not str(effective_db_uri).strip():
            raise ValueError(
                "CRITICAL: Konfigurasi basis data pengujian 'SQLALCHEMY_DATABASE_URI' "
                "(variabel lingkungan 'TEST_DATABASE_URL') wajib disetel saat menggunakan TestingConfig. "
                "Aplikasi dihentikan karena basis data pengujian tidak terdefinisi."
            )

        normalized_test_uri = str(effective_db_uri).strip()
        for env_var_name in ('DEV_DATABASE_URL', 'DATABASE_URL'):
            other_uri = os.environ.get(env_var_name)
            if other_uri and str(other_uri).strip() == normalized_test_uri:
                raise ValueError(
                    f"CRITICAL: URI basis data pengujian tidak boleh sama dengan "
                    f"'{env_var_name}'. TestingConfig wajib menggunakan basis data terpisah. "
                    f"Aplikasi dihentikan demi isolasi data pengujian."
                )


class ProductionConfig(Config):
    """Konfigurasi khusus lingkungan produksi resmi."""
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SESSION_COOKIE_SECURE = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

    @classmethod
    def init_app(cls, app=None):
        """
        Validasi ketat khusus lingkungan produksi (Fail-Fast).
        Memeriksa nilai konfigurasi efektif yang benar-benar digunakan Flask
        (app.config['SQLALCHEMY_DATABASE_URI']) tanpa memicu koneksi database.
        """
        super().init_app(app)

        if app is not None and 'SQLALCHEMY_DATABASE_URI' in app.config:
            effective_db_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
        elif cls.SQLALCHEMY_DATABASE_URI is not None:
            effective_db_uri = cls.SQLALCHEMY_DATABASE_URI
        else:
            effective_db_uri = os.environ.get('DATABASE_URL')

        if not effective_db_uri or not str(effective_db_uri).strip():
            raise ValueError(
                "CRITICAL: Konfigurasi basis data produksi 'SQLALCHEMY_DATABASE_URI' "
                "(variabel lingkungan 'DATABASE_URL') wajib disetel saat menggunakan ProductionConfig. "
                "Aplikasi dihentikan karena basis data produksi tidak terdefinisi."
            )


config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig
}


def get_config_class(config_name=None):
    """
    Mengambil kelas konfigurasi dengan validasi fail-fast tanpa silent fallback.
    Konsisten dengan acceptance criteria TSK-F1-03.
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG')

    if not config_name or config_name not in config_by_name:
        valid_keys = ', '.join([f"'{k}'" for k in config_by_name.keys()])
        raise ValueError(
            f"CRITICAL: Lingkungan konfigurasi '{config_name}' tidak valid atau belum disetel. "
            f"Pilihan valid adalah: {valid_keys}. Silent fallback dilarang demi keamanan."
        )

    return config_by_name[config_name]

