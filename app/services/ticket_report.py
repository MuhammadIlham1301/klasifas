"""Validasi formulir dan pembuatan tiket laporan publik (FR-01)."""
from collections.abc import Mapping, Sequence

from sqlalchemy import or_, select

from app.extensions import db
from app.models.category import Category
from app.models.ticket import Ticket
from app.services.classification_service import classify_ticket_description
from app.services.ticket_photo import StoredPhoto
from app.utils.ticket_identity import (
    generate_access_token,
    generate_ticket_code,
)

BUILDING_NAME = "Gedung FTII"
FLOOR_NUMBERS = (1, 2, 3, 4)
DESCRIPTION_MAX_LENGTH = 2000
ROOM_MAX_LENGTH = 100
LOCATION_DETAIL_MAX_LENGTH = 255
REPORTER_NAME_MAX_LENGTH = 120
REPORTER_CONTACT_MAX_LENGTH = 120
IDENTITY_ATTEMPTS = 5


class ReportValidationError(ValueError):
    """Kesalahan validasi formulir laporan per field."""

    def __init__(self, errors: dict[str, str]):
        super().__init__("Data laporan tidak valid.")
        self.errors = errors


class TicketIdentityError(RuntimeError):
    """Kegagalan membuat kode atau hash token tiket yang unik."""


def get_active_categories() -> Sequence[Category]:
    """Ambil kategori aktif yang boleh dipilih pelapor."""
    return db.session.scalars(
        select(Category)
        .where(Category.is_active.is_(True))
        .order_by(Category.code)
    ).all()


def _clean(form: Mapping[str, str], field: str) -> str:
    return (form.get(field) or "").strip()


def _optional(value: str) -> str | None:
    return value or None


def validate_report_form(
    form: Mapping[str, str], active_categories: Sequence[Category]
) -> dict[str, object]:
    """Validasi input laporan dan kembalikan data yang sudah dinormalisasi."""
    errors: dict[str, str] = {}

    description = _clean(form, "description")
    building_name = _clean(form, "building_name")
    floor_raw = _clean(form, "floor_number")
    room_name = _clean(form, "room_name")
    location_detail = _clean(form, "location_detail")
    reporter_name = _clean(form, "reporter_name")
    reporter_contact = _clean(form, "reporter_contact")
    category_raw = _clean(form, "reporter_category_id")

    if not description:
        errors["description"] = "Deskripsi keluhan wajib diisi."
    elif len(description) > DESCRIPTION_MAX_LENGTH:
        errors["description"] = (
            f"Deskripsi keluhan maksimal {DESCRIPTION_MAX_LENGTH} karakter."
        )

    if building_name != BUILDING_NAME:
        errors["building_name"] = "Gedung yang dipilih tidak valid."

    valid_floors = {str(number) for number in FLOOR_NUMBERS}
    if floor_raw not in valid_floors:
        errors["floor_number"] = "Lantai wajib dipilih antara 1 sampai 4."

    if not room_name:
        errors["room_name"] = "Nama atau nomor ruang wajib diisi."
    elif len(room_name) > ROOM_MAX_LENGTH:
        errors["room_name"] = f"Nama ruang maksimal {ROOM_MAX_LENGTH} karakter."

    if len(location_detail) > LOCATION_DETAIL_MAX_LENGTH:
        errors["location_detail"] = (
            f"Detail lokasi maksimal {LOCATION_DETAIL_MAX_LENGTH} karakter."
        )

    reporter_category_id = None
    if category_raw:
        active_category_ids = {
            category.id for category in active_categories if category.is_active
        }
        if not category_raw.isdigit():
            errors["reporter_category_id"] = "Kategori yang dipilih tidak valid."
        else:
            candidate_id = int(category_raw)
            if candidate_id not in active_category_ids:
                errors["reporter_category_id"] = (
                    "Kategori yang dipilih tidak tersedia."
                )
            else:
                reporter_category_id = candidate_id

    if len(reporter_name) > REPORTER_NAME_MAX_LENGTH:
        errors["reporter_name"] = (
            f"Nama pelapor maksimal {REPORTER_NAME_MAX_LENGTH} karakter."
        )

    if len(reporter_contact) > REPORTER_CONTACT_MAX_LENGTH:
        errors["reporter_contact"] = (
            f"Kontak pelapor maksimal {REPORTER_CONTACT_MAX_LENGTH} karakter."
        )

    if errors:
        raise ReportValidationError(errors)

    return {
        "description": description,
        "building_name": building_name,
        "floor_number": int(floor_raw),
        "room_name": room_name,
        "location_detail": _optional(location_detail),
        "reporter_name": _optional(reporter_name),
        "reporter_contact": _optional(reporter_contact),
        "reporter_category_id": reporter_category_id,
    }


def _generate_unique_identity() -> tuple[str, str, str]:
    for _ in range(IDENTITY_ATTEMPTS):
        ticket_code = generate_ticket_code()
        raw_token, access_token_hash = generate_access_token()
        existing_id = db.session.scalar(
            select(Ticket.id).where(
                or_(
                    Ticket.ticket_code == ticket_code,
                    Ticket.access_token_hash == access_token_hash,
                )
            )
        )
        if existing_id is None:
            return ticket_code, raw_token, access_token_hash

    raise TicketIdentityError("Identitas tiket unik tidak dapat dibuat.")


def create_ticket_with_token(
    data: Mapping[str, object],
    photo: StoredPhoto | None = None,
    reporter_id: int | None = None,
) -> tuple[Ticket, str]:
    """Buat tiket dan kembalikan token asli hanya untuk distribusi."""
    ticket_code, raw_token, access_token_hash = _generate_unique_identity()
    classification = classify_ticket_description(str(data["description"]))

    ticket = Ticket(
        ticket_code=ticket_code,
        access_token_hash=access_token_hash,
        description=str(data["description"]),
        reporter_id=reporter_id,
        reporter_category_id=data["reporter_category_id"],
        predicted_category_id=classification.predicted_category_id,
        confidence_score=classification.confidence_score,
        status="Baru",
        building_name=str(data["building_name"]),
        floor_number=int(data["floor_number"]),
        room_name=str(data["room_name"]),
        location_detail=data["location_detail"],
        reporter_name=data["reporter_name"],
        reporter_contact=data["reporter_contact"],
        needs_manual_verification=classification.needs_manual_verification,
    )

    if photo is not None:
        ticket.photo_filename = photo.filename
        ticket.photo_mime_type = photo.mime_type
        ticket.photo_size_bytes = photo.size_bytes
        ticket.photo_uploaded_at = photo.uploaded_at

    db.session.add(ticket)
    db.session.flush()
    return ticket, raw_token


def create_ticket(
    data: Mapping[str, object],
    photo: StoredPhoto | None = None,
    reporter_id: int | None = None,
) -> Ticket:
    """Buat tiket baru tanpa melakukan commit (raw token dibuang)."""
    ticket, _ = create_ticket_with_token(data, photo, reporter_id=reporter_id)
    return ticket


def rotate_access_token(ticket: Ticket) -> str:
    """Ganti hash token tiket dan kembalikan token asli baru."""
    raw_token, access_token_hash = generate_access_token()
    ticket.access_token_hash = access_token_hash
    db.session.flush()
    return raw_token
