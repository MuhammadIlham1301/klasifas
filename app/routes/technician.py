"""Rute operasional Papan Antrean Tiket Teknisi (FR-06)."""
from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)

from app.services.audit_service import AuditNoteLengthError
from app.services.complaint_service import (
    InvalidTicketStatusError,
    get_technician_assigned_tickets,
    get_technician_ticket_by_id,
    get_technician_ticket_counts,
    parse_and_validate_technician_filter_params,
    serve_ticket_photo,
    transition_ticket_status,
)
from app.utils.decorators import role_required

technician_bp = Blueprint("technician", __name__, url_prefix="/teknisi")


@technician_bp.route("/tiket", methods=["GET"])
@role_required("teknisi")
def ticket_queue():
    """
    Tampilkan papan antrean tiket yang secara sah ditugaskan kepada teknisi login (FR-06).
    
    Keamanan & Isolasi:
    - Hanya dapat diakses oleh peran 'teknisi'.
    - Seluruh data tiket dan metrik dibatasi ketat pada assigned_technician_id == g.current_user.id.
    - Validasi filter eksplisit untuk mencegah pembesaran hasil kueri secara diam-diam.
    """
    raw_params = {
        "status": request.args.get("status"),
        "page": request.args.get("page"),
        "per_page": request.args.get("per_page"),
    }

    form_filters = {
        k: (v.strip() if v is not None else "")
        for k, v in raw_params.items()
    }

    counts = get_technician_ticket_counts(g.current_user.id)

    # 1. Validasi parameter filter terlebih dahulu
    validated_params, errors = parse_and_validate_technician_filter_params(raw_params)

    # 2. Jika ada error validasi: tolak eksekusi kueri tiket dan tampilkan pesan error
    if errors:
        for err_msg in errors.values():
            flash(err_msg, "danger")

        return render_template(
            "technician/queue.html",
            tickets=[],
            pagination=None,
            active_filters=form_filters,
            counts=counts,
        )

    # 3. Kueri tiket terpaginasi dalam cakupan penugasan teknisi login
    pagination = get_technician_assigned_tickets(
        g.current_user.id,
        status_filter=validated_params["status"],
        page=validated_params["page"],
        per_page=validated_params["per_page"],
    )

    active_filters = {
        "status": validated_params["status"] or "all",
        "per_page": validated_params["per_page"],
    }

    return render_template(
        "technician/queue.html",
        tickets=pagination.items if pagination else [],
        pagination=pagination,
        active_filters=active_filters,
        counts=counts,
    )


@technician_bp.route("/tiket/<int:ticket_id>", methods=["GET"])
@role_required("teknisi")
def ticket_detail(ticket_id: int):
    """
    Tampilkan rincian pekerjaan tiket yang ditugaskan kepada teknisi login.

    IDOR Protection:
    - Memverifikasi secara ketat bahwa tiket ditugaskan kepada g.current_user.id.
    - Jika tiket tidak ada atau milik teknisi lain, sistem mengembalikan 404 Not Found.
    """
    ticket = get_technician_ticket_by_id(ticket_id, g.current_user.id)
    if ticket is None:
        abort(404)

    return render_template("technician/detail.html", ticket=ticket)


@technician_bp.route("/tiket/<int:ticket_id>/foto", methods=["GET"])
@role_required("teknisi")
def ticket_photo(ticket_id: int):
    """
    Sajikan bukti foto keluhan untuk tiket yang sah ditugaskan kepada teknisi login.

    IDOR & Filesystem Protection:
    - Memverifikasi kepemilikan penugasan tiket pada teknisi login sebelum melayani foto.
    - Menggunakan kembali helper serve_ticket_photo untuk containment path & symlink defense.
    """
    ticket = get_technician_ticket_by_id(ticket_id, g.current_user.id)
    if ticket is None:
        abort(404)

    return serve_ticket_photo(ticket)


@technician_bp.route("/tiket/<int:ticket_id>/status", methods=["POST"])
@role_required("teknisi")
def update_ticket_status(ticket_id: int):
    """
    Perbarui status pengerjaan operasional tiket yang ditugaskan kepada teknisi login (FR-06).

    Keamanan & Validasi:
    - Hanya dapat diakses oleh peran 'teknisi'.
    - IDOR Protection: Memverifikasi bahwa tiket ditugaskan kepada g.current_user.id (404 jika bukan).
    - Memanfaatkan transition_ticket_status() untuk validasi transisi, mutasi atomik, dan audit log.
    - Menangani InvalidTicketStatusError dan AuditNoteLengthError sebagai pesan flash pengguna.
    """
    ticket = get_technician_ticket_by_id(ticket_id, g.current_user.id)
    if ticket is None:
        abort(404)

    raw_status = (request.form.get("new_status") or "").strip()
    raw_note = request.form.get("note")

    try:
        ticket, status_changed = transition_ticket_status(
            ticket=ticket,
            new_status=raw_status,
            actor_user=g.current_user,
            note=raw_note,
            commit=True,
        )
    except (InvalidTicketStatusError, AuditNoteLengthError) as exc:
        flash(str(exc), "danger")
        return redirect(url_for("technician.ticket_detail", ticket_id=ticket.id))
    except Exception:
        current_app.logger.exception(
            "Gagal memperbarui status pengerjaan tiket %s oleh teknisi %s",
            ticket.id,
            g.current_user.id,
        )
        flash("Terjadi kesalahan sistem saat memperbarui status tiket.", "danger")
        return redirect(url_for("technician.ticket_detail", ticket_id=ticket.id))

    if status_changed:
        if ticket.status == "Diproses":
            flash(
                f"Status tiket {ticket.ticket_code} berhasil diperbarui menjadi Diproses. Selamat mengerjakan!",
                "success",
            )
        elif ticket.status == "Selesai":
            flash(
                f"Tiket {ticket.ticket_code} berhasil diselesaikan dan catatan tindakan perbaikan telah tersimpan.",
                "success",
            )
        else:
            flash(
                f"Status tiket {ticket.ticket_code} berhasil diperbarui menjadi {ticket.status}.",
                "success",
            )
    else:
        flash("Status tiket tidak mengalami perubahan.", "info")

    return redirect(url_for("technician.ticket_detail", ticket_id=ticket.id))


