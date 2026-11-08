"""Model tiket keluhan fasilitas (FR-01, FR-02, FR-04-FR-06)."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

TICKET_STATUSES = ("Baru", "Terverifikasi", "Diproses", "Selesai")

TICKET_CODE_CHECK_SQL = r"ticket_code ~ '^KF-[23456789A-HJ-NP-Z]{6}$'"
STATUS_CHECK_SQL = "status IN ('Baru', 'Terverifikasi', 'Diproses', 'Selesai')"
CONFIDENCE_CHECK_SQL = (
    "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)"
)
BUILDING_CHECK_SQL = "building_name = 'Gedung FTII'"
FLOOR_CHECK_SQL = "floor_number BETWEEN 1 AND 4"
DESCRIPTION_LENGTH_CHECK_SQL = "char_length(description) <= 2000"


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    ticket_code: Mapped[str] = mapped_column(String(9), nullable=False, unique=True)
    access_token_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )

    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Kategori pelapor (opsional) - FK ON DELETE RESTRICT.
    reporter_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reporter_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reporter_contact: Mapped[str | None] = mapped_column(String(120), nullable=True)

    reporter_category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    predicted_category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    official_category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    confidence_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4), nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="Baru", server_default="Baru", index=True
    )

    assigned_technician_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    building_name: Mapped[str] = mapped_column(String(100), nullable=False)
    floor_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    room_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location_detail: Mapped[str | None] = mapped_column(String(255), nullable=True)

    needs_manual_verification: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )

    photo_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    photo_mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    photo_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    photo_uploaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    reporter: Mapped["User | None"] = relationship(
        "User", back_populates="reported_tickets", foreign_keys=[reporter_id]
    )
    assigned_technician: Mapped["User | None"] = relationship(
        "User", back_populates="assigned_tickets", foreign_keys=[assigned_technician_id]
    )
    reporter_category: Mapped["Category | None"] = relationship(
        "Category",
        back_populates="reporter_chosen_tickets",
        foreign_keys=[reporter_category_id],
    )
    predicted_category: Mapped["Category | None"] = relationship(
        "Category",
        back_populates="predicted_tickets",
        foreign_keys=[predicted_category_id],
    )
    official_category: Mapped["Category | None"] = relationship(
        "Category",
        back_populates="official_tickets",
        foreign_keys=[official_category_id],
    )

    # Tanpa cascade delete: audit trail TIDAK boleh ikut terhapus bersama tiket.
    audit_entries: Mapped[list] = relationship(
        "AuditLog", back_populates="ticket", foreign_keys="AuditLog.ticket_id"
    )

    __table_args__ = (
        CheckConstraint(TICKET_CODE_CHECK_SQL, name="ck_tickets_ticket_code"),
        CheckConstraint(STATUS_CHECK_SQL, name="ck_tickets_status"),
        CheckConstraint(CONFIDENCE_CHECK_SQL, name="ck_tickets_confidence_score"),
        CheckConstraint(BUILDING_CHECK_SQL, name="ck_tickets_building_name"),
        CheckConstraint(FLOOR_CHECK_SQL, name="ck_tickets_floor_number"),
        CheckConstraint(
            DESCRIPTION_LENGTH_CHECK_SQL, name="ck_tickets_description_length"
        ),
        Index(
            "ix_tickets_building_name_floor_number",
            "building_name",
            "floor_number",
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover - representation only
        return f"<Ticket id={self.id} code={self.ticket_code!r} status={self.status!r}>"


# Impor di akhir untuk memastikan resolusi string relationship pada type hint.
from app.models.user import User  # noqa: E402,F401
from app.models.category import Category  # noqa: E402,F401
