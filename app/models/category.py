"""Model referensi tujuh kategori fasilitas (K1-K7)."""
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

CATEGORY_CODES = ("K1", "K2", "K3", "K4", "K5", "K6", "K7")

CODE_CHECK_SQL = "code IN ('K1', 'K2', 'K3', 'K4', 'K5', 'K6', 'K7')"


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    code: Mapped[str] = mapped_column(String(2), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    responsible_unit: Mapped[str | None] = mapped_column(String(100), nullable=True)

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    reporter_chosen_tickets: Mapped[list] = relationship(
        "Ticket",
        back_populates="reporter_category",
        foreign_keys="Ticket.reporter_category_id",
    )
    predicted_tickets: Mapped[list] = relationship(
        "Ticket",
        back_populates="predicted_category",
        foreign_keys="Ticket.predicted_category_id",
    )
    official_tickets: Mapped[list] = relationship(
        "Ticket",
        back_populates="official_category",
        foreign_keys="Ticket.official_category_id",
    )

    __table_args__ = (CheckConstraint(CODE_CHECK_SQL, name="ck_categories_code"),)

    def __repr__(self) -> str:  # pragma: no cover - representation only
        return f"<Category id={self.id} code={self.code!r}>"
