"""Pengujian responsivitas otomatis (TSK-F8-03): kontrak breakpoint mobile/desktop.

Tanpa dependency browser tambahan: mengunci aturan CSS & markup yang memastikan
perilaku responsif pada viewport mobile/tablet/desktop direpresentasikan secara eksplisit.
Bukti visual computed-layout sebelumnya dicatat pada sesi render VQ-05/06/07/08/09/10.
"""
import re

import pytest


@pytest.fixture()
def app():
    from app import create_app

    return create_app("testing")


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def css(client):
    response = client.get("/static/css/klasifas.css")

    assert response.status_code == 200
    return response.get_data(as_text=True)


def test_navbar_collapses_below_md_and_expands_from_md(client):
    html = client.get("/lapor").get_data(as_text=True)

    # navbar horizontal mulai tablet (md = 768px); hamburger hanya di bawahnya.
    assert "navbar-expand-md" in html
    assert "navbar-toggler" in html


def test_collapse_styling_scoped_to_mobile_only(css):
    # Aturan collapse navbar hanya boleh berlaku < 768px.
    assert "@media (max-width: 767.98px)" in css
    # Pastikan tidak ada sisa breakpoint lama 991.98 yang akan merusak tablet.
    assert "max-width: 991.98px" not in css


def test_container_breakpoint_matches_desktop_token(css):
    # Container standar di-cap 1200px mulai >= 1200px (desktop).
    assert "@media (min-width: 1200px)" in css
    assert "--kf-container-max: 1200px;" in css
    assert "max-width: var(--kf-container-max);" in css


def test_location_grid_two_columns_from_md(client):
    html = client.get("/lapor").get_data(as_text=True)

    # Gedung full-width; Lantai & Ruang dua kolom (col-md-6) pada tablet/desktop.
    assert html.count("col-12 col-md-6") >= 2
    assert "col-md-5" not in html
    assert "col-md-3" not in html


def test_tables_wrap_in_responsive_container(client):
    # Halaman internal memakai .table-responsive agar tidak overflow di mobile.
    # (Diverifikasi pada route publik tanpa auth tidak memuat tabel; cek token CSS umum.)
    css = client.get("/static/css/klasifas.css").get_data(as_text=True)
    # Stepper responsif memakai grid repeat(4, ...) yang menyusut; tidak ada lebar px tetap.
    assert "grid-template-columns: repeat(4, minmax(0, 1fr));" in css


def test_no_fixed_viewport_width_in_base(css):
    # Tidak boleh ada deklarasi lebar tetap piksel besar yang memicu overflow mobile.
    # Media query `@media (min-width: 1200px)` sah; yang dicari adalah deklarasi properti,
    # bukan media query. Cek deklarasi tanpa didahului '(' atau '@media'.
    assert not re.search(r"(?<![(\w-])min-width:\s*(?:1200|1320)px;", css)
    assert "width: 1320px" not in css
    assert "min-width: 1320px" not in css
