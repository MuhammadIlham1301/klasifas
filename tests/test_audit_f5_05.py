"""
Pengujian Komprehensif TSK-F5-05:
Tampilan Riwayat Audit (FR-09).

Mencakup seluruh kriteria penerimaan (AC-1 s.d. AC-7):
1. AC-1: Otorisasi & pembatasan hak akses server-side (admin_sarpras only; teknisi & pimpinan 403, reporter redirected to login).
2. AC-2: Read-only & immutability mutlak (GET only, POST/PUT/PATCH/DELETE 405, data AuditLog & Ticket tidak bermutasi).
3. AC-3: Kelengkapan informasi audit (waktu WIB, tiket, aktor & role, aksi, nilai lama/baru, note).
4. AC-4: Historical category mapping (kategori nonaktif tetap terbaca, fallback unknown ID "ID: xxx").
5. AC-5: Paginasi dan pengurutan kronologis terbalik (created_at desc, id desc, retensi query params).
6. AC-6: Validasi filter eksplisit ("category_changed", "status_changed", "technician_assigned", "", "all", "semua")
   & zero audit-data query pada kegagalan validasi.
7. AC-7: Proteksi data sensitif (tanpa leak token/password hash) & Jinja autoescape XSS protection.
"""
from datetime import datetime, timezone
import hashlib
import secrets
from unittest.mock import patch

import pytest
from sqlalchemy import delete, event, select
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.category import Category
from app.models.ticket import TICKET_STATUSES, Ticket
from app.models.user import User
from app.services.audit_service import (
    VALID_AUDIT_ACTIONS,
    get_all_categories_map,
    get_audit_logs_paginated,
    parse_and_validate_audit_filter_params,
)
from app.utils.ticket_identity import generate_ticket_code

PASSWORD = "Valid-Test-Pass-123!"
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
    access_token_hash: str | None = None,
    created_at: datetime | None = None,
) -> Ticket:
    ticket_code = code or generate_ticket_code()
    if access_token_hash is None:
        token_seed = secrets.token_hex(16)
        access_token_hash = hashlib.sha256(token_seed.encode("ascii")).hexdigest()

    ticket = Ticket(
        ticket_code=ticket_code,
        access_token_hash=access_token_hash,
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


def _create_audit_log(
    *,
    ticket_id: int,
    actor_user_id: int | None = None,
    actor_role: str | None = None,
    action: str = "status_changed",
    field_name: str = "status",
    old_value: str | None = None,
    new_value: str | None = None,
    note: str | None = None,
    created_at: datetime | None = None,
) -> AuditLog:
    log = AuditLog(
        ticket_id=ticket_id,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        action=action,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
        note=note,
        created_at=created_at or datetime.now(timezone.utc),
    )
    db.session.add(log)
    db.session.flush()
    return log


# ==============================================================================
# 1. AC-1: Otorisasi & Pembatasan Hak Akses Server-Side
# ==============================================================================


def test_audit_log_page_unauthenticated_redirects_to_login(client):
    """Pengguna tanpa login dialihkan secara aman ke halaman login."""
    resp = client.get("/admin/audit-log")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers.get("Location", "")


def test_audit_log_page_non_admin_roles_forbidden(client):
    """Pengguna staf non-admin (teknisi, pimpinan) ditolak dengan 403, reporter dialihkan ke login."""
    for staff_role in ["teknisi", "pimpinan"]:
        staff_client = client.application.test_client()
        _login_as(staff_client, staff_role)
        resp = staff_client.get("/admin/audit-log")
        assert resp.status_code == 403, f"Role {staff_role} seharusnya mendapat 403"

    reporter_client = client.application.test_client()
    _login_as(reporter_client, "reporter")
    resp_rep = reporter_client.get("/admin/audit-log")
    assert resp_rep.status_code == 302
    assert "/auth/login" in resp_rep.headers.get("Location", "")


def test_audit_log_page_admin_sarpras_access_success(client):
    """Admin Sarpras berhasil mengakses halaman riwayat log audit (200 OK)."""
    admin = _login_as(client, "admin_sarpras")
    ticket = _create_dummy_ticket(status="Baru")
    _create_audit_log(
        ticket_id=ticket.id,
        actor_user_id=admin.id,
        actor_role=admin.role,
        action="status_changed",
        old_value=None,
        new_value="Baru",
        note="Initial log entry",
    )
    db.session.commit()

    resp = client.get("/admin/audit-log")
    assert resp.status_code == 200
    assert "Riwayat Log Audit Operasional" in resp.text
    assert "Filter Log Audit" in resp.text
    assert "Waktu" in resp.text
    assert "Tiket" in resp.text
    assert "Aktor" in resp.text


# ==============================================================================
# 2. AC-2: Read-Only & Immutability Mutlak
# ==============================================================================


def test_audit_log_page_strictly_readonly_methods(client):
    """Endpoint /admin/audit-log strictly read-only; metode selain GET ditolak 405."""
    _login_as(client, "admin_sarpras")

    for method in ["post", "put", "patch", "delete"]:
        caller = getattr(client, method)
        resp = caller("/admin/audit-log")
        assert resp.status_code == 405, f"Metode {method.upper()} harus ditolak dengan 405"


def test_audit_log_view_and_filtering_does_not_mutate_data(client):
    """
    Membuka halaman dan memicu filter terbukti tidak menambah, memodifikasi,
    atau menghapus data AuditLog DAN Ticket di basis data.
    """
    admin = _login_as(client, "admin_sarpras")
    t1 = _create_dummy_ticket(status="Baru")
    t2 = _create_dummy_ticket(status="Terverifikasi")

    _create_audit_log(
        ticket_id=t1.id,
        actor_user_id=admin.id,
        actor_role=admin.role,
        action="status_changed",
        old_value=None,
        new_value="Baru",
        note="Initial log 1",
    )
    _create_audit_log(
        ticket_id=t2.id,
        actor_user_id=admin.id,
        actor_role=admin.role,
        action="category_changed",
        old_value="1",
        new_value="2",
        note="Initial log 2",
    )
    db.session.commit()

    # Capture snapshot sebelum akses halaman & filter
    audit_count_before = len(db.session.scalars(select(AuditLog)).all())
    ticket_count_before = len(db.session.scalars(select(Ticket)).all())
    audit_snapshot_before = [
        (l.id, l.ticket_id, l.action, l.old_value, l.new_value, l.note, l.created_at)
        for l in db.session.scalars(select(AuditLog).order_by(AuditLog.id)).all()
    ]
    ticket_snapshot_before = [
        (t.id, t.ticket_code, t.status, t.official_category_id, t.assigned_technician_id, t.updated_at)
        for t in db.session.scalars(select(Ticket).order_by(Ticket.id)).all()
    ]

    # Eksekusi berbagai request baca dan penyaringan
    client.get("/admin/audit-log")
    client.get("/admin/audit-log?action=status_changed")
    client.get(f"/admin/audit-log?ticket_code={t1.ticket_code}")
    client.get("/admin/audit-log?action=all&per_page=10&page=1")
    client.get("/admin/audit-log?action=invalid_hack&page=-5")

    # Capture snapshot sesudah seluruh request
    audit_count_after = len(db.session.scalars(select(AuditLog)).all())
    ticket_count_after = len(db.session.scalars(select(Ticket)).all())
    audit_snapshot_after = [
        (l.id, l.ticket_id, l.action, l.old_value, l.new_value, l.note, l.created_at)
        for l in db.session.scalars(select(AuditLog).order_by(AuditLog.id)).all()
    ]
    ticket_snapshot_after = [
        (t.id, t.ticket_code, t.status, t.official_category_id, t.assigned_technician_id, t.updated_at)
        for t in db.session.scalars(select(Ticket).order_by(Ticket.id)).all()
    ]

    # Verifikasi immutability mutlak
    assert audit_count_after == audit_count_before
    assert ticket_count_after == ticket_count_before
    assert audit_snapshot_after == audit_snapshot_before
    assert ticket_snapshot_after == ticket_snapshot_before


# ==============================================================================
# 3. AC-3 & AC-5: Kronologi Terbalik & Kelengkapan Informasi
# ==============================================================================


def test_audit_log_displays_chronological_order(client):
    """Log audit disajikan dalam urutan kronologis terbalik (terbaru di atas)."""
    admin = _login_as(client, "admin_sarpras")
    ticket = _create_dummy_ticket()

    _create_audit_log(
        ticket_id=ticket.id,
        actor_user_id=admin.id,
        actor_role=admin.role,
        note="Audit Log Paling Pertama 2026-01-01",
        created_at=datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc),
    )
    _create_audit_log(
        ticket_id=ticket.id,
        actor_user_id=admin.id,
        actor_role=admin.role,
        note="Audit Log Kedua 2026-01-02",
        created_at=datetime(2026, 1, 2, 8, 0, tzinfo=timezone.utc),
    )
    _create_audit_log(
        ticket_id=ticket.id,
        actor_user_id=admin.id,
        actor_role=admin.role,
        note="Audit Log Paling Baru 2026-01-03",
        created_at=datetime(2026, 1, 3, 8, 0, tzinfo=timezone.utc),
    )
    db.session.commit()

    resp = client.get("/admin/audit-log")
    assert resp.status_code == 200

    idx_terbaru = resp.text.find("Audit Log Paling Baru 2026-01-03")
    idx_kedua = resp.text.find("Audit Log Kedua 2026-01-02")
    idx_pertama = resp.text.find("Audit Log Paling Pertama 2026-01-01")

    assert idx_terbaru != -1
    assert idx_kedua != -1
    assert idx_pertama != -1
    assert idx_terbaru < idx_kedua < idx_pertama


def test_audit_log_displays_category_change_details(client):
    """Menampilkan rincian mutasi kategori resmi secara lengkap dan akurat."""
    admin = _login_as(client, "admin_sarpras", "admin_verifikator")
    categories = db.session.scalars(select(Category).order_by(Category.id)).all()
    assert len(categories) >= 2, "Perlu minimal 2 kategori untuk pengujian"
    cat_old = categories[0]
    cat_new = categories[1]

    ticket = _create_dummy_ticket()
    _create_audit_log(
        ticket_id=ticket.id,
        actor_user_id=admin.id,
        actor_role=admin.role,
        action="category_changed",
        field_name="official_category_id",
        old_value=str(cat_old.id),
        new_value=str(cat_new.id),
        note="Koreksi kategori dari lab ke kelistrikan",
    )
    db.session.commit()

    resp = client.get("/admin/audit-log")
    assert resp.status_code == 200
    assert ticket.ticket_code in resp.text
    assert admin.full_name in resp.text
    assert admin.username in resp.text
    assert "Perubahan Kategori" in resp.text
    assert f"{cat_old.code} - {cat_old.name}" in resp.text
    assert f"{cat_new.code} - {cat_new.name}" in resp.text
    assert "Koreksi kategori dari lab ke kelistrikan" in resp.text


# ==============================================================================
# 4. AC-4: Historical Category Mapping & Fallback Unknown ID
# ==============================================================================


def test_audit_log_displays_inactive_historical_category_and_unknown_id_fallback(client):
    """
    Kategori nonaktif tetap dipetakan namanya, dan ID kategori yang tidak ada
    di basis data menampilkan fallback ID mentah tanpa kegagalan sistem.
    """
    admin = _login_as(client, "admin_sarpras")

    # Ambil kategori yang ada dan tandai sebagai nonaktif
    cat_to_inactivate = db.session.scalar(select(Category).where(Category.code == "K7"))
    assert cat_to_inactivate is not None
    cat_to_inactivate.is_active = False
    db.session.flush()

    ticket = _create_dummy_ticket()
    _create_audit_log(
        ticket_id=ticket.id,
        actor_user_id=admin.id,
        actor_role=admin.role,
        action="category_changed",
        field_name="official_category_id",
        old_value=str(cat_to_inactivate.id),
        new_value="999888",  # ID kategori tidak ada di DB
        note="Uji coba fallback historical",
    )
    db.session.commit()

    resp = client.get("/admin/audit-log")
    assert resp.status_code == 200
    # Kategori nonaktif harus tetap tampil namanya
    assert f"{cat_to_inactivate.code} - {cat_to_inactivate.name}" in resp.text
    # ID yang tidak terdaftar harus tampil sebagai fallback ID mentah
    assert "ID: 999888" in resp.text


def test_audit_log_displays_status_change_details(client):
    """Menampilkan transisi status resmi beserta badge semantik yang konsisten."""
    admin = _login_as(client, "admin_sarpras")
    ticket = _create_dummy_ticket()

    _create_audit_log(
        ticket_id=ticket.id,
        actor_user_id=admin.id,
        actor_role=admin.role,
        action="status_changed",
        field_name="status",
        old_value="Baru",
        new_value="Terverifikasi",
        note="Tiket telah diperiksa dan dinyatakan valid",
    )
    db.session.commit()

    resp = client.get("/admin/audit-log")
    assert resp.status_code == 200
    assert "Perubahan Status" in resp.text
    assert "Baru" in resp.text
    assert "Terverifikasi" in resp.text
    assert "Tiket telah diperiksa dan dinyatakan valid" in resp.text


def test_audit_log_displays_technician_assignment_details(client):
    """Menampilkan rincian aksi technician_assigned secara kompatibel."""
    admin = _login_as(client, "admin_sarpras")
    tech = _create_user("teknisi_lapangan", "teknisi")
    ticket = _create_dummy_ticket()

    _create_audit_log(
        ticket_id=ticket.id,
        actor_user_id=admin.id,
        actor_role=admin.role,
        action="technician_assigned",
        field_name="assigned_technician_id",
        old_value=None,
        new_value=str(tech.id),
        note="Ditugaskan untuk perbaikan mendesak",
    )
    db.session.commit()

    resp = client.get("/admin/audit-log")
    assert resp.status_code == 200
    assert "Penugasan Teknisi" in resp.text
    assert "Belum ditugaskan" in resp.text
    assert str(tech.id) in resp.text
    assert "Ditugaskan untuk perbaikan mendesak" in resp.text


# ==============================================================================
# 5. AC-5 & AC-6: Filter, Paginasi, dan Validasi
# ==============================================================================


def test_audit_log_pagination_limits_and_navigation(client):
    """Paginasi membatasi entri per halaman dan mempertahankan parameter aktif."""
    admin = _login_as(client, "admin_sarpras")
    ticket = _create_dummy_ticket()

    # Buat 25 entri audit log
    for i in range(25):
        _create_audit_log(
            ticket_id=ticket.id,
            actor_user_id=admin.id,
            actor_role=admin.role,
            action="status_changed",
            old_value="Baru",
            new_value="Terverifikasi",
            note=f"Entri Paginasi Nomor {i+1:02d}",
            created_at=datetime(2026, 1, 1, 0, i, tzinfo=timezone.utc),
        )
    db.session.commit()

    # Halaman 1 default per_page=20
    resp_p1 = client.get("/admin/audit-log")
    assert resp_p1.status_code == 200
    assert "Entri Paginasi Nomor 25" in resp_p1.text
    assert "Entri Paginasi Nomor 06" in resp_p1.text
    assert "Entri Paginasi Nomor 05" not in resp_p1.text  # Berada di halaman 2

    # Halaman 2
    resp_p2 = client.get("/admin/audit-log?page=2")
    assert resp_p2.status_code == 200
    assert "Entri Paginasi Nomor 05" in resp_p2.text
    assert "Entri Paginasi Nomor 01" in resp_p2.text

    # Custom per_page=10 dengan filter aksi
    resp_custom = client.get("/admin/audit-log?action=status_changed&per_page=10&page=1")
    assert resp_custom.status_code == 200
    # Verifikasi link paginasi mempertahankan parameter
    assert "action=status_changed" in resp_custom.text
    assert "per_page=10" in resp_custom.text


def test_audit_log_filter_by_action(client):
    """Penyaringan berdasarkan action (category_changed, status_changed, technician_assigned, all, semua)."""
    admin = _login_as(client, "admin_sarpras")
    ticket = _create_dummy_ticket()

    _create_audit_log(
        ticket_id=ticket.id,
        actor_user_id=admin.id,
        actor_role=admin.role,
        action="category_changed",
        field_name="official_category_id",
        old_value="1",
        new_value="2",
        note="UNIK_AKSI_KATEGORI",
    )
    _create_audit_log(
        ticket_id=ticket.id,
        actor_user_id=admin.id,
        actor_role=admin.role,
        action="status_changed",
        field_name="status",
        old_value="Baru",
        new_value="Terverifikasi",
        note="UNIK_AKSI_STATUS",
    )
    _create_audit_log(
        ticket_id=ticket.id,
        actor_user_id=admin.id,
        actor_role=admin.role,
        action="technician_assigned",
        field_name="assigned_technician_id",
        old_value=None,
        new_value="10",
        note="UNIK_AKSI_TEKNISI",
    )
    db.session.commit()

    # Filter category_changed
    r_cat = client.get("/admin/audit-log?action=category_changed")
    assert "UNIK_AKSI_KATEGORI" in r_cat.text
    assert "UNIK_AKSI_STATUS" not in r_cat.text
    assert "UNIK_AKSI_TEKNISI" not in r_cat.text

    # Filter status_changed
    r_stat = client.get("/admin/audit-log?action=status_changed")
    assert "UNIK_AKSI_STATUS" in r_stat.text
    assert "UNIK_AKSI_KATEGORI" not in r_stat.text
    assert "UNIK_AKSI_TEKNISI" not in r_stat.text

    # Filter technician_assigned
    r_tech = client.get("/admin/audit-log?action=technician_assigned")
    assert "UNIK_AKSI_TEKNISI" in r_tech.text
    assert "UNIK_AKSI_KATEGORI" not in r_tech.text
    assert "UNIK_AKSI_STATUS" not in r_tech.text

    # Filter all dan semua
    r_all = client.get("/admin/audit-log?action=all")
    assert "UNIK_AKSI_KATEGORI" in r_all.text
    assert "UNIK_AKSI_STATUS" in r_all.text
    assert "UNIK_AKSI_TEKNISI" in r_all.text

    r_semua = client.get("/admin/audit-log?action=semua")
    assert "UNIK_AKSI_KATEGORI" in r_semua.text
    assert "UNIK_AKSI_STATUS" in r_semua.text
    assert "UNIK_AKSI_TEKNISI" in r_semua.text


def test_audit_log_filter_by_ticket_code(client):
    """Penyaringan berdasarkan kode tiket (substring case-insensitive)."""
    admin = _login_as(client, "admin_sarpras")
    t1 = _create_dummy_ticket()
    t2 = _create_dummy_ticket()

    _create_audit_log(
        ticket_id=t1.id,
        actor_user_id=admin.id,
        actor_role=admin.role,
        note="LOG_KHUSUS_ALPHA",
    )
    _create_audit_log(
        ticket_id=t2.id,
        actor_user_id=admin.id,
        actor_role=admin.role,
        note="LOG_KHUSUS_BETA",
    )
    db.session.commit()

    sub_code = t1.ticket_code[3:6].lower()
    resp = client.get(f"/admin/audit-log?ticket_code={sub_code}")
    assert resp.status_code == 200
    assert "LOG_KHUSUS_ALPHA" in resp.text
    assert "LOG_KHUSUS_BETA" not in resp.text


def test_audit_log_explicit_validation_rejection_and_retention(client):
    """Input filter invalid ditolak secara eksplisit dengan pesan error, mempertahankan input, dan tidak memperluas hasil."""
    _login_as(client, "admin_sarpras")
    ticket = _create_dummy_ticket()
    _create_audit_log(ticket_id=ticket.id, note="LOG_VALID_TERSELEKSI")
    db.session.commit()

    # 1. Action invalid
    resp_act = client.get("/admin/audit-log?action=aksi_palsu_ilegal")
    assert resp_act.status_code == 200
    assert "Aksi audit &#39;aksi_palsu_ilegal&#39; tidak valid" in resp_act.text or "Aksi audit 'aksi_palsu_ilegal' tidak valid" in resp_act.text
    assert "LOG_VALID_TERSELEKSI" not in resp_act.text

    # 2. Ticket code melebihi 20 karakter
    long_code = "A" * 25
    resp_code = client.get(f"/admin/audit-log?ticket_code={long_code}")
    assert resp_code.status_code == 200
    assert "Kode tiket tidak boleh melebihi 20 karakter." in resp_code.text
    assert "LOG_VALID_TERSELEKSI" not in resp_code.text
    assert long_code in resp_code.text  # Retensi input

    # 3. Page non-integer atau negatif
    resp_page = client.get("/admin/audit-log?page=0")
    assert resp_page.status_code == 200
    assert "Nomor halaman harus bernilai minimal 1." in resp_page.text
    assert "LOG_VALID_TERSELEKSI" not in resp_page.text

    resp_page_str = client.get("/admin/audit-log?page=abc")
    assert resp_page_str.status_code == 200
    assert "Nomor halaman harus berupa bilangan bulat positif." in resp_page_str.text

    # 4. Per_page di luar rentang 1-50
    resp_pp = client.get("/admin/audit-log?per_page=999")
    assert resp_pp.status_code == 200
    assert "Jumlah data per halaman harus antara 1 sampai 50." in resp_pp.text


# ==============================================================================
# 6. AC-6: Zero Audit-Data Query on Error
# ==============================================================================


def test_audit_log_invalid_filter_executes_zero_audit_data_queries(client, app):
    """
    Validasi filter yang gagal sama sekali tidak mengeksekusi query data fitur audit
    (khususnya tabel categories, audit_logs, dan tickets).
    """
    _login_as(client, "admin_sarpras")

    captured_queries = []

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        stmt_lower = statement.lower()
        captured_queries.append(stmt_lower)

    # Pasang listener SQL
    event.listen(db.engine, "before_cursor_execute", before_cursor_execute)

    try:
        with patch("app.routes.admin.get_all_categories_map") as mock_cat_map, \
             patch("app.routes.admin.get_audit_logs_paginated") as mock_logs_paginated:

            resp = client.get("/admin/audit-log?action=aksi_tidak_dikenal&ticket_code=KF-TEST")
            assert resp.status_code == 200

            # Pastikan fungsi query service tidak pernah dipanggil
            assert mock_cat_map.called is False
            assert mock_logs_paginated.called is False

        # Periksa query database yang terekam
        for q in captured_queries:
            # Query sesi autentikasi pada tabel users diizinkan, tetapi tabel data audit dilarang
            assert "from audit_logs" not in q
            assert "from categories" not in q
            assert "from tickets" not in q

    finally:
        event.remove(db.engine, "before_cursor_execute", before_cursor_execute)


# ==============================================================================
# 7. AC-7: Proteksi Data Sensitif & Sanitasi Output (XSS)
# ==============================================================================


def test_audit_log_no_sensitive_data_leaked_and_xss_protection(client):
    """
    Log audit tidak mengekspos hash token akses, hash password, dan teks catatan
    di-escape secara aman oleh Jinja2 tanpa bypass | safe.
    """
    admin = _login_as(client, "admin_sarpras")
    secret_token_hash = "rahasia_super_kritis_access_token_hash_987654321"

    ticket = _create_dummy_ticket(
        access_token_hash=secret_token_hash,
    )

    xss_payload = "<script>alert('XSS_AUDIT_LOG_ATTACK')</script><b>Bold Note</b>"
    _create_audit_log(
        ticket_id=ticket.id,
        actor_user_id=admin.id,
        actor_role=admin.role,
        note=xss_payload,
    )
    db.session.commit()

    resp = client.get("/admin/audit-log")
    assert resp.status_code == 200

    # 1. Data sensitif tidak boleh bocor
    assert secret_token_hash not in resp.text
    assert admin.password_hash not in resp.text

    # 2. XSS dicegah melalui Jinja autoescaping
    assert "<script>alert('XSS_AUDIT_LOG_ATTACK')</script>" not in resp.text
    assert "&lt;script&gt;alert(" in resp.text
    assert "&lt;b&gt;Bold Note&lt;/b&gt;" in resp.text
    assert "<b>Bold Note</b>" not in resp.text


# ==============================================================================
# 8. Kompatibilitas Regresi Kartu Audit Verifikasi Tiket
# ==============================================================================


def test_ticket_verification_detail_audit_card_remains_functional(client):
    """Kartu audit pada halaman verifikasi tiket tunggal (/admin/tiket/<id>/verifikasi) tetap berfungsi."""
    admin = _login_as(client, "admin_sarpras")
    ticket = _create_dummy_ticket(status="Baru")

    _create_audit_log(
        ticket_id=ticket.id,
        actor_user_id=admin.id,
        actor_role=admin.role,
        action="status_changed",
        old_value=None,
        new_value="Baru",
        note="Pencatatan status awal pada kartu detail",
    )
    db.session.commit()

    resp = client.get(f"/admin/tiket/{ticket.id}/verifikasi")
    assert resp.status_code == 200
    assert "Riwayat Audit Operasional" in resp.text
    assert "Pencatatan status awal pada kartu detail" in resp.text
