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


@pytest.fixture()
def motion_js(client):
    response = client.get("/static/js/motion.js")

    assert response.status_code == 200
    return response.get_data(as_text=True)


def test_motion_script_is_loaded_before_page_scripts(client):
    html = client.get("/lapor").get_data(as_text=True)

    assert "js/motion.js" in html
    assert html.index("js/motion.js") < html.index("js/portal.js")


def test_motion_uses_observer_and_reduced_motion(motion_js):
    assert "IntersectionObserver" in motion_js
    assert "prefers-reduced-motion: reduce" in motion_js
    assert "kf-motion-ready" in motion_js
    assert "refresh" in motion_js


def test_reveal_state_is_gated_by_javascript(css):
    assert "html.kf-motion-ready .kf-reveal:not(.is-revealed)" in css
    assert "animation: kf-reveal-in" in css
    assert "--kf-reveal-delay" in css


def test_reveal_has_print_and_reduced_motion_fallbacks(css):
    assert "opacity: 1 !important;" in css
    assert "animation: none !important;" in css
    assert "@media print" in css
    assert "@media (prefers-reduced-motion: reduce)" in css


def test_interactive_transitions_are_declared(css):
    assert ".dropdown-menu.show" in css
    assert ".modal.fade .modal-dialog" in css
    assert ".navbar-collapse.collapsing" in css
    assert ".page-link" in css
