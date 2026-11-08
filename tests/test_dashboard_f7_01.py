"""
Pengujian Terarah TSK-F7-01:
Layanan Pengolahan Data Agregat Dashboard (FR-07).

Mencakup seluruh 12 skenario pengujian:
1. test_kpi_summary_empty_database: Database kosong aman dari ZeroDivisionError (completion_rate = 0.0).
2. test_kpi_summary_accuracy_with_multi_status_data: Akurasi KPI 4 status resmi & penyelesaian.
3. test_category_distribution_empty_database_all_seven_present: 7 kategori K1–K7 tetap muncul saat tiket kosong.
4. test_category_distribution_count_and_percentage_accuracy: Akurasi hitungan & persentase kategori K1–K7.
5. test_category_distribution_unverified_tickets_handling: Tiket baru tanpa kategori resmi masuk unverified_count.
6. test_ticket_trends_empty_database_zero_filled: Tren 30 hari zero-filled pada database kosong.
7. test_ticket_trends_boundary_timezone_and_chronological_order: Batas inklusif UTC, timezone, & kronologi ascending.
8. test_location_distribution_empty_database_floors_present: Lantai 1–4 tetap terdaftar pada database kosong.
9. test_location_distribution_accuracy_and_ranking: Akurasi lantai 1–4 & ranking top rooms descending.
10. test_location_distribution_null_and_whitespace_room_handling: Sanitasi trim ruangan & unverified/unspecified count.
11. test_privacy_strict_zero_pii_in_all_service_outputs: Verifikasi ketat Zero PII pada seluruh return value.
12. test_read_only_integrity_no_state_mutation_or_audit_generation: Sifat murni read-only tanpa mutasi & tanpa audit log.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import secrets

import pytest
from sqlalchemy import delete, func, select

from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.category import Category
from app.models.ticket import Ticket
from app.models.user import User
from app.services.dashboard_service import (
    get_category_distribution,
    get_dashboard_summary_kpi,
    get_location_distribution,
    get_ticket_trends,
)
from app.utils.ticket_identity import generate_ticket_code


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
    """Helper membuat entri tiket untuk pengujian agregasi dashboard."""
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
# Skenario 1 s.d. 12 Pengujian TSK-F7-01
# ==============================================================================


def test_kpi_summary_empty_database(app):
    """Skenario 1: Database kosong aman dari ZeroDivisionError (completion_rate = 0.0)."""
    with app.app_context():
        # Pastikan tidak ada tiket
        db.session.execute(delete(Ticket))
        db.session.flush()

        kpi = get_dashboard_summary_kpi()

        assert kpi["total_tickets"] == 0
        assert isinstance(kpi["total_tickets"], int)
        assert kpi["status_counts"] == {
            "Baru": 0,
            "Terverifikasi": 0,
            "Diproses": 0,
            "Selesai": 0,
        }
        assert kpi["active_tickets"] == 0
        assert kpi["completion_rate"] == 0.0
        assert isinstance(kpi["completion_rate"], float)


def test_kpi_summary_accuracy_with_multi_status_data(app):
    """Skenario 2: Akurasi kalkulasi KPI 4 status resmi & rasio penyelesaian."""
    with app.app_context():
        db.session.execute(delete(Ticket))
        db.session.flush()

        # Buat: 2 Baru, 3 Terverifikasi, 4 Diproses, 6 Selesai (Total 15)
        for _ in range(2):
            _create_test_ticket(status="Baru")
        for _ in range(3):
            _create_test_ticket(status="Terverifikasi")
        for _ in range(4):
            _create_test_ticket(status="Diproses")
        for _ in range(6):
            _create_test_ticket(status="Selesai")

        kpi = get_dashboard_summary_kpi()

        assert kpi["total_tickets"] == 15
        assert kpi["status_counts"]["Baru"] == 2
        assert kpi["status_counts"]["Terverifikasi"] == 3
        assert kpi["status_counts"]["Diproses"] == 4
        assert kpi["status_counts"]["Selesai"] == 6

        # Invarian: total = sum(status_counts)
        assert sum(kpi["status_counts"].values()) == 15
        # Active = Baru + Terverifikasi + Diproses = 9
        assert kpi["active_tickets"] == 9
        # Completion rate = (6 / 15) * 100 = 40.0
        assert kpi["completion_rate"] == 40.0


def test_category_distribution_empty_database_all_seven_present(app):
    """Skenario 3: 7 kategori resmi (K1–K7) tetap muncul lengkap saat database tiket kosong."""
    with app.app_context():
        db.session.execute(delete(Ticket))
        db.session.flush()

        dist = get_category_distribution()

        categories = dist["categories"]
        assert len(categories) == 7

        expected_codes = ["K1", "K2", "K3", "K4", "K5", "K6", "K7"]
        actual_codes = [c["code"] for c in categories]
        assert actual_codes == expected_codes

        for cat in categories:
            assert cat["count"] == 0
            assert cat["percentage"] == 0.0

        assert dist["total_verified"] == 0
        assert dist["unverified_count"] == 0


def test_category_distribution_count_and_percentage_accuracy(app):
    """Skenario 4: Akurasi hitungan & persentase kategori K1–K7."""
    with app.app_context():
        db.session.execute(delete(Ticket))
        db.session.flush()

        cats = {
            c.code: c.id
            for c in db.session.scalars(select(Category)).all()
        }

        # Buat: 5 tiket K1, 3 tiket K2, 2 tiket K3 (Total verified = 10)
        for _ in range(5):
            _create_test_ticket(status="Terverifikasi", official_category_id=cats["K1"])
        for _ in range(3):
            _create_test_ticket(status="Diproses", official_category_id=cats["K2"])
        for _ in range(2):
            _create_test_ticket(status="Selesai", official_category_id=cats["K3"])

        dist = get_category_distribution()

        assert dist["total_verified"] == 10
        assert dist["unverified_count"] == 0

        cat_map = {c["code"]: c for c in dist["categories"]}
        assert cat_map["K1"]["count"] == 5
        assert cat_map["K1"]["percentage"] == 50.0

        assert cat_map["K2"]["count"] == 3
        assert cat_map["K2"]["percentage"] == 30.0

        assert cat_map["K3"]["count"] == 2
        assert cat_map["K3"]["percentage"] == 20.0

        # K4 s.d. K7 harus tetap hadir dengan count 0
        for code in ["K4", "K5", "K6", "K7"]:
            assert cat_map[code]["count"] == 0
            assert cat_map[code]["percentage"] == 0.0


def test_category_distribution_unverified_tickets_handling(app):
    """Skenario 5: Tiket berstatus 'Baru' tanpa kategori resmi masuk unverified_count."""
    with app.app_context():
        db.session.execute(delete(Ticket))
        db.session.flush()

        cat_k1 = db.session.scalar(select(Category).where(Category.code == "K1"))

        # 4 tiket baru (official_category_id IS NULL)
        for _ in range(4):
            _create_test_ticket(status="Baru", official_category_id=None)

        # 2 tiket terverifikasi K1
        for _ in range(2):
            _create_test_ticket(status="Terverifikasi", official_category_id=cat_k1.id)

        dist = get_category_distribution()

        assert dist["unverified_count"] == 4
        assert dist["total_verified"] == 2

        cat_map = {c["code"]: c for c in dist["categories"]}
        assert cat_map["K1"]["count"] == 2
        assert cat_map["K1"]["percentage"] == 100.0

        # Invarian kelengkapan data: total_verified + unverified = total tiket
        assert dist["total_verified"] + dist["unverified_count"] == 6


def test_ticket_trends_empty_database_zero_filled(app):
    """Skenario 6: Tren harian 10 hari zero-filled pada database kosong."""
    with app.app_context():
        db.session.execute(delete(Ticket))
        db.session.flush()

        trends = get_ticket_trends(days=10)

        assert len(trends) == 10
        for item in trends:
            assert isinstance(item["date"], str)
            assert len(item["date"]) == 10  # Format YYYY-MM-DD
            assert item["count"] == 0

        # Verifikasi urutan strictly ascending
        dates = [item["date"] for item in trends]
        assert dates == sorted(dates)


def test_ticket_trends_boundary_timezone_and_chronological_order(app):
    """Skenario 7: Batas inklusif UTC, presisi timezone, & urutan strictly ascending."""
    with app.app_context():
        db.session.execute(delete(Ticket))
        db.session.flush()

        fixed_end = datetime(2026, 11, 5, 12, 0, 0, tzinfo=timezone.utc)

        # Buat tiket dengan timestamp spesifik UTC:
        # Hari 1: 2026-11-01 -> 2 tiket
        _create_test_ticket(created_at=datetime(2026, 11, 1, 1, 0, 0, tzinfo=timezone.utc))
        _create_test_ticket(created_at=datetime(2026, 11, 1, 23, 0, 0, tzinfo=timezone.utc))

        # Hari 3: 2026-11-03 -> 1 tiket
        _create_test_ticket(created_at=datetime(2026, 11, 3, 14, 30, 0, tzinfo=timezone.utc))

        # Hari 5: 2026-11-05 -> 3 tiket
        for _ in range(3):
            _create_test_ticket(created_at=datetime(2026, 11, 5, 8, 0, 0, tzinfo=timezone.utc))

        # Tiket DI LUAR RENTANG (harus diabaikan):
        # Sebelum start (31 Oktober 2026)
        _create_test_ticket(created_at=datetime(2026, 10, 31, 23, 59, 59, tzinfo=timezone.utc))
        # Setelah end (6 November 2026)
        _create_test_ticket(created_at=datetime(2026, 11, 6, 0, 0, 1, tzinfo=timezone.utc))

        trends = get_ticket_trends(days=5, end_date=fixed_end)

        assert len(trends) == 5
        trend_map = {item["date"]: item["count"] for item in trends}

        assert trend_map["2026-11-01"] == 2
        assert trend_map["2026-11-02"] == 0  # Zero-filled
        assert trend_map["2026-11-03"] == 1
        assert trend_map["2026-11-04"] == 0  # Zero-filled
        assert trend_map["2026-11-05"] == 3

        # Pastikan tiket tanggal 31 Okt dan 6 Nov tidak masuk
        assert "2026-10-31" not in trend_map
        assert "2026-11-06" not in trend_map


def test_location_distribution_empty_database_floors_present(app):
    """Skenario 8: Lantai 1 s.d. 4 tetap terdaftar dengan count 0 saat database kosong."""
    with app.app_context():
        db.session.execute(delete(Ticket))
        db.session.flush()

        loc = get_location_distribution()

        assert loc["building_name"] == "Gedung FTII"
        assert len(loc["floors"]) == 4

        floors = {f["floor"]: f["count"] for f in loc["floors"]}
        assert floors == {1: 0, 2: 0, 3: 0, 4: 0}

        assert loc["top_rooms"] == []
        assert loc["unspecified_room_count"] == 0
        assert loc["other_floors_count"] == 0


def test_location_distribution_accuracy_and_ranking(app):
    """Skenario 9: Akurasi lantai 1–4 & ranking top rooms terurut descending."""
    with app.app_context():
        db.session.execute(delete(Ticket))
        db.session.flush()

        # Lantai 1: 3 tiket (2 Lab Komputer 1, 1 R. Kuliah 101)
        _create_test_ticket(floor_number=1, room_name="Lab Komputer 1")
        _create_test_ticket(floor_number=1, room_name="Lab Komputer 1")
        _create_test_ticket(floor_number=1, room_name="R. Kuliah 101")

        # Lantai 2: 4 tiket (semua di Lab Komputer 2)
        for _ in range(4):
            _create_test_ticket(floor_number=2, room_name="Lab Komputer 2")

        # Lantai 3: 1 tiket (Lab Komputer 1)
        _create_test_ticket(floor_number=3, room_name="Lab Komputer 1")

        # Lantai 4: 0 tiket

        loc = get_location_distribution()

        floor_map = {f["floor"]: f["count"] for f in loc["floors"]}
        assert floor_map[1] == 3
        assert floor_map[2] == 4
        assert floor_map[3] == 1
        assert floor_map[4] == 0

        # Verifikasi ranking top rooms
        # Lab Komputer 2: 4 tiket (peringkat 1)
        # Lab Komputer 1: 3 tiket (peringkat 2: 2 di lt 1 + 1 di lt 3)
        # R. Kuliah 101: 1 tiket (peringkat 3)
        top = loc["top_rooms"]
        assert len(top) == 3
        assert top[0] == {"room_name": "Lab Komputer 2", "count": 4}
        assert top[1] == {"room_name": "Lab Komputer 1", "count": 3}
        assert top[2] == {"room_name": "R. Kuliah 101", "count": 1}


def test_location_distribution_null_and_whitespace_room_handling(app):
    """Skenario 10: Sanitasi trim ruangan & pencatatan unspecified_room_count."""
    with app.app_context():
        db.session.execute(delete(Ticket))
        db.session.flush()

        # Tiket dengan room_name NULL (2 tiket)
        _create_test_ticket(floor_number=1, room_name=None)
        _create_test_ticket(floor_number=2, room_name=None)

        # Tiket dengan room_name kosong (2 tiket)
        _create_test_ticket(floor_number=1, room_name="")
        _create_test_ticket(floor_number=3, room_name="")

        # Tiket dengan room_name hanya spasi (1 tiket)
        _create_test_ticket(floor_number=2, room_name="   ")

        # Tiket dengan ruangan valid berjarak spasi padding (3 tiket)
        _create_test_ticket(floor_number=2, room_name="  Lab Jaringan  ")
        _create_test_ticket(floor_number=2, room_name="Lab Jaringan  ")
        _create_test_ticket(floor_number=2, room_name="Lab Jaringan")

        loc = get_location_distribution()

        # 2 (None) + 2 ("") + 1 ("   ") = 5
        assert loc["unspecified_room_count"] == 5

        # Seluruh spasi pada "Lab Jaringan" dinormalisasi menjadi 1 grup bernilai 3
        assert len(loc["top_rooms"]) == 1
        assert loc["top_rooms"][0] == {"room_name": "Lab Jaringan", "count": 3}


def test_privacy_strict_zero_pii_in_all_service_outputs(app):
    """Skenario 11: Verifikasi ketat Zero PII pada seluruh return value service."""
    with app.app_context():
        db.session.execute(delete(Ticket))
        db.session.flush()

        cat = db.session.scalar(select(Category).where(Category.code == "K1"))

        # Buat tiket lengkap dengan identitas sensitif pelapor
        _create_test_ticket(
            status="Terverifikasi",
            official_category_id=cat.id,
            reporter_name="Budi Santoso Rahasia",
            reporter_contact="081999888777",
            description="Isi pesan keluhan sensitif pelapor fasilitas",
        )

        kpi = get_dashboard_summary_kpi()
        cat_dist = get_category_distribution()
        trends = get_ticket_trends(days=7)
        loc = get_location_distribution()

        all_structures = [kpi, cat_dist, trends, loc]

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
            "Budi Santoso Rahasia",
            "081999888777",
            "Isi pesan keluhan sensitif pelapor fasilitas",
        }

        def _scan_obj(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    assert k not in forbidden_keys, f"PII key terdeteksi: {k}"
                    if isinstance(v, str):
                        for f_val in forbidden_values:
                            assert f_val not in v, f"PII value terdeteksi dalam {k}: {v}"
                    _scan_obj(v)
            elif isinstance(obj, list):
                for item in obj:
                    _scan_obj(item)

        for s in all_structures:
            _scan_obj(s)


def test_read_only_integrity_no_state_mutation_or_audit_generation(app):
    """Skenario 12: Sifat murni read-only tanpa mutasi tiket & tanpa audit log."""
    with app.app_context():
        db.session.execute(delete(Ticket))
        db.session.flush()

        cat = db.session.scalar(select(Category).where(Category.code == "K1"))
        _create_test_ticket(status="Terverifikasi", official_category_id=cat.id)

        # Catat baseline count
        ticket_count_before = db.session.scalar(select(func.count(Ticket.id)))
        audit_count_before = db.session.scalar(select(func.count(AuditLog.id)))

        # Panggil berulang kali seluruh fungsi service
        for _ in range(3):
            get_dashboard_summary_kpi()
            get_category_distribution()
            get_ticket_trends(days=14)
            get_location_distribution()

        # Verifikasi tidak ada mutasi state atau log audit baru
        ticket_count_after = db.session.scalar(select(func.count(Ticket.id)))
        audit_count_after = db.session.scalar(select(func.count(AuditLog.id)))

        assert ticket_count_after == ticket_count_before
        assert audit_count_after == audit_count_before
