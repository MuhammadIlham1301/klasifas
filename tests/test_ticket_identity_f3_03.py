"""Pengujian TSK-F3-03: kode referensi dan token akses tiket."""
import hashlib
import re

import pytest
from flask import g
from sqlalchemy import delete, select, update
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models.category import Category
from app.models.ticket import Ticket
from app.services.ticket_report import (
    BUILDING_NAME,
    create_ticket_with_token,
    rotate_access_token,
)
from app.utils import ticket_identity

CSRF_TOKEN_PATTERN = re.compile(r'name="csrf_token" value="([^"]+)"')
TICKET_CODE_PATTERN = re.compile(r"^KF-[23456789A-HJ-NP-Z]{6}$")
RAW_TOKEN = "raw-token-f3-03-test"


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


def _post_report(client, data, token):
    payload = dict(data)
    payload["csrf_token"] = token
    return client.post(
        "/lapor", data=payload, follow_redirects=False
    )


def test_ticket_code_format_and_alphabet():
    for _ in range(100):
        code = ticket_identity.generate_ticket_code()
        assert TICKET_CODE_PATTERN.fullmatch(code)
        assert all(
            character not in "01IO"
            for character in code.removeprefix("KF-")
        )


def test_generate_access_token_returns_raw_and_hash(monkeypatch):
    calls = []

    def fake_token_urlsafe(size):
        calls.append(size)
        return RAW_TOKEN

    monkeypatch.setattr(
        ticket_identity.secrets, "token_urlsafe", fake_token_urlsafe
    )

    raw_token, token_hash = ticket_identity.generate_access_token()

    assert calls == [16]
    assert raw_token == RAW_TOKEN
    assert token_hash == hashlib.sha256(
        RAW_TOKEN.encode("utf-8")
    ).hexdigest()
    assert len(token_hash) == 64


def test_generate_access_token_hash_remains_compatible(monkeypatch):
    monkeypatch.setattr(
        ticket_identity.secrets,
        "token_urlsafe",
        lambda _size: RAW_TOKEN,
    )

    token_hash = ticket_identity.generate_access_token_hash()

    assert token_hash == hashlib.sha256(
        RAW_TOKEN.encode("utf-8")
    ).hexdigest()


def test_verify_access_token_matches_hash_only():
    token_hash = hashlib.sha256(
        RAW_TOKEN.encode("utf-8")
    ).hexdigest()

    assert ticket_identity.verify_access_token(RAW_TOKEN, token_hash)
    assert not ticket_identity.verify_access_token("wrong", token_hash)
    assert not ticket_identity.verify_access_token("", token_hash)
    assert not ticket_identity.verify_access_token(RAW_TOKEN, "")


def test_post_displays_token_once_without_url_or_session(
    client, monkeypatch, caplog
):
    monkeypatch.setattr(
        ticket_identity.secrets,
        "token_urlsafe",
        lambda _size: RAW_TOKEN,
    )

    response = _post_report(
        client,
        _valid_data(),
        _get_csrf_token(client),
    )

    assert response.status_code == 200
    assert "Location" not in response.headers
    assert response.headers["Cache-Control"] == "no-store"
    assert RAW_TOKEN not in str(response.headers)

    html = response.get_data(as_text=True)
    assert html.count(RAW_TOKEN) == 1

    ticket = db.session.scalar(select(Ticket))
    assert ticket is not None
    assert ticket.ticket_code in html
    assert ticket.access_token_hash == hashlib.sha256(
        RAW_TOKEN.encode("utf-8")
    ).hexdigest()
    assert RAW_TOKEN not in str(ticket.__dict__)

    with client.session_transaction() as session_data:
        assert "last_ticket_code" not in session_data
        assert RAW_TOKEN not in str(dict(session_data))

    assert RAW_TOKEN not in caplog.text

    no_token_page = client.get("/lapor/sukses")
    assert no_token_page.status_code == 302
    assert no_token_page.headers["Location"].endswith("/lapor")
    assert RAW_TOKEN not in no_token_page.get_data(as_text=True)


def test_rotate_access_token_changes_hash_and_rolls_back(app):
    data = _valid_data(
        reporter_category_id=None,
        reporter_name=None,
        reporter_contact=None,
    )
    ticket, old_token = create_ticket_with_token(data)
    db.session.commit()
    ticket_id = ticket.id
    old_hash = ticket.access_token_hash
    assert ticket_identity.verify_access_token(old_token, old_hash)

    db.session.begin_nested()
    new_token = rotate_access_token(ticket)

    assert ticket.access_token_hash != old_hash
    assert ticket_identity.verify_access_token(
        new_token, ticket.access_token_hash
    )
    assert not ticket_identity.verify_access_token(
        old_token, ticket.access_token_hash
    )

    db.session.rollback()
    restored = db.session.get(Ticket, ticket_id)
    assert restored is not None
    assert restored.access_token_hash == old_hash
    assert ticket_identity.verify_access_token(
        old_token, restored.access_token_hash
    )


def test_failed_persistence_does_not_display_token(client, monkeypatch):
    from app.routes import report as report_routes

    original_create = report_routes.create_ticket_with_token

    def failing_create(data, photo=None):
        original_create(data, photo)
        raise SQLAlchemyError("simulated persistence failure")

    monkeypatch.setattr(
        report_routes, "create_ticket_with_token", failing_create
    )
    monkeypatch.setattr(
        ticket_identity.secrets,
        "token_urlsafe",
        lambda _size: RAW_TOKEN,
    )

    response = _post_report(
        client,
        _valid_data(),
        _get_csrf_token(client),
    )

    assert response.status_code == 500
    assert RAW_TOKEN not in response.get_data(as_text=True)
    assert db.session.scalar(select(Ticket)) is None
