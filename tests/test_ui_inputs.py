"""Pengujian VQ-07 & VQ-09: tinggi dan padding input/select publik."""
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


def test_input_tokens_defined(css):
    assert "--kf-input-height: 2.75rem;" in css
    assert "--kf-input-padding-y: 0.625rem;" in css
    assert "--kf-input-padding-x: 0.875rem;" in css


def test_inputs_use_padding_token(css):
    assert "padding: var(--kf-input-padding-y) var(--kf-input-padding-x);" in css


def test_inputs_have_min_height_excluding_textarea(css):
    assert ".form-control:not(textarea)," in css
    assert "min-height: var(--kf-input-height);" in css


def test_duplicate_report_form_input_rule_removed(css):
    assert ".kf-report-form .form-control:not(textarea)" not in css


def test_login_inputs_use_plain_form_control(client):
    html = client.get("/auth/login").get_data(as_text=True)

    assert "form-control-lg" not in html
    assert html.count("form-control") >= 2


@pytest.mark.parametrize("path", ["/lapor", "/lacak", "/auth/login"])
def test_public_pages_render_form_control(client, path):
    response = client.get(path)

    assert response.status_code == 200
    assert "form-control" in response.get_data(as_text=True)
