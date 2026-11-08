import os
import re
from datetime import timedelta
from dotenv import load_dotenv

# Pemuatan .env hanya jika tidak dinonaktifkan oleh environment pengujian
if os.environ.get('PYTHON_DOTENV_DISABLED', '').lower() != 'true':
    load_dotenv()

# Pola regex ketat: tepat 64 karakter heksadesimal tanpa spasi/whitespace
SECRET_KEY_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


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
    ML_CONFIDENCE_THRESHOLD = float(os.environ.get('ML_CONFIDENCE_THRESHOLD', '0.60'))
    TRUSTED_PROXIES_COUNT = int(os.environ.get('TRUSTED_PROXIES_COUNT', '0'))
    TRACK_RATE_LIMIT_PER_MINUTE = int(os.environ.get('TRACK_RATE_LIMIT_PER_MINUTE', '15'))
    TRACK_RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get('TRACK_RATE_LIMIT_WINDOW_SECONDS', '60'))

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


class DevelopmentConfig(Config):
    """Konfigurasi khusus lingkungan pengembangan lokal."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL')
    SESSION_COOKIE_SECURE = False


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

