"""Layanan pencatatan audit trail operasional (FR-09)."""
from typing import Any

from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.audit_log import AUDIT_ACTIONS, AuditLog
from app.models.category import Category
from app.models.ticket import Ticket

MAX_AUDIT_NOTE_LENGTH = 1000
MAX_PAGE = 10_000
VALID_AUDIT_ACTIONS = {"category_changed", "status_changed", "technician_assigned"}


class AuditServiceError(Exception):
    """Kesalahan umum pada layanan audit operasional."""


class AuditNoteLengthError(AuditServiceError):
    """Panjang catatan audit melebihi batas maksimal 1000 karakter."""


def sanitize_audit_note(note: str | None) -> str | None:
    """
    Sanitasi dan validasi panjang catatan audit secara ketat sebelum mutasi data.

    Aturan:
    - Menghilangkan whitespace di awal/akhir string (strip).
    - String kosong ("") atau hanya spasi dikonversi menjadi None.
    - Catatan dengan panjang melebihi 1000 karakter ditolak secara eksplisit dengan
      AuditNoteLengthError (bukan dipotong diam-diam).
    """
    if note is None:
        return None
    clean_note = note.strip()
    if not clean_note:
        return None
    if len(clean_note) > MAX_AUDIT_NOTE_LENGTH:
        raise AuditNoteLengthError(
            f"Catatan audit tidak boleh melebihi {MAX_AUDIT_NOTE_LENGTH} karakter."
        )
    return clean_note


def record_audit_log(
    *,
    ticket_id: int,
    actor_user_id: int | None,
    actor_role: str | None,
    action: str,
    field_name: str,
    old_value: Any,
    new_value: Any,
    note: str | None = None,
) -> AuditLog | None:
    """
    Catat mutasi operasional ke tabel audit_logs jika terjadi perubahan nilai riil.

    Aturan:
    - action wajib termasuk dalam VALID_AUDIT_ACTIONS whitelist.
    - note disanitasi dan divalidasi panjangnya sebelum pencatatan.
    - Hanya mencatat entri jika old_value berbeda dari new_value (setelah dikonversi ke string).
    - Menambahkan entri ke db.session aktif tanpa commit mandiri agar tetap atomik
      dengan transaksi pemanggil.
    - Mengembalikan objek AuditLog jika dicatat, atau None jika tidak ada perubahan nilai.
    """
    if action not in VALID_AUDIT_ACTIONS:
        raise AuditServiceError(f"Aksi audit '{action}' tidak terdaftar dalam whitelist.")

    clean_note = sanitize_audit_note(note)

    old_str = None if old_value is None else str(old_value)
    new_str = None if new_value is None else str(new_value)

    # Idempoten: Jangan membuat entri jika nilai tidak berubah
    if old_str == new_str:
        return None

    entry = AuditLog(
        ticket_id=ticket_id,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        action=action,
        field_name=field_name,
        old_value=old_str,
        new_value=new_str,
        note=clean_note,
    )
    db.session.add(entry)
    return entry


def log_category_change(
    *,
    ticket_id: int,
    actor_user_id: int | None,
    actor_role: str | None,
    old_category_id: int | None,
    new_category_id: int,
    note: str | None = None,
) -> AuditLog | None:
    """Catat perubahan kategori resmi tiket ke audit log."""
    return record_audit_log(
        ticket_id=ticket_id,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        action="category_changed",
        field_name="official_category_id",
        old_value=old_category_id,
        new_value=new_category_id,
        note=note,
    )


def log_status_change(
    *,
    ticket_id: int,
    actor_user_id: int | None,
    actor_role: str | None,
    old_status: str,
    new_status: str,
    note: str | None = None,
) -> AuditLog | None:
    """Catat perubahan status operasional tiket ke audit log."""
    return record_audit_log(
        ticket_id=ticket_id,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        action="status_changed",
        field_name="status",
        old_value=old_status,
        new_value=new_status,
        note=note,
    )


def log_technician_assignment(
    *,
    ticket_id: int,
    actor_user_id: int | None,
    actor_role: str | None,
    old_technician_id: int | None,
    new_technician_id: int,
    note: str | None = None,
) -> AuditLog | None:
    """Catat penetapan atau perubahan teknisi penanggung jawab ke audit log (FR-05)."""
    return record_audit_log(
        ticket_id=ticket_id,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        action="technician_assigned",
        field_name="assigned_technician_id",
        old_value=old_technician_id,
        new_value=new_technician_id,
        note=note,
    )


def get_all_categories_map() -> dict[int, Category]:
    """
    Ambil seluruh kategori (aktif maupun nonaktif) untuk pemetaan historis audit log.
    Mencegah kegagalan lookup pada entri audit lama jika kategori telah dinonaktifkan.
    """
    categories = db.session.scalars(select(Category)).all()
    return {cat.id: cat for cat in categories}


def parse_and_validate_audit_filter_params(
    raw_params: dict[str, str | None],
) -> tuple[dict[str, Any] | None, dict[str, str]]:
    """
    Validasi dan normalisasi parameter penyaringan log audit secara terpusat.

    Aturan:
    - action: menerima tiga aksi resmi ("category_changed", "status_changed", "technician_assigned"),
      string kosong "", "all", dan "semua" (diperlakukan sebagai tanpa filter aksi/semua aksi).
      Nilai lain di luar pilihan tersebut ditolak secara eksplisit dengan pesan validasi error.
    - ticket_code: teks dibersihkan (strip), maksimal 20 karakter.
    - page: bilangan bulat antara 1 sampai MAX_PAGE.
    - per_page: bilangan bulat antara 1 sampai 50 (default 20).
    - Konsistensi: jika ada error validasi, query pencarian TIDAK dijalankan
      dan seluruh nilai input pengguna dipertahankan.
    """
    errors: dict[str, str] = {}
    validated: dict[str, Any] = {}

    # 1. Validasi Aksi
    raw_action = raw_params.get("action")
    if raw_action is None or raw_action.strip() == "" or raw_action.strip().lower() in ("all", "semua"):
        validated["action"] = None
    else:
        clean_action = raw_action.strip()
        if clean_action in VALID_AUDIT_ACTIONS:
            validated["action"] = clean_action
        else:
            errors["action"] = (
                f"Aksi audit '{clean_action}' tidak valid. Pilihan resmi: "
                f"{', '.join(sorted(list(VALID_AUDIT_ACTIONS)))}."
            )

    # 2. Validasi Kode Tiket
    raw_code = raw_params.get("ticket_code")
    if raw_code is None or raw_code.strip() == "":
        validated["ticket_code"] = None
    else:
        clean_code = raw_code.strip()
        if len(clean_code) > 20:
            errors["ticket_code"] = "Kode tiket tidak boleh melebihi 20 karakter."
        else:
            validated["ticket_code"] = clean_code

    # 3. Validasi Paginasi: page
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

    # 4. Validasi Paginasi: per_page
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


def get_audit_logs_paginated(
    *,
    page: int = 1,
    per_page: int = 20,
    action: str | None = None,
    ticket_code: str | None = None,
) -> Pagination:
    """
    Ambil riwayat audit operasional terpaginasi dengan eager loading (FR-09).
    """
    stmt = (
        select(AuditLog)
        .join(AuditLog.ticket)
        .options(
            joinedload(AuditLog.actor),
            joinedload(AuditLog.ticket),
        )
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    )

    if action:
        stmt = stmt.where(AuditLog.action == action)

    if ticket_code:
        stmt = stmt.where(Ticket.ticket_code.ilike(f"%{ticket_code}%"))

    return db.paginate(stmt, page=page, per_page=per_page, error_out=False)


