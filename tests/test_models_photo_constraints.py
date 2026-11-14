"""Regression tests for Ticket photo metadata CHECK constraints (F1-04)."""
import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import (
    CheckConstraint,
    Column,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    func,
    select,
)
from sqlalchemy.exc import IntegrityError

from app.models import Base
from app.models.ticket import PHOTO_MIME_CHECK_SQL, PHOTO_SIZE_CHECK_SQL

VERSIONS_DIR = Path(__file__).resolve().parents[1] / "migrations" / "versions"
MIGRATION_FILE = VERSIONS_DIR / "0003_add_ticket_photo_constraints.py"
MAX_PHOTO_SIZE_BYTES = 3_145_728


def _photo_table(metadata):
    return Table(
        "tickets",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("photo_size_bytes", Integer, nullable=True),
        Column("photo_mime_type", String(100), nullable=True),
        CheckConstraint(
            PHOTO_SIZE_CHECK_SQL, name="ck_tickets_photo_size_bytes"
        ),
        CheckConstraint(
            PHOTO_MIME_CHECK_SQL, name="ck_tickets_photo_mime_type"
        ),
    )


@pytest.fixture()
def photo_db():
    engine = create_engine("sqlite://")
    metadata = MetaData()
    table = _photo_table(metadata)
    metadata.create_all(engine)
    try:
        yield engine, table
    finally:
        engine.dispose()


def _insert_photo_metadata(engine, table, size, mime):
    with engine.begin() as connection:
        connection.execute(
            table.insert().values(
                photo_size_bytes=size,
                photo_mime_type=mime,
            )
        )


@pytest.mark.parametrize(
    "size,mime",
    [
        (1, "image/jpeg"),
        (MAX_PHOTO_SIZE_BYTES, "image/png"),
        (None, None),
        (None, "image/jpeg"),
        (1024, None),
    ],
)
def test_photo_constraints_accept_valid_and_null(photo_db, size, mime):
    engine, table = photo_db
    _insert_photo_metadata(engine, table, size, mime)

    with engine.connect() as connection:
        assert connection.execute(
            select(func.count()).select_from(table)
        ).scalar_one() == 1


@pytest.mark.parametrize(
    "size,mime",
    [
        (-1, "image/jpeg"),
        (0, "image/jpeg"),
        (MAX_PHOTO_SIZE_BYTES + 1, "image/jpeg"),
        (1024, "image/gif"),
        (1024, "image/jpg"),
        (1024, "text/plain"),
        (1024, ""),
    ],
)
def test_photo_constraints_reject_invalid_values(photo_db, size, mime):
    engine, table = photo_db
    with pytest.raises(IntegrityError):
        _insert_photo_metadata(engine, table, size, mime)


def test_model_registers_photo_constraints_and_nullable_columns():
    tickets = Base.metadata.tables["tickets"]
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in tickets.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "ck_tickets_photo_size_bytes" in checks
    assert "ck_tickets_photo_mime_type" in checks
    assert "3145728" in checks["ck_tickets_photo_size_bytes"]
    assert "image/jpeg" in checks["ck_tickets_photo_mime_type"]
    assert "image/png" in checks["ck_tickets_photo_mime_type"]
    assert tickets.columns["photo_size_bytes"].nullable is True
    assert tickets.columns["photo_mime_type"].nullable is True


def _load_photo_migration():
    spec = importlib.util.spec_from_file_location(
        "0003_add_ticket_photo_constraints", MIGRATION_FILE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_photo_migration_chain_and_sql_match_model():
    migration = _load_photo_migration()

    assert migration.revision == "0003_add_ticket_photo_constraints"
    assert migration.down_revision == "0002_seed_categories"
    assert migration.PHOTO_SIZE_CHECK_SQL == PHOTO_SIZE_CHECK_SQL
    assert migration.PHOTO_MIME_CHECK_SQL == PHOTO_MIME_CHECK_SQL


def test_photo_migration_is_self_contained_and_names_constraints():
    text = MIGRATION_FILE.read_text(encoding="utf-8")

    assert "from app.models" not in text
    assert "ck_tickets_photo_size_bytes" in text
    assert "ck_tickets_photo_mime_type" in text
    assert "UPDATE tickets SET photo_size_bytes = NULL" in text
    assert "UPDATE tickets SET photo_mime_type = NULL" in text
    assert "op.create_check_constraint(" in text
    assert "op.drop_constraint(" in text
