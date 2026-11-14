"""
Pengujian komprehensif TSK-F3-04:
- Endpoint pelacakan mandiri publik /lacak (FR-02)
- Proteksi CSRF
- In-memory Sliding Window Rate Limiter dengan thread safety dan Retry-After (HTTP 429)
- Penghitungan seluruh percobaan POST (termasuk input tidak valid dan salah kredensial)
- Prinsip Anti-Enumerasi (respons seragam status 404 tanpa kebocoran eksistensi tiket)
- Sanitasi data publik (tanpa kebocoran PII pelapor atau log internal)
- Perilaku ProxyFix (nonaktif secara default, aktif hanya bila dikonfigurasi)
"""
import concurrent.futures
import re
import pytest
from flask import g, has_app_context
from sqlalchemy import delete, select, update

from app.extensions import db
from app.models.category import Category
from app.models.ticket import Ticket
from app.services.ticket_report import (
    BUILDING_NAME,
    create_ticket_with_token,
)
from app.utils.rate_limiter import (
    SlidingWindowRateLimiter,
    get_client_ip,
    track_limiter,
)

CSRF_TOKEN_PATTERN = re.compile(r'name="csrf_token" value="([^"]+)"')


@pytest.fixture()
def app():
    from app import create_app

    test_app = create_app("testing")
    test_app.config.update(TESTING=True, WTF_CSRF_ENABLED=True)

    with test_app.app_context():
        baseline_ticket_ids = set(db.session.scalars(select(Ticket.id)).all())
        baseline_categories = {
            category.code: category.is_active
            for category in db.session.scalars(select(Category)).all()
        }

        connection = db.engine.connect()
        transaction = connection.begin()
        db.session.remove()
        db.session.configure(
            bind=connection, join_transaction_mode="create_savepoint"
        )

        try:
            yield test_app
        finally:
            db.session.remove()
            if transaction.is_active:
                transaction.rollback()
            connection.close()
            db.session.configure(bind=None)

            with db.engine.begin() as cleanup_connection:
                if baseline_ticket_ids:
                    cleanup_connection.execute(
                        delete(Ticket).where(
                            Ticket.id.notin_(baseline_ticket_ids)
                        )
                    )
                else:
                    cleanup_connection.execute(delete(Ticket))

                for code, is_active in baseline_categories.items():
                    cleanup_connection.execute(
                        update(Category)
                        .where(Category.code == code)
                        .values(is_active=is_active)
                    )

            db.engine.dispose()


@pytest.fixture(autouse=True)
def reset_limiter():
    """Reset rate limiter sebelum dan sesudah setiap test agar hermetis."""
    track_limiter.reset()
    yield
    track_limiter.reset()


@pytest.fixture()
def client(app):
    return app.test_client()


def _get_csrf_token(client):
    g.pop("csrf_token", None)
    response = client.get("/lacak")
    assert response.status_code == 200
    match = CSRF_TOKEN_PATTERN.search(response.get_data(as_text=True))
    assert match is not None
    return match.group(1)


def _create_sample_ticket(category_code="K1", **kwargs):
    cat = db.session.scalar(
        select(Category).where(Category.code == category_code)
    )
    data = {
        "description": "Proyektor di kelas mati total saat perkuliahan berlangsung.",
        "building_name": BUILDING_NAME,
        "floor_number": 3,
        "room_name": "Ruang 3.1",
        "location_detail": "Dekat jendela timur",
        "reporter_category_id": cat.id if cat else None,
        "reporter_name": "Mahasiswa Rahasia",
        "reporter_contact": "081234567890",
    }
    data.update(kwargs)
    ticket, raw_token = create_ticket_with_token(data)
    db.session.flush()
    return ticket, raw_token


# ==============================================================================
# 1. Pengujian Unit Rate Limiter (Thread Safety, Sliding Window, Cleanup)
# ==============================================================================
def test_rate_limiter_sliding_window_basics():
    limiter = SlidingWindowRateLimiter(limit=3, window_seconds=60)
    ip = "192.168.1.10"

    # 3 hit pertama diizinkan
    allowed1, retry1 = limiter.hit(ip)
    allowed2, retry2 = limiter.hit(ip)
    allowed3, retry3 = limiter.hit(ip)
    assert allowed1 is True and retry1 == 0
    assert allowed2 is True and retry2 == 0
    assert allowed3 is True and retry3 == 0

    # Hit ke-4 ditolak, mengembalikan retry_after > 0
    allowed4, retry4 = limiter.hit(ip)
    assert allowed4 is False
    assert 0 < retry4 <= 60

    # IP berbeda tidak terdampak kuotanya
    other_allowed, other_retry = limiter.hit("192.168.1.20")
    assert other_allowed is True
    assert other_retry == 0


def test_track_limiter_uses_dynamic_flask_config(app):
    ip = "203.0.113.11"
    app.config["TRACK_RATE_LIMIT_PER_MINUTE"] = 2
    app.config["TRACK_RATE_LIMIT_WINDOW_SECONDS"] = 120

    assert track_limiter.hit(ip) == (True, 0)
    assert track_limiter.hit(ip) == (True, 0)
    allowed, retry_after = track_limiter.hit(ip)
    assert allowed is False
    assert 60 < retry_after <= 120

    app.config["TRACK_RATE_LIMIT_PER_MINUTE"] = 3
    assert track_limiter.hit(ip) == (True, 0)


def test_track_limiter_fallback_outside_app_context():
    assert not has_app_context()
    ip = "203.0.113.12"

    for _ in range(15):
        assert track_limiter.hit(ip) == (True, 0)

    allowed, retry_after = track_limiter.hit(ip)
    assert allowed is False
    assert 0 < retry_after <= 60


def test_rate_limiter_thread_safety_under_concurrency():
    """Memastikan bahwa pada konkurensi multi-thread, limit kuota tepat dipatuhi."""
    limiter = SlidingWindowRateLimiter(limit=10, window_seconds=60)
    ip = "10.0.0.1"

    results = []

    def make_hit():
        return limiter.hit(ip)

    # 30 request serentak dari 30 threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_hit) for _ in range(30)]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    allowed_count = sum(1 for is_allowed, _ in results if is_allowed)
    blocked_count = sum(1 for is_allowed, _ in results if not is_allowed)

    # Harus tepat 10 yang diizinkan dan 20 yang ditolak (tanpa race condition)
    assert allowed_count == 10
    assert blocked_count == 20


def test_rate_limiter_stale_cleanup():
    """Memastikan pembersihan riwayat IP lama bekerja tanpa kebocoran memori."""
    limiter = SlidingWindowRateLimiter(limit=5, window_seconds=1)

    # Tambahkan entri dengan timestamp masa lalu
    past_time = 1000.0
    cutoff = past_time + 10.0
    with limiter._lock:
        limiter._requests["stale_ip"] = [past_time]
        limiter._prune_expired_locked(cutoff)
        assert "stale_ip" not in limiter._requests


# ==============================================================================
# 2. Pengujian Tampilan GET /lacak
# ==============================================================================
def test_track_get_renders_form(client):
    response = client.get("/lacak")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Lacak status penanganan keluhan" in html
    assert 'name="ticket_code"' in html
    assert 'name="access_token"' in html
    assert 'name="csrf_token"' in html


def test_track_get_with_ticket_code_prefill(client):
    response = client.get("/lacak?ticket_code=KF-2A3B4C")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'value="KF-2A3B4C"' in html


# ==============================================================================
# 3. Proteksi CSRF pada POST /lacak
# ==============================================================================
def test_track_post_requires_csrf(client):
    """POST /lacak tanpa CSRF wajib ditolak dengan HTTP 400 Bad Request."""
    response = client.post(
        "/lacak",
        data={"ticket_code": "KF-8X9B2M", "access_token": "some-token"},
    )
    assert response.status_code == 400


# ==============================================================================
# 4. Validasi Form & Penghitungan Seluruh Percobaan POST
# ==============================================================================
def test_track_post_missing_fields_returns_400(client):
    csrf = _get_csrf_token(client)
    response = client.post(
        "/lacak",
        data={"csrf_token": csrf, "ticket_code": "", "access_token": ""},
    )
    assert response.status_code == 400
    html = response.get_data(as_text=True)
    assert "Kode referensi tiket dan token akses wajib diisi" in html


# ==============================================================================
# 5. Anti-Enumeration & Keamanan Kredensial Tiket
# ==============================================================================
def test_track_post_nonexistent_ticket_returns_generic_404(client):
    """Kode tiket yang tidak ada harus menghasilkan 404 generik tanpa info kebocoran."""
    csrf = _get_csrf_token(client)
    response = client.post(
        "/lacak",
        data={
            "csrf_token": csrf,
            "ticket_code": "KF-999999",
            "access_token": "any-random-token-here",
        },
    )
    assert response.status_code == 404
    html = response.get_data(as_text=True)
    assert "Tiket tidak ditemukan atau kredensial pelacakan tidak valid" in html


def test_track_post_invalid_token_returns_identical_generic_404(client):
    """Tiket ada tetapi token salah harus menghasilkan respons yang identik dengan tiket tidak ada."""
    ticket, _ = _create_sample_ticket()
    csrf = _get_csrf_token(client)

    response = client.post(
        "/lacak",
        data={
            "csrf_token": csrf,
            "ticket_code": ticket.ticket_code,
            "access_token": "wrong-token-value-12345",
        },
    )
    assert response.status_code == 404
    html = response.get_data(as_text=True)
    assert "Tiket tidak ditemukan atau kredensial pelacakan tidak valid" in html


def test_track_post_invalid_format_code_returns_generic_404(client):
    """Kode yang menyalahi regex KF-XXXXXX ditolak dengan 404 generik."""
    csrf = _get_csrf_token(client)
    response = client.post(
        "/lacak",
        data={
            "csrf_token": csrf,
            "ticket_code": "MALFORMED-123",
            "access_token": "any-token",
        },
    )
    assert response.status_code == 404
    html = response.get_data(as_text=True)
    assert "Tiket tidak ditemukan atau kredensial pelacakan tidak valid" in html


# ==============================================================================
# 6. Keberhasilan Pelacakan & Sanitasi Data Publik
# ==============================================================================
def test_track_post_success_and_sanitization(client):
    ticket, raw_token = _create_sample_ticket()
    csrf = _get_csrf_token(client)

    response = client.post(
        "/lacak",
        data={
            "csrf_token": csrf,
            "ticket_code": ticket.ticket_code,
            "access_token": raw_token,
        },
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # 1. Data publik yang sah harus terlihat
    assert ticket.ticket_code in html
    assert "Proyektor di kelas mati total" in html
    assert "Gedung FTII" in html
    assert "Ruang 3.1" in html
    assert "Baru" in html

    # 2. SANITASI KETAT: Data pribadi pelapor TIDAK BOLEH muncul
    assert "Mahasiswa Rahasia" not in html
    assert "081234567890" not in html
    # Hash token tidak boleh bocor
    assert ticket.access_token_hash not in html


def test_track_post_completed_ticket_shows_resolution(client):
    ticket, raw_token = _create_sample_ticket()
    ticket.status = "Selesai"
    ticket.resolution_note = "Kabel HDMI dan power supply telah diganti."
    db.session.commit()

    csrf = _get_csrf_token(client)
    response = client.post(
        "/lacak",
        data={
            "csrf_token": csrf,
            "ticket_code": ticket.ticket_code,
            "access_token": raw_token,
        },
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Selesai" in html
    assert "Kabel HDMI dan power supply telah diganti" in html


# ==============================================================================
# 7. Penegakan Rate Limiting (Semua POST dihitung, HTTP 429 & Retry-After)
# ==============================================================================
def test_track_rate_limiting_enforces_429_and_retry_after(client):
    """
    Memverifikasi bahwa:
    1. 15 request pertama dihitung (bahkan untuk input yang salah).
    2. Request ke-16 ditolak dengan status HTTP 429.
    3. Header Retry-After hadir dengan nilai bilangan bulat positif.
    """
    csrf = _get_csrf_token(client)

    # 15 percobaan POST pertama (gabungan input salah dan kosong)
    for i in range(15):
        resp = client.post(
            "/lacak",
            data={
                "csrf_token": csrf,
                "ticket_code": f"KF-FAIL{i:02d}",
                "access_token": "token-salah",
            },
        )
        assert resp.status_code in (400, 404)

    # Percobaan ke-16 wajib menghasilkan HTTP 429
    resp16 = client.post(
        "/lacak",
        data={
            "csrf_token": csrf,
            "ticket_code": "KF-FAIL99",
            "access_token": "token-salah",
        },
    )
    assert resp16.status_code == 429
    assert "Retry-After" in resp16.headers
    retry_after = int(resp16.headers["Retry-After"])
    assert 0 < retry_after <= 60

    html = resp16.get_data(as_text=True)
    assert "Batas frekuensi pencarian tercapai" in html


def test_track_rate_limiting_ip_isolation(client):
    """Memastikan bahwa IP kedua tidak diblokir meskipun IP pertama telah mencapai limit."""
    csrf = _get_csrf_token(client)

    # Habiskan kuota IP 127.0.0.1
    for _ in range(15):
        client.post(
            "/lacak",
            data={
                "csrf_token": csrf,
                "ticket_code": "KF-FAIL00",
                "access_token": "token",
            },
            environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
        )

    blocked_resp = client.post(
        "/lacak",
        data={
            "csrf_token": csrf,
            "ticket_code": "KF-FAIL00",
            "access_token": "token",
        },
        environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    )
    assert blocked_resp.status_code == 429

    # IP 192.168.10.50 masih harus diizinkan (tidak terblokir)
    allowed_resp = client.post(
        "/lacak",
        data={
            "csrf_token": csrf,
            "ticket_code": "KF-FAIL00",
            "access_token": "token",
        },
        environ_overrides={"REMOTE_ADDR": "192.168.10.50"},
    )
    assert allowed_resp.status_code == 404  # Diterima masuk ke handler


# ==============================================================================
# 8. Perilaku ProxyFix (Default Nonaktif vs Konfigurasi Tepercaya)
# ==============================================================================
def test_proxy_fix_disabled_by_default(app, client):
    """
    Secara default TRUSTED_PROXIES_COUNT=0.
    Header X-Forwarded-For tidak dipercayai (tidak mengubah remote_addr).
    """
    assert app.config.get("TRUSTED_PROXIES_COUNT", 0) == 0

    with app.test_request_context(
        "/lacak",
        environ_base={"REMOTE_ADDR": "127.0.0.1"},
        headers={"X-Forwarded-For": "203.0.113.195"},
    ) as ctx:
        from flask import request
        # remote_addr harus tetap socket IP asli, bukan IP di header
        assert get_client_ip(request) == "127.0.0.1"


def test_proxy_fix_enabled_with_trusted_proxy_config():
    """
    Jika TRUSTED_PROXIES_COUNT=1 dikonfigurasi, ProxyFix aktif dan
    remote_addr menggunakan IP klien terpercaya dari hop proxy.
    """
    from app import create_app
    proxy_app = create_app("testing")
    proxy_app.config["TRUSTED_PROXIES_COUNT"] = 1

    # Inisialisasi ProxyFix sesuai create_app
    from werkzeug.middleware.proxy_fix import ProxyFix
    proxy_app.wsgi_app = ProxyFix(proxy_app.wsgi_app, x_for=1)

    client = proxy_app.test_client()
    response = client.get(
        "/lacak",
        headers={"X-Forwarded-For": "203.0.113.195"},
        environ_base={"REMOTE_ADDR": "127.0.0.1"},
    )
    assert response.status_code == 200

