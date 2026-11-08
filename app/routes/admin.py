"""Rute operasional Sarpras: Antrean tiket, verifikasi, dan penyajian foto (FR-04)."""
from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)

from app.extensions import db
from app.models.ticket import TICKET_STATUSES, Ticket
from app.services.audit_service import (
    VALID_AUDIT_ACTIONS,
    get_all_categories_map,
    get_audit_logs_paginated,
    parse_and_validate_audit_filter_params,
)
from app.services.complaint_service import (
    CategoryValidationError,
    InvalidTicketStatusError,
    TechnicianValidationError,
    assign_technician_to_ticket,
    get_active_technicians,
    get_ticket_audit_logs,
    get_ticket_by_id,
    get_ticket_status_counts,
    get_verification_queue,
    parse_and_validate_filter_params,
    search_and_filter_tickets,
    serve_ticket_photo,
    verify_ticket_category,
)
from app.services.ticket_report import get_active_categories
from app.utils.decorators import role_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/tiket", methods=["GET"])
@role_required("admin_sarpras")
def ticket_queue():
    """Tampilkan antrean tiket dengan dukungan filter multi-kriteria dan paginasi."""
    categories = get_active_categories()

    # 1. Kumpulkan seluruh raw parameter tanpa mengubah None menjadi string kosong
    raw_params = {
        "keyword": request.args.get("keyword"),
        "status": request.args.get("status"),  # Tetap None jika tidak dikirim dalam query string
        "category_id": request.args.get("category_id"),
        "floor_number": request.args.get("floor_number"),
        "room_name": request.args.get("room_name"),
        "date_from": request.args.get("date_from"),
        "date_to": request.args.get("date_to"),
        "page": request.args.get("page"),
        "per_page": request.args.get("per_page"),
    }

    # 2. Validasi terpusat via Service Layer
    validated_params, errors = parse_and_validate_filter_params(raw_params)

    # Dictionary retensi isian form (mengonversi None menjadi "" agar aman dirender di atribut HTML)
    form_filters = {
        k: (v.strip() if v is not None else "")
        for k, v in raw_params.items()
    }

    # 3. Jika ada kesalahan validasi: Tampilkan flash message, JANGAN jalankan kueri
    if errors:
        for err_msg in errors.values():
            flash(err_msg, "danger")

        return render_template(
            "admin/queue.html",
            tickets=[],
            pagination=None,
            categories=categories,
            current_status=form_filters.get("status") or "all",
            active_filters=form_filters,
            statuses=TICKET_STATUSES,
            status_counts=get_ticket_status_counts(),
        )

    # 4. Jika validasi sukses: Jalankan kueri pencarian & paginasi
    pagination = search_and_filter_tickets(validated_params)
    tickets = pagination.items if pagination else []

    effective_status = validated_params.get("status")
    status_for_links = effective_status if effective_status else "all"

    # Format parameter aktif untuk pagination links dan retensi filter
    active_filters = {
        "keyword": form_filters["keyword"],
        "status": status_for_links,
        "category_id": str(validated_params.get("category_id") or ""),
        "floor_number": str(validated_params.get("floor_number") or ""),
        "room_name": form_filters["room_name"],
        "date_from": form_filters["date_from"],
        "date_to": form_filters["date_to"],
        "per_page": validated_params["per_page"],
    }

    return render_template(
        "admin/queue.html",
        tickets=tickets,
        pagination=pagination,
        categories=categories,
        current_status=status_for_links,
        active_filters=active_filters,
        statuses=TICKET_STATUSES,
        status_counts=get_ticket_status_counts(),
    )


@admin_bp.route("/tiket/<int:ticket_id>/verifikasi", methods=["GET"])
@role_required("admin_sarpras")
def verify_ticket_form(ticket_id: int):
    """Tampilkan formulir verifikasi dan detail lengkap tiket."""
    ticket = get_ticket_by_id(ticket_id)
    if ticket is None:
        abort(404)

    categories = get_active_categories()
    technicians = get_active_technicians()
    audit_logs = get_ticket_audit_logs(ticket_id)
    return render_template(
        "admin/verify.html",
        ticket=ticket,
        categories=categories,
        technicians=technicians,
        audit_logs=audit_logs,
    )


@admin_bp.route("/tiket/<int:ticket_id>/verifikasi", methods=["POST"])
@role_required("admin_sarpras")
def verify_ticket(ticket_id: int):
    """Proses verifikasi atau koreksi kategori resmi tiket."""
    ticket = get_ticket_by_id(ticket_id)
    if ticket is None:
        abort(404)

    category_raw = (request.form.get("official_category_id") or "").strip()
    note = (request.form.get("note") or "").strip() or None

    if not category_raw.isdigit():
        flash("Kategori resmi wajib dipilih.", "danger")
        return redirect(url_for("admin.verify_ticket_form", ticket_id=ticket.id))

    try:
        ticket, category_changed, status_changed = verify_ticket_category(
            ticket=ticket,
            new_category_id=int(category_raw),
            actor_user=g.current_user,
            note=note,
        )
    except CategoryValidationError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("admin.verify_ticket_form", ticket_id=ticket.id))
    except Exception:
        current_app.logger.exception(
            "Gagal memproses verifikasi kategori tiket %s", ticket.id
        )
        flash("Terjadi kesalahan sistem saat memverifikasi tiket.", "danger")
        return redirect(url_for("admin.verify_ticket_form", ticket_id=ticket.id))

    if status_changed:
        flash(
            f"Tiket {ticket.ticket_code} berhasil diverifikasi (Status: Terverifikasi).",
            "success",
        )
    elif category_changed:
        flash(
            f"Kategori resmi tiket {ticket.ticket_code} berhasil diperbarui.",
            "success",
        )
    else:
        flash(
            f"Kategori resmi tiket {ticket.ticket_code} tidak mengalami perubahan.",
            "info",
        )

    return redirect(url_for("admin.verify_ticket_form", ticket_id=ticket.id))


@admin_bp.route("/tiket/<int:ticket_id>/penugasan", methods=["POST"])
@role_required("admin_sarpras")
def assign_technician(ticket_id: int):
    """Proses penugasan teknisi penanggung jawab pada tiket (FR-05)."""
    ticket = get_ticket_by_id(ticket_id)
    if ticket is None:
        abort(404)

    technician_raw = (request.form.get("technician_id") or "").strip()
    note = (request.form.get("note") or "").strip() or None

    if not technician_raw.isdigit():
        flash("Teknisi penanggung jawab wajib dipilih.", "danger")
        return redirect(url_for("admin.verify_ticket_form", ticket_id=ticket.id))

    try:
        ticket, assignment_changed = assign_technician_to_ticket(
            ticket=ticket,
            technician_id=int(technician_raw),
            actor_user=g.current_user,
            note=note,
        )
    except (TechnicianValidationError, InvalidTicketStatusError) as exc:
        flash(str(exc), "danger")
        return redirect(url_for("admin.verify_ticket_form", ticket_id=ticket.id))
    except Exception:
        current_app.logger.exception(
            "Gagal memproses penugasan teknisi untuk tiket %s", ticket.id
        )
        flash("Terjadi kesalahan sistem saat memproses penugasan teknisi.", "danger")
        return redirect(url_for("admin.verify_ticket_form", ticket_id=ticket.id))

    if assignment_changed:
        tech_name = (
            ticket.assigned_technician.full_name
            if ticket.assigned_technician
            else "Teknisi"
        )
        flash(
            f"Tiket {ticket.ticket_code} berhasil ditugaskan kepada {tech_name}.",
            "success",
        )
    else:
        flash(
            f"Penugasan teknisi untuk tiket {ticket.ticket_code} tidak mengalami perubahan.",
            "info",
        )

    return redirect(url_for("admin.verify_ticket_form", ticket_id=ticket.id))


@admin_bp.route("/tiket/<int:ticket_id>/foto", methods=["GET"])
@role_required("admin_sarpras")
def ticket_photo(ticket_id: int):
    """
    Sajikan foto bukti tiket secara aman untuk staf Sarpras yang berwenang.

    Keamanan:
    - Hanya dapat diakses oleh role staf terotorisasi.
    - Direktori filesystem tidak diekspos langsung ke publik.
    - Validasi path traversal & symlink containment via serve_ticket_photo.
    """
    ticket = db.session.get(Ticket, ticket_id)
    return serve_ticket_photo(ticket)


@admin_bp.route("/audit-log", methods=["GET"])
@role_required("admin_sarpras")
def audit_log_list():
    """Tampilkan riwayat log audit operasional sarpras secara terpusat (FR-09)."""
    raw_params = {
        "action": request.args.get("action"),
        "ticket_code": request.args.get("ticket_code"),
        "page": request.args.get("page"),
        "per_page": request.args.get("per_page"),
    }

    form_filters = {
        k: (v.strip() if v is not None else "")
        for k, v in raw_params.items()
    }

    # 1. Validasi parameter filter terlebih dahulu SEBELUM menyentuh basis data
    validated_params, errors = parse_and_validate_audit_filter_params(raw_params)

    # 2. Jika terdapat error validasi: langsung render error, TANPA query database fitur audit
    # categories dilewatkan sebagai dict kosong ({}) sehingga template merender tanpa akses DB
    if errors:
        for err_msg in errors.values():
            flash(err_msg, "danger")

        return render_template(
            "admin/audit_log.html",
            pagination=None,
            logs=[],
            active_filters=form_filters,
            categories={},
            valid_actions=VALID_AUDIT_ACTIONS,
        )

    # 3. Panggil query basis data HANYA setelah seluruh validasi filter berhasil
    all_categories = get_all_categories_map()
    pagination = get_audit_logs_paginated(
        page=validated_params["page"],
        per_page=validated_params["per_page"],
        action=validated_params["action"],
        ticket_code=validated_params["ticket_code"],
    )

    active_filters = {
        "action": validated_params["action"] or "all",
        "ticket_code": form_filters["ticket_code"],
        "per_page": validated_params["per_page"],
    }

    return render_template(
        "admin/audit_log.html",
        pagination=pagination,
        logs=pagination.items if pagination else [],
        active_filters=active_filters,
        categories=all_categories,
        valid_actions=VALID_AUDIT_ACTIONS,
    )

