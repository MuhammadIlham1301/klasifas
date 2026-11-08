"""
Rute Dasbor Pemantauan Manajerial dan Visualisasi (FR-07).
Menyediakan halaman dasbor manajerial dan endpoint data grafik JSON untuk Chart.js.
Hanya dapat diakses oleh peran manajerial yang berwenang: Admin Sarpras dan Pimpinan/Kaprodi.
"""
from flask import Blueprint, jsonify, make_response, render_template, request
from sqlalchemy import select

from app.extensions import db
from app.models.category import Category
from app.services.dashboard_service import (
    DashboardFilterError,
    get_dashboard_chart_payload,
    parse_and_validate_dashboard_filters,
)
from app.utils.decorators import role_required

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


def _no_store(response):
    """Cegah cache untuk data agregat terautentikasi."""
    response.headers["Cache-Control"] = "no-store"
    return response


@dashboard_bp.route("", methods=["GET"])
@dashboard_bp.route("/", methods=["GET"])
@role_required("admin_sarpras", "pimpinan")
def dashboard_view():
    """
    Menampilkan halaman Dasbor Pemantauan Manajerial dan Visualisasi (FR-07).
    
    Fitur & Keamanan:
    - Otorisasi: Dibatasi ketat hanya untuk peran 'admin_sarpras' dan 'pimpinan'.
    - Kontrol Filter: Menyediakan daftar 7 kategori resmi dan 4 lantai gedung FTII.
    - Template: Merender dashboard/index.html dengan Chart.js lokal.
    - Privasi: Strict Zero PII (tidak ada data identitas pribadi pelapor).
    - Read-Only: Operasi murni query basis data tanpa mutasi atau pencatatan AuditLog.
    """
    categories = db.session.scalars(
        select(Category).order_by(Category.code.asc())
    ).all()

    return _no_store(make_response(render_template(
        "dashboard/index.html",
        categories=categories,
        default_days=30,
        floors=[1, 2, 3, 4],
    )))


@dashboard_bp.route("/api/chart-data", methods=["GET"])
@role_required("admin_sarpras", "pimpinan")
def chart_data_api():
    """
    Endpoint JSON internal untuk menyediakan data visualisasi agregat Chart.js (FR-07).
    
    Fitur & Keamanan:
    - Otorisasi: Dibatasi ketat hanya untuk peran 'admin_sarpras' dan 'pimpinan'.
    - Input: Menerima parameter query opsional: days (1..365), category (K1..K7), floor (1..4).
    - Validasi: Parameter tidak valid ditolak dengan HTTP 400 Bad Request JSON.
    - Privasi: Strict Zero PII (tidak ada data identitas pelapor yang diproses atau dikirim).
    - Read-Only: Operasi murni query basis data tanpa mutasi atau pencatatan AuditLog.
    """
    raw_params = {
        "days": request.args.get("days"),
        "category": request.args.get("category"),
        "floor": request.args.get("floor"),
    }

    try:
        clean_filters = parse_and_validate_dashboard_filters(raw_params)
        payload = get_dashboard_chart_payload(clean_filters)
        return _no_store(make_response(jsonify(payload), 200))
    except DashboardFilterError as err:
        return _no_store(make_response(jsonify({
            "error": "Parameter filter tidak valid",
            "message": str(err),
        }), 400))

