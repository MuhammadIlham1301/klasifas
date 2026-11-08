"""
Application Factory KlasiFas.
Menginisialisasi instance Flask dengan validasi konfigurasi yang aman dan ketat.
"""
from flask import Flask, redirect, url_for
from app.config import get_config_class
from app.extensions import db, migrate, csrf
from app.routes.admin import admin_bp
from app.routes.auth import auth_bp
from app.routes.dashboard import dashboard_bp
from app.routes.report import report_bp
from app.routes.technician import technician_bp
from app.cli import register_cli
from app.utils.error_handlers import register_error_handlers
from app.utils.security_headers import apply_security_headers


def create_app(config_name=None):
    """
    Membuat dan mengonfigurasi instance aplikasi Flask KlasiFas.

    Args:
        config_name (str, optional): Nama mode konfigurasi ('development', 'testing', 'production').
                                     Jika None, membaca variabel lingkungan FLASK_CONFIG.

    Returns:
        Flask: Instance aplikasi Flask yang terkonfigurasi.

    Raises:
        ValueError: Jika nama konfigurasi tidak valid, FLASK_CONFIG tidak disetel,
                    atau validasi keamanan lingkungan (SECRET_KEY/DATABASE_URL) gagal.
    """
    # 1. Resolusi kelas konfigurasi tanpa silent fallback
    config_class = get_config_class(config_name)

    # 2. Inisialisasi instance Flask
    app = Flask(__name__)

    # 3. Muat konfigurasi dari kelas yang valid
    app.config.from_object(config_class)

    # 4. Eksekusi validasi spesifik lingkungan (SECRET_KEY & SQLALCHEMY_DATABASE_URI)
    config_class.init_app(app)

    # 5. Inisialisasi ekstensi inti (lazy binding, tanpa koneksi fisik)
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # 5b. Pasang ProxyFix hanya jika konfigurasi proxy tepercaya aktif (> 0)
    trusted_proxies = app.config.get("TRUSTED_PROXIES_COUNT", 0)
    if isinstance(trusted_proxies, int) and trusted_proxies > 0:
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=trusted_proxies)

    # 6. Registrasi blueprint autentikasi staf, operasional admin, pelaporan publik, teknisi, dan dashboard
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(technician_bp)
    app.register_blueprint(dashboard_bp)

    # 6b. Favicon root: arahkan /favicon.ico ke aset SVG lokal (menghindari 404)
    @app.get("/favicon.ico")
    def favicon():
        return redirect(url_for("static", filename="favicon.svg"), code=308)

    # 6c. Halaman error bernuansa aplikasi (403/404/500) dengan status HTTP tetap
    register_error_handlers(app)

    # 6d. Perintah CLI lokal untuk provisioning akun staf
    register_cli(app)

    # 7. Terapkan header keamanan pada seluruh respons
    app.after_request(apply_security_headers)

    return app

