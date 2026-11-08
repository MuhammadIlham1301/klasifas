"""
Pengujian Komprehensif TSK-F6-03:
Integrasi Audit Perubahan Status (FR-09).

Mencakup seluruh kriteria penerimaan (AC-1 s.d. AC-7):
1. Kelompok 1: Konsistensi Audit Siklus Hidup Penuh Antar-Peran:
   - Siklus hidup lengkap 1 tiket (Baru -> Terverifikasi -> Diproses -> Selesai)
     dengan pembedaan eksplisit antara audit perubahan status (3 entri) dan penugasan teknisi (1 entri).
   - Presisi metadata audit (aktor, timestamp server UTC, old_value, new_value).
   - Hak baca audit: Admin Sarpras dapat mengakses GET /admin/audit-log; Teknisi ditolak 403 Forbidden.
2. Kelompok 2: Pencegahan Celah Audit, Duplikasi & Idempotensi:
   - Tepat 1 rekaman audit per mutasi status yang berhasil (bebas duplikasi).
   - Operasi no-op menghasilkan changed=False dan 0 rekaman audit baru.
   - Transisi status ilegal ditolak tanpa menghasilkan audit palsu.
   - Rollback transaksi atomik mencegah orphan audit atau orphan status.
3. Kelompok 3: Integritas Catatan Tindakan & Batasan Jalur Mutasi HTTP:
   - Konsistensi teks 100% antara ticket.resolution_note dan AuditLog.note.
   - Penolakan penyelesaian tiket tanpa catatan menghasilkan 0 audit baru.
   - Batasan jalur HTTP audit (metode POST/PUT/PATCH/DELETE ditolak 405) dan proteksi foreign key ON DELETE RESTRICT.
"""
from datetime import datetime, timezone
import hashlib
import secrets
from unittest.mock import patch

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.category import Category
from app.models.ticket import Ticket
from app.models.user import User
from app.services.complaint_service import (
    InvalidTicketStatusError,
    assign_technician_to_ticket,
    transition_ticket_status,
    verify_ticket_category,
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
    location_detail: str | None = None,
    reporter_category_id: int | None = None,
    predicted_category_id: int | None = None,
    official_category_id: int | None = None,
    assigned_technician_id: int | None = None,
    confidence_score: float | None = None,
    access_token_hash: str | None = None,
    photo_filename: str | None = None,
    photo_mime_type: str | None = None,
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
        location_detail=location_detail or "Area tengah ruangan",
        status=status,
        needs_manual_verification=(status == "Baru"),
        reporter_category_id=reporter_category_id,
        predicted_category_id=predicted_category_id,
        official_category_id=official_category_id,
        assigned_technician_id=assigned_technician_id,
        confidence_score=confidence_score,
        photo_filename=photo_filename,
        photo_mime_type=photo_mime_type,
        photo_size_bytes=1024 if photo_filename else None,
        photo_uploaded_at=datetime.now(timezone.utc) if photo_filename else None,
        created_at=created_at or datetime.now(timezone.utc),
    )
    db.session.add(ticket)
    db.session.flush()
    return ticket


# ==============================================================================
# 1. Kelompok 1: Konsistensi Audit Siklus Hidup Penuh Antar-Peran (AC-1, AC-2, AC-3)
# ==============================================================================


def test_audit_lifecycle_full_cycle_admin_and_technician_consistency(app):
    """
    AC-1, AC-2, AC-3: Memverifikasi siklus hidup lengkap 1 tiket (Baru -> Terverifikasi -> Diproses -> Selesai)
    dengan membedakan secara eksplisit audit perubahan status (tepat 3 entri) dan penugasan teknisi (1 entri).
    Event penugasan tidak dihitung sebagai mutasi status.
    """
    with app.app_context():
        admin = _create_user("admin_sarpras", "admin_sarpras")
        tech = _create_user("teknisi_lapangan", "teknisi")
        category = db.session.scalar(select(Category).where(Category.is_active.is_(True)))

        # 1. Laporan baru dibuat (status 'Baru')
        ticket = _create_dummy_ticket(
            status="Baru",
            official_category_id=category.id,
            assigned_technician_id=None,
        )
        db.session.commit()

        # 2. Admin Sarpras memverifikasi kategori (Baru -> Terverifikasi)
        ticket, cat_changed, status_changed = verify_ticket_category(
            ticket=ticket,
            new_category_id=category.id,
            actor_user=admin,
            note="Kategori resmi dikonfirmasi",
        )
        assert status_changed is True
        assert ticket.status == "Terverifikasi"

        # 3. Admin Sarpras menugaskan teknisi penanggung jawab (Status TETAP Terverifikasi)
        ticket, assign_changed = assign_technician_to_ticket(
            ticket=ticket,
            technician_id=tech.id,
            actor_user=admin,
            note="Penugasan teknisi lab FTII",
        )
        assert assign_changed is True
        assert ticket.assigned_technician_id == tech.id
        assert ticket.status == "Terverifikasi"  # Penugasan BUKAN status!

        # 4. Teknisi yang ditugaskan memulai pengerjaan (Terverifikasi -> Diproses)
        ticket, status_changed2 = transition_ticket_status(
            ticket=ticket,
            new_status="Diproses",
            actor_user=tech,
            note="Menyiapkan peralatan dan suku cadang",
            commit=True,
        )
        assert status_changed2 is True
        assert ticket.status == "Diproses"
        assert ticket.resolved_at is None

        # 5. Teknisi yang ditugaskan menyelesaikan pengerjaan (Diproses -> Selesai)
        action_note = "Penggantian komponen kabel dan saklar telah selesai diuji."
        ticket, status_changed3 = transition_ticket_status(
            ticket=ticket,
            new_status="Selesai",
            actor_user=tech,
            note=action_note,
            commit=True,
        )
        assert status_changed3 is True
        assert ticket.status == "Selesai"
        assert ticket.resolved_at is not None
        assert ticket.resolution_note == action_note

        # Ambil seluruh audit log untuk tiket ini secara kronologis
        all_logs = db.session.scalars(
            select(AuditLog)
            .where(AuditLog.ticket_id == ticket.id)
            .order_by(AuditLog.id.asc())
        ).all()

        # Pisahkan event status_changed dan technician_assigned
        status_logs = [log for log in all_logs if log.action == "status_changed"]
        assign_logs = [log for log in all_logs if log.action == "technician_assigned"]

        # Verifikasi kuantitatif: TEPAT 3 mutasi status dan TEPAT 1 mutasi penugasan
        assert len(status_logs) == 3, "Harus ada tepat 3 rekaman mutasi status"
        assert len(assign_logs) == 1, "Harus ada tepat 1 rekaman penugasan teknisi"

        # Rincian Event 1: Baru -> Terverifikasi oleh Admin Sarpras
        assert status_logs[0].field_name == "status"
        assert status_logs[0].old_value == "Baru"
        assert status_logs[0].new_value == "Terverifikasi"
        assert status_logs[0].actor_user_id == admin.id
        assert status_logs[0].actor_role == "admin_sarpras"
        assert status_logs[0].note == "Kategori resmi dikonfirmasi"

        # Rincian Event Penugasan: BUKAN perubahan status
        assert assign_logs[0].field_name == "assigned_technician_id"
        assert assign_logs[0].old_value is None
        assert assign_logs[0].new_value == str(tech.id)
        assert assign_logs[0].actor_user_id == admin.id
        assert assign_logs[0].actor_role == "admin_sarpras"
        assert assign_logs[0].note == "Penugasan teknisi lab FTII"

        # Rincian Event 2: Terverifikasi -> Diproses oleh Teknisi
        assert status_logs[1].field_name == "status"
        assert status_logs[1].old_value == "Terverifikasi"
        assert status_logs[1].new_value == "Diproses"
        assert status_logs[1].actor_user_id == tech.id
        assert status_logs[1].actor_role == "teknisi"
        assert status_logs[1].note == "Menyiapkan peralatan dan suku cadang"

        # Rincian Event 3: Diproses -> Selesai oleh Teknisi
        assert status_logs[2].field_name == "status"
        assert status_logs[2].old_value == "Diproses"
        assert status_logs[2].new_value == "Selesai"
        assert status_logs[2].actor_user_id == tech.id
        assert status_logs[2].actor_role == "teknisi"
        assert status_logs[2].note == action_note

        # Verifikasi urutan ID autoincrement membuktikan kronologi sekuensial
        assert status_logs[0].id < assign_logs[0].id < status_logs[1].id < status_logs[2].id


def test_audit_metadata_fidelity_actor_timestamp_and_values(app):
    """
    AC-2: Memverifikasi presisi metadata audit log:
    - actor_user_id dan actor_role sesuai identitas login.
    - created_at merekam waktu UTC server yang valid.
    - old_value dan new_value berupa string akurat sesuai state DB.
    """
    with app.app_context():
        tech = _create_user("tech_meta", "teknisi")
        ticket = _create_dummy_ticket(status="Terverifikasi", assigned_technician_id=tech.id)
        db.session.commit()

        start_time = datetime.now(timezone.utc)
        transition_ticket_status(ticket, "Diproses", tech, note="Uji metadata", commit=True)
        end_time = datetime.now(timezone.utc)

        log = db.session.scalar(
            select(AuditLog).where(
                AuditLog.ticket_id == ticket.id,
                AuditLog.action == "status_changed",
            )
        )
        assert log is not None
        assert log.actor_user_id == tech.id
        assert log.actor_role == "teknisi"
        assert log.field_name == "status"
        assert log.old_value == "Terverifikasi"
        assert log.new_value == "Diproses"
        assert log.note == "Uji metadata"
        assert log.created_at is not None
        assert start_time <= log.created_at <= end_time


def test_audit_visibility_accessible_by_admin_forbidden_to_technician(client):
    """
    AC-3 & FR-09: Log audit perubahan status dapat diakses dan difilter oleh Admin Sarpras,
    tetapi teknisi ditolak dengan 403 Forbidden saat mengakses riwayat audit.
    """
    admin = _login_as(client, "admin_sarpras", "admin_auditor")
    tech = _create_user("tech_field", "teknisi")
    ticket = _create_dummy_ticket(status="Terverifikasi", assigned_technician_id=tech.id)
    db.session.commit()

    # Buat entri mutasi status
    transition_ticket_status(ticket, "Diproses", tech, note="Audit visibility test", commit=True)

    # 1. Admin Sarpras membuka riwayat audit log terpusat
    resp_admin = client.get(f"/admin/audit-log?action=status_changed&ticket_code={ticket.ticket_code}")
    assert resp_admin.status_code == 200
    html_admin = resp_admin.get_data(as_text=True)
    assert ticket.ticket_code in html_admin
    assert "Perubahan Status" in html_admin
    assert "Terverifikasi" in html_admin
    assert "Diproses" in html_admin

    # 2. Teknisi mencoba mengakses riwayat audit log terpusat -> 403 Forbidden
    _login_as(client, "teknisi", "tech_field")
    resp_tech = client.get("/admin/audit-log")
    assert resp_tech.status_code == 403


# ==============================================================================
# 2. Kelompok 2: Pencegahan Celah Audit, Duplikasi & Idempotensi (AC-4, AC-5, AC-6, AC-7)
# ==============================================================================


def test_audit_no_duplicate_records_on_single_status_transition(app):
    """
    AC-6: Memastikan tidak terjadi duplikasi rekaman audit. Satu kali transisi status sah
    hanya menghasilkan tepat satu baris AuditLog beraksi 'status_changed'.
    """
    with app.app_context():
        tech = _create_user("tech_single", "teknisi")
        ticket = _create_dummy_ticket(status="Terverifikasi", assigned_technician_id=tech.id)
        db.session.commit()

        ticket, changed = transition_ticket_status(
            ticket, "Diproses", tech, note="Single transition test", commit=True
        )
        assert changed is True

        count = db.session.scalar(
            select(db.func.count(AuditLog.id)).where(
                AuditLog.ticket_id == ticket.id,
                AuditLog.action == "status_changed",
            )
        )
        assert count == 1, "Hanya boleh ada tepat 1 baris audit log untuk mutasi status tunggal"


def test_audit_no_op_produces_zero_audit_logs(app):
    """
    AC-7: Operasi no-op (status baru sama dengan status saat ini) mengembalikan changed=False
    dan tidak menghasilkan rekaman audit baru baik untuk Admin maupun Teknisi.
    """
    with app.app_context():
        admin = _create_user("admin_noop", "admin_sarpras")
        tech = _create_user("tech_noop", "teknisi")

        ticket_admin = _create_dummy_ticket(status="Terverifikasi")
        ticket_tech = _create_dummy_ticket(status="Diproses", assigned_technician_id=tech.id)
        db.session.commit()

        # 1. No-op oleh Admin Sarpras pada Terverifikasi
        res_t1, ch1 = transition_ticket_status(ticket_admin, "Terverifikasi", admin, commit=True)
        assert ch1 is False
        assert res_t1.status == "Terverifikasi"

        # 2. No-op oleh Teknisi pada Diproses
        res_t2, ch2 = transition_ticket_status(ticket_tech, "Diproses", tech, commit=True)
        assert ch2 is False
        assert res_t2.status == "Diproses"

        # Pastikan 0 rekaman audit tercipta untuk kedua tiket
        count = db.session.scalar(
            select(db.func.count(AuditLog.id)).where(
                AuditLog.ticket_id.in_([ticket_admin.id, ticket_tech.id])
            )
        )
        assert count == 0


def test_audit_illegal_transitions_produce_zero_audit_logs(app):
    """
    AC-4: Transisi status ilegal (lompat alur, mundur, status tidak dikenal, tiket selesai)
    ditolak dengan InvalidTicketStatusError dan tidak menghasilkan audit palsu (0 audit log).
    """
    with app.app_context():
        admin = _create_user("admin_illegal", "admin_sarpras")
        tech = _create_user("tech_illegal", "teknisi")

        ticket_baru = _create_dummy_ticket(status="Baru")
        ticket_terverifikasi = _create_dummy_ticket(status="Terverifikasi", assigned_technician_id=tech.id)
        ticket_diproses = _create_dummy_ticket(status="Diproses", assigned_technician_id=tech.id)
        ticket_selesai = _create_dummy_ticket(status="Selesai", assigned_technician_id=tech.id)
        db.session.commit()

        all_ids = [ticket_baru.id, ticket_terverifikasi.id, ticket_diproses.id, ticket_selesai.id]

        # 1. Admin mencoba lompat dari Baru langsung ke Diproses atau Selesai
        for target in ["Diproses", "Selesai"]:
            with pytest.raises(InvalidTicketStatusError):
                transition_ticket_status(ticket_baru, target, admin)

        # 2. Teknisi mencoba lompat dari Terverifikasi langsung ke Selesai
        with pytest.raises(InvalidTicketStatusError):
            transition_ticket_status(ticket_terverifikasi, "Selesai", tech, note="Catatan lompat")

        # 3. Teknisi mencoba mundur dari Diproses ke Terverifikasi
        with pytest.raises(InvalidTicketStatusError):
            transition_ticket_status(ticket_diproses, "Terverifikasi", tech, note="Catatan mundur")

        # 4. Status tidak dikenal / sembarang
        with pytest.raises(InvalidTicketStatusError):
            transition_ticket_status(ticket_diproses, "StatusSembarang", tech, note="Catatan")

        # 5. Tiket berstatus Selesai diubah kembali
        with pytest.raises(InvalidTicketStatusError):
            transition_ticket_status(ticket_selesai, "Diproses", admin, note="Catatan")

        # Verifikasi: seluruh percobaan ilegal di atas menghasilkan TEPAT 0 audit log
        count = db.session.scalar(
            select(db.func.count(AuditLog.id)).where(AuditLog.ticket_id.in_(all_ids))
        )
        assert count == 0, "Transisi ilegal dilarang menghasilkan entri audit palsu"


def test_audit_transaction_rollback_prevents_orphan_audit_and_status(app):
    """
    AC-5: Atomisitas transaksi: jika terjadi kegagalan sistem saat commit basis data,
    rollback membatalkan mutasi status tiket dan entri audit log secara bersamaan (tidak ada orphan record).
    """
    with app.app_context():
        tech = _create_user("tech_atom", "teknisi")
        ticket = _create_dummy_ticket(status="Terverifikasi", assigned_technician_id=tech.id)
        db.session.commit()

        # Simulasikan kegagalan database saat commit
        with patch.object(db.session, "commit", side_effect=RuntimeError("Simulated DB connection drop on commit")):
            with pytest.raises(RuntimeError):
                transition_ticket_status(ticket, "Diproses", tech, note="Catatan rollback", commit=True)

        # Verifikasi: status tiket tidak berubah (tetap Terverifikasi)
        db.session.refresh(ticket)
        assert ticket.status == "Terverifikasi"

        # Verifikasi: 0 rekaman audit log tercipta (tidak ada orphan audit)
        count = db.session.scalar(
            select(db.func.count(AuditLog.id)).where(AuditLog.ticket_id == ticket.id)
        )
        assert count == 0


# ==============================================================================
# 3. Kelompok 3: Integritas Catatan Tindakan & Batasan Jalur Mutasi HTTP (AC-4, AC-6)
# ==============================================================================


def test_audit_note_consistency_between_resolution_note_and_audit_log(app):
    """
    AC-2, AC-6: Memverifikasi konsistensi teks catatan perbaikan:
    String clean_note yang disimpan pada ticket.resolution_note identik 100% dengan AuditLog.note.
    """
    with app.app_context():
        tech = _create_user("tech_consistent", "teknisi")
        ticket = _create_dummy_ticket(status="Diproses", assigned_technician_id=tech.id)
        db.session.commit()

        raw_note = "   Penggantian MCB 16A dan penataan kabel panel distribusi.   "
        ticket, changed = transition_ticket_status(
            ticket, "Selesai", tech, note=raw_note, commit=True
        )
        assert changed is True
        assert ticket.status == "Selesai"

        expected_clean = "Penggantian MCB 16A dan penataan kabel panel distribusi."
        assert ticket.resolution_note == expected_clean

        audit = db.session.scalar(
            select(AuditLog).where(
                AuditLog.ticket_id == ticket.id,
                AuditLog.action == "status_changed",
            )
        )
        assert audit is not None
        assert audit.note == expected_clean
        assert ticket.resolution_note == audit.note


def test_audit_rejection_when_completing_without_note_leaves_zero_audit(app):
    """
    AC-4: Percobaan menyelesaikan tiket tanpa catatan (None, string kosong, atau hanya spasi)
    ditolak sebelum mutasi data dan sebelum audit dicatat (0 audit log baru).
    """
    with app.app_context():
        tech = _create_user("tech_reject", "teknisi")
        ticket = _create_dummy_ticket(status="Diproses", assigned_technician_id=tech.id)
        db.session.commit()

        for invalid_note in [None, "", "    ", "\t\n  "]:
            with pytest.raises(InvalidTicketStatusError) as exc_info:
                transition_ticket_status(ticket, "Selesai", tech, note=invalid_note, commit=True)
            assert "Catatan tindakan perbaikan wajib diisi" in str(exc_info.value)

        # Tiket tetap Diproses, resolved_at dan resolution_note tetap None
        db.session.refresh(ticket)
        assert ticket.status == "Diproses"
        assert ticket.resolved_at is None
        assert ticket.resolution_note is None

        # 0 audit log tercipta
        count = db.session.scalar(
            select(db.func.count(AuditLog.id)).where(AuditLog.ticket_id == ticket.id)
        )
        assert count == 0


def test_audit_no_http_mutation_endpoints_and_foreign_key_protection(app, client):
    """
    Integritas & Batasan Immutabilitas:
    - Batasan HTTP: Aplikasi web tidak menyediakan antarmuka HTTP untuk mutasi/penghapusan audit log
      (POST, PUT, PATCH, DELETE pada /admin/audit-log ditolak 405 Method Not Allowed).
    - Batasan Relasional Basis Data: Foreign key AuditLog.ticket_id berstatus ON DELETE RESTRICT,
      sehingga tiket yang memiliki riwayat audit tidak dapat dihapus secara langsung dari database.
    """
    # 1. Uji batas antarmuka HTTP: Admin Sarpras tidak memiliki endpoint untuk mengubah atau menghapus audit log
    _login_as(client, "admin_sarpras")
    for method in ["post", "put", "patch", "delete"]:
        caller = getattr(client, method)
        resp = caller("/admin/audit-log")
        assert resp.status_code == 405, f"Method {method.upper()} pada /admin/audit-log harus ditolak 405"

    # 2. Uji integritas relasional basis data: penghapusan tiket diblokir jika memiliki rekam audit (RESTRICT)
    with app.app_context():
        tech = _create_user("tech_restrict", "teknisi")
        ticket = _create_dummy_ticket(status="Terverifikasi", assigned_technician_id=tech.id)
        db.session.commit()

        # Buat entri audit yang terikat pada tiket
        transition_ticket_status(ticket, "Diproses", tech, note="Audit restrict test", commit=True)

        # Percobaan menghapus tiket langsung di database harus gagal karena constraint ON DELETE RESTRICT
        with pytest.raises(IntegrityError):
            db.session.execute(delete(Ticket).where(Ticket.id == ticket.id))
            db.session.flush()

        db.session.rollback()

