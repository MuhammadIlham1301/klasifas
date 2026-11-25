"""Pengujian TSK-F3-01: formulir pelaporan dan penyimpanan tiket."""
import hashlib
import re
import secrets

import pytest
from flask import g
from sqlalchemy import delete, select, update
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models.category import Category
from app.models.ticket import Ticket
from app.models.user import User
from app.services.ticket_report import BUILDING_NAME
from app.utils import ticket_identity

CSRF_TOKEN_PATTERN = re.compile(r'name="csrf_token" value="([^"]+)"')
TICKET_CODE_PATTERN = re.compile(r"^KF-[23456789A-HJ-NP-Z]{6}$")
RAW_TOKEN = "raw-token-f3-01-test"


@pytest.fixture()
def app():
    from app import create_app

    test_app = create_app("testing")
    test_app.config.update(TESTING=True, WTF_CSRF_ENABLED=True)

    with test_app.app_context():
        baseline_ticket_ids = set(db.session.scalars(select(Ticket.id)).all())
        baseline_categories = {
            category.code: category.is_active
            for category in db.session.scalars(select(Category)).all()
        }

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

            with db.engine.begin() as cleanup_connection:
                if baseline_ticket_ids:
                    cleanup_connection.execute(
                        delete(Ticket).where(
                            Ticket.id.notin_(baseline_ticket_ids)
                        )
                    )
                else:
                    cleanup_connection.execute(delete(Ticket))

                for code, is_active in baseline_categories.items():
                    cleanup_connection.execute(
                        update(Category)
                        .where(Category.code == code)
                        .values(is_active=is_active)
                    )

            db.engine.dispose()


@pytest.fixture()
def client(app):
    return app.test_client()


def _get_csrf_token(client):
    g.pop("csrf_token", None)
    response = client.get("/lapor")
    assert response.status_code == 200
    match = CSRF_TOKEN_PATTERN.search(response.get_data(as_text=True))
    assert match is not None
    return match.group(1)


def _get_category(code):
    category = db.session.scalar(
        select(Category).where(Category.code == code)
    )
    assert category is not None
    return category


def _set_category_active(code, is_active):
    category = _get_category(code)
    category.is_active = is_active
    db.session.flush()
    return category


def _valid_data(**overrides):
    data = {
        "description": "AC di ruang kelas tidak dingin sejak pagi.",
        "building_name": BUILDING_NAME,
        "floor_number": "2",
        "room_name": "Ruang 2.3",
        "location_detail": "Dekat papan tulis",
        "reporter_category_id": "",
        "reporter_name": "",
        "reporter_contact": "",
    }
    data.update(overrides)
    return data


def _post_report(client, data, token=None):
    payload = dict(data)
    if token is not None:
        payload["csrf_token"] = token
    return client.post("/lapor", data=payload, follow_redirects=False)


def test_root_redirects_to_reporter_login(client):
    response = client.get("/")

    assert response.status_code == 302
    assert response.headers["Location"] == "/auth/pelapor/login"


def test_root_follow_redirects_to_reporter_login(client):
    response = client.get("/", follow_redirects=True)
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Login Pelapor KlasiFas" in html
    assert 'action="/auth/pelapor/login"' in html
    assert 'class="kf-report-form"' not in html


def test_root_post_returns_405(client):
    response = client.post("/")

    assert response.status_code == 405


def test_get_report_form_renders_fields_and_local_assets(client):
    response = client.get("/lapor")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    for field in (
        "description",
        "building_name",
        "floor_number",
        "room_name",
        "location_detail",
        "reporter_category_id",
        "reporter_name",
        "reporter_contact",
        "csrf_token",
    ):
        assert f'name="{field}"' in html

    assert "vendor/bootstrap/bootstrap.min.css" in html
    assert "css/klasifas.css" in html
    assert "cdn.jsdelivr.net" not in html
    assert 'type="file"' in html
    assert "multipart/form-data" in html


def test_get_report_form_lists_only_active_categories(client):
    active = _get_category("K1")
    inactive = _set_category_active("K7", False)

    response = client.get("/lapor")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert active.name in html
    assert inactive.name not in html


def test_valid_report_saves_ticket_with_defaults(
    client, monkeypatch, caplog
):
    category = _get_category("K1")
    token_sizes = []

    def fake_token_urlsafe(size):
        token_sizes.append(size)
        return RAW_TOKEN

    monkeypatch.setattr(
        ticket_identity.secrets,
        "token_urlsafe",
        fake_token_urlsafe,
    )

    response = _post_report(
        client,
        _valid_data(reporter_category_id=str(category.id)),
        _get_csrf_token(client),
    )

    assert response.status_code == 200
    assert "Location" not in response.headers
    assert response.headers["Cache-Control"] == "no-store"

    ticket = db.session.scalar(select(Ticket))
    assert ticket is not None
    assert token_sizes == [16]
    assert TICKET_CODE_PATTERN.fullmatch(ticket.ticket_code)
    assert ticket.access_token_hash == hashlib.sha256(
        RAW_TOKEN.encode("utf-8")
    ).hexdigest()
    assert len(ticket.access_token_hash) == 64
    assert RAW_TOKEN not in str(ticket.__dict__)

    assert ticket.description == "AC di ruang kelas tidak dingin sejak pagi."
    assert ticket.building_name == BUILDING_NAME
    assert ticket.floor_number == 2
    assert ticket.room_name == "Ruang 2.3"
    assert ticket.location_detail == "Dekat papan tulis"
    assert ticket.reporter_category_id == category.id
    assert ticket.reporter_name is None
    assert ticket.reporter_contact is None
    assert ticket.reporter_id is None
    assert ticket.predicted_category_id is None
    assert ticket.official_category_id is None
    assert ticket.confidence_score is None
    assert ticket.assigned_technician_id is None
    assert ticket.status == "Baru"
    assert ticket.needs_manual_verification is True
    assert ticket.photo_filename is None
    assert ticket.photo_mime_type is None
    assert ticket.photo_size_bytes is None
    assert ticket.photo_uploaded_at is None

    with client.session_transaction() as session_data:
        assert "last_ticket_code" not in session_data
        assert RAW_TOKEN not in str(dict(session_data))

    success_html = response.get_data(as_text=True)
    assert ticket.ticket_code in success_html
    assert success_html.count(RAW_TOKEN) == 1
    assert RAW_TOKEN not in caplog.text
    assert RAW_TOKEN not in str(response.headers)

    repeated = client.get("/lapor/sukses")
    assert repeated.status_code == 302
    assert repeated.headers["Location"].endswith("/lapor")


def test_optional_fields_are_stored_as_none(client):
    response = _post_report(
        client,
        _valid_data(
            location_detail="   ",
            reporter_category_id="",
            reporter_name="   ",
            reporter_contact="   ",
        ),
        _get_csrf_token(client),
    )

    assert response.status_code == 200
    ticket = db.session.scalar(select(Ticket))
    assert ticket is not None
    assert ticket.location_detail is None
    assert ticket.reporter_category_id is None
    assert ticket.reporter_name is None
    assert ticket.reporter_contact is None


def test_inactive_category_is_rejected(client):
    inactive = _set_category_active("K7", False)

    response = _post_report(
        client,
        _valid_data(reporter_category_id=str(inactive.id)),
        _get_csrf_token(client),
    )

    assert response.status_code == 400
    assert "Kategori yang dipilih tidak tersedia." in response.get_data(
        as_text=True
    )
    assert db.session.scalar(select(Ticket)) is None


@pytest.mark.parametrize("category_id", ["999999", "abc", "0"])
def test_unknown_or_invalid_category_is_rejected(client, category_id):
    response = _post_report(
        client,
        _valid_data(reporter_category_id=category_id),
        _get_csrf_token(client),
    )

    assert response.status_code == 400
    assert db.session.scalar(select(Ticket)) is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("description", ""),
        ("description", "   "),
        ("description", "x" * 2001),
        ("building_name", ""),
        ("building_name", "Gedung Lain"),
        ("floor_number", ""),
        ("floor_number", "0"),
        ("floor_number", "5"),
        ("floor_number", "2.0"),
        ("room_name", ""),
        ("room_name", "   "),
        ("room_name", "x" * 101),
        ("location_detail", "x" * 256),
        ("reporter_name", "x" * 121),
        ("reporter_contact", "x" * 121),
    ],
)
def test_invalid_fields_are_rejected(client, field, value):
    response = _post_report(
        client,
        _valid_data(**{field: value}),
        _get_csrf_token(client),
    )

    assert response.status_code == 400
    assert db.session.scalar(select(Ticket)) is None


def test_boundary_length_values_are_accepted(client):
    response = _post_report(
        client,
        _valid_data(
            description="x" * 2000,
            room_name="r" * 100,
            location_detail="l" * 255,
            reporter_name="n" * 120,
            reporter_contact="c" * 120,
        ),
        _get_csrf_token(client),
    )

    assert response.status_code == 200
    ticket = db.session.scalar(select(Ticket))
    assert ticket is not None
    assert len(ticket.description) == 2000
    assert len(ticket.room_name) == 100
    assert len(ticket.location_detail) == 255
    assert len(ticket.reporter_name) == 120
    assert len(ticket.reporter_contact) == 120


def test_missing_csrf_token_is_rejected(client):
    response = _post_report(client, _valid_data())

    assert response.status_code == 400
    assert db.session.scalar(select(Ticket)) is None


def test_invalid_csrf_token_is_rejected(client):
    response = _post_report(client, _valid_data(), token="invalid-token")

    assert response.status_code == 400
    assert db.session.scalar(select(Ticket)) is None


def test_validation_error_escapes_user_input(client):
    payload = "<script>alert('xss')</script>"
    response = _post_report(
        client,
        _valid_data(description=payload, room_name=""),
        _get_csrf_token(client),
    )

    html = response.get_data(as_text=True)
    assert response.status_code == 400
    assert payload not in html
    assert "&lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;" in html
    assert db.session.scalar(select(Ticket)) is None


def test_storage_failure_rolls_back_ticket(client, monkeypatch):
    from app.routes import report as report_routes

    original_create_ticket = report_routes.create_ticket_with_token

    def failing_create_ticket(data, photo=None, **kwargs):
        original_create_ticket(data, photo, **kwargs)
        raise SQLAlchemyError("simulated storage failure")

    monkeypatch.setattr(
        report_routes, "create_ticket_with_token", failing_create_ticket
    )

    response = _post_report(
        client,
        _valid_data(reporter_name="Pelapor"),
        _get_csrf_token(client),
    )

    assert response.status_code == 500
    assert "Laporan belum dapat dikirim." in response.get_data(as_text=True)
    assert db.session.scalar(select(Ticket)) is None


def test_success_without_session_redirects_to_form(client):
    response = client.get("/lapor/sukses")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/lapor")


def test_logged_in_reporter_ticket_is_linked(client):
    reporter = User(
        username=f"linked_reporter_{secrets.token_hex(4)}",
        full_name="Pelapor Terhubung",
        password_hash=None,
        role="reporter",
        is_active=True,
    )
    db.session.add(reporter)
    db.session.flush()

    with client.session_transaction() as session_data:
        session_data["reporter_id"] = reporter.id

    description = "Laporan pelapor terhubung ke akun."
    response = _post_report(
        client,
        _valid_data(description=description),
        _get_csrf_token(client),
    )

    assert response.status_code == 200
    ticket = db.session.scalar(
        select(Ticket).where(Ticket.description == description)
    )
    assert ticket is not None
    assert ticket.reporter_id == reporter.id
