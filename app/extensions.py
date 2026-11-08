"""
Inisialisasi ekstensi Flask terpusat untuk proyek KlasiFas.
Pemisahan file ini mencegah circular dependency antar modul.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

# Pola unattached extension (diikat ke app di create_app)
db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
