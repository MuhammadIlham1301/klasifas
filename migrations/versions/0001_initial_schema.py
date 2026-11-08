"""initial schema: users, categories, tickets, audit_logs

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-11-02

Seluruh DDL ditulis manual agar nama constraint eksplisit (CHECK/FK/UNIQUE)
sesuai Implementation Plan F1-04 FINAL yang dikunci.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("username", name="uq_users_username"),
        sa.CheckConstraint(
            "role IN ('reporter', 'admin_sarpras', 'teknisi', 'pimpinan')",
            name="ck_users_role",
        ),
        sa.CheckConstraint(
            "role = 'reporter' OR password_hash IS NOT NULL",
            name="ck_users_password_hash",
        ),
    )
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_users_is_active", "users", ["is_active"])

    # --- categories ---
    op.create_table(
        "categories",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=2), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("responsible_unit", sa.String(length=100), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_categories"),
        sa.UniqueConstraint("code", name="uq_categories_code"),
        sa.UniqueConstraint("name", name="uq_categories_name"),
        sa.CheckConstraint(
            "code IN ('K1', 'K2', 'K3', 'K4', 'K5', 'K6', 'K7')",
            name="ck_categories_code",
        ),
    )

    # --- tickets ---
    op.create_table(
        "tickets",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("ticket_code", sa.String(length=9), nullable=False),
        sa.Column("access_token_hash", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("reporter_id", sa.BigInteger(), nullable=True),
        sa.Column("reporter_name", sa.String(length=120), nullable=True),
        sa.Column("reporter_contact", sa.String(length=120), nullable=True),
        sa.Column("reporter_category_id", sa.BigInteger(), nullable=True),
        sa.Column("predicted_category_id", sa.BigInteger(), nullable=True),
        sa.Column("official_category_id", sa.BigInteger(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'Baru'"),
        ),
        sa.Column("assigned_technician_id", sa.BigInteger(), nullable=True),
        sa.Column("building_name", sa.String(length=100), nullable=False),
        sa.Column("floor_number", sa.SmallInteger(), nullable=False),
        sa.Column("room_name", sa.String(length=100), nullable=True),
        sa.Column("location_detail", sa.String(length=255), nullable=True),
        sa.Column(
            "needs_manual_verification",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("photo_filename", sa.String(length=255), nullable=True),
        sa.Column("photo_mime_type", sa.String(length=100), nullable=True),
        sa.Column("photo_size_bytes", sa.Integer(), nullable=True),
        sa.Column("photo_uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tickets"),
        sa.UniqueConstraint("ticket_code", name="uq_tickets_ticket_code"),
        sa.UniqueConstraint(
            "access_token_hash", name="uq_tickets_access_token_hash"
        ),
        sa.CheckConstraint(
            r"ticket_code ~ '^KF-[23456789A-HJ-NP-Z]{6}$'",
            name="ck_tickets_ticket_code",
        ),
        sa.CheckConstraint(
            "status IN ('Baru', 'Terverifikasi', 'Diproses', 'Selesai')",
            name="ck_tickets_status",
        ),
        sa.CheckConstraint(
            "confidence_score IS NULL OR "
            "(confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_tickets_confidence_score",
        ),
        sa.CheckConstraint(
            "building_name = 'Gedung FTII'", name="ck_tickets_building_name"
        ),
        sa.CheckConstraint(
            "floor_number BETWEEN 1 AND 4", name="ck_tickets_floor_number"
        ),
        sa.CheckConstraint(
            "char_length(description) <= 2000",
            name="ck_tickets_description_length",
        ),
        sa.ForeignKeyConstraint(
            ["reporter_id"],
            ["users.id"],
            name="fk_tickets_reporter_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["reporter_category_id"],
            ["categories.id"],
            name="fk_tickets_reporter_category_id_categories",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["predicted_category_id"],
            ["categories.id"],
            name="fk_tickets_predicted_category_id_categories",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["official_category_id"],
            ["categories.id"],
            name="fk_tickets_official_category_id_categories",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_technician_id"],
            ["users.id"],
            name="fk_tickets_assigned_technician_id_users",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_tickets_status", "tickets", ["status"])
    op.create_index(
        "ix_tickets_reporter_category_id", "tickets", ["reporter_category_id"]
    )
    op.create_index(
        "ix_tickets_predicted_category_id", "tickets", ["predicted_category_id"]
    )
    op.create_index(
        "ix_tickets_official_category_id", "tickets", ["official_category_id"]
    )
    op.create_index(
        "ix_tickets_assigned_technician_id",
        "tickets",
        ["assigned_technician_id"],
    )
    op.create_index("ix_tickets_created_at", "tickets", ["created_at"])
    op.create_index(
        "ix_tickets_needs_manual_verification",
        "tickets",
        ["needs_manual_verification"],
    )
    op.create_index(
        "ix_tickets_building_name_floor_number",
        "tickets",
        ["building_name", "floor_number"],
    )

    # --- audit_logs ---
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("ticket_id", sa.BigInteger(), nullable=False),
        sa.Column("actor_user_id", sa.BigInteger(), nullable=True),
        sa.Column("actor_role", sa.String(length=32), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("field_name", sa.String(length=64), nullable=False),
        sa.Column("old_value", sa.String(length=255), nullable=True),
        sa.Column("new_value", sa.String(length=255), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["tickets.id"],
            name="fk_audit_logs_ticket_id_tickets",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name="fk_audit_logs_actor_user_id_users",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_audit_logs_ticket_id", "audit_logs", ["ticket_id"])
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])


def downgrade():
    # Urutan drop: audit_logs -> tickets -> categories -> users.
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_ticket_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index(
        "ix_tickets_building_name_floor_number", table_name="tickets"
    )
    op.drop_index(
        "ix_tickets_needs_manual_verification", table_name="tickets"
    )
    op.drop_index("ix_tickets_created_at", table_name="tickets")
    op.drop_index(
        "ix_tickets_assigned_technician_id", table_name="tickets"
    )
    op.drop_index("ix_tickets_official_category_id", table_name="tickets")
    op.drop_index("ix_tickets_predicted_category_id", table_name="tickets")
    op.drop_index("ix_tickets_reporter_category_id", table_name="tickets")
    op.drop_index("ix_tickets_status", table_name="tickets")
    op.drop_table("tickets")

    op.drop_table("categories")

    op.drop_index("ix_users_is_active", table_name="users")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_table("users")
