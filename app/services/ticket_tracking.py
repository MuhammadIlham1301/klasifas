"""
Layanan verifikasi kredensial pelacakan dan sanitasi data publik tiket (FR-02).
"""
import re
from typing import Any

from sqlalchemy import select

from app.extensions import db
from app.models.ticket import Ticket
from app.utils.ticket_identity import verify_access_token

TICKET_CODE_REGEX = re.compile(r"^KF-[23456789A-HJ-NP-Z]{6}$")


def sanitize_ticket_tracking_data(ticket: Ticket) -> dict[str, Any]:
    """
    Ekstrak data tiket yang diizinkan untuk dikonsumsi publik oleh pelapor.

    Aturan Keamanan dan Privasi:
    - Identitas pelapor (reporter_name, reporter_contact) TIDAK PERNAH disertakan.
    - Teknisi penanggung jawab (assigned_technician_id) TIDAK PERNAH disertakan.
    - Token hash, skor keyakinan ML, dan nama fisik file foto internal TIDAK DISERTAKAN.
    - Catatan penyelesaian teknisi (resolution_note) hanya disertakan jika tiket berstatus 'Selesai'.
    """
    category_name: str
    if ticket.official_category:
        category_name = ticket.official_category.name
    elif ticket.reporter_category:
        category_name = ticket.reporter_category.name
    else:
        category_name = "Menunggu Verifikasi"

    return {
        "ticket_code": ticket.ticket_code,
        "status": ticket.status,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
        "resolved_at": ticket.resolved_at,
        "resolution_note": (
            ticket.resolution_note if ticket.status == "Selesai" else None
        ),
        "building_name": ticket.building_name,
        "floor_number": ticket.floor_number,
        "room_name": ticket.room_name,
        "location_detail": ticket.location_detail,
        "description": ticket.description,
        "category_name": category_name,
        "has_photo": bool(ticket.photo_filename),
    }


def get_ticket_tracking_info(
    ticket_code: str, raw_token: str
) -> dict[str, Any] | None:
    """
    Validasi kredensial pelacakan mandiri dan kembalikan data publik yang disanitasi.

    Perlindungan Anti-Enumerasi:
    - Jika format kode tiket tidak valid, tiket tidak ditemukan di basis data,
      atau token akses tidak cocok dengan hash tersimpan, fungsi selalu mengembalikan
      None tanpa membedakan penyebab kegagalan.
    - Komparasi token dilakukan secara constant-time melalui hmac.compare_digest.
    """
    clean_code = (ticket_code or "").strip().upper()
    clean_token = (raw_token or "").strip()

    if not clean_code or not clean_token:
        return None

    if not TICKET_CODE_REGEX.fullmatch(clean_code):
        return None

    ticket = db.session.scalar(
        select(Ticket).where(Ticket.ticket_code == clean_code)
    )
    if ticket is None:
        return None

    if not verify_access_token(clean_token, ticket.access_token_hash):
        return None

    return sanitize_ticket_tracking_data(ticket)

