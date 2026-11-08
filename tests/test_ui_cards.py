"""Pengujian VQ-04: style kartu dasar dan pembatasan accent."""
import re

import pytest

ACCENT_CLASSES = (
    ".kf-form-card",
    ".kf-sidebar-card",
    ".kf-receipt-card",
    ".kf-kpi",
)


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


def test_card_base_uses_tokens(css):
    body = _rule_body(css, ".card")

    assert "background-color: var(--kf-surface) !important;" in body
    assert "border: 1px solid var(--kf-border) !important;" in body
    assert "border-radius: var(--kf-card-radius) !important;" in body


def test_card_radius_token_is_12px(css):
    match = re.search(r"--kf-card-radius:\s*([0-9.]+)rem;", css)

    assert match is not None
    assert float(match.group(1)) * 16 == 12


def test_inner_surface_radius_token_stays_8px(css):
    match = re.search(r"--kf-radius-lg:\s*([0-9.]+)rem;", css)

    assert match is not None
    assert float(match.group(1)) * 16 == 8


def test_accent_is_3px_for_allowed_cards(css):
    assert "border-top: 3px solid var(--kf-secondary) !important;" in _rule_body(
        css, ".kf-form-card"
    )
    assert "border-top: 3px solid var(--kf-primary) !important;" in _rule_body(
        css, ".kf-sidebar-card"
    )
    assert "border-top: 3px solid var(--kf-border-strong) !important;" in _rule_body(
        css, ".kf-kpi"
    )

    receipt_rule = _rule_body(css, ".kf-receipt-card")
    assert "border-top-color: var(--kf-success) !important;" in receipt_rule


def test_no_4px_card_accent_remains(css):
    for selector in ACCENT_CLASSES:
        for match in re.finditer(re.escape(selector) + r"[^{]*\{([^}]*)\}", css):
            assert "4px" not in match.group(1), (
                f"accent 4px masih tersisa pada {selector}"
            )
