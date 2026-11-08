"""Pengujian VQ-10: favicon lokal tanpa CDN dan tanpa 404."""
import pytest


@pytest.fixture()
def app():
    from app import create_app

    return create_app("testing")


@pytest.fixture()
def client(app):
    return app.test_client()


def test_favicon_svg_is_served(client):
    response = client.get("/static/favicon.svg")

    assert response.status_code == 200
    assert response.mimetype == "image/svg+xml"
    body = response.get_data(as_text=True)
    assert "<svg" in body
    assert "#0c356a" in body
    assert "#ffc436" in body


def test_favicon_ico_redirects_to_svg(client):
    response = client.get("/favicon.ico")

    assert response.status_code == 308
    assert response.headers["Location"].endswith("/static/favicon.svg")


def test_base_html_links_local_favicon(client):
    html = client.get("/lapor").get_data(as_text=True)

    assert 'rel="icon"' in html
    assert 'type="image/svg+xml"' in html
    assert "/static/favicon.svg" in html
    assert "http://" not in html.split("favicon", 1)[1].split(">", 1)[0]
    assert "https://" not in html.split("favicon", 1)[1].split(">", 1)[0]


def test_favicon_not_referenced_via_cdn(client):
    for path in ("/lapor", "/lacak", "/auth/login"):
        html = client.get(path).get_data(as_text=True)
        assert "/static/favicon.svg" in html
        assert "http://" not in html
        assert "https://" not in html


def test_csp_still_allows_local_icon_only(client):
    response = client.get("/lapor")
    csp = response.headers["Content-Security-Policy"]

    assert "img-src 'self' data:" in csp
    assert "http://" not in csp
    assert "https://" not in csp
    assert "*" not in csp
