"""Pengujian VQ-08: touch target tombol hamburger navbar minimal 44x44px."""
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


def _rule_body(css, selector):
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
    assert match is not None, f"rule {selector} tidak ditemukan"
    return match.group(1)


def test_toggler_vertical_padding_meets_touch_target(css):
    body = _rule_body(css, ".kf-navbar .navbar-toggler")

    match = re.search(r"padding:\s*([0-9.]+)rem", body)
    assert match is not None

    # Icon 1.5em @ 1.25rem = 30px, border 2px, padding atas+bawah.
    vertical_padding_px = float(match.group(1)) * 2 * 16
    total_height = 30 + vertical_padding_px + 2
    assert total_height >= 44, f"tinggi toggler {total_height}px < 44px"


def test_toggler_icon_remains_present(client):
    html = client.get("/lapor").get_data(as_text=True)

    assert 'class="navbar-toggler"' in html
    assert 'class="navbar-toggler-icon"' in html
