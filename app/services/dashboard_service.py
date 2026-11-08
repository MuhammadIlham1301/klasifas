"""
Layanan pengolahan data agregat dashboard manajerial (FR-07).
Menyediakan kalkulasi metrik, distribusi kategori, tren waktu, dan lokasi
secara murni read-only dengan proteksi privasi ketat (Zero PII).
Mendukung penyaringan konsisten (periode, kategori, lokasi).
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, or_, select

from app.extensions import db
from app.models.category import Category
from app.models.ticket import Ticket

BUILDING_NAME_DEFAULT = "Gedung FTII"
OFFICIAL_FLOORS = (1, 2, 3, 4)
OFFICIAL_STATUSES = ("Baru", "Terverifikasi", "Diproses", "Selesai")


class DashboardFilterError(ValueError):
    """Kesalahan validasi parameter penyaringan data dashboard."""


def parse_and_validate_dashboard_filters(
    raw_params: dict[str, Any] | None, session=None
) -> dict[str, Any]:
    """
    Validasi dan sanitasi parameter query filter dashboard.
    Menerima parameter:
    - days: int (1..365), default 30 jika None atau string kosong.
    - category: str (K1..K7) atau None jika tidak disertakan.
    - floor: int (1..4) atau None jika tidak disertakan.

    Raises:
        DashboardFilterError: jika parameter tidak valid.
    """
    params = raw_params or {}
    s = session or db.session

    # 1. Validasi days
    raw_days = params.get("days")
    if raw_days is None or str(raw_days).strip() == "":
        clean_days = 30
    else:
        try:
            clean_days = int(str(raw_days).strip())
        except (ValueError, TypeError):
            raise DashboardFilterError(
                "Parameter 'days' harus berupa bilangan bulat antara 1 dan 365."
            )
        if clean_days < 1 or clean_days > 365:
            raise DashboardFilterError(
                "Parameter 'days' harus berada dalam rentang 1 hingga 365 hari."
            )

    # 2. Validasi category
    raw_category = params.get("category")
    clean_cat_code = None
    clean_cat_id = None
    if raw_category is not None and str(raw_category).strip() != "":
        clean_cat_code = str(raw_category).strip().upper()
        cat_obj = s.scalar(select(Category).where(Category.code == clean_cat_code))
        if cat_obj is None:
            raise DashboardFilterError(
                f"Parameter 'category' tidak valid: '{clean_cat_code}'. Pilih antara K1 sampai K7."
            )
        clean_cat_id = cat_obj.id

    # 3. Validasi floor
    raw_floor = params.get("floor")
    clean_floor = None
    if raw_floor is not None and str(raw_floor).strip() != "":
        try:
            clean_floor = int(str(raw_floor).strip())
        except (ValueError, TypeError):
            raise DashboardFilterError(
                "Parameter 'floor' harus berupa bilangan bulat antara 1 dan 4."
            )
        if clean_floor not in OFFICIAL_FLOORS:
            raise DashboardFilterError(
                f"Parameter 'floor' tidak valid: {clean_floor}. Lantai harus antara 1 dan 4."
            )

    return {
        "days": clean_days,
        "category_code": clean_cat_code,
        "category_id": clean_cat_id,
        "floor": clean_floor,
    }


def get_dashboard_summary_kpi(
    session=None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    category_id: int | None = None,
    floor_number: int | None = None,
) -> dict[str, Any]:
    """
    Menghitung metrik ringkasan eksekutif dashboard:
    - total_tickets: Total seluruh keluhan terdaftar (COUNT(Ticket.id)).
    - status_counts: Jumlah tiket untuk masing-masing dari 4 status resmi KlasiFas.
    - active_tickets: Tiket yang sedang berjalan (Baru + Terverifikasi + Diproses).
    - completion_rate: Persentase tiket selesai terhadap total tiket (dibulatkan 1 desimal).
      Jika total tiket = 0, mengembalikan 0.0 secara eksplisit tanpa ZeroDivisionError.
    Dapat menerima filter opsional: start_date, end_date, category_id, floor_number.
    """
    s = session or db.session

    status_counts = {st: 0 for st in OFFICIAL_STATUSES}

    conditions = []
    if start_date is not None:
        conditions.append(Ticket.created_at >= start_date)
    if end_date is not None:
        conditions.append(Ticket.created_at <= end_date)
    if category_id is not None:
        conditions.append(Ticket.official_category_id == category_id)
    if floor_number is not None:
        conditions.append(Ticket.floor_number == floor_number)

    stmt = select(Ticket.status, func.count(Ticket.id))
    if conditions:
        stmt = stmt.where(*conditions)
    stmt = stmt.group_by(Ticket.status)

    for st_name, count_val in s.execute(stmt).all():
        if st_name in status_counts:
            status_counts[st_name] = count_val

    total_tickets = sum(status_counts.values())
    selesai_count = status_counts["Selesai"]
    active_tickets = (
        status_counts["Baru"]
        + status_counts["Terverifikasi"]
        + status_counts["Diproses"]
    )

    if total_tickets == 0:
        completion_rate = 0.0
    else:
        completion_rate = round((selesai_count / total_tickets) * 100, 1)

    return {
        "total_tickets": total_tickets,
        "status_counts": status_counts,
        "active_tickets": active_tickets,
        "completion_rate": completion_rate,
    }


def get_category_distribution(
    session=None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    floor_number: int | None = None,
    category_id: int | None = None,
) -> dict[str, Any]:
    """
    Menghitung sebaran keluhan untuk 7 kategori fasilitas resmi (K1–K7):
    - Seluruh 7 kategori resmi (K1 s.d. K7) selalu dicantumkan terurut meskipun
      memiliki 0 tiket.
    - Murni mengacu pada official_category_id (kategori resmi hasil verifikasi).
    - Tiket berstatus 'Baru' yang belum diverifikasi (official_category_id IS NULL)
      tidak dispekulasikan ke K1–K7, melainkan dicatat pada unverified_count.
    - Persentase dihitung terhadap total_verified (tiket yang sudah diverifikasi).
    Dapat menerima filter opsional: start_date, end_date, floor_number, category_id.
    """
    s = session or db.session

    # 1. Ambil seluruh 7 master kategori resmi terurut berdasarkan kode K1..K7
    cats_stmt = (
        select(Category)
        .order_by(Category.code.asc())
    )
    all_categories = s.execute(cats_stmt).scalars().all()

    # 2. Filter kondisi untuk tiket
    base_conditions = []
    if start_date is not None:
        base_conditions.append(Ticket.created_at >= start_date)
    if end_date is not None:
        base_conditions.append(Ticket.created_at <= end_date)
    if floor_number is not None:
        base_conditions.append(Ticket.floor_number == floor_number)

    # Kondisi terverifikasi
    verified_conditions = list(base_conditions)
    verified_conditions.append(Ticket.official_category_id.is_not(None))
    if category_id is not None:
        verified_conditions.append(Ticket.official_category_id == category_id)

    counts_stmt = (
        select(Ticket.official_category_id, func.count(Ticket.id))
        .where(*verified_conditions)
        .group_by(Ticket.official_category_id)
    )
    counts_map = dict(s.execute(counts_stmt).all())

    # 3. Hitung tiket yang belum diverifikasi (hanya jika category_id tidak difilter)
    if category_id is not None:
        unverified_count = 0
    else:
        unverified_conditions = list(base_conditions)
        unverified_conditions.append(Ticket.official_category_id.is_(None))
        unverified_stmt = (
            select(func.count(Ticket.id))
            .where(*unverified_conditions)
        )
        unverified_count = s.execute(unverified_stmt).scalar() or 0

    # 4. Susun daftar 7 kategori terurut K1..K7
    total_verified = sum(counts_map.values())
    category_list = []
    for cat in all_categories:
        c = counts_map.get(cat.id, 0)
        pct = round((c / total_verified) * 100, 1) if total_verified > 0 else 0.0
        category_list.append({
            "code": cat.code,
            "name": cat.name,
            "count": c,
            "percentage": pct,
        })

    return {
        "categories": category_list,
        "total_verified": total_verified,
        "unverified_count": unverified_count,
    }


def _format_date(val: Any) -> str:
    """Helper untuk memformat objek tanggal atau string ke ISO-8601 (YYYY-MM-DD)."""
    if hasattr(val, "strftime"):
        return val.strftime("%Y-%m-%d")
    return str(val)[:10]


def get_ticket_trends(
    days: int = 30,
    end_date: datetime | None = None,
    session=None,
    category_id: int | None = None,
    floor_number: int | None = None,
) -> list[dict[str, Any]]:
    """
    Menghitung data tren temporal keluhan berdasarkan waktu pembuatan tiket (Ticket.created_at):
    - Rentang default 30 hari terakhir.
    - Menormalkan start_date ke 00:00:00 UTC dan end_date ke 23:59:59.999999 UTC.
    - Menggunakan filter range inklusif pada Ticket.created_at (memanfaatkan ix_tickets_created_at).
    - Menghasilkan deret kronologis strictly ascending per tanggal UTC (YYYY-MM-DD).
    - Melakukan zero-filling: tanggal tanpa tiket tetap memiliki entri dengan count 0.
    Dapat menerima filter opsional: category_id, floor_number.
    """
    s = session or db.session

    if days < 1:
        days = 30

    if end_date is None:
        target_end = datetime.now(timezone.utc)
    else:
        target_end = end_date
        if target_end.tzinfo is None:
            target_end = target_end.replace(tzinfo=timezone.utc)

    # Batas inklusif UTC
    normalized_end = datetime(
        target_end.year,
        target_end.month,
        target_end.day,
        23,
        59,
        59,
        999999,
        tzinfo=timezone.utc,
    )
    raw_start = normalized_end - timedelta(days=days - 1)
    normalized_start = datetime(
        raw_start.year,
        raw_start.month,
        raw_start.day,
        0,
        0,
        0,
        0,
        tzinfo=timezone.utc,
    )

    # 1. Siapkan zero-filled map untuk seluruh tanggal dalam rentang
    date_counts: dict[str, int] = {}
    curr_date = normalized_start.date()
    end_date_obj = normalized_end.date()
    while curr_date <= end_date_obj:
        date_counts[curr_date.strftime("%Y-%m-%d")] = 0
        curr_date += timedelta(days=1)

    # 2. Query agregasi per tanggal dalam rentang UTC
    bind = s.get_bind()
    if bind is not None and bind.dialect.name == "postgresql":
        date_col = func.date(func.timezone("UTC", Ticket.created_at))
    else:
        date_col = func.date(Ticket.created_at)

    conditions = [
        Ticket.created_at >= normalized_start,
        Ticket.created_at <= normalized_end,
    ]
    if category_id is not None:
        conditions.append(Ticket.official_category_id == category_id)
    if floor_number is not None:
        conditions.append(Ticket.floor_number == floor_number)

    stmt = (
        select(date_col, func.count(Ticket.id))
        .where(*conditions)
        .group_by(date_col)
    )

    for raw_dt, count_val in s.execute(stmt).all():
        dt_key = _format_date(raw_dt)
        if dt_key in date_counts:
            date_counts[dt_key] = count_val

    # 3. Kembalikan list terurut kronologis menaik
    return [
        {"date": d_str, "count": date_counts[d_str]}
        for d_str in sorted(date_counts.keys())
    ]


def get_location_distribution(
    session=None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    category_id: int | None = None,
    floor_number: int | None = None,
) -> dict[str, Any]:
    """
    Menghitung sebaran fisik keluhan di Gedung FTII:
    - floors: Selalu mencantumkan 4 lantai resmi (1, 2, 3, 4) dengan count 0 jika kosong.
    - other_floors_count: Menampung tiket dengan lantai di luar 1–4 secara defensif.
    - top_rooms: Maksimal 5 ruangan teratas dengan keluhan terbanyak, terurut descending.
      Hanya mencakup ruangan valid (non-null dan non-empty). Whitespace dinormalisasi (.strip()).
    - unspecified_room_count: Menampung jumlah tiket dengan room_name bernilai NULL atau
      hanya spasi kosong.
    Dapat menerima filter opsional: start_date, end_date, category_id, floor_number.
    """
    s = session or db.session

    conditions = []
    if start_date is not None:
        conditions.append(Ticket.created_at >= start_date)
    if end_date is not None:
        conditions.append(Ticket.created_at <= end_date)
    if category_id is not None:
        conditions.append(Ticket.official_category_id == category_id)
    if floor_number is not None:
        conditions.append(Ticket.floor_number == floor_number)

    # 1. Agregasi per lantai
    floor_counts = {fl: 0 for fl in OFFICIAL_FLOORS}
    other_floors_count = 0

    floor_stmt = select(Ticket.floor_number, func.count(Ticket.id))
    if conditions:
        floor_stmt = floor_stmt.where(*conditions)
    floor_stmt = floor_stmt.group_by(Ticket.floor_number)

    for fl_num, count_val in s.execute(floor_stmt).all():
        if fl_num in floor_counts:
            floor_counts[fl_num] = count_val
        else:
            other_floors_count += count_val

    floors_list = [
        {"floor": fl, "count": floor_counts[fl]}
        for fl in sorted(floor_counts.keys())
    ]

    # 2. Tiket tanpa ruangan spesifik (NULL atau whitespace saja)
    unspecified_conditions = list(conditions)
    unspecified_conditions.append(
        or_(
            Ticket.room_name.is_(None),
            func.trim(Ticket.room_name) == "",
        )
    )
    unspecified_stmt = (
        select(func.count(Ticket.id))
        .where(*unspecified_conditions)
    )
    unspecified_room_count = s.execute(unspecified_stmt).scalar() or 0

    # 3. Top rooms valid (ternormalisasi trim)
    cleaned_room = func.trim(Ticket.room_name).label("cleaned_room")
    room_conditions = list(conditions)
    room_conditions.extend([
        Ticket.room_name.is_not(None),
        func.trim(Ticket.room_name) != "",
    ])

    room_stmt = (
        select(cleaned_room, func.count(Ticket.id).label("room_count"))
        .where(*room_conditions)
        .group_by(cleaned_room)
        .order_by(func.count(Ticket.id).desc(), cleaned_room.asc())
        .limit(5)
    )
    top_rooms = [
        {"room_name": r_name, "count": r_count}
        for r_name, r_count in s.execute(room_stmt).all()
    ]

    return {
        "building_name": BUILDING_NAME_DEFAULT,
        "floors": floors_list,
        "top_rooms": top_rooms,
        "unspecified_room_count": unspecified_room_count,
        "other_floors_count": other_floors_count,
    }


def get_dashboard_chart_payload(
    clean_filters: dict[str, Any] | None = None, session=None
) -> dict[str, Any]:
    """
    Orkestrator data visualisasi untuk Chart.js (FR-07).
    Mengonsolidasikan seluruh komponen agregasi dengan parameter filter yang seragam.
    Menghasilkan payload JSON terstruktur yang siap dikonsumsi langsung oleh Chart.js.
    """
    s = session or db.session
    filters = clean_filters or {}

    days = filters.get("days", 30)
    category_code = filters.get("category_code")
    category_id = filters.get("category_id")
    floor = filters.get("floor")

    # Hitung batas waktu UTC yang seragam untuk seluruh komponen grafik
    target_end = datetime.now(timezone.utc)
    normalized_end = datetime(
        target_end.year,
        target_end.month,
        target_end.day,
        23,
        59,
        59,
        999999,
        tzinfo=timezone.utc,
    )
    raw_start = normalized_end - timedelta(days=days - 1)
    normalized_start = datetime(
        raw_start.year,
        raw_start.month,
        raw_start.day,
        0,
        0,
        0,
        0,
        tzinfo=timezone.utc,
    )

    # Panggil fungsi agregasi dengan batas tanggal & filter yang seragam
    kpi = get_dashboard_summary_kpi(
        session=s,
        start_date=normalized_start,
        end_date=normalized_end,
        category_id=category_id,
        floor_number=floor,
    )
    cat_dist = get_category_distribution(
        session=s,
        start_date=normalized_start,
        end_date=normalized_end,
        floor_number=floor,
        category_id=category_id,
    )
    trends = get_ticket_trends(
        days=days,
        end_date=normalized_end,
        session=s,
        category_id=category_id,
        floor_number=floor,
    )
    loc_dist = get_location_distribution(
        session=s,
        start_date=normalized_start,
        end_date=normalized_end,
        category_id=category_id,
        floor_number=floor,
    )

    # Format struktur standar Chart.js
    category_chart = {
        "labels": [c["code"] for c in cat_dist["categories"]],
        "category_names": [c["name"] for c in cat_dist["categories"]],
        "datasets": [
            {
                "label": "Jumlah Tiket",
                "data": [c["count"] for c in cat_dist["categories"]],
            }
        ],
        "percentages": [c["percentage"] for c in cat_dist["categories"]],
        "total_verified": cat_dist["total_verified"],
        "unverified_count": cat_dist["unverified_count"],
    }

    trend_chart = {
        "labels": [t["date"] for t in trends],
        "datasets": [
            {
                "label": "Tiket Masuk",
                "data": [t["count"] for t in trends],
            }
        ],
    }

    location_chart = {
        "labels": [f"Lantai {f['floor']}" for f in loc_dist["floors"]],
        "datasets": [
            {
                "label": "Jumlah Tiket",
                "data": [f["count"] for f in loc_dist["floors"]],
            }
        ],
        "top_rooms": loc_dist["top_rooms"],
        "unspecified_room_count": loc_dist["unspecified_room_count"],
        "other_floors_count": loc_dist["other_floors_count"],
    }

    return {
        "kpi": kpi,
        "category_chart": category_chart,
        "trend_chart": trend_chart,
        "location_chart": location_chart,
        "filters_applied": {
            "days": days,
            "category": category_code,
            "floor": floor,
        },
    }
