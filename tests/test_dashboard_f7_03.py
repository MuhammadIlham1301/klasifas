"""
Pengujian Terarah TSK-F7-03:
Implementasi Tampilan Dashboard dan Visualisasi Grafik Chart.js (FR-07).

Mencakup seluruh 11 skenario pengujian:
1. test_dashboard_view_unauthenticated_redirects_to_login: Request tanpa login dialihkan (302) ke login.
2. test_dashboard_view_technician_role_forbidden: Peran 'teknisi' ditolak dengan 403 Forbidden.
3. test_dashboard_view_admin_sarpras_allowed: Peran 'admin_sarpras' diizinkan (200 OK) dengan konten dasbor lengkap.
4. test_dashboard_view_pimpinan_allowed: Peran 'pimpinan' diizinkan (200 OK) dengan penanda manajerial read-only.
5. test_dashboard_html_contains_chart_canvas_elements: Tiga elemen canvas HTML5 (trendChart, categoryChart, locationChart) ada di DOM.
6. test_dashboard_html_contains_kpi_card_containers: Kontainer elemen metrik 4 KPI dan rincian 4 status resmi lengkap.
7. test_dashboard_html_contains_complete_filter_controls: Kontrol filter (days, category K1–K7, floor 1–4, submit, reset) lengkap.
8. test_dashboard_html_strict_zero_pii_rendered: Verifikasi ketat ketiadaan data pribadi pelapor pada HTML yang dirender.
9. test_dashboard_navbar_link_conditional_rendering: Tautan 'Dasbor' hanya muncul untuk admin_sarpras dan pimpinan.
10. test_dashboard_html_contains_loading_and_error_state_elements: Elemen loading spinner, alert empty, error alert, dan retry button ada di DOM.
11. test_dashboard_view_read_only_integrity: Operasi view murni read-only tanpa mutasi tiket atau penambahan AuditLog.
"""
from datetime import datetime, timezone
import hashlib
import secrets

import pytest
from sqlalchemy import delete, func, select
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.category import Category
from app.models.ticket import Ticket
from app.models.user import User
from app.utils.ticket_identity import generate_ticket_code

PASSWORD = "Valid-Password-123!"
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

            # Pembersihan data test
            with db.engine.begin() as cleanup_connection:
                if baseline_ticket_ids:
                    cleanup_connection.execute(
                        delete(AuditLog).where(
                            AuditLog.ticket_id.notin_(baseline_ticket_ids)
                        )
                    )
                    cleanup_connection.execute(
                        delete(Ticket).where(
                            Ticket.id.notin_(baseline_ticket_ids)
                        )
                    )
                else:
                    cleanup_connection.execute(delete(AuditLog))
                    cleanup_connection.execute(delete(Ticket))

                if baseline_user_ids:
                    cleanup_connection.execute(
                        delete(User).where(
                            User.id.notin_(baseline_user_ids)
                        )
                    )
                else:
                    cleanup_connection.execute(delete(User))

            db.engine.dispose()


@pytest.fixture()
def client(app):
    return app.test_client()


def _create_user(username: str, role: str) -> User:
    unique_uname = f"{username}_{secrets.token_hex(4)}"
    user = User(
        username=unique_uname,
        full_name=f"Pengguna {username}",
        password_hash=PASSWORD_HASH,
        role=role,
        is_active=True,
    )
    db.session.add(user)
    db.session.flush()
    return user


def _login_as(client, role: str, username: str | None = None) -> User:
    uname = username or f"{role}_user"
    user = _create_user(uname, role)
    db.session.commit()
    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["role"] = user.role
        sess.permanent = True
    return user


def _create_test_ticket(
    *,
    status: str = "Baru",
    official_category_id: int | None = None,
    floor_number: int = 2,
    room_name: str | None = "Lab 2.1",
    building_name: str = "Gedung FTII",
    reporter_name: str | None = "Ahmad Pelapor",
    reporter_contact: str | None = "081234567890",
    description: str = "Deskripsi keluhan uji coba fasilitas.",
) -> Ticket:
    """Helper membuat entri tiket untuk pengujian halaman visualisasi dashboard."""
    ticket_code = generate_ticket_code()
    token_seed = secrets.token_hex(16)
    token_hash = hashlib.sha256(token_seed.encode("ascii")).hexdigest()

    ticket = Ticket(
        ticket_code=ticket_code,
        access_token_hash=token_hash,
        description=description,
        building_name=building_name,
        floor_number=floor_number,
        room_name=room_name,
        location_detail="Detail lokasi uji",
        status=status,
        official_category_id=official_category_id,
        reporter_name=reporter_name,
        reporter_contact=reporter_contact,
    )
    db.session.add(ticket)
    db.session.flush()
    return ticket


# ==============================================================================
# Skenario 1 s.d. 11 Pengujian TSK-F7-03
# ==============================================================================


def test_dashboard_view_unauthenticated_redirects_to_login(client):
    """Skenario 1: Request tanpa sesi dialihkan (302) ke halaman login."""
    # Test path tanpa trailing slash dan dengan trailing slash
    for path in ["/dashboard", "/dashboard/"]:
        resp = client.get(path)
        assert resp.status_code == 302
        assert "/auth/login" in resp.headers["Location"]


def test_dashboard_view_technician_role_forbidden(client):
    """Skenario 2: Peran 'teknisi' ditolak mengakses dasbor dengan HTTP 403 Forbidden."""
    _login_as(client, "teknisi")
    resp = client.get("/dashboard")
    assert resp.status_code == 403


def test_dashboard_view_admin_sarpras_allowed(client):
    """Skenario 3: Peran 'admin_sarpras' diizinkan mengakses dasbor (200 OK) dengan konten lengkap."""
    _login_as(client, "admin_sarpras")
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Dasbor Pemantauan Manajerial" in html
    assert "Peran: Admin Sarpras" in html
    assert "dashboard-filter-form" in html


def test_dashboard_view_pimpinan_allowed(client):
    """Skenario 4: Peran 'pimpinan' diizinkan mengakses dasbor (200 OK) dengan penanda read-only."""
    _login_as(client, "pimpinan")
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Dasbor Pemantauan Manajerial" in html
    assert "Peran: Pimpinan (Read-Only)" in html


def test_dashboard_html_contains_chart_canvas_elements(client):
    """Skenario 5: Tiga elemen canvas HTML5 (trendChart, categoryChart, locationChart) ada di DOM."""
    _login_as(client, "admin_sarpras")
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    assert '<canvas id="trendChart">' in html or 'id="trendChart"' in html
    assert '<canvas id="categoryChart">' in html or 'id="categoryChart"' in html
    assert '<canvas id="locationChart">' in html or 'id="locationChart"' in html


def test_dashboard_html_contains_kpi_card_containers(client):
    """Skenario 6: Kontainer elemen metrik 4 KPI dan rincian 4 status resmi lengkap."""
    _login_as(client, "admin_sarpras")
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # 4 KPI Utama
    assert 'id="kpi-total-tickets"' in html
    assert 'id="kpi-active-tickets"' in html
    assert 'id="kpi-completed-tickets"' in html
    assert 'id="kpi-completion-rate"' in html

    # Rincian 4 Status Resmi
    assert 'id="kpi-count-baru"' in html
    assert 'id="kpi-count-terverifikasi"' in html
    assert 'id="kpi-count-diproses"' in html
    assert 'id="kpi-count-selesai"' in html


def test_dashboard_html_contains_complete_filter_controls(client):
    """Skenario 7: Kontrol filter (days, category K1–K7, floor 1–4, submit, reset) lengkap."""
    _login_as(client, "admin_sarpras")
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # Kontrol Form
    assert 'id="filter_days"' in html
    assert 'id="filter_category"' in html
    assert 'id="filter_floor"' in html
    assert 'id="btn-apply-filter"' in html
    assert 'id="btn-reset-filter"' in html

    # Opsi Kategori K1 s.d. K7 harus terdaftar di dropdown
    for code in ["K1", "K2", "K3", "K4", "K5", "K6", "K7"]:
        assert f'value="{code}"' in html

    # Opsi Lantai 1 s.d. 4 harus terdaftar
    for fl in [1, 2, 3, 4]:
        assert f'value="{fl}"' in html


def test_dashboard_html_strict_zero_pii_rendered(client):
    """Skenario 8: Verifikasi ketat ketiadaan data pribadi pelapor pada HTML yang dirender."""
    db.session.execute(delete(Ticket))
    db.session.commit()

    cat = db.session.scalar(select(Category).where(Category.code == "K1"))
    secret_ticket = _create_test_ticket(
        status="Terverifikasi",
        official_category_id=cat.id,
        reporter_name="Rahasia Budi PDP Satria",
        reporter_contact="081999777123",
        description="Keluhan rahasia nomor telepon dan nama pribadi",
    )
    db.session.commit()

    _login_as(client, "admin_sarpras")
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # Pastikan data pribadi pelapor sama sekali tidak dirender pada antarmuka dasbor
    assert "Rahasia Budi PDP Satria" not in html
    assert "081999777123" not in html
    assert "Keluhan rahasia nomor telepon dan nama pribadi" not in html
    assert secret_ticket.access_token_hash not in html


def test_dashboard_navbar_link_conditional_rendering(client):
    """Skenario 9: Tautan 'Dasbor' hanya muncul di navbar untuk admin_sarpras dan pimpinan."""
    # 1. Admin Sarpras -> Harus melihat tautan Dasbor
    _login_as(client, "admin_sarpras")
    resp = client.get("/admin/tiket")
    assert resp.status_code == 200
    html_admin = resp.get_data(as_text=True)
    assert ('href="/dashboard"' in html_admin or 'href="/dashboard/"' in html_admin)
    assert ">Dasbor<" in html_admin

    # 2. Pimpinan -> Harus melihat tautan Dasbor
    _login_as(client, "pimpinan")
    resp_pimpinan = client.get("/dashboard")
    assert resp_pimpinan.status_code == 200
    html_pimpinan = resp_pimpinan.get_data(as_text=True)
    assert ('href="/dashboard"' in html_pimpinan or 'href="/dashboard/"' in html_pimpinan)
    assert ">Dasbor<" in html_pimpinan

    # 3. Teknisi -> TIDAK boleh melihat tautan Dasbor
    _login_as(client, "teknisi")
    resp_tech = client.get("/teknisi/tiket")
    assert resp_tech.status_code == 200
    html_tech = resp_tech.get_data(as_text=True)
    assert ">Dasbor<" not in html_tech
    assert 'href="/dashboard"' not in html_tech
    assert 'href="/dashboard/"' not in html_tech

    # 4. Pengguna Publik (tanpa login) -> TIDAK boleh melihat tautan Dasbor
    anon_client = client.application.test_client()
    resp_anon = anon_client.get("/lapor")
    assert resp_anon.status_code == 200
    html_anon = resp_anon.get_data(as_text=True)
    assert ">Dasbor<" not in html_anon
    assert 'href="/dashboard"' not in html_anon
    assert 'href="/dashboard/"' not in html_anon


def test_dashboard_html_contains_loading_and_error_state_elements(client):
    """Skenario 10: Elemen loading spinner, alert empty, error alert, dan retry button ada di DOM."""
    _login_as(client, "admin_sarpras")
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    assert 'id="dashboard-loading-spinner"' in html
    assert 'id="dashboard-empty-alert"' in html
    assert 'id="dashboard-error-alert"' in html
    assert 'id="btn-retry-load"' in html

    # Pastikan file skrip terdaftar
    assert "vendor/chartjs/chart.umd.min.js" in html
    assert "js/dashboard.js" in html


def test_dashboard_view_read_only_integrity(client):
    """Skenario 11: Operasi view murni read-only tanpa mutasi tiket atau penambahan AuditLog."""
    db.session.execute(delete(Ticket))
    db.session.commit()

    cat = db.session.scalar(select(Category).where(Category.code == "K1"))
    _create_test_ticket(status="Diproses", official_category_id=cat.id)
    db.session.commit()

    ticket_count_before = db.session.scalar(select(func.count(Ticket.id)))
    audit_count_before = db.session.scalar(select(func.count(AuditLog.id)))

    _login_as(client, "admin_sarpras")

    # Buka halaman dasbor beberapa kali
    for _ in range(3):
        resp = client.get("/dashboard")
        assert resp.status_code == 200

    ticket_count_after = db.session.scalar(select(func.count(Ticket.id)))
    audit_count_after = db.session.scalar(select(func.count(AuditLog.id)))

    assert ticket_count_after == ticket_count_before
    assert audit_count_after == audit_count_before
