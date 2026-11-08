"""
Pengujian Komprehensif TSK-F5-04:
Pencatatan Audit Kategori dan Status (FR-09).

Mencakup seluruh kriteria penerimaan (AC-1 s.d. AC-7):
1. AC-1: Audit mutasi kategori resmi (category_changed, official_category_id, old/new IDs stabil).
2. AC-2: Audit transisi status resmi (status_changed) & bebas audit ganda pada Baru -> Terverifikasi.
3. AC-3: Non-repudiasi & anti-manipulasi (aktor dari User, timestamp server, old_value riil DB).
4. AC-4: Penegakan otorisasi peran & state machine transisi status (tolak transisi mundur/ilegal).
5. AC-5: Atomisitas transaksi & rollback pada kegagalan audit.
6. AC-6: Idempotensi & sanitasi catatan audit (strip, empty -> None, tolak > 1000 chars).
7. AC-7: Whitelist aksi audit dan kompatibilitas technician_assigned (F5-02).
"""
from datetime import datetime, timezone
import hashlib
import secrets
from unittest.mock import patch

import pytest
from sqlalchemy import delete, select
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.category import Category
from app.models.ticket import TICKET_STATUSES, Ticket
from app.models.user import User
from app.services.audit_service import (
    MAX_AUDIT_NOTE_LENGTH,
    VALID_AUDIT_ACTIONS,
    AuditNoteLengthError,
    AuditServiceError,
    log_category_change,
    log_status_change,
    record_audit_log,
    sanitize_audit_note,
)
from app.services.complaint_service import (
    CategoryValidationError,
    InvalidTicketStatusError,
    get_active_categories,
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

            # Bersihkan record yang dibuat selama test secara aman
            with db.engine.begin() as cleanup_connection:
                current_ticket_ids = set(
                    cleanup_connection.execute(select(Ticket.id)).scalars().all()
                )
                extra_tickets = current_ticket_ids - baseline_ticket_ids
                if extra_tickets:
                    cleanup_connection.execute(
                        delete(AuditLog).where(AuditLog.ticket_id.in_(extra_tickets))
                    )
                    cleanup_connection.execute(
                        delete(Ticket).where(Ticket.id.in_(extra_tickets))
                    )

                current_user_ids = set(
                    cleanup_connection.execute(select(User.id)).scalars().all()
                )
                extra_users = current_user_ids - baseline_user_ids
                if extra_users:
                    cleanup_connection.execute(
                        delete(User).where(User.id.in_(extra_users))
                    )


def _create_user(role: str, username_prefix: str = "user") -> User:
    unique_uname = f"{username_prefix}_{secrets.token_hex(4)}"
    user = User(
        username=unique_uname,
        full_name=f"Pengguna {role.title()} {unique_uname}",
        password_hash=PASSWORD_HASH,
        role=role,
        is_active=True,
    )
    db.session.add(user)
    db.session.flush()
    return user


def _create_dummy_ticket(
    *,
    status: str = "Baru",
    needs_manual: bool = False,
    official_category_id: int | None = None,
    assigned_technician_id: int | None = None,
) -> Ticket:
    ticket_code = generate_ticket_code()
    token_seed = secrets.token_hex(16)
    token_hash = hashlib.sha256(token_seed.encode("ascii")).hexdigest()

    ticket = Ticket(
        ticket_code=ticket_code,
        access_token_hash=token_hash,
        description=f"Keluhan uji coba F5-04 untuk {ticket_code}",
        building_name="Gedung FTII",
        floor_number=1,
        room_name="Ruang 101",
        status=status,
        needs_manual_verification=needs_manual,
        official_category_id=official_category_id,
        assigned_technician_id=assigned_technician_id,
    )
    db.session.add(ticket)
    db.session.flush()
    return ticket


# ==============================================================================
# Skenario 1 & 2: Audit Mutasi Kategori Resmi (AC-1, AC-3) & Idempotensi Kategori
# ==============================================================================

def test_audit_category_change_records_actor_timestamp_and_stable_ids(app):
    """
    AC-1 & AC-3: Memverifikasi pencatatan audit log mutasi kategori resmi dengan
    identitas aktor terotentikasi, timestamp server, dan ID kategori yang stabil.
    """
    with app.app_context():
        active_cats = get_active_categories()
        assert len(active_cats) >= 2
        cat1, cat2 = active_cats[0], active_cats[1]

        admin = _create_user("admin_sarpras", "admin")
        ticket = _create_dummy_ticket(status="Baru", official_category_id=cat1.id)

        ticket, cat_changed, status_changed = verify_ticket_category(
            ticket=ticket,
            new_category_id=cat2.id,
            actor_user=admin,
            note="Koreksi kategori dari AC ke Kelistrikan",
        )

        assert cat_changed is True
        assert status_changed is True
        assert ticket.official_category_id == cat2.id
        assert ticket.status == "Terverifikasi"

        # Periksa entri audit kategori
        cat_audit = db.session.scalar(
            select(AuditLog).where(
                AuditLog.ticket_id == ticket.id,
                AuditLog.action == "category_changed",
            )
        )
        assert cat_audit is not None
        assert cat_audit.field_name == "official_category_id"
        assert cat_audit.old_value == str(cat1.id)
        assert cat_audit.new_value == str(cat2.id)
        assert cat_audit.actor_user_id == admin.id
        assert cat_audit.actor_role == "admin_sarpras"
        assert cat_audit.note == "Koreksi kategori dari AC ke Kelistrikan"
        assert cat_audit.created_at is not None


def test_audit_category_change_idempotent_no_duplicate(app):
    """
    AC-6: Memverifikasi jika kategori baru sama dengan kategori saat ini,
    tidak ada entri audit kategori yang dibuat.
    """
    with app.app_context():
        active_cats = get_active_categories()
        cat1 = active_cats[0]

        admin = _create_user("admin_sarpras", "admin")
        # Tiket non-Baru agar tidak memicu transisi status
        ticket = _create_dummy_ticket(status="Terverifikasi", official_category_id=cat1.id)

        ticket, cat_changed, status_changed = verify_ticket_category(
            ticket=ticket,
            new_category_id=cat1.id,
            actor_user=admin,
            note="Konfirmasi ulang kategori yang sama",
        )

        assert cat_changed is False
        assert status_changed is False

        # Tidak ada audit log yang tercipta
        audit_count = db.session.scalar(
            select(db.func.count(AuditLog.id)).where(AuditLog.ticket_id == ticket.id)
        )
        assert audit_count == 0


# ==============================================================================
# Skenario 3, 4, 5, 6, 7, 8: Validasi Status, Otorisasi No-Op, dan Idempotensi
# ==============================================================================

def test_transition_status_invalid_status_rejected_before_idempotency(app):
    """
    AC-4: Memverifikasi status baru yang bukan anggota resmi TICKET_STATUSES
    langsung ditolak dengan InvalidTicketStatusError sebelum pengecekan idempotensi.
    """
    with app.app_context():
        admin = _create_user("admin_sarpras", "admin")
        ticket = _create_dummy_ticket(status="Baru")

        with pytest.raises(InvalidTicketStatusError) as exc_info:
            transition_ticket_status(ticket, "StatusTidakDikenal", admin)

        assert "bukan status resmi" in str(exc_info.value)

        # Tidak ada audit log yang tercipta
        audit_count = db.session.scalar(
            select(db.func.count(AuditLog.id)).where(AuditLog.ticket_id == ticket.id)
        )
        assert audit_count == 0


def test_transition_status_idempotent_rejects_unauthorized_actor(app):
    """
    AC-4: Memverifikasi pemanggilan no-op status yang sama oleh aktor tidak berwenang
    (reporter, pimpinan, atau teknisi yang tidak ditugaskan) tetap ditolak.
    """
    with app.app_context():
        reporter = _create_user("reporter", "reporter")
        pimpinan = _create_user("pimpinan", "pimpinan")
        unassigned_tech = _create_user("teknisi", "tech_unassigned")

        ticket = _create_dummy_ticket(status="Terverifikasi")

        # Reporter ditolak
        with pytest.raises(InvalidTicketStatusError) as exc_info:
            transition_ticket_status(ticket, "Terverifikasi", reporter)
        assert "tidak memiliki kewenangan" in str(exc_info.value)

        # Pimpinan ditolak
        with pytest.raises(InvalidTicketStatusError) as exc_info:
            transition_ticket_status(ticket, "Terverifikasi", pimpinan)
        assert "tidak memiliki kewenangan" in str(exc_info.value)

        # Teknisi yang tidak ditugaskan ditolak
        with pytest.raises(InvalidTicketStatusError) as exc_info:
            transition_ticket_status(ticket, "Terverifikasi", unassigned_tech)
        assert "ditugaskan kepadanya" in str(exc_info.value)

        # 0 audit log
        audit_count = db.session.scalar(
            select(db.func.count(AuditLog.id)).where(AuditLog.ticket_id == ticket.id)
        )
        assert audit_count == 0


def test_transition_status_idempotent_assigned_technician_rejected_on_baru(app):
    """
    Kewenangan Operasional Per Status: Teknisi yang ditugaskan mencoba no-op pada tiket
    berstatus 'Baru' ditolak secara eksplisit dengan InvalidTicketStatusError.
    """
    with app.app_context():
        tech = _create_user("teknisi", "assigned_tech")
        ticket = _create_dummy_ticket(status="Baru", assigned_technician_id=tech.id)

        with pytest.raises(InvalidTicketStatusError) as exc_info:
            transition_ticket_status(ticket, "Baru", tech)

        assert "tidak memiliki kewenangan operasional pada tiket berstatus 'Baru'" in str(exc_info.value)

        # Sesi DB bersih, 0 audit log
        audit_count = db.session.scalar(
            select(db.func.count(AuditLog.id)).where(AuditLog.ticket_id == ticket.id)
        )
        assert audit_count == 0


def test_transition_status_idempotent_assigned_technician_rejected_on_selesai(app):
    """
    Kewenangan Operasional Per Status: Teknisi yang ditugaskan mencoba no-op pada tiket
    berstatus 'Selesai' ditolak secara eksplisit dengan InvalidTicketStatusError.
    """
    with app.app_context():
        tech = _create_user("teknisi", "assigned_tech")
        ticket = _create_dummy_ticket(status="Selesai", assigned_technician_id=tech.id)

        with pytest.raises(InvalidTicketStatusError) as exc_info:
            transition_ticket_status(ticket, "Selesai", tech)

        assert "tidak memiliki kewenangan operasional pada tiket berstatus 'Selesai'" in str(exc_info.value)

        # Sesi DB bersih, 0 audit log
        audit_count = db.session.scalar(
            select(db.func.count(AuditLog.id)).where(AuditLog.ticket_id == ticket.id)
        )
        assert audit_count == 0


def test_transition_status_idempotent_assigned_technician_success_on_operational_statuses(app):
    """
    Kewenangan Operasional Per Status: Teknisi yang ditugaskan berhasil melakukan no-op
    pada status operasional aktif yang menjadi kewenangannya ('Terverifikasi' dan 'Diproses').
    """
    with app.app_context():
        tech = _create_user("teknisi", "assigned_tech")

        # 1. No-op pada Terverifikasi
        ticket_terverifikasi = _create_dummy_ticket(
            status="Terverifikasi", assigned_technician_id=tech.id
        )
        res_ticket, changed = transition_ticket_status(
            ticket_terverifikasi, "Terverifikasi", tech
        )
        assert changed is False
        assert res_ticket.status == "Terverifikasi"

        # 2. No-op pada Diproses
        ticket_diproses = _create_dummy_ticket(
            status="Diproses", assigned_technician_id=tech.id
        )
        res_ticket, changed = transition_ticket_status(
            ticket_diproses, "Diproses", tech
        )
        assert changed is False
        assert res_ticket.status == "Diproses"

        # 0 audit log tercipta
        audit_count = db.session.scalar(
            select(db.func.count(AuditLog.id)).where(
                AuditLog.ticket_id.in_([ticket_terverifikasi.id, ticket_diproses.id])
            )
        )
        assert audit_count == 0


def test_transition_status_idempotent_admin_sarpras_success_across_all_statuses(app):
    """
    AC-6: Memverifikasi Admin Sarpras dapat melakukan no-op pada seluruh status resmi
    (Baru, Terverifikasi, Diproses, Selesai) dengan hasil (ticket, False) dan 0 audit log.
    """
    with app.app_context():
        admin = _create_user("admin_sarpras", "admin")

        for st in ("Baru", "Terverifikasi", "Diproses", "Selesai"):
            ticket = _create_dummy_ticket(status=st)
            res_ticket, changed = transition_ticket_status(ticket, st, admin)
            assert changed is False
            assert res_ticket.status == st

            # Pastikan 0 audit log
            audit_count = db.session.scalar(
                select(db.func.count(AuditLog.id)).where(AuditLog.ticket_id == ticket.id)
            )
            assert audit_count == 0


# ==============================================================================
# Skenario 9, 10, 11: Single Atomic Audit & Integrasi verify_ticket_category
# ==============================================================================

def test_verify_ticket_category_baru_single_status_and_category_audit(app):
    """
    AC-2: Memverifikasi transisi Baru -> Terverifikasi melalui verify_ticket_category()
    menghasilkan TEPAT 1 entri audit status dan 1 entri audit kategori (bebas audit ganda).
    """
    with app.app_context():
        active_cats = get_active_categories()
        cat1, cat2 = active_cats[0], active_cats[1]

        admin = _create_user("admin_sarpras", "admin")
        ticket = _create_dummy_ticket(
            status="Baru",
            needs_manual=True,
            official_category_id=cat1.id,
        )

        ticket, cat_changed, status_changed = verify_ticket_category(
            ticket=ticket,
            new_category_id=cat2.id,
            actor_user=admin,
            note="Verifikasi sekaligus koreksi kategori",
        )

        assert cat_changed is True
        assert status_changed is True
        assert ticket.status == "Terverifikasi"
        assert ticket.needs_manual_verification is False

        # Verifikasi entri audit pada tiket ini
        audits = db.session.scalars(
            select(AuditLog)
            .where(AuditLog.ticket_id == ticket.id)
            .order_by(AuditLog.id.asc())
        ).all()

        assert len(audits) == 2, f"Diharapkan tepat 2 audit log, ditemukan {len(audits)}"
        action_names = {a.action for a in audits}
        assert action_names == {"category_changed", "status_changed"}

        status_audit = next(a for a in audits if a.action == "status_changed")
        assert status_audit.old_value == "Baru"
        assert status_audit.new_value == "Terverifikasi"
        assert status_audit.field_name == "status"
        assert status_audit.actor_user_id == admin.id
        assert status_audit.actor_role == "admin_sarpras"
        assert status_audit.note == "Verifikasi sekaligus koreksi kategori"


def test_verify_ticket_category_non_baru_clears_flag_without_category_change_no_audit(app):
    """
    Memverifikasi tiket non-Baru dengan flag verifikasi manual dibersihkan penandanya
    secara atomik tanpa mengubah status dan tanpa menghasilkan entri audit log apa pun.
    """
    with app.app_context():
        active_cats = get_active_categories()
        cat1 = active_cats[0]

        admin = _create_user("admin_sarpras", "admin")
        ticket = _create_dummy_ticket(
            status="Terverifikasi",
            needs_manual=True,
            official_category_id=cat1.id,
        )

        ticket, cat_changed, status_changed = verify_ticket_category(
            ticket=ticket,
            new_category_id=cat1.id,
            actor_user=admin,
            note="Konfirmasi kategori sama untuk bersihkan flag",
        )

        assert cat_changed is False
        assert status_changed is False
        assert ticket.status == "Terverifikasi"
        assert ticket.needs_manual_verification is False

        # 0 audit log karena status dan kategori tidak bermutasi
        audit_count = db.session.scalar(
            select(db.func.count(AuditLog.id)).where(AuditLog.ticket_id == ticket.id)
        )
        assert audit_count == 0


def test_verify_ticket_category_non_baru_clears_flag_with_category_change(app):
    """
    Memverifikasi tiket non-Baru dengan flag manual yang mengalami koreksi kategori
    berhasil mengubah kategori dan membersihkan flag, dengan tepat 1 audit kategori
    dan 0 audit status.
    """
    with app.app_context():
        active_cats = get_active_categories()
        cat1, cat2 = active_cats[0], active_cats[1]

        admin = _create_user("admin_sarpras", "admin")
        ticket = _create_dummy_ticket(
            status="Diproses",
            needs_manual=True,
            official_category_id=cat1.id,
        )

        ticket, cat_changed, status_changed = verify_ticket_category(
            ticket=ticket,
            new_category_id=cat2.id,
            actor_user=admin,
            note="Koreksi kategori pada tiket yang sedang diproses",
        )

        assert cat_changed is True
        assert status_changed is False
        assert ticket.status == "Diproses"
        assert ticket.official_category_id == cat2.id
        assert ticket.needs_manual_verification is False

        # Tepat 1 audit log kategori, 0 audit status
        audits = db.session.scalars(
            select(AuditLog).where(AuditLog.ticket_id == ticket.id)
        ).all()
        assert len(audits) == 1
        assert audits[0].action == "category_changed"
        assert audits[0].old_value == str(cat1.id)
        assert audits[0].new_value == str(cat2.id)


# ==============================================================================
# Skenario 12, 13, 14, 15, 16: Transisi Status Teknisi & Penolakan Ilegal (AC-4)
# ==============================================================================

def test_transition_status_terverifikasi_to_diproses_by_assigned_technician(app):
    """
    AC-4: Memverifikasi teknisi yang ditugaskan dapat mengubah status dari
    'Terverifikasi' ke 'Diproses' dan tercatat dalam audit log.
    """
    with app.app_context():
        tech = _create_user("teknisi", "tech_assigned")
        ticket = _create_dummy_ticket(
            status="Terverifikasi", assigned_technician_id=tech.id
        )

        ticket, changed = transition_ticket_status(
            ticket, "Diproses", tech, note="Mulai investigasi lapangan"
        )

        assert changed is True
        assert ticket.status == "Diproses"

        audit = db.session.scalar(
            select(AuditLog).where(
                AuditLog.ticket_id == ticket.id,
                AuditLog.action == "status_changed",
            )
        )
        assert audit is not None
        assert audit.old_value == "Terverifikasi"
        assert audit.new_value == "Diproses"
        assert audit.actor_user_id == tech.id
        assert audit.actor_role == "teknisi"
        assert audit.note == "Mulai investigasi lapangan"


def test_transition_status_diproses_to_selesai_by_assigned_technician(app):
    """
    AC-4: Memverifikasi teknisi yang ditugaskan dapat menyelesaikan pengerjaan tiket
    (transisi 'Diproses' -> 'Selesai') dan tercatat dalam audit log.
    """
    with app.app_context():
        tech = _create_user("teknisi", "tech_assigned")
        ticket = _create_dummy_ticket(
            status="Diproses", assigned_technician_id=tech.id
        )

        ticket, changed = transition_ticket_status(
            ticket, "Selesai", tech, note="Perbaikan kabel selesai dilakukan"
        )

        assert changed is True
        assert ticket.status == "Selesai"

        audit = db.session.scalar(
            select(AuditLog).where(
                AuditLog.ticket_id == ticket.id,
                AuditLog.action == "status_changed",
            )
        )
        assert audit is not None
        assert audit.old_value == "Diproses"
        assert audit.new_value == "Selesai"
        assert audit.actor_user_id == tech.id
        assert audit.actor_role == "teknisi"
        assert audit.note == "Perbaikan kabel selesai dilakukan"


def test_transition_status_by_unassigned_technician_rejected(app):
    """
    AC-4: Memverifikasi teknisi lain yang tidak ditugaskan pada tiket tersebut
    ditolak untuk mengubah status tiket ke 'Diproses'.
    """
    with app.app_context():
        assigned_tech = _create_user("teknisi", "assigned")
        other_tech = _create_user("teknisi", "other")
        ticket = _create_dummy_ticket(
            status="Terverifikasi", assigned_technician_id=assigned_tech.id
        )

        with pytest.raises(InvalidTicketStatusError) as exc_info:
            transition_ticket_status(ticket, "Diproses", other_tech)

        assert "ditugaskan kepadanya" in str(exc_info.value)
        assert ticket.status == "Terverifikasi"

        # 0 audit log
        audit_count = db.session.scalar(
            select(db.func.count(AuditLog.id)).where(AuditLog.ticket_id == ticket.id)
        )
        assert audit_count == 0


def test_transition_status_by_unauthorized_role_rejected(app):
    """
    AC-4: Memverifikasi peran selain admin_sarpras dan teknisi (reporter, pimpinan)
    ditolak secara mutlak untuk memicu transisi status.
    """
    with app.app_context():
        reporter = _create_user("reporter", "reporter")
        pimpinan = _create_user("pimpinan", "pimpinan")
        ticket = _create_dummy_ticket(status="Terverifikasi")

        with pytest.raises(InvalidTicketStatusError):
            transition_ticket_status(ticket, "Diproses", reporter)

        with pytest.raises(InvalidTicketStatusError):
            transition_ticket_status(ticket, "Diproses", pimpinan)

        assert ticket.status == "Terverifikasi"


def test_backward_or_illegal_status_transitions_rejected(app):
    """
    AC-4: Memverifikasi seluruh transisi status yang tidak valid atau mundur
    ditolak secara konsisten dengan InvalidTicketStatusError tanpa audit log.
    """
    with app.app_context():
        admin = _create_user("admin_sarpras", "admin")

        # 1. Dari 'Selesai' mundur ke status lain
        ticket_selesai = _create_dummy_ticket(status="Selesai")
        for target in ("Baru", "Terverifikasi", "Diproses"):
            with pytest.raises(InvalidTicketStatusError) as exc_info:
                transition_ticket_status(ticket_selesai, target, admin)
            assert "tidak diizinkan" in str(exc_info.value)

        # 2. Dari 'Diproses' mundur ke 'Baru' atau 'Terverifikasi'
        ticket_diproses = _create_dummy_ticket(status="Diproses")
        for target in ("Baru", "Terverifikasi"):
            with pytest.raises(InvalidTicketStatusError) as exc_info:
                transition_ticket_status(ticket_diproses, target, admin)
            assert "tidak diizinkan" in str(exc_info.value)

        # 3. Dari 'Baru' melompati alur ke 'Diproses' atau 'Selesai'
        ticket_baru = _create_dummy_ticket(status="Baru")
        for target in ("Diproses", "Selesai"):
            with pytest.raises(InvalidTicketStatusError) as exc_info:
                transition_ticket_status(ticket_baru, target, admin)
            assert "tidak diizinkan" in str(exc_info.value)

        # 0 audit log untuk seluruh tiket di atas
        audit_count = db.session.scalar(
            select(db.func.count(AuditLog.id)).where(
                AuditLog.ticket_id.in_([ticket_selesai.id, ticket_diproses.id, ticket_baru.id])
            )
        )
        assert audit_count == 0


# ==============================================================================
# Skenario 17: Atomisitas Transaksi & Rollback (AC-5)
# ==============================================================================

def test_atomic_rollback_on_audit_failure_in_status_transition(app):
    """
    AC-5: Memverifikasi bahwa jika pencatatan audit log gagal, seluruh mutasi
    status tiket di-rollback secara atomik sehingga data tetap konsisten.
    """
    with app.app_context():
        admin = _create_user("admin_sarpras", "admin")
        ticket = _create_dummy_ticket(status="Baru")
        db.session.commit()

        # Mock log_status_change agar melempar error saat pencatatan audit
        with patch("app.services.complaint_service.log_status_change", side_effect=RuntimeError("Simulasi gagal catat audit")):
            with pytest.raises(RuntimeError):
                transition_ticket_status(ticket, "Terverifikasi", admin, commit=True)

        # Muat ulang status tiket dari basis data
        db.session.expire_all()
        reloaded_ticket = db.session.get(Ticket, ticket.id)
        assert reloaded_ticket.status == "Baru"

        # 0 audit log
        audit_count = db.session.scalar(
            select(db.func.count(AuditLog.id)).where(AuditLog.ticket_id == ticket.id)
        )
        assert audit_count == 0


# ==============================================================================
# Skenario 18 & 19: Sanitasi & Validasi Panjang Note (AC-6)
# ==============================================================================

def test_audit_note_sanitization_and_rejection_over_1000_chars(app):
    """
    AC-6: Memverifikasi sanitasi catatan audit:
    - Whitespace di-strip
    - String kosong atau whitespace dikonversi menjadi None
    - Note > 1000 karakter ditolak secara eksplisit dengan AuditNoteLengthError
    """
    # 1. Sanitasi normal
    assert sanitize_audit_note("   catatan perbaikan   ") == "catatan perbaikan"
    assert sanitize_audit_note("") is None
    assert sanitize_audit_note("    \t\n   ") is None
    assert sanitize_audit_note(None) is None

    # 2. Panjang tepat 1000 karakter diizinkan
    valid_1000_chars = "a" * MAX_AUDIT_NOTE_LENGTH
    assert sanitize_audit_note(valid_1000_chars) == valid_1000_chars

    # 3. Panjang 1001 karakter ditolak eksplisit
    invalid_1001_chars = "a" * (MAX_AUDIT_NOTE_LENGTH + 1)
    with pytest.raises(AuditNoteLengthError) as exc_info:
        sanitize_audit_note(invalid_1001_chars)
    assert "tidak boleh melebihi 1000 karakter" in str(exc_info.value)


def test_note_validation_failure_leaves_clean_session(app):
    """
    AC-6: Memverifikasi penolakan note > 1000 karakter terjadi sebelum mutasi data
    sehingga sesi basis data tetap bersih tanpa perubahan tertinggal.
    """
    with app.app_context():
        admin = _create_user("admin_sarpras", "admin")
        active_cats = get_active_categories()
        cat1, cat2 = active_cats[0], active_cats[1]

        ticket = _create_dummy_ticket(status="Baru", official_category_id=cat1.id)
        too_long_note = "x" * 1001

        # Uji pada transition_ticket_status
        with pytest.raises(AuditNoteLengthError):
            transition_ticket_status(ticket, "Terverifikasi", admin, note=too_long_note)

        assert ticket.status == "Baru"
        assert not db.session.dirty

        # Uji pada verify_ticket_category
        with pytest.raises(AuditNoteLengthError):
            verify_ticket_category(ticket, cat2.id, admin, note=too_long_note)

        assert ticket.official_category_id == cat1.id
        assert not db.session.dirty


# ==============================================================================
# Skenario 20: Whitelist Aksi Audit & Kompatibilitas (AC-7)
# ==============================================================================

def test_audit_action_validation_whitelist_and_compatibility(app):
    """
    AC-7: Memverifikasi bahwa aksi category_changed, status_changed, dan
    technician_assigned diterima, sedangkan aksi di luar whitelist ditolak.
    """
    with app.app_context():
        admin = _create_user("admin_sarpras", "admin")
        ticket = _create_dummy_ticket(status="Baru")

        # 1. category_changed valid
        log1 = record_audit_log(
            ticket_id=ticket.id,
            actor_user_id=admin.id,
            actor_role=admin.role,
            action="category_changed",
            field_name="official_category_id",
            old_value=1,
            new_value=2,
        )
        assert log1 is not None

        # 2. status_changed valid
        log2 = record_audit_log(
            ticket_id=ticket.id,
            actor_user_id=admin.id,
            actor_role=admin.role,
            action="status_changed",
            field_name="status",
            old_value="Baru",
            new_value="Terverifikasi",
        )
        assert log2 is not None

        # 3. technician_assigned valid (kompatibel dengan F5-02)
        log3 = record_audit_log(
            ticket_id=ticket.id,
            actor_user_id=admin.id,
            actor_role=admin.role,
            action="technician_assigned",
            field_name="assigned_technician_id",
            old_value=None,
            new_value=admin.id,
        )
        assert log3 is not None

        # 4. Aksi di luar whitelist ditolak
        with pytest.raises(AuditServiceError) as exc_info:
            record_audit_log(
                ticket_id=ticket.id,
                actor_user_id=admin.id,
                actor_role=admin.role,
                action="unauthorized_action",
                field_name="some_field",
                old_value="a",
                new_value="b",
            )
        assert "tidak terdaftar dalam whitelist" in str(exc_info.value)
