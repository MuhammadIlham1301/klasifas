"""Rute pelaporan keluhan publik (FR-01)."""
from flask import (
    Blueprint,
    current_app,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.services.ticket_photo import (
    PhotoStorageError,
    PhotoValidationError,
    delete_photo,
    store_photo,
    validate_photo,
)
from app.services.ticket_report import (
    BUILDING_NAME,
    FLOOR_NUMBERS,
    ReportValidationError,
    TicketIdentityError,
    create_ticket_with_token,
    get_active_categories,
    validate_report_form,
)
from app.services.ticket_tracking import get_ticket_tracking_info
from app.utils.rate_limiter import get_client_ip, track_limiter

report_bp = Blueprint("report", __name__)


def _render_form(categories, errors=None, form=None, status=200):
    max_photo_size_bytes = current_app.config["MAX_PHOTO_SIZE_BYTES"]
    return (
        render_template(
            "report/form.html",
            categories=categories,
            errors=errors or {},
            form=form or {},
            building_name=BUILDING_NAME,
            floor_numbers=FLOOR_NUMBERS,
            max_photo_size_mb=max_photo_size_bytes // (1024 * 1024),
            max_photo_dimension=current_app.config["MAX_PHOTO_DIMENSION"],
        ),
        status,
    )


def _remove_stored_photo(stored_photo):
    if stored_photo is None:
        return

    try:
        delete_photo(
            stored_photo.filename,
            current_app.config["UPLOAD_FOLDER"],
        )
    except PhotoStorageError:
        current_app.logger.error(
            "Stored photo cleanup failed after ticket persistence failure."
        )


@report_bp.get("/")
def root():
    """Alihkan halaman root publik ke formulir pelaporan."""
    return redirect(url_for("report.report_form"))


@report_bp.route("/lapor", methods=["GET", "POST"])
def report_form():
    """Tampilkan formulir pelaporan dan simpan laporan yang valid."""
    categories = get_active_categories()

    if request.method == "POST":
        try:
            data = validate_report_form(request.form, categories)
        except ReportValidationError as exc:
            return _render_form(categories, exc.errors, request.form, 400)

        try:
            photo = validate_photo(
                request.files.get("photo"),
                max_size_bytes=current_app.config["MAX_PHOTO_SIZE_BYTES"],
                max_dimension=current_app.config["MAX_PHOTO_DIMENSION"],
                allowed_extensions=current_app.config[
                    "PHOTO_ALLOWED_EXTENSIONS"
                ],
                allowed_mime_types=current_app.config[
                    "PHOTO_ALLOWED_MIME_TYPES"
                ],
            )
        except PhotoValidationError as exc:
            return _render_form(
                categories,
                {"photo": str(exc)},
                request.form,
                400,
            )

        stored_photo = None
        try:
            if photo is not None:
                stored_photo = store_photo(
                    photo,
                    current_app.config["UPLOAD_FOLDER"],
                )

            ticket, access_token = create_ticket_with_token(
                data, stored_photo
            )
            db.session.commit()
        except PhotoStorageError:
            db.session.rollback()
            _remove_stored_photo(stored_photo)
            flash(
                "Laporan belum dapat dikirim. Silakan coba lagi.",
                "danger",
            )
            return _render_form(categories, form=request.form, status=500)
        except (SQLAlchemyError, TicketIdentityError):
            db.session.rollback()
            _remove_stored_photo(stored_photo)
            flash(
                "Laporan belum dapat dikirim. Silakan periksa kembali data Anda.",
                "danger",
            )
            return _render_form(categories, form=request.form, status=500)

        response = make_response(
            render_template(
                "report/success.html",
                ticket_code=ticket.ticket_code,
                access_token=access_token,
            )
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    return _render_form(categories)


@report_bp.get("/lapor/sukses")
def success():
    """Kembalikan pengunjung langsung ke formulir pelaporan."""
    return redirect(url_for("report.report_form"))


@report_bp.route("/lacak", methods=["GET", "POST"])
def track():
    """Endpoint pelacakan mandiri status tiket keluhan (FR-02)."""
    if request.method == "POST":
        # 1. Enforcement Rate Limiting (Pre-check):
        # Seluruh percobaan POST dihitung, termasuk input tidak valid, format salah,
        # token keliru, maupun tiket fiktif.
        client_ip = get_client_ip(request)
        is_allowed, retry_after = track_limiter.hit(client_ip)
        if not is_allowed:
            response = make_response(
                render_template(
                    "report/track.html",
                    error="Batas frekuensi pencarian tercapai. Silakan coba beberapa saat lagi.",
                    retry_after=retry_after,
                    ticket=None,
                    ticket_code=(request.form.get("ticket_code") or "").strip().upper(),
                ),
                429,
            )
            response.headers["Retry-After"] = str(retry_after)
            return response

        ticket_code = (request.form.get("ticket_code") or "").strip().upper()
        access_token = (request.form.get("access_token") or "").strip()

        # 2. Validasi kelengkapan input formulir
        if not ticket_code or not access_token:
            return (
                render_template(
                    "report/track.html",
                    error="Kode referensi tiket dan token akses wajib diisi.",
                    ticket_code=ticket_code,
                    ticket=None,
                ),
                400,
            )

        # 3. Verifikasi kredensial tiket & sanitasi data publik
        ticket_data = get_ticket_tracking_info(ticket_code, access_token)
        if ticket_data is None:
            # Respons generik anti-enumeration: status 404 tanpa membedakan
            # apakah kode tiket tidak ada atau token aksesnya yang salah.
            return (
                render_template(
                    "report/track.html",
                    error="Tiket tidak ditemukan atau kredensial pelacakan tidak valid.",
                    ticket_code=ticket_code,
                    ticket=None,
                ),
                404,
            )

        return render_template(
            "report/track.html",
            ticket=ticket_data,
            ticket_code=ticket_code,
            error=None,
        )

    # Permintaan GET: tampilkan form pencarian awal
    ticket_code = (request.args.get("ticket_code") or "").strip().upper()
    return render_template(
        "report/track.html",
        ticket=None,
        ticket_code=ticket_code,
        error=None,
    )

