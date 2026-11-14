"""
Pengujian Komprehensif TSK-F5-03:
Pencarian dan Filter Tiket Multi-Kriteria (FR-08).

Mencakup seluruh Acceptance Criteria (AC-1 s.d. AC-7):
1. AC-1: Pencarian teks bebas (kode tiket case-insensitive & kata kunci deskripsi).
2. AC-2: Filter kategori dinamis berbasis ID database (penolakan ID invalid / non-integer).
3. AC-3: Filter status (default 'Baru', navigasi pagination saja tetap 'Baru',
   filter lain tanpa status mencari seluruh status, eksplisit 'all' / 'semua' / '', status invalid ditolak).
4. AC-4: Filter lokasi (lantai 1-4, penolakan lantai di luar 1-4 / non-integer, pencarian nama ruang).
5. AC-5: Filter rentang tanggal eksklusif (date_from, date_to + 1 hari, format ISO, penolakan tanggal terbalik).
6. AC-6: Penolakan eksplisit & retensi input pengguna saat terjadi kesalahan validasi (zero query on error).
7. AC-7: Paginasi aman bebas N+1 (db.paginate, batas per_page 1-50, retensi filter query string, RBAC).
"""
from datetime import datetime, timedelta, timezone
import hashlib
import secrets

import pytest
from sqlalchemy import delete, select
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.category import Category
from app.models.ticket import Ticket
from app.models.user import User
from app.services.complaint_service import MAX_PAGE, parse_and_validate_filter_params
from app.services.ticket_report import get_active_categories
from app.utils.ticket_identity import generate_ticket_code

PASSWORD = "Valid-Admin-Pass-123!"
PASSWORD_HASH = generate_password_hash(PASSWORD, method="scrypt")


@pytest.fixture()
def app():
    from app import create_app

    test_app = create_app("testing")
    test_app.config.update(TESTING=True, WTF_CSRF_ENABLED=True)

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
    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["role"] = user.role
        sess.permanent = True
    return user


def _create_dummy_ticket(
    *,
    code: str | None = None,
    description: str | None = None,
    status: str = "Baru",
    floor_number: int = 2,
    room_name: str = "Lab 2.1",
    reporter_category_id: int | None = None,
    predicted_category_id: int | None = None,
    official_category_id: int | None = None,
    assigned_technician_id: int | None = None,
    confidence_score: float | None = None,
    created_at: datetime | None = None,
) -> Ticket:
    ticket_code = code or generate_ticket_code()
    token_seed = secrets.token_hex(16)
    token_hash = hashlib.sha256(token_seed.encode("ascii")).hexdigest()

    ticket = Ticket(
        ticket_code=ticket_code,
        access_token_hash=token_hash,
        description=description or f"Keluhan fasilitas untuk {ticket_code}",
        building_name="Gedung FTII",
        floor_number=floor_number,
        room_name=room_name,
        location_detail="Area tengah ruangan",
        status=status,
        needs_manual_verification=(status == "Baru"),
        reporter_category_id=reporter_category_id,
        predicted_category_id=predicted_category_id,
        official_category_id=official_category_id,
        assigned_technician_id=assigned_technician_id,
        confidence_score=confidence_score,
        created_at=created_at or datetime.now(timezone.utc),
    )
    db.session.add(ticket)
    db.session.flush()
    return ticket


# ==============================================================================
# 1. AC-1: Pencarian Teks Bebas (Kode Tiket & Deskripsi)
# ==============================================================================


def test_search_by_ticket_code_case_insensitive(client):
    _login_as(client, "admin_sarpras")
    t1 = _create_dummy_ticket(status="Baru")
    t2 = _create_dummy_ticket(status="Baru")
    db.session.commit()

    # Cari dengan huruf kecil dari kode tiket
    lower_code = t1.ticket_code.lower()
    resp = client.get(f"/admin/tiket?keyword={lower_code}")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert t1.ticket_code in html
    assert t2.ticket_code not in html

    # Cari sebagian karakter kode tiket
    sub_code = t2.ticket_code[3:7]
    resp = client.get(f"/admin/tiket?keyword={sub_code}")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert t2.ticket_code in html


def test_search_by_description_keyword(client):
    _login_as(client, "admin_sarpras")
    t_ac = _create_dummy_ticket(
        status="Baru",
        description="Air conditioner ruangan bocor menetes ke meja dosen",
    )
    t_proyektor = _create_dummy_ticket(
        status="Baru",
        description="Lampu proyektor mati saat kuliah kalkulus",
    )
    db.session.commit()

    resp = client.get("/admin/tiket?keyword=bocor")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert t_ac.ticket_code in html
    assert t_proyektor.ticket_code not in html


# ==============================================================================
# 2. AC-3: Filter Status, Default Antrean 'Baru', dan Multi-Kasus
# ==============================================================================


def test_default_queue_shows_status_baru_only(client):
    _login_as(client, "admin_sarpras")
    t_baru = _create_dummy_ticket(status="Baru")
    t_verif = _create_dummy_ticket(status="Terverifikasi")
    t_proses = _create_dummy_ticket(status="Diproses")
    t_selesai = _create_dummy_ticket(status="Selesai")
    db.session.commit()

    resp = client.get("/admin/tiket")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert t_baru.ticket_code in html
    assert t_verif.ticket_code not in html
    assert t_proses.ticket_code not in html
    assert t_selesai.ticket_code not in html


def test_pagination_only_preserves_default_status_baru(client):
    _login_as(client, "admin_sarpras")
    t_baru = _create_dummy_ticket(status="Baru")
    t_verif = _create_dummy_ticket(status="Terverifikasi")
    db.session.commit()

    # Navigasi hanya dengan parameter pagination
    resp = client.get("/admin/tiket?page=1&per_page=10")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert t_baru.ticket_code in html
    assert t_verif.ticket_code not in html


def test_filter_by_specific_status(client):
    _login_as(client, "admin_sarpras")
    t_baru = _create_dummy_ticket(status="Baru")
    t_verif = _create_dummy_ticket(status="Terverifikasi")
    t_selesai = _create_dummy_ticket(status="Selesai")
    db.session.commit()

    resp = client.get("/admin/tiket?status=Terverifikasi")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert t_verif.ticket_code in html
    assert t_baru.ticket_code not in html
    assert t_selesai.ticket_code not in html


def test_status_all_and_semua_and_empty_shows_all_statuses(client):
    _login_as(client, "admin_sarpras")
    t_baru = _create_dummy_ticket(status="Baru")
    t_verif = _create_dummy_ticket(status="Terverifikasi")
    t_selesai = _create_dummy_ticket(status="Selesai")
    db.session.commit()

    for s_val in ["all", "semua", ""]:
        resp = client.get(f"/admin/tiket?status={s_val}")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert t_baru.ticket_code in html
        assert t_verif.ticket_code in html
        assert t_selesai.ticket_code in html


def test_search_with_other_criteria_without_status_searches_all_statuses(client):
    _login_as(client, "admin_sarpras")
    t_baru = _create_dummy_ticket(
        status="Baru",
        description="Kerusakan saklar lampu lantai 3",
        floor_number=3,
    )
    t_selesai = _create_dummy_ticket(
        status="Selesai",
        description="Lampu gantung putus di lantai 3",
        floor_number=3,
    )
    t_lain = _create_dummy_ticket(
        status="Baru",
        description="Pintu rusak di lantai 1",
        floor_number=1,
    )
    db.session.commit()

    # Filter lantai=3 tanpa menyertakan status
    resp = client.get("/admin/tiket?floor_number=3")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert t_baru.ticket_code in html
    assert t_selesai.ticket_code in html
    assert t_lain.ticket_code not in html


# ==============================================================================
# 3. AC-2: Filter Kategori Resmi Dinamis dari Database
# ==============================================================================


def test_filter_by_official_category_from_database(client):
    _login_as(client, "admin_sarpras")
    categories = get_active_categories()
    assert len(categories) >= 2, "Minimal 2 kategori aktif diperlukan untuk pengujian."
    cat_a = categories[0]
    cat_b = categories[1]

    t_a = _create_dummy_ticket(
        status="Terverifikasi", official_category_id=cat_a.id
    )
    t_b = _create_dummy_ticket(
        status="Terverifikasi", official_category_id=cat_b.id
    )
    db.session.commit()

    resp = client.get(
        f"/admin/tiket?category_id={cat_a.id}&status=Terverifikasi"
    )
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert t_a.ticket_code in html
    assert t_b.ticket_code not in html


# ==============================================================================
# 4. AC-4: Filter Lokasi (Lantai dan Ruangan)
# ==============================================================================


def test_filter_by_floor_and_room_name(client):
    _login_as(client, "admin_sarpras")
    t_target = _create_dummy_ticket(
        status="Baru", floor_number=4, room_name="Lab Jaringan 402"
    )
    t_wrong_room = _create_dummy_ticket(
        status="Baru", floor_number=4, room_name="R. Dosen 401"
    )
    t_wrong_floor = _create_dummy_ticket(
        status="Baru", floor_number=2, room_name="Lab Jaringan 202"
    )
    db.session.commit()

    resp = client.get("/admin/tiket?floor_number=4&room_name=Jaringan")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert t_target.ticket_code in html
    assert t_wrong_room.ticket_code not in html
    assert t_wrong_floor.ticket_code not in html


# ==============================================================================
# 5. AC-5: Filter Rentang Tanggal Eksklusif
# ==============================================================================


def test_filter_by_date_range_exclusive_upper_bound(client):
    _login_as(client, "admin_sarpras")
    # Tanggal acuan: 2026-11-02 s.d. 2026-11-04
    dt_target_early = datetime(2026, 11, 2, 8, 30, tzinfo=timezone.utc)
    dt_target_late = datetime(2026, 11, 4, 23, 59, 58, tzinfo=timezone.utc)
    dt_too_early = datetime(2026, 11, 1, 23, 59, 59, tzinfo=timezone.utc)
    dt_too_late = datetime(2026, 11, 5, 0, 0, 1, tzinfo=timezone.utc)

    t_early = _create_dummy_ticket(status="Baru", created_at=dt_target_early)
    t_late = _create_dummy_ticket(status="Baru", created_at=dt_target_late)
    t_before = _create_dummy_ticket(status="Baru", created_at=dt_too_early)
    t_after = _create_dummy_ticket(status="Baru", created_at=dt_too_late)
    db.session.commit()

    resp = client.get("/admin/tiket?date_from=2026-11-02&date_to=2026-11-04")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert t_early.ticket_code in html
    assert t_late.ticket_code in html
    assert t_before.ticket_code not in html
    assert t_after.ticket_code not in html


# ==============================================================================
# 6. Kombinasi Filter Multi-Kriteria
# ==============================================================================


def test_combined_multi_criteria_filter(client):
    _login_as(client, "admin_sarpras")
    categories = get_active_categories()
    cat_ac = categories[0]
    cat_other = categories[1]

    # Tiket tepat yang memenuhi semua 5 kriteria
    t_match = _create_dummy_ticket(
        status="Terverifikasi",
        official_category_id=cat_ac.id,
        floor_number=3,
        room_name="Lab 305",
        description="AC tidak dingin keluar hawa panas",
        created_at=datetime(2026, 11, 3, 10, 0, tzinfo=timezone.utc),
    )
    # Tiket dengan status berbeda
    t_wrong_status = _create_dummy_ticket(
        status="Diproses",
        official_category_id=cat_ac.id,
        floor_number=3,
        room_name="Lab 305",
        description="AC bocor",
        created_at=datetime(2026, 11, 3, 10, 0, tzinfo=timezone.utc),
    )
    # Tiket dengan kategori berbeda
    t_wrong_cat = _create_dummy_ticket(
        status="Terverifikasi",
        official_category_id=cat_other.id,
        floor_number=3,
        room_name="Lab 305",
        description="AC mati",
        created_at=datetime(2026, 11, 3, 10, 0, tzinfo=timezone.utc),
    )
    db.session.commit()

    url = (
        f"/admin/tiket?keyword=AC&status=Terverifikasi"
        f"&category_id={cat_ac.id}&floor_number=3&room_name=305"
        f"&date_from=2026-11-01&date_to=2026-11-05"
    )
    resp = client.get(url)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert t_match.ticket_code in html
    assert t_wrong_status.ticket_code not in html
    assert t_wrong_cat.ticket_code not in html


# ==============================================================================
# 7. AC-6: Penolakan Eksplisit, Zero-Query, dan Retensi Input Form
# ==============================================================================


@pytest.mark.parametrize(
    ("query_params", "expected_error_snippet"),
    [
        ({"status": "InvalidStatus"}, "tidak valid"),
        ({"category_id": "bukan_angka"}, "harus berupa angka ID"),
        ({"category_id": "999999"}, "tidak valid atau tidak aktif"),
        ({"floor_number": "lima"}, "harus berupa angka antara 1 sampai 4"),
        ({"floor_number": "5"}, "harus berupa angka antara 1 sampai 4"),
        ({"floor_number": "0"}, "harus berupa angka antara 1 sampai 4"),
        ({"date_from": "02-11-2026"}, "Format tanggal awal tidak valid"),
        ({"date_to": "2026/11/04"}, "Format tanggal akhir tidak valid"),
        (
            {"date_from": "2026-11-10", "date_to": "2026-11-01"},
            "tidak boleh melebihi tanggal akhir",
        ),
        ({"page": "0"}, "minimal 1"),
        ({"page": "-5"}, "minimal 1"),
        ({"page": "abc"}, "minimal 1"),
        ({"per_page": "0"}, "antara 1 sampai 50"),
        ({"per_page": "51"}, "antara 1 sampai 50"),
        ({"per_page": "xyz"}, "antara 1 sampai 50"),
    ],
)
def test_explicit_validation_rejection(
    client, query_params, expected_error_snippet
):
    _login_as(client, "admin_sarpras")
    t_sample = _create_dummy_ticket(status="Baru")
    db.session.commit()

    resp = client.get("/admin/tiket", query_string=query_params)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # 1. Pesan validasi bahaya (danger flash) muncul
    assert expected_error_snippet in html

    # 2. Zero-query: tiket sama sekali tidak ditampilkan pada tabel
    assert t_sample.ticket_code not in html


def test_form_input_retention_on_validation_error(client):
    """Memverifikasi bahwa saat validasi gagal, seluruh nilai input pengguna tetap dipertahankan pada form."""
    _login_as(client, "admin_sarpras")
    t_sample = _create_dummy_ticket(status="Baru")
    db.session.commit()

    # Kirim input form lengkap, tapi dengan tanggal terbalik untuk memicu error
    params = {
        "keyword": "Keluhan Spesifik AC Ruang 202",
        "room_name": "Ruang Dosen 202",
        "floor_number": "2",
        "date_from": "2026-11-15",
        "date_to": "2026-11-01",  # Terbalik!
    }
    resp = client.get("/admin/tiket", query_string=params)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # Error message muncul
    assert "tidak boleh melebihi tanggal akhir" in html

    # Zero-query: tiket tidak ditampilkan
    assert t_sample.ticket_code not in html

    # Seluruh input form pengguna dipertahankan
    assert 'value="Keluhan Spesifik AC Ruang 202"' in html
    assert 'value="Ruang Dosen 202"' in html
    assert 'value="2" selected' in html
    assert 'value="2026-11-15"' in html
    assert 'value="2026-11-01"' in html


# ==============================================================================
# 8. AC-7: Paginasi Aman, Kontrol Navigasi, dan RBAC
# ==============================================================================


def test_pagination_limits_and_navigation(client):
    _login_as(client, "admin_sarpras")
    tickets = [_create_dummy_ticket(status="Baru") for _ in range(5)]
    db.session.commit()

    # Per_page = 2 -> Halaman 1 menghasilkan 2 tiket
    resp = client.get("/admin/tiket?per_page=2&page=1")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Halaman <strong>1</strong> dari <strong>3</strong>" in html

    # Halaman 2 menghasilkan tiket berikutnya
    resp_page2 = client.get("/admin/tiket?per_page=2&page=2")
    assert resp_page2.status_code == 200
    html_page2 = resp_page2.get_data(as_text=True)
    assert "Halaman <strong>2</strong> dari <strong>3</strong>" in html_page2

    # Link pagination mempertahankan query string
    assert "per_page=2" in html_page2


@pytest.mark.parametrize("role", ["teknisi", "pimpinan"])
def test_search_and_filter_rbac_rejected_for_non_admin(client, role):
    _login_as(client, role)
    resp = client.get("/admin/tiket?keyword=ac")
    assert resp.status_code == 403


def test_search_and_filter_unauthenticated_redirects_to_login(client):
    resp = client.get("/admin/tiket?keyword=ac")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/auth/login")


def test_admin_page_boundaries_accepted():
    for raw_page, expected in (("1", 1), (str(MAX_PAGE), MAX_PAGE)):
        validated, errors = parse_and_validate_filter_params({"page": raw_page})
        assert errors == {}
        assert validated["page"] == expected


@pytest.mark.parametrize(
    "raw_page",
    ["0", str(MAX_PAGE + 1), "abc", "1.5", "9" * 100, "9" * 5000],
)
def test_admin_page_invalid_values_rejected(raw_page):
    validated, errors = parse_and_validate_filter_params({"page": raw_page})
    assert validated is None
    assert "page" in errors


def test_admin_invalid_page_rejected_before_category_query(monkeypatch):
    def fail_if_called():
        pytest.fail("get_active_categories dipanggil sebelum validasi page")

    monkeypatch.setattr(
        "app.services.complaint_service.get_active_categories", fail_if_called
    )
    validated, errors = parse_and_validate_filter_params(
        {"page": str(MAX_PAGE + 1), "category_id": "1"}
    )
    assert validated is None
    assert "page" in errors
