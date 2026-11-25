"""Konfigurasi Gunicorn produksi KlasiFas.

Gunicorn hanya mendengarkan loopback; Nginx menjadi satu-satunya pintu masuk
publik dan meneruskan header proxy tepercaya.
"""
import multiprocessing
import os

bind = "127.0.0.1:8000"
workers = int(
    os.environ.get(
        "GUNICORN_WORKERS",
        min(4, (multiprocessing.cpu_count() or 1) * 2 + 1),
    )
)
worker_class = "sync"
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "30"))
graceful_timeout = 30
keepalive = 5

max_requests = 1000
max_requests_jitter = 100
preload_app = False

forwarded_allow_ips = "127.0.0.1"
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
proc_name = "klasifas"
umask = 0o027
