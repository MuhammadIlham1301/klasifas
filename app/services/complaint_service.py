"""Layanan operasional tiket dan verifikasi keluhan sarpras (FR-04)."""
from collections.abc import Sequence
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

from flask import abort, current_app, send_from_directory
from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.category import Category
from app.models.ticket import TICKET_STATUSES, Ticket
from app.models.user import User
from app.services.audit_service import (
    AuditNoteLengthError,
    AuditServiceError,
    log_category_change,
    log_status_change,
    log_technician_assignment,
    sanitize_audit_note,
)
from app.services.ticket_report import FLOOR_NUMBERS, get_active_categories

MAX_PAGE = 10_000

ALLOWED_STATUS_TRANSITIONS: dict[str, dict[str, set[str]]] = {
    "Baru": {
        "Terverifikasi": {"admin_sarpras"},
    },
    "Terverifikasi": {
        "Diproses": {"teknisi", "admin_sarpras"},
    },
    "Diproses": {
        "Selesai": {"teknisi", "admin_sarpras"},
    },
    "Selesai": {},
}


class ComplaintServiceError(Exception):
    """Kesalahan umum pada layanan keluhan operasional."""


class CategoryValidationError(ComplaintServiceError):
    """Kategori yang dipilih tidak valid atau tidak terdaftar."""


class TechnicianValidationError(ComplaintServiceError):
    """Akun teknisi tidak valid, tidak aktif, atau role tidak sesuai."""


class InvalidTicketStatusError(ComplaintServiceError):
    """Status tiket tidak mengizinkan operasi penugasan teknisi."""


class FilterValidationError(ComplaintServiceError):
    """Kesalahan validasi parameter pencarian dan penyaringan tiket."""


def parse_and_validate_filter_params(
    raw_params: dict[str, str | None],
) -> tuple[dict[str, Any] | None, dict[str, str]]:
    """
    Validasi dan normalisasi seluruh parameter filter multi-kriteria secara terpusat.

    Aturan Penentuan Status:
    1. Status tidak dikirim (raw_status is None):
       - Akses antrean awal atau hanya pagination (tanpa filter substantif) -> default 'Baru'.
       - Filter lain terisi (keyword, kategori, lokasi, tanggal) -> None (seluruh status).
    2. Status eksplisit 'all', 'semua', atau string kosong ('') -> None (seluruh status).
    3. Status resmi ('Baru', 'Terverifikasi', 'Diproses', 'Selesai') -> status tersebut.
    4. Status lain -> error validasi eksplisit.
    """
    errors: dict[str, str] = {}
    validated: dict[str, Any] = {}

    # 0. Paginasi (page & per_page): validasi sebelum akses database
    raw_page = raw_params.get("page")
    if raw_page is None or str(raw_page).strip() == "":
        validated["page"] = 1
    else:
        try:
            page_val = int(str(raw_page).strip())
        except (TypeError, ValueError):
            errors["page"] = "Nomor halaman harus berupa angka bulat positif minimal 1."
        else:
            if page_val < 1:
                errors["page"] = "Nomor halaman harus berupa angka bulat positif minimal 1."
            elif page_val > MAX_PAGE:
                errors["page"] = f"Nomor halaman harus berada pada rentang 1 sampai {MAX_PAGE}."
            else:
                validated["page"] = page_val

    raw_per_page = raw_params.get("per_page")
    if raw_per_page is None or str(raw_per_page).strip() == "":
        validated["per_page"] = 15
    else:
        try:
            per_page_val = int(str(raw_per_page).strip())
        except (TypeError, ValueError):
            errors["per_page"] = "Jumlah data per halaman harus berupa angka antara 1 sampai 50."
        else:
            if per_page_val < 1 or per_page_val > 50:
                errors["per_page"] = "Jumlah data per halaman harus berupa angka antara 1 sampai 50."
            else:
                validated["per_page"] = per_page_val

    if errors:
        return None, errors

    # 1. Kata Kunci: teks bebas, sanitasi whitespace
    raw_keyword = (raw_params.get("keyword") or "").strip()
    validated["keyword"] = raw_keyword if raw_keyword else None

    # 2. Kategori Resmi (category_id):
    # Wajib integer dan wajib ada dalam daftar kategori aktif di database
    raw_category = (raw_params.get("category_id") or "").strip()
    if raw_category:
        if not raw_category.isdigit():
            errors["category_id"] = "Kategori fasilitas harus berupa angka ID yang valid."
        else:
            cat_id = int(raw_category)
            active_ids = {c.id for c in get_active_categories()}
            if cat_id not in active_ids:
                errors["category_id"] = "Kategori fasilitas yang dipilih tidak valid atau tidak aktif."
            else:
                validated["category_id"] = cat_id
    else:
        validated["category_id"] = None

    # 3. Lantai (floor_number):
    # Wajib integer antara 1 sampai 4
    raw_floor = (raw_params.get("floor_number") or "").strip()
    if raw_floor:
        if not raw_floor.isdigit() or int(raw_floor) not in FLOOR_NUMBERS:
            errors["floor_number"] = f"Nomor lantai harus berupa angka antara {min(FLOOR_NUMBERS)} sampai {max(FLOOR_NUMBERS)}."
        else:
            validated["floor_number"] = int(raw_floor)
    else:
        validated["floor_number"] = None

    # 4. Nama Ruangan (room_name):
    raw_room = (raw_params.get("room_name") or "").strip()
    validated["room_name"] = raw_room if raw_room else None

    # 5. Rentang Tanggal (date_from & date_to):
    # Format ISO YYYY-MM-DD, batas akhir eksklusif date_to + 1 hari
    raw_date_from = (raw_params.get("date_from") or "").strip()
    raw_date_to = (raw_params.get("date_to") or "").strip()
    start_dt, end_dt_exclusive = None, None

    if raw_date_from:
        try:
            d_from = datetime.strptime(raw_date_from, "%Y-%m-%d").date()
            start_dt = datetime.combine(d_from, time.min, tzinfo=timezone.utc)
            validated["start_dt"] = start_dt
        except ValueError:
            errors["date_from"] = "Format tanggal awal tidak valid (gunakan format YYYY-MM-DD)."
    else:
        validated["start_dt"] = None

    if raw_date_to:
        try:
            d_to = datetime.strptime(raw_date_to, "%Y-%m-%d").date()
            end_dt_exclusive = datetime.combine(d_to + timedelta(days=1), time.min, tzinfo=timezone.utc)
            validated["end_dt_exclusive"] = end_dt_exclusive
        except ValueError:
            errors["date_to"] = "Format tanggal akhir tidak valid (gunakan format YYYY-MM-DD)."
    else:
        validated["end_dt_exclusive"] = None

    if start_dt and end_dt_exclusive and start_dt >= end_dt_exclusive:
        errors["date_range"] = "Tanggal awal pencarian tidak boleh melebihi tanggal akhir."

    # Evaluasi apakah ada filter kriteria substantif (di luar status dan pagination)
    has_substantive_filters = bool(
        validated.get("keyword")
        or validated.get("category_id") is not None
        or validated.get("floor_number") is not None
        or validated.get("room_name")
        or validated.get("start_dt")
        or validated.get("end_dt_exclusive")
    )

    # 6. Status Tiket:
    raw_status = raw_params.get("status")
    if raw_status is None:
        if not has_substantive_filters:
            validated["status"] = "Baru"
        else:
            validated["status"] = None
    else:
        clean_status = raw_status.strip()
        if not clean_status or clean_status.lower() in ("all", "semua"):
            validated["status"] = None
        elif clean_status in TICKET_STATUSES:
            validated["status"] = clean_status
        else:
            errors["status"] = (
                f"Status '{clean_status}' tidak valid. "
                f"Pilihan resmi: {', '.join(TICKET_STATUSES)} atau Semua."
            )

    if errors:
        return None, errors

    return validated, {}


def search_and_filter_tickets(validated_params: dict[str, Any]) -> Pagination:
    """
    Eksekusi kueri pencarian dan penyaringan multi-kriteria berbasis parameter tervalidasi.

    Menjamin:
    - Parameter binding aman via ORM.
    - Eager loading relasi many-to-one (mencegah N+1 query tanpa menduplikasi baris tiket).
    - Batas tanggal eksklusif.
    """
    stmt = (
        select(Ticket)
        .options(
            joinedload(Ticket.reporter_category),
            joinedload(Ticket.predicted_category),
            joinedload(Ticket.official_category),
            joinedload(Ticket.assigned_technician),
        )
        .order_by(Ticket.created_at.desc(), Ticket.id.desc())
    )

    if validated_params.get("status"):
        stmt = stmt.where(Ticket.status == validated_params["status"])

    if validated_params.get("keyword"):
        kw = f"%{validated_params['keyword']}%"
        stmt = stmt.where(or_(Ticket.ticket_code.ilike(kw), Ticket.description.ilike(kw)))

    if validated_params.get("category_id") is not None:
        stmt = stmt.where(Ticket.official_category_id == validated_params["category_id"])

    if validated_params.get("floor_number") is not None:
        stmt = stmt.where(Ticket.floor_number == validated_params["floor_number"])

    if validated_params.get("room_name"):
        stmt = stmt.where(Ticket.room_name.ilike(f"%{validated_params['room_name']}%"))

    if validated_params.get("start_dt"):
        stmt = stmt.where(Ticket.created_at >= validated_params["start_dt"])

    if validated_params.get("end_dt_exclusive"):
        stmt = stmt.where(Ticket.created_at < validated_params["end_dt_exclusive"])

    return db.paginate(
        stmt,
        page=validated_params["page"],
        per_page=validated_params["per_page"],
        error_out=False,
    )


def get_verification_queue(status_filter: str | None = "Baru") -> Sequence[Ticket]:
    """
    Ambil daftar tiket untuk antrean kerja sarpras dengan eager loading relasi.

    Args:
        status_filter: Filter status resmi ('Baru', 'Terverifikasi', dsb.)
                       atau 'all'/'semua' untuk mengambil seluruh tiket.
                       Default adalah 'Baru' (antrean verifikasi utama).
    """
    stmt = (
        select(Ticket)
        .options(
            joinedload(Ticket.reporter_category),
            joinedload(Ticket.predicted_category),
            joinedload(Ticket.official_category),
            joinedload(Ticket.assigned_technician),
        )
        .order_by(Ticket.created_at.desc())
    )

    clean_filter = (status_filter or "").strip()
    if clean_filter and clean_filter.lower() not in ("all", "semua"):
        if clean_filter in TICKET_STATUSES:
            stmt = stmt.where(Ticket.status == clean_filter)

    return db.session.scalars(stmt).all()


def get_ticket_by_id(ticket_id: int) -> Ticket | None:
    """Ambil tiket tunggal beserta relasi kategori, teknisi, dan pelapor."""
    stmt = (
        select(Ticket)
        .options(
            joinedload(Ticket.reporter_category),
            joinedload(Ticket.predicted_category),
            joinedload(Ticket.official_category),
            joinedload(Ticket.assigned_technician),
            joinedload(Ticket.reporter),
        )
        .where(Ticket.id == ticket_id)
    )
    return db.session.scalar(stmt)


def get_active_technicians() -> Sequence[User]:
    """Ambil seluruh akun pengguna dengan role 'teknisi' yang berstatus aktif."""
    return db.session.scalars(
        select(User)
        .where(User.role == "teknisi", User.is_active.is_(True))
        .order_by(User.full_name, User.username)
    ).all()


def get_ticket_audit_logs(ticket_id: int) -> Sequence[AuditLog]:
    """Ambil seluruh entri riwayat audit log untuk satu tiket tertentu."""
    stmt = (
        select(AuditLog)
        .options(joinedload(AuditLog.actor))
        .where(AuditLog.ticket_id == ticket_id)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    )
    return db.session.scalars(stmt).all()


def transition_ticket_status(
    ticket: Ticket,
    new_status: str,
    actor_user: User,
    note: str | None = None,
    *,
    commit: bool = True,
) -> tuple[Ticket, bool]:
    """
    Eksekusi transisi status resmi tiket dengan otorisasi peran ketat dan audit atomik (FR-09).

    Aturan Otorisasi Operasional & Idempotensi:
    - new_status divalidasi terhadap TICKET_STATUSES sebelum pengecekan idempotensi.
    - Admin Sarpras berwenang di seluruh siklus status resmi (Baru, Terverifikasi, Diproses, Selesai).
    - Teknisi hanya berwenang pada tiket yang ditugaskan kepadanya dan hanya pada status
      operasional aktif: Terverifikasi atau Diproses. Pemanggilan no-op pada Baru atau Selesai
      oleh teknisi ditolak secara eksplisit dengan InvalidTicketStatusError.
    - Peran selain admin_sarpras dan teknisi (reporter, pimpinan) ditolak secara eksplisit.
    - Idempoten: Jika new_status sama dengan current_status setelah otorisasi valid,
      fungsi mengembalikan (ticket, False) tanpa mutasi database dan tanpa AuditLog.
    - Transisi mundur atau ilegal ditolak dengan InvalidTicketStatusError.

    Returns:
        tuple[Ticket, bool]: (ticket, status_changed)
    """
    # 1. Validasi & sanitasi note di awal sebelum mutasi data atau sesi DB
    clean_note = sanitize_audit_note(note)

    # 2. Validasi new_status terhadap daftar resmi TICKET_STATUSES (sebelum cek idempotensi)
    if new_status not in TICKET_STATUSES:
        raise InvalidTicketStatusError(f"Status '{new_status}' bukan status resmi tiket.")

    current_status = ticket.status

    # 3. Validasi kewenangan operasional aktor terhadap tiket dan status saat ini
    actor_role = getattr(actor_user, "role", None)

    if actor_role == "admin_sarpras":
        # Admin Sarpras memiliki kewenangan operasional penuh di seluruh siklus status
        allowed_actor_statuses = {"Baru", "Terverifikasi", "Diproses", "Selesai"}
    elif actor_role == "teknisi":
        # Teknisi HANYA berwenang pada tiket yang ditugaskan kepadanya
        if ticket.assigned_technician_id != actor_user.id:
            raise InvalidTicketStatusError(
                "Teknisi hanya dapat memperbarui status tiket yang ditugaskan kepadanya."
            )
        # DAN hanya berwenang pada status operasional aktif: Terverifikasi atau Diproses.
        # Status 'Baru' (milik Admin) dan 'Selesai' (arsip/tutup) di luar kewenangan operasional teknisi.
        allowed_actor_statuses = {"Terverifikasi", "Diproses"}
    else:
        # Peran lain (reporter, pimpinan) tidak memiliki kewenangan operasional transisi status
        raise InvalidTicketStatusError(
            f"Peran '{actor_role}' tidak memiliki kewenangan mengubah status tiket."
        )

    if current_status not in allowed_actor_statuses:
        raise InvalidTicketStatusError(
            f"Peran '{actor_role}' tidak memiliki kewenangan operasional pada tiket berstatus '{current_status}'."
        )

    # 4. Pengecekan Idempotensi (No-Op):
    # Dijalankan HANYA SETELAH new_status valid dan aktor terbukti berwenang atas status tiket saat ini.
    # Mengembalikan (ticket, False) tanpa mutasi DB dan tanpa membuat entri AuditLog.
    if new_status == current_status:
        return ticket, False

    # 5. Validasi State Machine Transisi Resmi (ketika new_status != current_status):
    allowed_roles_for_transition = ALLOWED_STATUS_TRANSITIONS.get(current_status, {}).get(new_status)

    if allowed_roles_for_transition is None:
        raise InvalidTicketStatusError(
            f"Transisi status dari '{current_status}' ke '{new_status}' tidak diizinkan."
        )

    if actor_role not in allowed_roles_for_transition:
        raise InvalidTicketStatusError(
            f"Peran '{actor_role}' tidak memiliki kewenangan mengubah status dari '{current_status}' ke '{new_status}'."
        )

    # 6. Validasi Catatan Wajib untuk Transisi Nyata ke 'Selesai' (FR-06):
    # Terjadi SEBELUM mutasi Ticket dan SEBELUM pencatatan AuditLog.
    # Menolak catatan yang None, string kosong (""), atau hanya whitespace.
    if new_status == "Selesai" and not clean_note:
        raise InvalidTicketStatusError(
            "Catatan tindakan perbaikan wajib diisi saat menyelesaikan tiket."
        )

    old_status = current_status
    status_changed = True

    try:
        ticket.status = new_status
        if new_status == "Terverifikasi" and ticket.needs_manual_verification:
            ticket.needs_manual_verification = False
        elif new_status == "Selesai":
            ticket.resolved_at = datetime.now(timezone.utc)
            ticket.resolution_note = clean_note

        log_status_change(
            ticket_id=ticket.id,
            actor_user_id=actor_user.id,
            actor_role=actor_user.role,
            old_status=old_status,
            new_status=new_status,
            note=clean_note,
        )

        if commit:
            db.session.commit()
    except Exception:
        if commit:
            db.session.rollback()
        raise

    return ticket, status_changed


def verify_ticket_category(
    ticket: Ticket,
    new_category_id: int,
    actor_user: User,
    note: str | None = None,
) -> tuple[Ticket, bool, bool]:
    """
    Verifikasi atau koreksi kategori resmi tiket secara atomik (FR-04, FR-09).

    Aturan:
    - new_category_id wajib ada dalam daftar kategori aktif K1-K7.
    - Validasi dan sanitasi catatan audit dilakukan di awal sebelum mutasi tiket.
    - Jika tiket berstatus 'Baru', transisi status didelegasikan ke transition_ticket_status(commit=False).
    - Jika tiket non-Baru memiliki needs_manual_verification=True, flag dibersihkan tanpa mengubah status.
    - Mutasi kategori resmi dicatat dengan log_category_change().
    - Mutasi tiket dan seluruh AuditLog dicatat dalam transaksi tunggal (commit atomik).

    Returns:
        tuple[Ticket, bool, bool]: (ticket, category_changed, status_changed)
    """
    # 1. Validasi & sanitasi catatan audit di awal sebelum mutasi data apa pun
    clean_note = sanitize_audit_note(note)

    # 2. Validasi kategori resmi K1-K7 aktif
    active_categories = get_active_categories()
    valid_ids = {cat.id for cat in active_categories}
    if new_category_id not in valid_ids:
        raise CategoryValidationError("Kategori resmi yang dipilih tidak valid.")

    old_category_id = ticket.official_category_id
    category_changed = old_category_id != new_category_id

    # 3. Transisi status hanya dijalankan jika tiket masih berstatus 'Baru'
    status_changed = False
    try:
        if ticket.status == "Baru":
            ticket, status_changed = transition_ticket_status(
                ticket=ticket,
                new_status="Terverifikasi",
                actor_user=actor_user,
                note=clean_note,
                commit=False,
            )
        elif ticket.needs_manual_verification:
            # Tiket non-Baru (Terverifikasi/Diproses/Selesai) yang memiliki flag manual
            # dibersihkan penandanya secara atomik tanpa memicu mutasi status atau audit status.
            ticket.needs_manual_verification = False

        # 4. Koreksi kategori resmi jika ada perubahan nilai riil
        if category_changed:
            ticket.official_category_id = new_category_id
            log_category_change(
                ticket_id=ticket.id,
                actor_user_id=actor_user.id,
                actor_role=actor_user.role,
                old_category_id=old_category_id,
                new_category_id=new_category_id,
                note=clean_note,
            )

        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return ticket, category_changed, status_changed


def assign_technician_to_ticket(
    ticket: Ticket,
    technician_id: int,
    actor_user: User,
    note: str | None = None,
) -> tuple[Ticket, bool]:
    """
    Tugaskan teknisi penanggung jawab pada tiket (FR-05).

    Aturan Status:
    - 'Terverifikasi': penugasan awal atau penugasan ulang diizinkan.
    - 'Diproses': hanya penugasan ulang yang diizinkan (tiket harus sudah memiliki penugasan sebelumnya).
    - 'Baru' dan 'Selesai': penugasan ditolak.

    Aturan Teknisi:
    - Akun teknisi wajib ditemukan, aktif (is_active=True), dan memiliki role 'teknisi'.

    AuditLog:
    - old_value dan new_value menyimpan ID teknisi yang stabil (FR-09).
    - Idempoten: tidak ada audit baru jika teknisi yang dipilih sama dengan teknisi saat ini.

    Returns:
        tuple[Ticket, bool]: (ticket, assignment_changed)
    """
    clean_note = sanitize_audit_note(note)

    if ticket.status == "Baru":
        raise InvalidTicketStatusError(
            "Tiket berstatus 'Baru' harus diverifikasi kategorinya terlebih dahulu sebelum dapat ditugaskan."
        )

    if ticket.status == "Selesai":
        raise InvalidTicketStatusError(
            "Tiket berstatus 'Selesai' tidak dapat diubah penugasan teknisinya."
        )

    if ticket.status == "Diproses" and ticket.assigned_technician_id is None:
        raise InvalidTicketStatusError(
            "Tiket berstatus 'Diproses' hanya mengizinkan penugasan ulang teknisi."
        )

    if ticket.status not in ("Terverifikasi", "Diproses"):
        raise InvalidTicketStatusError(
            f"Status tiket '{ticket.status}' tidak mengizinkan operasi penugasan teknisi."
        )

    technician = db.session.get(User, technician_id)
    if technician is None:
        raise TechnicianValidationError("Akun teknisi tidak ditemukan.")

    if not technician.is_active:
        raise TechnicianValidationError(
            "Akun teknisi yang dipilih berstatus nonaktif dan tidak dapat ditugaskan."
        )

    if technician.role != "teknisi":
        raise TechnicianValidationError(
            "Pengguna yang dipilih tidak memiliki kewenangan sebagai teknisi."
        )

    old_technician_id = ticket.assigned_technician_id
    assignment_changed = old_technician_id != technician.id

    if assignment_changed:
        try:
            ticket.assigned_technician_id = technician.id
            log_technician_assignment(
                ticket_id=ticket.id,
                actor_user_id=actor_user.id,
                actor_role=actor_user.role,
                old_technician_id=old_technician_id,
                new_technician_id=technician.id,
                note=clean_note,
            )
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    return ticket, assignment_changed


TECHNICIAN_ALLOWED_STATUS_FILTERS = {"Terverifikasi", "Diproses", "Selesai"}


def parse_and_validate_technician_filter_params(
    raw_params: dict[str, str | None],
) -> tuple[dict[str, Any] | None, dict[str, str]]:
    """
    Validasi parameter penyaringan antrean teknisi secara eksplisit.

    Aturan:
    - status: hanya menerima anggota TECHNICIAN_ALLOWED_STATUS_FILTERS ('Terverifikasi', 'Diproses', 'Selesai'),
      atau None/""/'all'/'semua' (tanpa filter status/menampilkan seluruh status penugasan).
      Nilai lain (misal status ilegal atau 'Baru') DITOLAK secara eksplisit dengan error
      dan TIDAK memperluas hasil kueri secara diam-diam.
    - page: integer antara 1 sampai MAX_PAGE.
    - per_page: integer antara 1 sampai 50 (default 20).
    """
    errors: dict[str, str] = {}
    validated: dict[str, Any] = {}

    # 1. Validasi Status
    raw_status = raw_params.get("status")
    if raw_status is None or raw_status.strip() == "" or raw_status.strip().lower() in ("all", "semua"):
        validated["status"] = None
    else:
        clean_status = raw_status.strip()
        if clean_status in TECHNICIAN_ALLOWED_STATUS_FILTERS:
            validated["status"] = clean_status
        else:
            errors["status"] = (
                f"Filter status '{clean_status}' tidak valid untuk teknisi. Pilihan: "
                f"{', '.join(sorted(list(TECHNICIAN_ALLOWED_STATUS_FILTERS)))}."
            )

    # 2. Validasi Paginasi: page
    raw_page = raw_params.get("page")
    if raw_page is None or str(raw_page).strip() == "":
        validated["page"] = 1
    else:
        try:
            page_val = int(str(raw_page).strip())
        except (TypeError, ValueError):
            errors["page"] = "Nomor halaman harus berupa bilangan bulat positif."
        else:
            if page_val < 1:
                errors["page"] = "Nomor halaman harus bernilai minimal 1."
            elif page_val > MAX_PAGE:
                errors["page"] = f"Nomor halaman harus bernilai maksimal {MAX_PAGE}."
            else:
                validated["page"] = page_val

    # 3. Validasi Paginasi: per_page
    raw_per_page = raw_params.get("per_page")
    if raw_per_page is None or raw_per_page.strip() == "":
        validated["per_page"] = 20
    else:
        try:
            per_page_val = int(raw_per_page.strip())
            if per_page_val < 1 or per_page_val > 50:
                errors["per_page"] = "Jumlah data per halaman harus antara 1 sampai 50."
            else:
                validated["per_page"] = per_page_val
        except ValueError:
            errors["per_page"] = "Jumlah data per halaman harus berupa bilangan bulat antara 1 sampai 50."

    if errors:
        return None, errors

    return validated, {}


def get_technician_assigned_tickets(
    technician_id: int,
    *,
    status_filter: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> Pagination:
    """
    Ambil daftar tiket yang secara sah ditugaskan kepada teknisi tertentu dengan eager loading.
    
    Aturan:
    - Kueri dibatasi secara ketat pada Ticket.assigned_technician_id == technician_id.
    - status_filter: disaring hanya jika bernilai 'Terverifikasi', 'Diproses', atau 'Selesai'.
    - Pengurutan: kronologis terbalik (Ticket.created_at.desc(), Ticket.id.desc()).
    - Paginasi: db.paginate dengan batas aman per_page (1 sampai 50).
    """
    stmt = (
        select(Ticket)
        .options(
            joinedload(Ticket.official_category),
            joinedload(Ticket.reporter_category),
            joinedload(Ticket.predicted_category),
            joinedload(Ticket.assigned_technician),
        )
        .where(Ticket.assigned_technician_id == technician_id)
        .order_by(Ticket.created_at.desc(), Ticket.id.desc())
    )

    if status_filter in TECHNICIAN_ALLOWED_STATUS_FILTERS:
        stmt = stmt.where(Ticket.status == status_filter)

    return db.paginate(stmt, page=page, per_page=per_page, error_out=False)


def get_technician_ticket_by_id(ticket_id: int, technician_id: int) -> Ticket | None:
    """
    Ambil tiket tunggal milik teknisi tertentu dengan proteksi IDOR di layer data.
    
    Mengembalikan objek Ticket HANYA JIKA id cocok DAN assigned_technician_id == technician_id.
    Jika tiket milik teknisi lain atau tiket belum ditugaskan, mengembalikan None.
    """
    stmt = (
        select(Ticket)
        .options(
            joinedload(Ticket.official_category),
            joinedload(Ticket.reporter_category),
            joinedload(Ticket.predicted_category),
            joinedload(Ticket.assigned_technician),
        )
        .where(Ticket.id == ticket_id, Ticket.assigned_technician_id == technician_id)
    )
    return db.session.scalar(stmt)


def get_ticket_status_counts() -> dict[str, int]:
    """
    Agregat jumlah seluruh tiket per status resmi untuk kartu KPI antrean Sarpras.

    Returns:
        dict: {'total': N, 'Baru': a, 'Terverifikasi': b, 'Diproses': c, 'Selesai': d}
        Kunci status selalu ada (default 0) untuk keempat status resmi.
    """
    stmt = select(Ticket.status, func.count(Ticket.id)).group_by(Ticket.status)
    counts = dict(db.session.execute(stmt).all())
    return {
        "total": sum(counts.values()),
        "Baru": counts.get("Baru", 0),
        "Terverifikasi": counts.get("Terverifikasi", 0),
        "Diproses": counts.get("Diproses", 0),
        "Selesai": counts.get("Selesai", 0),
    }


def get_technician_ticket_counts(technician_id: int) -> dict[str, int]:
    """
    Hitung ringkasan jumlah tiket penugasan teknisi berdasarkan status untuk kartu informasi.
    Seluruh kueri agregat status dibatasi secara ketat pada Ticket.assigned_technician_id == technician_id.
    
    Returns:
        dict: {'total': X, 'Terverifikasi': Y, 'Diproses': Z, 'Selesai': W}
    """
    stmt = (
        select(Ticket.status, func.count(Ticket.id))
        .where(Ticket.assigned_technician_id == technician_id)
        .group_by(Ticket.status)
    )
    counts = dict(db.session.execute(stmt).all())
    return {
        "total": sum(counts.values()),
        "Terverifikasi": counts.get("Terverifikasi", 0),
        "Diproses": counts.get("Diproses", 0),
        "Selesai": counts.get("Selesai", 0),
    }


def serve_ticket_photo(ticket: Ticket | None):
    """
    Sajikan file fisik bukti foto tiket secara aman dari UPLOAD_FOLDER dengan pencegahan path traversal
    dan perlindungan terhadap symbolic link yang menunjuk ke luar direktori.

    Keamanan:
    - Memeriksa bahwa objek tiket valid (bukan None) dan memiliki atribut photo_filename (abort 404 jika tidak).
    - Resolusi path absolut pada UPLOAD_FOLDER dan file foto (mengikuti symlink jika ada).
    - Memvalidasi containment path menggunakan photo_path.is_relative_to(upload_folder) untuk memastikan
      file benar-benar berada di dalam UPLOAD_FOLDER (bahkan jika berupa symbolic link yang mengarah ke luar).
    - Memeriksa photo_path.is_file() untuk memastikan target adalah file fisik reguler.
    - Otorisasi peran dan hak akses tiket WAJIB diselesaikan pada level route pemanggil
      (Admin Sarpras atau Teknisi penanggung jawab) sebelum helper ini dipanggil.
    """
    if ticket is None or not ticket.photo_filename:
        abort(404)

    upload_folder = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    safe_filename = Path(ticket.photo_filename).name
    photo_path = (upload_folder / safe_filename).resolve()

    # Validasi containment dan symlink escape: file harus berada di dalam UPLOAD_FOLDER dan merupakan file fisik
    if not photo_path.is_file() or not photo_path.is_relative_to(upload_folder):
        abort(404)

    return send_from_directory(
        upload_folder,
        safe_filename,
        mimetype=ticket.photo_mime_type or "application/octet-stream",
    )


