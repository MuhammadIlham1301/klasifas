"""seed kategori K1-K7

Revision ID: 0002_seed_categories
Revises: 0001_initial_schema
Create Date: 2026-11-02

Data migration self-contained: literal statis tanpa impor model aplikasi.
ID kategori dikunci 1..7; sequence ``categories_id_seq`` disinkronkan setelah
insert agar insert berikutnya tidak bentrok.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_seed_categories"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


CATEGORY_ROWS = [
    {
        "id": 1,
        "code": "K1",
        "name": "Ruang kelas dan perabot",
        "responsible_unit": "Sarana-prasarana",
        "description": (
            "Kursi kuliah, meja, papan tulis, proyektor kelas, "
            "kebersihan kelas."
        ),
    },
    {
        "id": 2,
        "code": "K2",
        "name": "Laboratorium dan perangkat",
        "responsible_unit": "Pengelola Lab / Unit TI",
        "description": (
            "Komputer laboratorium, perangkat keras praktikum, software lab."
        ),
    },
    {
        "id": 3,
        "code": "K3",
        "name": "Jaringan dan internet",
        "responsible_unit": "Unit TI",
        "description": (
            "Akses Wi-Fi lambat/putus, kendala login portal internet kampus."
        ),
    },
    {
        "id": 4,
        "code": "K4",
        "name": "Kebersihan dan sanitasi",
        "responsible_unit": "Kebersihan / Sarpras",
        "description": (
            "Toilet kotor/rusak, air bersih tidak mengalir, tempat sampah penuh."
        ),
    },
    {
        "id": 5,
        "code": "K5",
        "name": "Listrik, AC, dan penerangan",
        "responsible_unit": "Sarana-prasarana",
        "description": (
            "AC tidak dingin/bocor/mati, lampu padam, "
            "saklar atau stop kontak rusak."
        ),
    },
    {
        "id": 6,
        "code": "K6",
        "name": "Keamanan, parkir, dan akses",
        "responsible_unit": "Keamanan / Bagian Umum",
        "description": (
            "Area parkir kendaraan, pintu gerbang, lift gedung, "
            "fasilitas keamanan."
        ),
    },
    {
        "id": 7,
        "code": "K7",
        "name": "Lainnya",
        "responsible_unit": "Admin Sarpras",
        "description": (
            "Keluhan fasilitas di luar enam kategori di atas "
            "(memerlukan tinjauan manual)."
        ),
    },
]


def _categories_table():
    return sa.table(
        "categories",
        sa.column("id", sa.BigInteger()),
        sa.column("code", sa.String(length=2)),
        sa.column("name", sa.String(length=100)),
        sa.column("description", sa.Text()),
        sa.column("responsible_unit", sa.String(length=100)),
        sa.column("is_active", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )


def upgrade():
    table = _categories_table()
    op.bulk_insert(table, CATEGORY_ROWS)

    # BIGSERIAL: sinkronkan sequence ke MAX(id) agar insert berikutnya aman.
    op.execute(
        "SELECT setval(pg_get_serial_sequence('categories', 'id'), "
        "(SELECT MAX(id) FROM categories))"
    )


def downgrade():
    op.execute("DELETE FROM categories WHERE code IN "
               "('K1', 'K2', 'K3', 'K4', 'K5', 'K6', 'K7')")
