"""add defense-in-depth CHECK constraints for ticket photo metadata

Revision ID: 0003_add_ticket_photo_constraints
Revises: 0002_seed_categories
Create Date: 2026-11-09

Constraints are nullable so existing tickets without photo metadata remain
valid. Legacy photo metadata outside the allowed domain is normalized to NULL
before the validating constraints are added, so the upgrade does not fail on
pre-existing rows. Photo files themselves are not deleted.
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "0003_add_ticket_photo_constraints"
down_revision = "0002_seed_categories"
branch_labels = None
depends_on = None

PHOTO_SIZE_CHECK_SQL = (
    "photo_size_bytes IS NULL OR "
    "(photo_size_bytes >= 1 AND photo_size_bytes <= 3145728)"
)
PHOTO_MIME_CHECK_SQL = (
    "photo_mime_type IS NULL OR "
    "photo_mime_type IN ('image/jpeg', 'image/png')"
)


def upgrade():
    op.execute(
        "UPDATE tickets SET photo_size_bytes = NULL "
        "WHERE photo_size_bytes IS NOT NULL "
        "AND (photo_size_bytes < 1 OR photo_size_bytes > 3145728)"
    )
    op.execute(
        "UPDATE tickets SET photo_mime_type = NULL "
        "WHERE photo_mime_type IS NOT NULL "
        "AND photo_mime_type NOT IN ('image/jpeg', 'image/png')"
    )
    op.create_check_constraint(
        "ck_tickets_photo_size_bytes",
        "tickets",
        PHOTO_SIZE_CHECK_SQL,
    )
    op.create_check_constraint(
        "ck_tickets_photo_mime_type",
        "tickets",
        PHOTO_MIME_CHECK_SQL,
    )


def downgrade():
    op.drop_constraint(
        "ck_tickets_photo_mime_type",
        "tickets",
        type_="check",
    )
    op.drop_constraint(
        "ck_tickets_photo_size_bytes",
        "tickets",
        type_="check",
    )
