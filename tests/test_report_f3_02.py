"""Pengujian TSK-F3-02: validasi dan penyimpanan foto aman."""
import re
from io import BytesIO
from pathlib import Path

import pytest
from flask import g
from PIL import Image
from sqlalchemy import delete, select, update
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models.category import Category
from app.models.ticket import Ticket
from app.services import ticket_photo
from app.services.ticket_photo import (
    PhotoStorageError,
    ValidatedPhoto,
    store_photo,
)
from app.services.ticket_report import BUILDING_NAME

CSRF_TOKEN_PATTERN = re.compile(r'name="csrf_token" value="([^"]+)"')
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
THREE_MB = 3 * 1024 * 1024


@pytest.fixture()
def app(tmp_path):
    from app import create_app

    test_app = create_app("testing")
    test_app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=True,
        UPLOAD_FOLDER=str(tmp_path / "uploads"),
    )

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


def _image_bytes(fmt="PNG", size=(10, 10), exif_text=None):
    image = Image.new("RGB", size, "white")
    output = BytesIO()
    save_kwargs = {}
    if exif_text is not None:
        exif = Image.Exif()
        exif[0x010E] = exif_text
        save_kwargs["exif"] = exif
    image.save(output, format=fmt, **save_kwargs)
    return output.getvalue()


def _post_report(client, data, token, photo=None):
    payload = dict(data)
    payload["csrf_token"] = token
    if photo is not None:
        payload["photo"] = photo

    return client.post(
        "/lapor",
        data=payload,
        content_type="multipart/form-data",
        follow_redirects=False,
    )


def _upload(data, filename, mime_type):
    return (BytesIO(data), filename, mime_type)


def _upload_dir(app):
    return Path(app.config["UPLOAD_FOLDER"])


def _stored_files(app):
    upload_dir = _upload_dir(app)
    if not upload_dir.exists():
        return []
    return [path for path in upload_dir.iterdir() if path.is_file()]


def test_get_form_has_photo_input_and_multipart(client):
    response = client.get("/lapor")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'enctype="multipart/form-data"' in html
    assert 'name="photo"' in html
    assert 'type="file"' in html
    assert 'accept=".jpg,.jpeg,.png,image/jpeg,image/png"' in html


def test_report_without_photo_is_saved_without_file(client, app):
    response = _post_report(
        client,
        _valid_data(),
        _get_csrf_token(client),
    )

    assert response.status_code == 200
    ticket = db.session.scalar(select(Ticket))
    assert ticket is not None
    assert ticket.photo_filename is None
    assert ticket.photo_mime_type is None
    assert ticket.photo_size_bytes is None
    assert ticket.photo_uploaded_at is None
    assert _stored_files(app) == []


def test_valid_png_is_stored_with_random_name(client, app):
    original_name = "private-name.png"
    image_data = _image_bytes("PNG")

    response = _post_report(
        client,
        _valid_data(),
        _get_csrf_token(client),
        _upload(image_data, original_name, "image/png"),
    )

    assert response.status_code == 200
    ticket = db.session.scalar(select(Ticket))
    assert ticket is not None
    assert ticket.photo_filename is not None
    assert re.fullmatch(r"[0-9a-f]{32}\.png", ticket.photo_filename)
    assert ticket.photo_filename != original_name
    assert ticket.photo_mime_type == "image/png"
    assert ticket.photo_size_bytes is not None
    assert ticket.photo_uploaded_at is not None
    assert ticket.photo_uploaded_at.tzinfo is not None
    assert original_name not in str(ticket.__dict__)

    stored_path = _upload_dir(app) / ticket.photo_filename
    assert stored_path.is_file()
    assert stored_path.stat().st_size == ticket.photo_size_bytes
    assert not Path(app.static_folder).resolve() in stored_path.resolve().parents

    success_html = response.get_data(as_text=True)
    assert original_name not in success_html


def test_valid_jpeg_is_stored_as_jpg(client, app):
    response = _post_report(
        client,
        _valid_data(),
        _get_csrf_token(client),
        _upload(_image_bytes("JPEG"), "foto.jpeg", "image/jpeg"),
    )

    assert response.status_code == 200
    ticket = db.session.scalar(select(Ticket))
    assert ticket is not None
    assert re.fullmatch(r"[0-9a-f]{32}\.jpg", ticket.photo_filename)
    assert ticket.photo_mime_type == "image/jpeg"


def test_exif_metadata_is_removed(client, app):
    response = _post_report(
        client,
        _valid_data(),
        _get_csrf_token(client),
        _upload(
            _image_bytes("JPEG", exif_text="secret-exif-value"),
            "foto.jpg",
            "image/jpeg",
        ),
    )

    assert response.status_code == 200
    ticket = db.session.scalar(select(Ticket))
    assert ticket is not None
    stored_path = _upload_dir(app) / ticket.photo_filename

    with Image.open(stored_path) as stored:
        assert len(stored.getexif()) == 0
        assert "exif" not in stored.info


def test_invalid_extension_is_rejected(client, app):
    response = _post_report(
        client,
        _valid_data(),
        _get_csrf_token(client),
        _upload(_image_bytes("PNG"), "foto.gif", "image/png"),
    )

    assert response.status_code == 400
    assert "Format foto" in response.get_data(as_text=True)
    assert db.session.scalar(select(Ticket)) is None
    assert _stored_files(app) == []


def test_mime_mismatch_is_rejected(client, app):
    response = _post_report(
        client,
        _valid_data(),
        _get_csrf_token(client),
        _upload(_image_bytes("PNG"), "foto.png", "image/jpeg"),
    )

    assert response.status_code == 400
    assert "MIME" in response.get_data(as_text=True)
    assert db.session.scalar(select(Ticket)) is None
    assert _stored_files(app) == []


def test_magic_number_mismatch_is_rejected(client, app):
    response = _post_report(
        client,
        _valid_data(),
        _get_csrf_token(client),
        _upload(_image_bytes("PNG"), "foto.jpg", "image/jpeg"),
    )

    assert response.status_code == 400
    assert db.session.scalar(select(Ticket)) is None
    assert _stored_files(app) == []


def test_corrupt_image_is_rejected(client, app):
    corrupted = PNG_MAGIC + b"not-a-valid-png"
    response = _post_report(
        client,
        _valid_data(),
        _get_csrf_token(client),
        _upload(corrupted, "foto.png", "image/png"),
    )

    assert response.status_code == 400
    assert "bukan gambar yang valid" in response.get_data(as_text=True)
    assert db.session.scalar(select(Ticket)) is None
    assert _stored_files(app) == []


def test_empty_photo_is_rejected(client, app):
    response = _post_report(
        client,
        _valid_data(),
        _get_csrf_token(client),
        _upload(b"", "foto.png", "image/png"),
    )

    assert response.status_code == 400
    assert db.session.scalar(select(Ticket)) is None
    assert _stored_files(app) == []


def test_oversized_file_is_rejected(client, app):
    response = _post_report(
        client,
        _valid_data(),
        _get_csrf_token(client),
        _upload(b"x" * (THREE_MB + 1), "foto.png", "image/png"),
    )

    assert response.status_code == 400
    assert "Ukuran foto" in response.get_data(as_text=True)
    assert db.session.scalar(select(Ticket)) is None
    assert _stored_files(app) == []


def test_oversized_request_is_rejected(client, app):
    response = _post_report(
        client,
        _valid_data(),
        _get_csrf_token(client),
        _upload(b"x" * (4 * 1024 * 1024 + 1), "foto.png", "image/png"),
    )

    assert response.status_code == 413
    assert db.session.scalar(select(Ticket)) is None
    assert _stored_files(app) == []


def test_oversized_dimension_is_rejected(client, app):
    response = _post_report(
        client,
        _valid_data(),
        _get_csrf_token(client),
        _upload(_image_bytes("PNG", size=(6001, 1)), "foto.png", "image/png"),
    )

    assert response.status_code == 400
    assert "Dimensi foto" in response.get_data(as_text=True)
    assert db.session.scalar(select(Ticket)) is None
    assert _stored_files(app) == []


def test_path_traversal_name_is_discarded(client, app):
    response = _post_report(
        client,
        _valid_data(),
        _get_csrf_token(client),
        _upload(_image_bytes("PNG"), "../../private.png", "image/png"),
    )

    assert response.status_code == 200
    ticket = db.session.scalar(select(Ticket))
    assert ticket is not None
    assert ".." not in ticket.photo_filename
    stored_path = _upload_dir(app) / ticket.photo_filename
    assert stored_path.is_file()
    assert stored_path.resolve().parent == _upload_dir(app).resolve()


def test_missing_csrf_with_photo_is_rejected(client, app):
    response = client.post(
        "/lapor",
        data={
            **_valid_data(),
            "photo": _upload(
                _image_bytes("PNG"), "foto.png", "image/png"
            ),
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert db.session.scalar(select(Ticket)) is None
    assert _stored_files(app) == []


def test_db_failure_removes_stored_photo(client, app, monkeypatch):
    from app.routes import report as report_routes

    original_create_ticket = report_routes.create_ticket_with_token

    def failing_create_ticket(data, photo=None, **kwargs):
        original_create_ticket(data, photo, **kwargs)
        raise SQLAlchemyError("simulated database failure")

    monkeypatch.setattr(
        report_routes, "create_ticket_with_token", failing_create_ticket
    )

    response = _post_report(
        client,
        _valid_data(),
        _get_csrf_token(client),
        _upload(_image_bytes("PNG"), "foto.png", "image/png"),
    )

    assert response.status_code == 500
    assert db.session.scalar(select(Ticket)) is None
    assert _stored_files(app) == []


def test_file_storage_failure_creates_no_ticket(client, app, monkeypatch):
    from app.routes import report as report_routes

    def failing_store_photo(photo, upload_folder):
        raise PhotoStorageError("simulated storage failure")

    monkeypatch.setattr(report_routes, "store_photo", failing_store_photo)

    response = _post_report(
        client,
        _valid_data(),
        _get_csrf_token(client),
        _upload(_image_bytes("PNG"), "foto.png", "image/png"),
    )

    assert response.status_code == 500
    assert db.session.scalar(select(Ticket)) is None
    assert _stored_files(app) == []


def test_store_photo_cleans_up_when_replace_fails(app, monkeypatch):
    upload_dir = _upload_dir(app)
    photo = ValidatedPhoto(
        data=b"data",
        extension="png",
        mime_type="image/png",
        size_bytes=4,
    )

    def failing_replace(source, destination):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(ticket_photo.os, "replace", failing_replace)

    with pytest.raises(PhotoStorageError):
        store_photo(photo, str(upload_dir))

    assert not upload_dir.exists() or list(upload_dir.iterdir()) == []
