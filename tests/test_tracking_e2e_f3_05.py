"""
Pengujian Integrasi End-to-End TSK-F3-05:
Alur Konfirmasi Pelaporan dan Pelacakan Mandiri Publik (FR-01, FR-02).

Mencakup 6 Skenario E2E:
1. E2E-01: Happy Path: Siklus lengkap submit laporan hingga pelacakan tiket berhasil.
2. E2E-02: Kerahasiaan Token: Cache-Control, isolasi session, isolasi log/URL.
3. E2E-03: Siklus Hidup Tiket: Pembaruan status ke 'Selesai' dan catatan tindakan.
4. E2E-04: Anti-Enumeration: Respons identik 404 pada kode/token salah vs fiktif.
5. E2E-05: Penegakan Rate Limiting (15 req/menit per IP, HTTP 429, Retry-After).
6. E2E-06: Proteksi Rute /lapor/sukses: Redirect aman ke formulir pelaporan.
"""
from datetime import datetime, timezone
import hashlib
import re

import pytest
from flask import g
from sqlalchemy import delete, select, update

from app.extensions import db
from app.models.category import Category
from app.models.ticket import Ticket
from app.services.ticket_report import BUILDING_NAME
from app.utils.rate_limiter import track_limiter

CSRF_TOKEN_PATTERN = re.compile(r'name="csrf_token" value="([^"]+)"')
TICKET_CODE_HTML_PATTERN = re.compile(
    r'<div class="fs-3 fw-semibold font-monospace">\s*([^\s<]+)\s*</div>'
)
ACCESS_TOKEN_HTML_PATTERN = re.compile(
    r'<div class="fs-5 fw-semibold font-monospace text-break">\s*([^\s<]+)\s*</div>'
)


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
def reset_rate_limiter():
    """Reset state rate limiter in-memory sebelum dan sesudah tiap test."""
    track_limiter.reset()
    yield
    track_limiter.reset()


@pytest.fixture()
def client(app):
    return app.test_client()


def _get_csrf_token(client, path="/lapor"):
    g.pop("csrf_token", None)
    response = client.get(path)
    assert response.status_code == 200
    match = CSRF_TOKEN_PATTERN.search(response.get_data(as_text=True))
    assert match is not None
    return match.group(1)


def _submit_valid_report(client, **overrides):
    """Helper untuk mensimulasikan pelapor mengirimkan keluhan di /lapor."""
    csrf = _get_csrf_token(client, "/lapor")
    payload = {
        "csrf_token": csrf,
        "description": "Lampu LED di laboratorium komputer berkedip dan mati.",
        "building_name": BUILDING_NAME,
        "floor_number": "2",
        "room_name": "Lab Jaringan 2.4",
        "location_detail": "Baris komputer sebelah barat",
        "reporter_category_id": "",
        "reporter_name": "Siti Mahasiswa",
        "reporter_contact": "081299887766",
    }
    payload.update(overrides)

    response = client.post("/lapor", data=payload)
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    code_match = TICKET_CODE_HTML_PATTERN.search(html)
    token_match = ACCESS_TOKEN_HTML_PATTERN.search(html)
    assert code_match is not None, "Kode tiket harus dirender pada success.html"
    assert token_match is not None, "Token akses harus dirender pada success.html"

    ticket_code = code_match.group(1).strip()
    access_token = token_match.group(1).strip()
    return ticket_code, access_token, response


# ==============================================================================
# Skenario E2E-01: Happy Path Siklus Lengkap (Submit Laporan -> Lacak Tiket)
# ==============================================================================
def test_e2e_01_full_report_to_tracking_happy_path(client):
    # 1. Pelapor mengisi dan mengirim laporan
    ticket_code, access_token, post_resp = _submit_valid_report(
        client,
        description="Saklar stop kontak di Ruang 3.2 longgar dan menimbulkan percikan api.",
        floor_number="3",
        room_name="Ruang 3.2",
    )
    assert re.match(r"^KF-[23456789A-HJ-NP-Z]{6}$", ticket_code)
    assert len(access_token) >= 20

    # 2. Pelapor menekan tombol navigasi "Lacak tiket sekarang"
    track_get_resp = client.get(f"/lacak?ticket_code={ticket_code}")
    assert track_get_resp.status_code == 200
    track_get_html = track_get_resp.get_data(as_text=True)

    # Pastikan kode tiket ter-prefill pada form, namun token rahasia TIDAK ada
    assert f'value="{ticket_code}"' in track_get_html
    assert access_token not in track_get_html

    # 3. Pelapor memasukkan token akses dan mengirim formulir pelacakan
    csrf_track = _get_csrf_token(client, "/lacak")
    track_post_resp = client.post(
        "/lacak",
        data={
            "csrf_token": csrf_track,
            "ticket_code": ticket_code,
            "access_token": access_token,
        },
    )
    assert track_post_resp.status_code == 200
    track_post_html = track_post_resp.get_data(as_text=True)

    # 4. Verifikasi data publik tampil secara lengkap
    assert ticket_code in track_post_html
    assert "Ruang 3.2" in track_post_html
    assert "Saklar stop kontak di Ruang 3.2 longgar" in track_post_html
    assert "Baru" in track_post_html

    # 5. Verifikasi privasi pelapor (PII tidak bocor ke halaman publik)
    assert "Siti Mahasiswa" not in track_post_html
    assert "081299887766" not in track_post_html


# ==============================================================================
# Skenario E2E-02: Kerahasiaan Token, Header Cache-Control, dan Isolasi Sesi
# ==============================================================================
def test_e2e_02_token_security_and_storage_isolation(client):
    ticket_code, access_token, post_resp = _submit_valid_report(client)

    # 1. Pastikan header Cache-Control: no-store terpasang ketat
    assert post_resp.headers.get("Cache-Control") == "no-store"

    # 2. Pastikan token tidak disimpan pada cookie atau session
    with client.session_transaction() as sess:
        assert access_token not in str(dict(sess))
        assert "access_token" not in sess

    # 3. Pastikan token tidak bocor di header response apa pun
    for header_name, header_val in post_resp.headers:
        assert access_token not in header_val

    # 4. Pastikan di database hanya hash SHA-256 yang tersimpan
    ticket = db.session.scalar(
        select(Ticket).where(Ticket.ticket_code == ticket_code)
    )
    assert ticket is not None
    assert ticket.access_token_hash == hashlib.sha256(
        access_token.encode("utf-8")
    ).hexdigest()
    assert access_token not in str(ticket.__dict__)


# ==============================================================================
# Skenario E2E-03: Siklus Hidup Status Tiket ke Selesai & Catatan Tindakan
# ==============================================================================
def test_e2e_03_status_lifecycle_to_completed_with_resolution_note(client):
    ticket_code, access_token, _ = _submit_valid_report(client)

    # Cek awal: status masih Baru, belum ada catatan penyelesaian
    csrf = _get_csrf_token(client, "/lacak")
    r1 = client.post(
        "/lacak",
        data={
            "csrf_token": csrf,
            "ticket_code": ticket_code,
            "access_token": access_token,
        },
    )
    assert r1.status_code == 200
    assert "Baru" in r1.get_data(as_text=True)
    assert "Catatan Tindakan" not in r1.get_data(as_text=True)

    # Simulasi mutasi status oleh teknisi menjadi 'Selesai'
    ticket = db.session.scalar(
        select(Ticket).where(Ticket.ticket_code == ticket_code)
    )
    ticket.status = "Selesai"
    ticket.resolution_note = "MCB telah diganti baru dan instalasi diuji aman."
    ticket.resolved_at = datetime.now(timezone.utc)
    db.session.commit()

    # Pelapor melakukan pelacakan ulang
    csrf2 = _get_csrf_token(client, "/lacak")
    r2 = client.post(
        "/lacak",
        data={
            "csrf_token": csrf2,
            "ticket_code": ticket_code,
            "access_token": access_token,
        },
    )
    assert r2.status_code == 200
    html2 = r2.get_data(as_text=True)
    assert "Selesai" in html2
    assert "Catatan Tindakan" in html2
    assert "MCB telah diganti baru dan instalasi diuji aman" in html2


# ==============================================================================
# Skenario E2E-04: Prinsip Anti-Enumeration & Keamanan Kredensial Salah
# ==============================================================================
def test_e2e_04_anti_enumeration_and_invalid_credentials(client):
    ticket_code, access_token, _ = _submit_valid_report(client)
    csrf = _get_csrf_token(client, "/lacak")

    expected_generic_error = (
        "Tiket tidak ditemukan atau kredensial pelacakan tidak valid."
    )

    # 1. Tiket ada, token salah
    resp_wrong_token = client.post(
        "/lacak",
        data={
            "csrf_token": csrf,
            "ticket_code": ticket_code,
            "access_token": "token-palsu-1234567890",
        },
    )
    assert resp_wrong_token.status_code == 404
    assert expected_generic_error in resp_wrong_token.get_data(as_text=True)

    # 2. Tiket fiktif/tidak ada, token ada
    resp_fake_ticket = client.post(
        "/lacak",
        data={
            "csrf_token": csrf,
            "ticket_code": "KF-999999",
            "access_token": access_token,
        },
    )
    assert resp_fake_ticket.status_code == 404
    assert expected_generic_error in resp_fake_ticket.get_data(as_text=True)

    # 3. Format tiket tidak valid (misal sembarang teks)
    resp_invalid_format = client.post(
        "/lacak",
        data={
            "csrf_token": csrf,
            "ticket_code": "INVALID-FORMAT",
            "access_token": "random",
        },
    )
    assert resp_invalid_format.status_code == 404
    assert expected_generic_error in resp_invalid_format.get_data(as_text=True)


# ==============================================================================
# Skenario E2E-05: Penegakan Rate Limiting pada Alur Pelacakan (HTTP 429)
# ==============================================================================
def test_e2e_05_tracking_rate_limiting_enforcement(client):
    ticket_code, access_token, _ = _submit_valid_report(client)
    csrf = _get_csrf_token(client, "/lacak")

    # Kirim 15 request pertama (habiskan kuota rate limit 15 req/menit)
    for _ in range(15):
        resp = client.post(
            "/lacak",
            data={
                "csrf_token": csrf,
                "ticket_code": ticket_code,
                "access_token": "dummy-token",
            },
            environ_overrides={"REMOTE_ADDR": "192.168.1.50"},
        )
        assert resp.status_code == 404

    # Request ke-16 wajib menghasilkan HTTP 429 Too Many Requests
    blocked_resp = client.post(
        "/lacak",
        data={
            "csrf_token": csrf,
            "ticket_code": ticket_code,
            "access_token": access_token,
        },
        environ_overrides={"REMOTE_ADDR": "192.168.1.50"},
    )
    assert blocked_resp.status_code == 429
    assert "Retry-After" in blocked_resp.headers
    retry_after = int(blocked_resp.headers["Retry-After"])
    assert 0 < retry_after <= 60

    html = blocked_resp.get_data(as_text=True)
    assert "Batas frekuensi pencarian tercapai" in html

    # IP berbeda tidak boleh terblokir
    allowed_other_ip = client.post(
        "/lacak",
        data={
            "csrf_token": csrf,
            "ticket_code": ticket_code,
            "access_token": access_token,
        },
        environ_overrides={"REMOTE_ADDR": "192.168.1.99"},
    )
    assert allowed_other_ip.status_code == 200


# ==============================================================================
# Skenario E2E-06: Proteksi Akses Langsung /lapor/sukses Tanpa POST
# ==============================================================================
def test_e2e_06_direct_access_lapor_sukses_redirects(client):
    # Akses langsung GET /lapor/sukses harus me-redirect ke /lapor
    response = client.get("/lapor/sukses", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/lapor")

