"""Entry point WSGI produksi KlasiFas."""
from app import create_app

app = create_app("production")
