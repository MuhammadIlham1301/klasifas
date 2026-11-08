"""
Pengujian Terarah TSK-F7-02:
Penyediaan Data Visualisasi Dashboard (FR-07).

Mencakup seluruh 13 skenario pengujian:
1. test_chart_data_endpoint_unauthenticated_denied: Request tanpa sesi login dialihkan (302) ke login.
2. test_chart_data_endpoint_technician_role_forbidden: Peran 'teknisi' ditolak 403 Forbidden.
3. test_chart_data_endpoint_admin_sarpras_allowed: Peran 'admin_sarpras' diizinkan (200 JSON).
4. test_chart_data_endpoint_pimpinan_allowed: Peran 'pimpinan' diizinkan (200 JSON).
5. test_chart_data_payload_structure_chartjs_compliance: Kesesuaian struktur JSON dengan spesifikasi Chart.js.
6. test_chart_data_empty_database_returns_valid_structure: Database kosong mengembalikan 200 JSON lengkap dengan nilai 0.
7. test_chart_data_filter_by_days_period: Parameter ?days=N menyaring rentang tren waktu dan KPI secara konsisten.
8. test_chart_data_filter_by_category: Parameter ?category=KX menyaring seluruh grafik hanya untuk kategori tersebut.
9. test_chart_data_filter_by_floor: Parameter ?floor=F menyaring seluruh grafik hanya untuk lantai tersebut.
10. test_chart_data_combined_multi_filters_consistency: Kombinasi filter multi-dimensi konsisten di seluruh komponen data.
11. test_chart_data_invalid_query_params_rejected_400: Parameter invalid (days, category, floor) ditolak 400 Bad Request JSON.
12. test_chart_data_zero_pii_deep_inspection: Verifikasi mendalam ketiadaan atribut PII pelapor pada payload JSON.
13. test_chart_data_read_only_integrity: Sifat murni read-only tanpa mutasi tiket atau pencatatan audit log.
"""
from datetime import datetime, timedelta, timezone
import hashlib
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

            # Pembersihan data test
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


def _create_user(username: str, role: str) -> User:
    unique_uname = f"{username}_{secrets.token_hex(4)}"
    user = User(
        username=unique_uname,
        full_name=f"Pengguna {username}",
        password_hash=PASSWORD_HASH,
        role=role,
        is_active=True,
    )
    db.session.add(user)
    db.session.flush()
    return user


def _login_as(client, role: str, username: str | None = None) -> User:
    uname = username or f"{role}_user"
    user = _create_user(uname, role)
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
    created_at: datetime | None = None,
    reporter_name: str | None = "Ahmad Pelapor",
    reporter_contact: str | None = "081234567890",
    description: str = "Deskripsi keluhan uji coba fasilitas.",
) -> Ticket:
    """Helper membuat entri tiket untuk pengujian visualisasi dashboard."""
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
# Skenario 1 s.d. 13 Pengujian TSK-F7-02
# ==============================================================================


def test_chart_data_endpoint_unauthenticated_denied(client):
    """Skenario 1: Request tanpa sesi login dialihkan (302) ke halaman login."""
    resp = client.get("/dashboard/api/chart-data")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_chart_data_endpoint_technician_role_forbidden(client):
    """Skenario 2: Peran 'teknisi' ditolak dengan HTTP 403 Forbidden."""
    _login_as(client, "teknisi")
    resp = client.get("/dashboard/api/chart-data")
    assert resp.status_code == 403


def test_chart_data_endpoint_admin_sarpras_allowed(client):
    """Skenario 3: Peran 'admin_sarpras' diizinkan mengakses endpoint (200 JSON)."""
    _login_as(client, "admin_sarpras")
    resp = client.get("/dashboard/api/chart-data")
    assert resp.status_code == 200
    assert resp.is_json
    data = resp.get_json()
    assert "kpi" in data
    assert "category_chart" in data
    assert "trend_chart" in data
    assert "location_chart" in data
    assert "filters_applied" in data


def test_chart_data_endpoint_pimpinan_allowed(client):
    """Skenario 4: Peran 'pimpinan' diizinkan mengakses endpoint (200 JSON)."""
    _login_as(client, "pimpinan")
    resp = client.get("/dashboard/api/chart-data")
    assert resp.status_code == 200
    assert resp.is_json
    data = resp.get_json()
    assert "kpi" in data
    assert "category_chart" in data


def test_chart_data_payload_structure_chartjs_compliance(client):
    """Skenario 5: Kesesuaian struktur JSON dengan spesifikasi pustaka Chart.js."""
    _login_as(client, "admin_sarpras")
    resp = client.get("/dashboard/api/chart-data")
    assert resp.status_code == 200
    data = resp.get_json()

    # 1. KPI Structure
    kpi = data["kpi"]
    assert "total_tickets" in kpi
    assert "status_counts" in kpi
    assert "active_tickets" in kpi
    assert "completion_rate" in kpi
    for st in ["Baru", "Terverifikasi", "Diproses", "Selesai"]:
        assert st in kpi["status_counts"]

    # 2. Category Chart (Chart.js format)
    cat_c = data["category_chart"]
    assert "labels" in cat_c
    assert "category_names" in cat_c
    assert "datasets" in cat_c
    assert len(cat_c["labels"]) == 7
    assert len(cat_c["category_names"]) == 7
    assert len(cat_c["datasets"]) == 1
    assert "label" in cat_c["datasets"][0]
    assert "data" in cat_c["datasets"][0]
    assert len(cat_c["datasets"][0]["data"]) == 7
    assert "total_verified" in cat_c
    assert "unverified_count" in cat_c

    # 3. Trend Chart (Chart.js format)
    trend_c = data["trend_chart"]
    assert "labels" in trend_c
    assert "datasets" in trend_c
    assert len(trend_c["labels"]) == 30  # Default 30 hari
    assert len(trend_c["datasets"]) == 1
    assert "data" in trend_c["datasets"][0]
    assert len(trend_c["datasets"][0]["data"]) == 30

    # 4. Location Chart (Chart.js format)
    loc_c = data["location_chart"]
    assert "labels" in loc_c
    assert "datasets" in loc_c
    assert len(loc_c["labels"]) == 4  # Lantai 1 s.d. 4
    assert len(loc_c["datasets"]) == 1
    assert len(loc_c["datasets"][0]["data"]) == 4
    assert "top_rooms" in loc_c
    assert "unspecified_room_count" in loc_c
    assert "other_floors_count" in loc_c

    # 5. Filters Applied
    filters = data["filters_applied"]
    assert filters["days"] == 30
    assert filters["category"] is None
    assert filters["floor"] is None


def test_chart_data_empty_database_returns_valid_structure(client):
    """Skenario 6: Database kosong mengembalikan 200 JSON lengkap dengan nilai 0."""
    db.session.execute(delete(Ticket))
    db.session.commit()

    _login_as(client, "admin_sarpras")
    resp = client.get("/dashboard/api/chart-data")
    assert resp.status_code == 200
    data = resp.get_json()

    assert data["kpi"]["total_tickets"] == 0
    assert data["kpi"]["completion_rate"] == 0.0
    assert data["category_chart"]["total_verified"] == 0
    assert data["category_chart"]["unverified_count"] == 0
    assert all(val == 0 for val in data["category_chart"]["datasets"][0]["data"])
    assert all(val == 0 for val in data["trend_chart"]["datasets"][0]["data"])
    assert all(val == 0 for val in data["location_chart"]["datasets"][0]["data"])
    assert data["location_chart"]["top_rooms"] == []


def test_chart_data_filter_by_days_period(client):
    """Skenario 7: Parameter ?days=N menyaring rentang tren waktu dan KPI secara konsisten."""
    db.session.execute(delete(Ticket))
    db.session.commit()

    # Tiket dibuat hari ini
    _create_test_ticket(status="Baru")
    # Tiket dibuat 10 hari lalu (di luar rentang 7 hari)
    old_time = datetime.now(timezone.utc) - timedelta(days=10)
    _create_test_ticket(status="Baru", created_at=old_time)
    db.session.commit()

    _login_as(client, "admin_sarpras")
    resp = client.get("/dashboard/api/chart-data?days=7")
    assert resp.status_code == 200
    data = resp.get_json()

    assert data["filters_applied"]["days"] == 7
    assert len(data["trend_chart"]["labels"]) == 7
    assert len(data["trend_chart"]["datasets"][0]["data"]) == 7

    # Total KPI harus hanya menghitung tiket dalam 7 hari terakhir (1 tiket)
    assert data["kpi"]["total_tickets"] == 1
    assert sum(data["trend_chart"]["datasets"][0]["data"]) == 1


def test_chart_data_filter_by_category(client):
    """Skenario 8: Parameter ?category=KX menyaring seluruh grafik hanya untuk kategori tersebut."""
    db.session.execute(delete(Ticket))
    db.session.commit()

    cat_k1 = db.session.scalar(select(Category).where(Category.code == "K1"))
    cat_k2 = db.session.scalar(select(Category).where(Category.code == "K2"))

    # 3 tiket K1 di Lantai 1
    for _ in range(3):
        _create_test_ticket(
            status="Terverifikasi",
            official_category_id=cat_k1.id,
            floor_number=1,
            room_name="Lab 1.1",
        )
    # 5 tiket K2 di Lantai 2
    for _ in range(5):
        _create_test_ticket(
            status="Diproses",
            official_category_id=cat_k2.id,
            floor_number=2,
            room_name="Lab 2.1",
        )
    db.session.commit()

    _login_as(client, "admin_sarpras")
    resp = client.get("/dashboard/api/chart-data?category=K1")
    assert resp.status_code == 200
    data = resp.get_json()

    assert data["filters_applied"]["category"] == "K1"
    assert data["kpi"]["total_tickets"] == 3
    assert data["kpi"]["status_counts"]["Terverifikasi"] == 3
    assert data["kpi"]["status_counts"]["Diproses"] == 0

    # Pada category chart, hanya K1 yang memiliki nilai 3
    cat_data = data["category_chart"]["datasets"][0]["data"]
    assert cat_data[0] == 3  # K1
    assert sum(cat_data[1:]) == 0  # K2..K7 bernilai 0
    assert data["category_chart"]["total_verified"] == 3
    assert data["category_chart"]["unverified_count"] == 0

    # Pada location chart, hanya lantai 1 yang bernilai 3
    loc_data = data["location_chart"]["datasets"][0]["data"]
    assert loc_data[0] == 3  # Lantai 1
    assert sum(loc_data[1:]) == 0  # Lantai 2..4 bernilai 0

    # Top rooms hanya mencatat Lab 1.1
    top = data["location_chart"]["top_rooms"]
    assert len(top) == 1
    assert top[0] == {"room_name": "Lab 1.1", "count": 3}


def test_chart_data_filter_by_floor(client):
    """Skenario 9: Parameter ?floor=F menyaring seluruh grafik hanya untuk lantai tersebut."""
    db.session.execute(delete(Ticket))
    db.session.commit()

    cat_k1 = db.session.scalar(select(Category).where(Category.code == "K1"))
    cat_k3 = db.session.scalar(select(Category).where(Category.code == "K3"))

    # Lantai 1: 2 tiket K1
    for _ in range(2):
        _create_test_ticket(
            status="Terverifikasi",
            official_category_id=cat_k1.id,
            floor_number=1,
        )
    # Lantai 2: 4 tiket K3
    for _ in range(4):
        _create_test_ticket(
            status="Diproses",
            official_category_id=cat_k3.id,
            floor_number=2,
        )
    db.session.commit()

    _login_as(client, "admin_sarpras")
    resp = client.get("/dashboard/api/chart-data?floor=2")
    assert resp.status_code == 200
    data = resp.get_json()

    assert data["filters_applied"]["floor"] == 2
    assert data["kpi"]["total_tickets"] == 4
    assert data["kpi"]["status_counts"]["Diproses"] == 4

    # Location chart hanya lantai 2 bernilai 4
    loc_data = data["location_chart"]["datasets"][0]["data"]
    assert loc_data == [0, 4, 0, 0]

    # Category chart hanya K3 bernilai 4
    cat_data = data["category_chart"]["datasets"][0]["data"]
    assert cat_data[2] == 4  # K3
    assert sum(cat_data[:2]) + sum(cat_data[3:]) == 0


def test_chart_data_combined_multi_filters_consistency(client):
    """Skenario 10: Kombinasi filter multi-dimensi konsisten di seluruh komponen data."""
    db.session.execute(delete(Ticket))
    db.session.commit()

    cat_k1 = db.session.scalar(select(Category).where(Category.code == "K1"))
    cat_k2 = db.session.scalar(select(Category).where(Category.code == "K2"))

    # Kategori K1, Lantai 2, dibuat hari ini (Cocok dengan filter kombinasi: 3 tiket)
    for _ in range(3):
        _create_test_ticket(
            status="Selesai",
            official_category_id=cat_k1.id,
            floor_number=2,
            room_name="Lab 2.1",
        )

    # Kategori K1, Lantai 1 (Lantai tidak cocok: 2 tiket)
    for _ in range(2):
        _create_test_ticket(
            status="Selesai",
            official_category_id=cat_k1.id,
            floor_number=1,
        )

    # Kategori K2, Lantai 2 (Kategori tidak cocok: 4 tiket)
    for _ in range(4):
        _create_test_ticket(
            status="Selesai",
            official_category_id=cat_k2.id,
            floor_number=2,
        )

    # Kategori K1, Lantai 2, tetapi 60 hari lalu (Periode tidak cocok: 1 tiket)
    sixty_days_ago = datetime.now(timezone.utc) - timedelta(days=60)
    _create_test_ticket(
        status="Selesai",
        official_category_id=cat_k1.id,
        floor_number=2,
        created_at=sixty_days_ago,
    )
    db.session.commit()

    _login_as(client, "admin_sarpras")
    # Filter: 30 hari terakhir, Kategori K1, Lantai 2
    resp = client.get("/dashboard/api/chart-data?days=30&category=K1&floor=2")
    assert resp.status_code == 200
    data = resp.get_json()

    assert data["filters_applied"]["days"] == 30
    assert data["filters_applied"]["category"] == "K1"
    assert data["filters_applied"]["floor"] == 2

    # Invarian Konsistensi Silang: Total KPI harus tepat 3
    total = data["kpi"]["total_tickets"]
    assert total == 3
    assert data["kpi"]["completion_rate"] == 100.0

    # Trend chart sum == 3
    assert sum(data["trend_chart"]["datasets"][0]["data"]) == total

    # Category chart sum == 3
    assert (
        sum(data["category_chart"]["datasets"][0]["data"])
        + data["category_chart"]["unverified_count"]
        == total
    )

    # Location chart sum == 3
    assert (
        sum(data["location_chart"]["datasets"][0]["data"])
        + data["location_chart"]["other_floors_count"]
        == total
    )


def test_chart_data_invalid_query_params_rejected_400(client):
    """Skenario 11: Parameter invalid (days, category, floor) ditolak 400 Bad Request JSON."""
    _login_as(client, "admin_sarpras")

    # 1. Parameter days invalid
    for bad_days in ["abc", "-5", "0", "366"]:
        resp = client.get(f"/dashboard/api/chart-data?days={bad_days}")
        assert resp.status_code == 400
        assert resp.is_json
        err_data = resp.get_json()
        assert "error" in err_data
        assert "message" in err_data

    # 2. Parameter category invalid
    for bad_cat in ["K8", "K99", "XYZ", "123"]:
        resp = client.get(f"/dashboard/api/chart-data?category={bad_cat}")
        assert resp.status_code == 400
        assert resp.is_json
        err_data = resp.get_json()
        assert "error" in err_data

    # 3. Parameter floor invalid
    for bad_floor in ["0", "5", "99", "lantai2"]:
        resp = client.get(f"/dashboard/api/chart-data?floor={bad_floor}")
        assert resp.status_code == 400
        assert resp.is_json
        err_data = resp.get_json()
        assert "error" in err_data


def test_chart_data_zero_pii_deep_inspection(client):
    """Skenario 12: Verifikasi mendalam ketiadaan atribut PII pelapor pada payload JSON."""
    db.session.execute(delete(Ticket))
    db.session.commit()

    cat = db.session.scalar(select(Category).where(Category.code == "K1"))
    _create_test_ticket(
        status="Terverifikasi",
        official_category_id=cat.id,
        reporter_name="Budi Rahasia PDP",
        reporter_contact="081999888123",
        description="Detail keluhan rahasia dengan informasi pribadi",
    )
    db.session.commit()

    _login_as(client, "admin_sarpras")
    resp = client.get("/dashboard/api/chart-data")
    assert resp.status_code == 200
    data = resp.get_json()

    forbidden_keys = {
        "reporter_name",
        "reporter_contact",
        "access_token_hash",
        "reporter_id",
        "description",
        "photo_filename",
        "ticket_code",
    }
    forbidden_values = {
        "Budi Rahasia PDP",
        "081999888123",
        "Detail keluhan rahasia dengan informasi pribadi",
    }

    def _scan(node):
        if isinstance(node, dict):
            for k, v in node.items():
                assert k not in forbidden_keys, f"Kunci PII terdeteksi: {k}"
                if isinstance(v, str):
                    for fv in forbidden_values:
                        assert fv not in v, f"Nilai PII terdeteksi di {k}: {v}"
                _scan(v)
        elif isinstance(node, list):
            for item in node:
                _scan(item)

    _scan(data)


def test_chart_data_read_only_integrity(client):
    """Skenario 13: Sifat murni read-only tanpa mutasi tiket atau pencatatan audit log."""
    db.session.execute(delete(Ticket))
    db.session.commit()

    cat = db.session.scalar(select(Category).where(Category.code == "K1"))
    _create_test_ticket(status="Terverifikasi", official_category_id=cat.id)
    db.session.commit()

    ticket_count_before = db.session.scalar(select(func.count(Ticket.id)))
    audit_count_before = db.session.scalar(select(func.count(AuditLog.id)))

    _login_as(client, "admin_sarpras")

    # Panggil beberapa kali dengan filter berbeda
    client.get("/dashboard/api/chart-data")
    client.get("/dashboard/api/chart-data?days=7")
    client.get("/dashboard/api/chart-data?category=K1&floor=2")

    ticket_count_after = db.session.scalar(select(func.count(Ticket.id)))
    audit_count_after = db.session.scalar(select(func.count(AuditLog.id)))

    assert ticket_count_after == ticket_count_before
    assert audit_count_after == audit_count_before
