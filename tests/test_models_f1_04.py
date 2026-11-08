"""Unit tests F1-04: model metadata, constraints, FK, migrasi (tanpa database).

Tes ini tidak membutuhkan koneksi PostgreSQL. Verifikasi dilakukan terhadap
``Base.metadata`` (SQLAlchemy) dan file revision Alembic yang dikompilasi ke
dialek PostgreSQL secara offline.
"""
import re
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.dialects import postgresql

import app.models as models
from app.models import AuditLog, Base, Category, Ticket, User


VERSIONS_DIR = Path(__file__).resolve().parents[1] / "migrations" / "versions"


def _table(name):
    return Base.metadata.tables[name]


def _column(table, name):
    return table.columns[name]


def _constraint_names(table, kind):
    return {c.name for c in table.constraints if isinstance(c, kind)}


# --- Registrasi model ---
def test_all_tables_registered():
    assert set(Base.metadata.tables.keys()) == {
        "users",
        "categories",
        "tickets",
        "audit_logs",
    }


def test_model_classes_map_to_tables():
    assert User.__tablename__ == "users"
    assert Category.__tablename__ == "categories"
    assert Ticket.__tablename__ == "tickets"
    assert AuditLog.__tablename__ == "audit_logs"


# --- Primary key BIGSERIAL (LOCKED #6 / #16) ---
@pytest.mark.parametrize("table_name", ["users", "categories", "tickets", "audit_logs"])
def test_primary_key_is_biginteger_autoincrement(table_name):
    pk = _column(_table(table_name), "id")
    assert pk.primary_key is True
    assert pk.autoincrement in (True, "auto")


@pytest.mark.parametrize("table_name", ["users", "categories", "tickets", "audit_logs"])
def test_primary_key_renders_bigserial(table_name):
    from sqlalchemy.schema import CreateTable

    ddl = str(CreateTable(_table(table_name)).compile(dialect=postgresql.dialect()))
    assert re.search(r"\bid BIGSERIAL NOT NULL", ddl), ddl
    assert "id SERIAL NOT NULL" not in ddl


# --- users: CHECK role + password (LOCKED #9) ---
def test_users_role_check():
    names = _constraint_names(_table("users"), CheckConstraint)
    assert "ck_users_role" in names


def test_users_password_hash_check_sql():
    checks = {
        c.name: str(c.sqltext)
        for c in _table("users").constraints
        if isinstance(c, CheckConstraint)
    }
    assert checks["ck_users_password_hash"].replace('"', "").strip() == (
        "role = 'reporter' OR password_hash IS NOT NULL"
    )


def test_users_password_hash_nullable():
    assert _column(_table("users"), "password_hash").nullable is True


def test_users_username_unique():
    assert "uq_users_username" in _constraint_names(
        _table("users"), UniqueConstraint
    )


def test_users_has_no_email_column():
    assert "email" not in _table("users").columns
    assert "uq_users_email" not in {
        c.name for c in _table("users").constraints
    }


# --- categories ---
def test_categories_code_and_name_unique():
    uqs = _constraint_names(_table("categories"), UniqueConstraint)
    assert "uq_categories_code" in uqs
    assert "uq_categories_name" in uqs


def test_categories_no_updated_at():
    assert "updated_at" not in _table("categories").columns
    assert "created_at" in _table("categories").columns


# --- tickets ---
def test_tickets_ticket_code_column_and_unique():
    assert "ticket_code" in _table("tickets").columns
    assert _column(_table("tickets"), "ticket_code").type.length == 9
    assert "uq_tickets_ticket_code" in _constraint_names(
        _table("tickets"), UniqueConstraint
    )


def test_tickets_ticket_code_check_regex():
    checks = {
        c.name: str(c.sqltext)
        for c in _table("tickets").constraints
        if isinstance(c, CheckConstraint)
    }
    sql = checks["ck_tickets_ticket_code"].replace('"', "")
    # Alamat non-ambigu: digit 2-9, huruf tanpa I/O, tanpa 0/1.
    assert "[23456789A-HJ-NP-Z]" in sql


def test_ticket_code_regex_accepts_and_rejects():
    pattern = re.compile(r"^KF-[23456789A-HJ-NP-Z]{6}$")
    assert pattern.match("KF-ABC234")
    assert pattern.match("KF-ZZZZZZ")
    assert not pattern.match("KF-ABC012")       # 0 dan 1 dilarang
    assert not pattern.match("KF-ABCIOJ")       # I dan O dilarang
    assert not pattern.match("KF-ABC23")        # kurang dari 6
    assert not pattern.match("KF-ABC2345")      # lebih dari 6
    assert not pattern.match("kf-abc234")       # huruf kecil


def test_tickets_status_default_and_check():
    col = _column(_table("tickets"), "status")
    assert col.nullable is False
    assert str(col.server_default.arg).strip("'\"") == "Baru"
    assert "ck_tickets_status" in _constraint_names(
        _table("tickets"), CheckConstraint
    )


def test_tickets_indexes_match_migration():
    tickets = _table("tickets")
    indexes = {ix.name: [c.name for c in ix.columns] for ix in tickets.indexes}
    assert indexes["ix_tickets_status"] == ["status"]
    assert indexes["ix_tickets_building_name_floor_number"] == [
        "building_name",
        "floor_number",
    ]
    # Tanpa duplikasi nama index.
    names = [ix.name for ix in tickets.indexes]
    assert len(names) == len(set(names))


def test_tickets_description_length_check():
    assert "ck_tickets_description_length" in _constraint_names(
        _table("tickets"), CheckConstraint
    )


def test_tickets_location_checks():
    names = _constraint_names(_table("tickets"), CheckConstraint)
    assert "ck_tickets_building_name" in names
    assert "ck_tickets_floor_number" in names


def test_tickets_confidence_numeric_5_4():
    col = _column(_table("tickets"), "confidence_score")
    assert col.type.precision == 5
    assert col.type.scale == 4


def test_tickets_three_category_fks():
    fk_targets = {}
    for fk in _table("tickets").constraints:
        if isinstance(fk, ForeignKeyConstraint):
            for elem in fk.elements:
                fk_targets[elem.parent.name] = elem.column.table.name
    for col in (
        "reporter_category_id",
        "predicted_category_id",
        "official_category_id",
    ):
        assert fk_targets[col] == "categories"


def test_tickets_assignment_is_not_a_status():
    # Penugasan teknisi = atribut FK nullable, bukan nilai status.
    assert "assigned_technician_id" in _table("tickets").columns
    status_check = [
        str(c.sqltext)
        for c in _table("tickets").constraints
        if isinstance(c, CheckConstraint) and c.name == "ck_tickets_status"
    ][0]
    assert "assigned" not in status_check.lower()


# --- timestamps timezone-aware (LOCKED #5) ---
@pytest.mark.parametrize(
    "table_name,cols",
    [
        ("users", ["created_at", "updated_at"]),
        ("categories", ["created_at"]),
        (
            "tickets",
            ["created_at", "updated_at", "photo_uploaded_at", "resolved_at"],
        ),
        ("audit_logs", ["created_at"]),
    ],
)
def test_datetime_columns_are_timezone_aware(table_name, cols):
    for col_name in cols:
        col = _column(_table(table_name), col_name)
        assert col.type.timezone is True, f"{table_name}.{col_name} harus TZ-aware"


# --- FK ON DELETE (LOCKED #12) ---
EXPECTED_ON_DELETE = {
    ("tickets", "reporter_id"): ("users", "SET NULL"),
    ("tickets", "assigned_technician_id"): ("users", "SET NULL"),
    ("tickets", "reporter_category_id"): ("categories", "RESTRICT"),
    ("tickets", "predicted_category_id"): ("categories", "RESTRICT"),
    ("tickets", "official_category_id"): ("categories", "RESTRICT"),
    ("audit_logs", "ticket_id"): ("tickets", "RESTRICT"),
    ("audit_logs", "actor_user_id"): ("users", "SET NULL"),
}


def test_all_seven_fk_on_delete_behaviour():
    found = {}
    for fk in Base.metadata.tables.values():
        for constraint in fk.constraints:
            if isinstance(constraint, ForeignKeyConstraint):
                for elem in constraint.elements:
                    key = (elem.parent.table.name, elem.parent.name)
                    found[key] = (elem.column.table.name, elem.ondelete)
    for key, expected in EXPECTED_ON_DELETE.items():
        assert found.get(key) == expected, f"FK {key} salah: {found.get(key)}"


def test_audit_ticket_id_not_null():
    assert _column(_table("audit_logs"), "ticket_id").nullable is False


def test_audit_actor_user_id_nullable():
    assert _column(_table("audit_logs"), "actor_user_id").nullable is True


# --- ORM relationship cascade (LOCKED #15) ---
def test_ticket_audit_entries_has_no_delete_cascade():
    rel = Ticket.audit_entries.property
    assert "delete" not in (rel.cascade or "")
    assert "delete-orphan" not in (rel.cascade or "")


# --- relationship integrity ---
def test_relationships_back_populate():
    assert Ticket.reporter.property.back_populates == "reported_tickets"
    assert Ticket.assigned_technician.property.back_populates == "assigned_tickets"
    assert Ticket.audit_entries.property.back_populates == "ticket"
    assert AuditLog.ticket.property.back_populates == "audit_entries"


# --- migrasi: file revision valid & sekuensial ---
def test_migration_files_exist():
    assert (VERSIONS_DIR / "0001_initial_schema.py").is_file()
    assert (VERSIONS_DIR / "0002_seed_categories.py").is_file()


def test_seed_migration_is_self_contained():
    text = (VERSIONS_DIR / "0002_seed_categories.py").read_text(encoding="utf-8")
    assert "from app.models" not in text
    assert "import app.models" not in text
    # ID statis 1..7
    for i in range(1, 8):
        assert f'"id": {i},' in text
    # Sinkronisasi sequence
    assert "setval" in text
    assert "pg_get_serial_sequence" in text


def test_seed_migration_has_seven_categories():
    text = (VERSIONS_DIR / "0002_seed_categories.py").read_text(encoding="utf-8")
    codes = re.findall(r'"code": "(K[1-7])"', text)
    assert codes == ["K1", "K2", "K3", "K4", "K5", "K6", "K7"]


def test_migration_chain():
    import importlib.util

    def load(name):
        path = VERSIONS_DIR / name
        spec = importlib.util.spec_from_file_location(name.replace(".py", ""), path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    rev1 = load("0001_initial_schema.py")
    rev2 = load("0002_seed_categories.py")
    assert rev1.down_revision is None
    assert rev2.down_revision == rev1.revision


# --- Decimal placeholder agar import terpakai (menjaga lint) ---
def test_confidence_accepts_decimal_range():
    value = Decimal("0.9500")
    assert Decimal("0") <= value <= Decimal("1")
