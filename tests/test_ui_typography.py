"""Pengujian VQ-03: Public Sans lokal dan CSP font."""
import pytest

FONT_FACES = {
    "PublicSans-Regular.woff2": "400",
    "PublicSans-Medium.woff2": "500",
    "PublicSans-SemiBold.woff2": "600",
    "PublicSans-Bold.woff2": "700",
}


@pytest.fixture()
def app():
    from app import create_app

    return create_app("testing")


@pytest.fixture()
def client(app):
    return app.test_client()


def test_public_sans_font_faces_are_local(client):
    response = client.get("/static/css/klasifas.css")

    assert response.status_code == 200
    css = response.get_data(as_text=True)
    assert css.count("@font-face") == 4
    assert '--kf-font-sans-serif: "Public Sans", system-ui' in css
    assert "fonts.googleapis.com" not in css
    assert "fonts.gstatic.com" not in css

    for filename, weight in FONT_FACES.items():
        assert f'fonts/public-sans/{filename}' in css
        assert f"font-weight: {weight};" in css

    assert css.count("font-display: swap;") == 4


def test_public_sans_woff2_assets_are_served(client):
    for filename in FONT_FACES:
        response = client.get(f"/static/fonts/public-sans/{filename}")

        assert response.status_code == 200
        assert response.data[:4] == b"wOF2"
        assert len(response.data) > 0


def test_public_sans_ofl_is_served(client):
    response = client.get("/static/fonts/public-sans/OFL.txt")

    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "SIL Open Font License" in text


def test_csp_allows_only_local_fonts(client):
    response = client.get("/lapor")

    assert response.status_code == 200
    csp = response.headers["Content-Security-Policy"]
    assert "font-src 'self'" in csp
    assert "https://" not in csp

    html = response.get_data(as_text=True)
    assert "fonts.googleapis.com" not in html
    assert "fonts.gstatic.com" not in html
