"""
Pengujian Terarah TSK-F7-04:
Otorisasi Multi-Peran dan Filter Agregat Dashboard (FR-07).

Mencakup 12 skenario pengujian komprehensif:
1. test_f7_04_rbac_dashboard_view_all_roles: Matriks akses view /dashboard/ untuk 5 status peran.
2. test_f7_04_rbac_dashboard_api_all_roles: Matriks akses API /dashboard/api/chart-data untuk 5 status peran.
3. test_f7_04_pimpinan_strictly_denied_from_operational_admin_endpoints: Isolasi Pimpinan dari rute operasional Admin Sarpras.
4. test_f7_04_pimpinan_strictly_denied_from_technician_endpoints: Isolasi Pimpinan dari rute teknisi.
5. test_f7_04_teknisi_strictly_denied_from_dashboard_and_admin_endpoints: Isolasi Teknisi dari dashboard dan admin.
6. test_f7_04_dashboard_http_mutation_methods_rejected: Penolakan metode mutasi HTTP pada dashboard dan API (405).
7. test_f7_04_deactivated_staff_session_immediate_revocation: Pencabutan langsung sesi akun nonaktif (is_active=False).
8. test_f7_04_session_role_tampering_resilience: Ketahanan terhadap manipulasi role via cookie/sesi berbasis database.
9. test_f7_04_query_param_fuzzing_and_tampering_rejected_400: Validasi dan penolakan query parameter ilegal/fuzzed (400).
10. test_f7_04_multi_filter_exact_intersection_and_consistency: Konsistensi matematis data saat filter kombinasi aktif.
11. test_f7_04_navbar_ui_strict_role_isolation: Pemisahan tampilan menu navigasi per peran secara ketat.
12. test_f7_04_strict_zero_pii_and_read_only_deep_integrity: Jaminan Zero PII dan integritas murni read-only.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import secrets

import pytest
from sqlalchemy import delete, func, select
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.category import Category
from app.models.ticket import Ticket
from app.models.user import User
from app.utils.ticket_identity import generate_ticket_code

PASSWORD = "Valid-Password-123!"
PASSWORD_HASH = generate_password_hash(PASSWORD, method="scrypt")


@pytest.fixture()
def app():
    from app import create_app

    test_app = create_app("testing")
    test_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    with test_app.app_context():
        baseline_ticket_ids = set(db.session.scalars(select(Ticket.id)).all())
        baseline_user_ids = set(db.session.scalars(select(User.id)).all())

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

            # Pembersihan data uji terisolasi
            with db.engine.begin() as cleanup_connection:
                if baseline_ticket_ids:
                    cleanup_connection.execute(
                        delete(AuditLog).where(
                            AuditLog.ticket_id.notin_(baseline_ticket_ids)
                        )
                    )
                    cleanup_connection.execute(
                        delete(Ticket).where(
                            Ticket.id.notin_(baseline_ticket_ids)
                        )
                    )
                else:
                    cleanup_connection.execute(delete(AuditLog))
                    cleanup_connection.execute(delete(Ticket))

                if baseline_user_ids:
                    cleanup_connection.execute(
                        delete(User).where(
                            User.id.notin_(baseline_user_ids)
                        )
                    )
                else:
                    cleanup_connection.execute(delete(User))

            db.engine.dispose()


@pytest.fixture()
def client(app):
    return app.test_client()


def _create_user(username: str, role: str, is_active: bool = True) -> User:
    unique_uname = f"{username}_{secrets.token_hex(4)}"
    user = User(
        username=unique_uname,
        full_name=f"Pengguna {username}",
        password_hash=PASSWORD_HASH if role != "reporter" else None,
        role=role,
        is_active=is_active,
    )
    db.session.add(user)
    db.session.flush()
    return user


def _login_as(client, role: str, username: str | None = None, is_active: bool = True) -> User:
    uname = username or f"{role}_user"
    user = _create_user(uname, role, is_active=is_active)
    db.session.commit()
    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["role"] = user.role
        sess.permanent = True
    return user


def _create_test_ticket(
    *,
    status: str = "Baru",
    official_category_id: int | None = None,
    floor_number: int = 2,
    room_name: str | None = "Lab 2.1",
    building_name: str = "Gedung FTII",
    reporter_name: str | None = "Ahmad Pelapor",
    reporter_contact: str | None = "081234567890",
    description: str = "Deskripsi keluhan uji coba fasilitas.",
    created_at: datetime | None = None,
) -> Ticket:
    """Helper membuat entri tiket untuk pengujian otorisasi dan filter agregat."""
    ticket_code = generate_ticket_code()
    token_seed = secrets.token_hex(16)
    token_hash = hashlib.sha256(token_seed.encode("ascii")).hexdigest()

    ticket = Ticket(
        ticket_code=ticket_code,
        access_token_hash=token_hash,
        description=description,
        building_name=building_name,
        floor_number=floor_number,
        room_name=room_name,
        location_detail="Detail lokasi uji",
        status=status,
        official_category_id=official_category_id,
        reporter_name=reporter_name,
        reporter_contact=reporter_contact,
    )
    if created_at is not None:
        ticket.created_at = created_at
    db.session.add(ticket)
    db.session.flush()
    return ticket


# ==============================================================================
# Skenario 1 s.d. 12 Pengujian Terarah TSK-F7-04
# ==============================================================================


def test_f7_04_rbac_dashboard_view_all_roles(client):
    """
    Skenario 1: Matriks akses view /dashboard/ dan /dashboard untuk 5 status pengguna:
    1. Anonim -> 302 Redirect ke login.
    2. Reporter -> 302 Redirect ke login (karena bukan anggota STAFF_ROLES).
    3. Teknisi -> 403 Forbidden.
    4. Pimpinan -> 200 OK.
    5. Admin Sarpras -> 200 OK.
    """
    # 1. Anonim (tanpa sesi)
    for path in ["/dashboard", "/dashboard/"]:
        resp_anon = client.get(path)
        assert resp_anon.status_code == 302
        assert "/auth/login" in resp_anon.headers.get("Location", "")

    # 2. Reporter (terautentikasi sesi)
    client_reporter = client.application.test_client()
    _login_as(client_reporter, "reporter")
    resp_reporter = client_reporter.get("/dashboard/")
    # Reporter bukan STAFF_ROLES, sesi dibersihkan oleh load_logged_in_user -> 302 ke login
    assert resp_reporter.status_code == 302
    assert "/auth/login" in resp_reporter.headers.get("Location", "")

    # 3. Teknisi
    client_tech = client.application.test_client()
    _login_as(client_tech, "teknisi")
    resp_tech = client_tech.get("/dashboard/")
    assert resp_tech.status_code == 403

    # 4. Pimpinan
    client_pim = client.application.test_client()
    _login_as(client_pim, "pimpinan")
    resp_pim = client_pim.get("/dashboard/")
    assert resp_pim.status_code == 200

    # 5. Admin Sarpras
    client_admin = client.application.test_client()
    _login_as(client_admin, "admin_sarpras")
    resp_admin = client_admin.get("/dashboard/")
    assert resp_admin.status_code == 200


def test_f7_04_rbac_dashboard_api_all_roles(client):
    """
    Skenario 2: Matriks akses API /dashboard/api/chart-data untuk 5 status pengguna:
    1. Anonim -> 302 Redirect ke login.
    2. Reporter -> 302 Redirect ke login.
    3. Teknisi -> 403 Forbidden.
    4. Pimpinan -> 200 OK dengan payload JSON valid.
    5. Admin Sarpras -> 200 OK dengan payload JSON valid.
    """
    # 1. Anonim
    resp_anon = client.get("/dashboard/api/chart-data")
    assert resp_anon.status_code == 302
    assert "/auth/login" in resp_anon.headers.get("Location", "")

    # 2. Reporter
    client_reporter = client.application.test_client()
    _login_as(client_reporter, "reporter")
    resp_reporter = client_reporter.get("/dashboard/api/chart-data")
    assert resp_reporter.status_code == 302
    assert "/auth/login" in resp_reporter.headers.get("Location", "")

    # 3. Teknisi
    client_tech = client.application.test_client()
    _login_as(client_tech, "teknisi")
    resp_tech = client_tech.get("/dashboard/api/chart-data")
    assert resp_tech.status_code == 403

    # 4. Pimpinan
    client_pim = client.application.test_client()
    _login_as(client_pim, "pimpinan")
    resp_pim = client_pim.get("/dashboard/api/chart-data")
    assert resp_pim.status_code == 200
    assert resp_pim.is_json
    data_pim = resp_pim.get_json()
    assert "kpi" in data_pim
    assert "category_chart" in data_pim
    assert "trend_chart" in data_pim
    assert "location_chart" in data_pim
    assert "filters_applied" in data_pim

    # 5. Admin Sarpras
    client_admin = client.application.test_client()
    _login_as(client_admin, "admin_sarpras")
    resp_admin = client_admin.get("/dashboard/api/chart-data")
    assert resp_admin.status_code == 200
    assert resp_admin.is_json


def test_f7_04_pimpinan_strictly_denied_from_operational_admin_endpoints(client):
    """
    Skenario 3: Pimpinan/Kaprodi terisolasi penuh dan dilarang mengakses seluruh endpoint
    operasional Admin Sarpras (PRD FR-07, DESIGN Bagian 5.5):
    - GET /admin/tiket -> 403 Forbidden.
    - GET /admin/tiket/1/verifikasi -> 403 Forbidden.
    - POST /admin/tiket/1/verifikasi -> 403 Forbidden.
    - GET /admin/audit-log -> 403 Forbidden.
    """
    _login_as(client, "pimpinan")

    # 1. Antrean tiket sarpras
    resp_queue = client.get("/admin/tiket")
    assert resp_queue.status_code == 403

    # 2. Form verifikasi tiket
    resp_verify_form = client.get("/admin/tiket/1/verifikasi")
    assert resp_verify_form.status_code == 403

    # 3. Aksi mutasi verifikasi tiket
    resp_verify_post = client.post("/admin/tiket/1/verifikasi", data={"official_category_id": 1})
    assert resp_verify_post.status_code == 403

    # 4. Log audit sarpras (FR-09)
    resp_audit = client.get("/admin/audit-log")
    assert resp_audit.status_code == 403


def test_f7_04_pimpinan_strictly_denied_from_technician_endpoints(client):
    """
    Skenario 4: Pimpinan/Kaprodi dilarang mengakses endpoint operasional teknisi (FR-06):
    - GET /teknisi/tiket -> 403 Forbidden.
    - POST /teknisi/tiket/1/status -> 403 Forbidden.
    """
    _login_as(client, "pimpinan")

    resp_tech_queue = client.get("/teknisi/tiket")
    assert resp_tech_queue.status_code == 403

    resp_tech_status = client.post("/teknisi/tiket/1/status", data={"status": "Diproses"})
    assert resp_tech_status.status_code == 403


def test_f7_04_teknisi_strictly_denied_from_dashboard_and_admin_endpoints(client):
    """
    Skenario 5: Teknisi hanya boleh mengakses tugasnya dan ditolak dari dashboard serta admin log:
    - GET /dashboard/ -> 403 Forbidden.
    - GET /dashboard/api/chart-data -> 403 Forbidden.
    - GET /admin/tiket -> 403 Forbidden.
    - GET /admin/audit-log -> 403 Forbidden.
    """
    _login_as(client, "teknisi")

    # Dashboard view & API
    assert client.get("/dashboard/").status_code == 403
    assert client.get("/dashboard").status_code == 403
    assert client.get("/dashboard/api/chart-data").status_code == 403

    # Admin endpoints
    assert client.get("/admin/tiket").status_code == 403
    assert client.get("/admin/audit-log").status_code == 403

    # Namun teknisi berwenang pada rute tugasnya sendiri
    assert client.get("/teknisi/tiket").status_code == 200


def test_f7_04_dashboard_http_mutation_methods_rejected(client):
    """
    Skenario 6: Seluruh metode mutasi HTTP pada /dashboard/ dan /dashboard/api/chart-data
    ditolak secara tegas dengan HTTP 405 Method Not Allowed.
    """
    _login_as(client, "pimpinan")

    # 1. Halaman view /dashboard/
    assert client.post("/dashboard/").status_code == 405
    assert client.put("/dashboard/").status_code == 405
    assert client.delete("/dashboard/").status_code == 405
    assert client.patch("/dashboard/").status_code == 405

    # 2. Endpoint API /dashboard/api/chart-data
    assert client.post("/dashboard/api/chart-data").status_code == 405
    assert client.put("/dashboard/api/chart-data").status_code == 405
    assert client.delete("/dashboard/api/chart-data").status_code == 405
    assert client.patch("/dashboard/api/chart-data").status_code == 405


def test_f7_04_deactivated_staff_session_immediate_revocation(client):
    """
    Skenario 7: Akun staf yang dinonaktifkan (is_active=False) langsung dicabut sesinya
    saat melakukan request ke dashboard dan dialihkan ke login (HTTP 302).
    """
    user = _login_as(client, "pimpinan")

    # Awalnya aktif -> 200 OK
    resp_ok = client.get("/dashboard/")
    assert resp_ok.status_code == 200

    # Nonaktifkan akun di basis data
    user.is_active = False
    db.session.commit()

    # Request berikutnya harus otomatis ditolak dan dialihkan (302)
    resp_revoked_view = client.get("/dashboard/")
    assert resp_revoked_view.status_code == 302
    assert "/auth/login" in resp_revoked_view.headers.get("Location", "")

    resp_revoked_api = client.get("/dashboard/api/chart-data")
    assert resp_revoked_api.status_code == 302
    assert "/auth/login" in resp_revoked_api.headers.get("Location", "")


def test_f7_04_session_role_tampering_resilience(client):
    """
    Skenario 8: Manipulasi role pada cookie sesi (misal teknisi memalsukan session['role'] = 'pimpinan')
    digagalkan oleh verifikasi database di before_app_request, sehingga akses tetap ditolak (403).
    """
    # 1. Login sah sebagai teknisi
    user = _login_as(client, "teknisi")

    # 2. Upaya penyerang memanipulasi dictionary sesi pada cookie
    with client.session_transaction() as sess:
        sess["role"] = "pimpinan"  # Memalsukan role di sisi klien

    # 3. Request ke dashboard harus tetap ditolak 403 karena role di database adalah 'teknisi'
    resp = client.get("/dashboard/")
    assert resp.status_code == 403

    resp_api = client.get("/dashboard/api/chart-data")
    assert resp_api.status_code == 403

    # Verifikasi sesi dikoreksi kembali sesuai database oleh load_logged_in_user
    with client.session_transaction() as sess:
        assert sess.get("role") == "teknisi"


def test_f7_04_query_param_fuzzing_and_tampering_rejected_400(client):
    """
    Skenario 9: Seluruh query parameter ilegal, rentang tidak valid, tipe data salah,
    atau upaya injeksi ditolak dengan HTTP 400 Bad Request JSON terstruktur tanpa pernah memicu 500.
    """
    _login_as(client, "pimpinan")

    invalid_queries = [
        # Pelanggaran days
        "?days=-1",
        "?days=0",
        "?days=366",
        "?days=999999",
        "?days=abc",
        "?days=30.5",
        "?days=null",
        # Pelanggaran category
        "?category=K8",
        "?category=K0",
        "?category=XX",
        "?category=' OR 1=1--",
        "?category=<script>alert(1)</script>",
        # Pelanggaran floor
        "?floor=0",
        "?floor=5",
        "?floor=-2",
        "?floor=lantai1",
        "?floor=3.14",
    ]

    for q in invalid_queries:
        resp = client.get(f"/dashboard/api/chart-data{q}")
        assert resp.status_code == 400, f"Query '{q}' seharusnya menghasilkan 400 tapi {resp.status_code}"
        assert resp.is_json
        payload = resp.get_json()
        assert "error" in payload
        assert "message" in payload

    # Parameter ekstra yang tidak dikenal diabaikan secara aman (HTTP 200 OK)
    resp_extra = client.get("/dashboard/api/chart-data?days=30&hack=1&debug=true")
    assert resp_extra.status_code == 200


def test_f7_04_multi_filter_exact_intersection_and_consistency(client):
    """
    Skenario 10: Konsistensi matematis data agregat saat kombinasi filter aktif
    (?days=7&category=K1&floor=2). Seluruh metrik KPI, tren, distribusi kategori,
    dan distribusi lokasi harus mencerminkan irisan filter yang tepat.
    """
    _login_as(client, "pimpinan")

    cat_k1 = db.session.scalar(select(Category).where(Category.code == "K1"))
    cat_k2 = db.session.scalar(select(Category).where(Category.code == "K2"))
    assert cat_k1 is not None and cat_k2 is not None

    now = datetime.now(timezone.utc)

    # 1. Tiket cocok: K1, Lantai 2, dalam 7 hari (status Diproses)
    t1 = _create_test_ticket(
        status="Diproses",
        official_category_id=cat_k1.id,
        floor_number=2,
        room_name="Lab 201",
        created_at=now - timedelta(days=2),
    )
    # 2. Tiket cocok: K1, Lantai 2, dalam 7 hari (status Selesai)
    t2 = _create_test_ticket(
        status="Selesai",
        official_category_id=cat_k1.id,
        floor_number=2,
        room_name="Lab 201",
        created_at=now - timedelta(days=3),
    )
    # 3. Tiket TIDAK cocok lantai: K1, Lantai 3, dalam 7 hari
    t3 = _create_test_ticket(
        status="Baru",
        official_category_id=cat_k1.id,
        floor_number=3,
        room_name="R 301",
        created_at=now - timedelta(days=1),
    )
    # 4. Tiket TIDAK cocok kategori: K2, Lantai 2, dalam 7 hari
    t4 = _create_test_ticket(
        status="Terverifikasi",
        official_category_id=cat_k2.id,
        floor_number=2,
        room_name="Lab 202",
        created_at=now - timedelta(days=4),
    )
    # 5. Tiket TIDAK cocok tanggal: K1, Lantai 2, 40 hari lalu (di luar 7 hari)
    t5 = _create_test_ticket(
        status="Selesai",
        official_category_id=cat_k1.id,
        floor_number=2,
        room_name="Lab 201",
        created_at=now - timedelta(days=40),
    )
    db.session.commit()

    # Eksekusi API dengan kombinasi filter lengkap
    resp = client.get("/dashboard/api/chart-data?days=7&category=K1&floor=2")
    assert resp.status_code == 200
    data = resp.get_json()

    kpi = data["kpi"]
    cat_chart = data["category_chart"]
    trend_chart = data["trend_chart"]
    loc_chart = data["location_chart"]

    # Harus tepat 2 tiket yang lolos irisan filter (t1 & t2)
    assert kpi["total_tickets"] == 2
    assert kpi["active_tickets"] == 1  # t1 (Diproses)
    assert kpi["status_counts"]["Diproses"] == 1
    assert kpi["status_counts"]["Selesai"] == 1
    assert kpi["status_counts"]["Baru"] == 0
    assert kpi["status_counts"]["Terverifikasi"] == 0
    assert kpi["completion_rate"] == 50.0  # 1 / 2 * 100

    # Konsistensi matematis antar komponen
    assert sum(kpi["status_counts"].values()) == kpi["total_tickets"]
    assert sum(d for d in trend_chart["datasets"][0]["data"]) == kpi["total_tickets"]

    # Kategori: hanya K1 yang memiliki count 2, lainnya 0
    k1_idx = cat_chart["labels"].index("K1")
    assert cat_chart["datasets"][0]["data"][k1_idx] == 2
    for idx, code in enumerate(cat_chart["labels"]):
        if code != "K1":
            assert cat_chart["datasets"][0]["data"][idx] == 0
    assert cat_chart["total_verified"] == 2
    assert cat_chart["unverified_count"] == 0

    # Lokasi: hanya Lantai 2 yang memiliki count 2, lantai 1, 3, 4 count 0
    l2_idx = loc_chart["labels"].index("Lantai 2")
    assert loc_chart["datasets"][0]["data"][l2_idx] == 2
    for idx, lbl in enumerate(loc_chart["labels"]):
        if lbl != "Lantai 2":
            assert loc_chart["datasets"][0]["data"][idx] == 0
    assert len(loc_chart["top_rooms"]) == 1
    assert loc_chart["top_rooms"][0]["room_name"] == "Lab 201"
    assert loc_chart["top_rooms"][0]["count"] == 2


def test_f7_04_navbar_ui_strict_role_isolation(client):
    """
    Skenario 11: Tampilan navigasi UI (navbar) terisolasi ketat sesuai peran:
    1. Admin Sarpras -> Melihat Dasbor, Antrean Sarpras, Log Audit. Tidak melihat Tugas Saya.
    2. Pimpinan -> Hanya melihat Dasbor. Tidak melihat Antrean Sarpras, Log Audit, Tugas Saya.
    3. Teknisi -> Hanya melihat Tugas Saya. Tidak melihat Dasbor, Antrean Sarpras, Log Audit.
    4. Anonim / Publik -> Hanya melihat Buat Laporan, Lacak Keluhan, Masuk Staf.
    """
    # 1. Admin Sarpras
    client_admin = client.application.test_client()
    _login_as(client_admin, "admin_sarpras")
    resp_admin = client_admin.get("/dashboard/")
    assert resp_admin.status_code == 200
    html_admin = resp_admin.get_data(as_text=True)
    assert ">Dasbor<" in html_admin
    assert ">Antrean Sarpras<" in html_admin
    assert ">Log Audit<" in html_admin
    assert ">Tugas Saya<" not in html_admin

    # 2. Pimpinan
    client_pim = client.application.test_client()
    _login_as(client_pim, "pimpinan")
    resp_pim = client_pim.get("/dashboard/")
    assert resp_pim.status_code == 200
    html_pim = resp_pim.get_data(as_text=True)
    assert ">Dasbor<" in html_pim
    assert ">Antrean Sarpras<" not in html_pim
    assert ">Log Audit<" not in html_pim
    assert ">Tugas Saya<" not in html_pim
    assert 'href="/admin/tiket"' not in html_pim
    assert 'href="/admin/audit-log"' not in html_pim

    # 3. Teknisi
    client_tech = client.application.test_client()
    _login_as(client_tech, "teknisi")
    resp_tech = client_tech.get("/teknisi/tiket")
    assert resp_tech.status_code == 200
    html_tech = resp_tech.get_data(as_text=True)
    assert ">Tugas Saya<" in html_tech
    assert ">Dasbor<" not in html_tech
    assert ">Antrean Sarpras<" not in html_tech
    assert ">Log Audit<" not in html_tech

    # 4. Pengguna Publik (tanpa login)
    client_anon = client.application.test_client()
    resp_anon = client_anon.get("/lapor")
    assert resp_anon.status_code == 200
    html_anon = resp_anon.get_data(as_text=True)
    assert ">Buat Laporan<" in html_anon
    assert ">Lacak Keluhan<" in html_anon
    assert ">Masuk Staf<" in html_anon
    assert ">Dasbor<" not in html_anon
    assert ">Antrean Sarpras<" not in html_anon
    assert ">Log Audit<" not in html_anon
    assert ">Tugas Saya<" not in html_anon


def test_f7_04_strict_zero_pii_and_read_only_deep_integrity(client):
    """
    Skenario 12: Jaminan mutlak Zero PII pada respons HTML dan JSON API untuk pimpinan
    serta verifikasi mendalam bahwa pemanggilan dashboard tidak menimbulkan efek samping
    mutasi basis data atau penambahan entri AuditLog (read-only murni).
    """
    _login_as(client, "pimpinan")

    # Buat tiket uji dengan data sensitif
    secret_ticket = _create_test_ticket(
        status="Diproses",
        floor_number=1,
        room_name="Lab 101",
        reporter_name="Prof. Dr. Rahasia Pribadi",
        reporter_contact="081299887766",
        description="Keluhan rahasia nomor kontak pribadi dan identitas dosen kaprodi.",
    )
    db.session.commit()

    # 1. Periksa ketiadaan PII pada tampilan HTML dashboard
    resp_view = client.get("/dashboard/")
    assert resp_view.status_code == 200
    html = resp_view.get_data(as_text=True)
    assert "Rahasia Pribadi" not in html
    assert "081299887766" not in html
    assert "Keluhan rahasia nomor kontak" not in html
    assert secret_ticket.access_token_hash not in html

    # 2. Periksa ketiadaan PII pada respons JSON API
    resp_api = client.get("/dashboard/api/chart-data")
    assert resp_api.status_code == 200
    api_text = resp_api.get_data(as_text=True)
    assert "Rahasia Pribadi" not in api_text
    assert "081299887766" not in api_text
    assert "Keluhan rahasia nomor kontak" not in api_text
    assert secret_ticket.access_token_hash not in api_text

    # 3. Integritas Read-Only Mendalam:
    # Catat jumlah baris seluruh tabel utama sebelum eksekusi berulang
    user_count_before = db.session.scalar(select(func.count(User.id)))
    ticket_count_before = db.session.scalar(select(func.count(Ticket.id)))
    cat_count_before = db.session.scalar(select(func.count(Category.id)))
    audit_count_before = db.session.scalar(select(func.count(AuditLog.id)))

    # Jalankan serangkaian request kueri agregat
    for days_param in [7, 30, 90]:
        client.get(f"/dashboard/api/chart-data?days={days_param}")
    client.get("/dashboard/api/chart-data?category=K1")
    client.get("/dashboard/api/chart-data?floor=2")
    client.get("/dashboard/")

    # Verifikasi jumlah baris basis data tidak berubah (delta = 0)
    assert db.session.scalar(select(func.count(User.id))) == user_count_before
    assert db.session.scalar(select(func.count(Ticket.id))) == ticket_count_before
    assert db.session.scalar(select(func.count(Category.id))) == cat_count_before
    assert db.session.scalar(select(func.count(AuditLog.id))) == audit_count_before

