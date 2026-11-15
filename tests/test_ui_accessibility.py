"""Kontrak aksesibilitas UI: touch target, kontras eyebrow, dan drawer mobile."""
import re
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT_DIR / "app" / "templates"
JS_DIR = ROOT_DIR / "app" / "static" / "js"


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


def _token(css, name):
    match = re.search(re.escape(name) + r":\s*(#[0-9a-fA-F]{6});", css)
    assert match is not None, f"token {name} tidak ditemukan"
    return match.group(1)


def _luminance(hex_color):
    value = hex_color.lstrip("#")
    channels = [int(value[index:index + 2], 16) / 255 for index in (0, 2, 4)]
    channels = [
        channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast(foreground, background):
    lighter, darker = sorted(
        (_luminance(foreground), _luminance(background)),
        reverse=True,
    )
    return (lighter + 0.05) / (darker + 0.05)


def _mobile_sidebar_block(css):
    for match in re.finditer(r"@media \(max-width: 767\.98px\) \{([\s\S]*?)\n\}", css):
        if ".kf-sidebar" in match.group(1):
            return match.group(1)
    raise AssertionError("media query mobile sidebar tidak ditemukan")


def test_mobile_touch_targets_are_48px(css):
    block = _mobile_sidebar_block(css)

    assert "--kf-input-height: 3rem;" in block
    assert re.search(r"\.btn,\s*\.kf-sidebar-link\s*\{\s*min-height: 48px;", block)
    assert re.search(
        r"\.kf-sidebar-toggle-btn\s*\{\s*width: 48px;\s*height: 48px;",
        block,
    )
    assert re.search(
        r"#kf-mobile-drawer-toggle\s*\{\s*min-width: 48px;\s*min-height: 48px;",
        block,
    )
    assert "--kf-input-height: 2.75rem;" in css


def test_eyebrow_uses_primary_and_meets_aa(css):
    eyebrow = _rule_body(css, ".kf-page-heading__eyebrow")

    assert "color: var(--kf-primary);" in eyebrow
    assert "var(--kf-secondary-dark)" not in eyebrow

    primary = _token(css, "--kf-primary")
    for background_name in ("--kf-surface", "--kf-background", "--kf-surface-subtle"):
        background = _token(css, background_name)
        assert _contrast(primary, background) >= 4.5


def test_mobile_drawer_markup_has_aria_contract():
    base = (TEMPLATES_DIR / "base.html").read_text(encoding="utf-8")

    toggle = re.search(r'<button[^>]*id="kf-mobile-drawer-toggle"[^>]*>', base)
    assert toggle is not None
    assert 'aria-controls="kf-sidebar"' in toggle.group(0)
    assert 'aria-expanded="false"' in toggle.group(0)

    close_button = re.search(r'<button[^>]*id="kf-mobile-drawer-close"[^>]*>', base)
    assert close_button is not None
    assert 'aria-label="Tutup menu navigasi"' in close_button.group(0)

    desktop_toggle = re.search(r'<button[^>]*id="kf-sidebar-toggle"[^>]*>', base)
    assert desktop_toggle is not None
    assert 'aria-controls="kf-sidebar"' in desktop_toggle.group(0)

    assert re.search(
        r'id="kf-sidebar"[^>]*aria-label="Navigasi Internal Staf"',
        base,
    )
    assert re.search(
        r'id="kf-sidebar-backdrop"[^>]*aria-hidden="true"',
        base,
    )


def test_drawer_css_hides_closed_state_and_has_focus_styles(css):
    block = _mobile_sidebar_block(css)

    assert re.search(
        r"\.kf-sidebar\s*\{[\s\S]*?visibility: hidden;[\s\S]*?pointer-events: none;",
        block,
    )
    assert re.search(
        r"\.kf-sidebar\.is-mobile-open\s*\{[\s\S]*?visibility: visible;[\s\S]*?pointer-events: auto;",
        block,
    )
    assert ".kf-sidebar-link:focus-visible," in css
    assert ".kf-sidebar-toggle-btn:focus-visible" in css
    assert "box-shadow: 0 0 0 0.2rem var(--kf-focus-ring);" in css
    assert ".kf-sidebar {\n        transition-delay: 0s !important;" in css

    toggle_button = _rule_body(css, ".kf-sidebar-toggle-btn")
    assert "transition: all" not in toggle_button
    assert "visibility" not in toggle_button


def _media_block(css, width, selector):
    for match in re.finditer(
        r"@media \(max-width: " + re.escape(width) + r"\) \{([\s\S]*?)\n\}",
        css,
    ):
        if selector in match.group(1):
            return match.group(1)
    raise AssertionError(f"media query {width} untuk {selector} tidak ditemukan")


def test_admin_queue_has_mobile_cards_and_desktop_table():
    html = (TEMPLATES_DIR / "admin" / "queue.html").read_text(encoding="utf-8")

    assert "d-lg-none vstack gap-3" in html
    assert "card border-0 shadow-sm d-none d-lg-block" in html
    assert "queue_action(t, 'w-100')" in html
    assert "queue_action(t)" in html


def test_track_stepper_is_vertical_on_mobile(css):
    block = _media_block(css, "575.98px", ".kf-stepper")

    assert "grid-template-columns: minmax(0, 1fr);" in block
    assert "grid-template-areas:" in block
    assert '"indicator label"' in block
    assert ".kf-stepper__step:not(:last-child)::after" in block
    assert ".kf-stepper__caption {\n        font-size: 0.75rem;" in block
    assert "display: none;" not in block


def test_audit_log_uses_human_labels_and_accessible_pagination():
    html = (TEMPLATES_DIR / "admin" / "audit_log.html").read_text(encoding="utf-8")
    macros = (TEMPLATES_DIR / "components" / "_macros.html").read_text(encoding="utf-8")

    assert "Perubahan Kategori (category_changed)" not in html
    assert "Perubahan Status (status_changed)" not in html
    assert "Penugasan Teknisi (technician_assigned)" not in html
    assert "role_badge(log.actor_role or 'sistem')" in html
    assert 'href="#"' not in html
    assert 'aria-current="page"' in html
    assert "'sistem': 'Sistem'" in macros


def test_report_form_references_only_present_error_ids(client):
    html = client.get("/lapor").get_data(as_text=True)

    assert 'aria-describedby="floor-error"' not in html
    assert 'id="floor-error"' not in html
    assert 'id="building-error"' not in html
    assert '<label for="building_name"' not in html
    assert 'role="group" aria-labelledby="building-label"' in html
    assert 'aria-describedby="category-help"' in html


def test_track_form_help_text_is_programmatically_associated():
    html = (TEMPLATES_DIR / "report" / "track.html").read_text(encoding="utf-8")

    assert 'aria-describedby="ticket-code-help"' in html
    assert 'id="ticket-code-help"' in html
    assert 'aria-describedby="access-token-help"' in html
    assert 'id="access-token-help"' in html


def test_verify_page_uses_non_label_text_for_static_fields():
    html = (TEMPLATES_DIR / "admin" / "verify.html").read_text(encoding="utf-8")

    assert '<label class="form-label text-secondary' not in html
    assert '<span class="form-label text-secondary small mb-1 d-block">Deskripsi Keluhan</span>' in html
    assert '<span class="visually-hidden">(wajib)</span>' in html


def test_sidebar_js_manages_inert_focus_and_keyboard():
    script = (JS_DIR / "sidebar.js").read_text(encoding="utf-8")

    assert 'matchMedia("(max-width: 767.98px)")' in script
    assert "getFocusableElements" in script
    assert 'setAttribute("inert", "")' in script
    assert 'removeAttribute("inert")' in script
    assert 'setAttribute("aria-hidden", "true")' in script
    assert 'setAttribute("aria-expanded"' in script
    assert 'focus({ preventScroll: true })' in script
    assert 'e.key === "Escape"' in script
    assert 'e.key === "Tab"' in script
    assert "mobileQuery.addEventListener" in script
    assert "mobileQuery.addListener" in script

    focus_branch = script.index("if (settings.focusDrawer)")
    focus_call = script.index("focusTarget.focus({ preventScroll: true });", focus_branch)
    inert_call = script.index('mainWrapper.setAttribute("inert", "")', focus_branch)
    assert focus_branch < focus_call < inert_call
    assert "void sidebar.offsetWidth;" in script[focus_branch:focus_call]
    assert "syncMobileDrawerState({ focusDrawer: true })" in script
