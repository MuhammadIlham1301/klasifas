"""Pengujian VQ-06: container standar 1200px dan workspace wide 1440px."""
import re
from pathlib import Path

import pytest

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "app" / "templates"


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


def test_container_tokens_defined(css):
    assert "--kf-container-max: 1200px;" in css
    assert "--kf-container-wide-max: 1440px;" in css


def test_container_rules_use_tokens(css):
    assert ".kf-container {" in css
    assert "max-width: var(--kf-container-max);" in css
    assert ".kf-container--wide {" in css
    assert "max-width: var(--kf-container-wide-max);" in css
    assert "@media (min-width: 1200px)" in css


def test_base_applies_container_class_to_all_containers():
    base = (TEMPLATES_DIR / "base.html").read_text(encoding="utf-8")
    assert base.count('container {{ kf_container }}') == 3
    assert 'class="container {{ kf_container }}' in base
    assert "{% block container_class %}kf-container{% endblock %}" in base


def test_standard_page_uses_default_container(client):
    html = client.get("/lapor").get_data(as_text=True)

    assert "kf-container" in html
    assert "kf-container--wide" not in html


def test_technician_pages_override_to_wide():
    for name in ("queue.html", "detail.html"):
        source = (TEMPLATES_DIR / "technician" / name).read_text(encoding="utf-8")
        assert "{% block container_class %}kf-container kf-container--wide{% endblock %}" in source


def test_non_technician_pages_do_not_override_wide():
    for path in TEMPLATES_DIR.rglob("*.html"):
        if "technician" in path.parts or path.name == "base.html":
            continue
        if "kf-container--wide" in path.read_text(encoding="utf-8"):
            pytest.fail(f"halaman non-teknisi memakai container wide: {path}")
