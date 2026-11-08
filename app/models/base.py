"""
Base deklaratif SQLAlchemy 2.0 untuk seluruh model KlasiFas.

Naming convention memakai nama constraint eksplisit untuk CHECK (tanpa token
``ck`` pada MetaData) guna menghindari double-prefix. Constraint yang perlu nama
spesifik selalu dideklarasikan dengan ``name=`` eksplisit pada model.
"""
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Naming convention untuk PK/FK/UQ/IX. Token ``ck`` sengaja dihilangkan;
# nama CHECK ditulis eksplisit pada setiap model.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base deklaratif dengan metadata bernaming convention terpusat."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
