"""Model audit log operasional (FR-09)."""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

# FR-09 mencakup perubahan kategori dan status saja. Mutasi penugasan teknisi
# (TSK-TBD-08) belum diputuskan; kolom ``action`` tetap VARCHAR bebas sehingga
# penambahan nilai di masa depan tidak memerlukan perubahan skema.
AUDIT_ACTIONS = ("category_changed", "status_changed")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Setiap entri audit terikat pada satu tiket (NOT NULL). ON DELETE RESTRICT
    # menjaga audit trail agar tidak hilang saat tiket dihapus.
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # Aktor nullable: entri sistem/tanpa akun tetap tercatat. ON DELETE SET NULL.
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    actor_role: Mapped[str | None] = mapped_column(String(32), nullable=True)

    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String(64), nullable=False)

    old_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    new_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    ticket: Mapped["Ticket"] = relationship(
        "Ticket", back_populates="audit_entries", foreign_keys=[ticket_id]
    )
    actor: Mapped["User | None"] = relationship(
        "User", back_populates="audit_entries", foreign_keys=[actor_user_id]
    )

    def __repr__(self) -> str:  # pragma: no cover - representation only
        return f"<AuditLog id={self.id} ticket_id={self.ticket_id} action={self.action!r}>"


from app.models.ticket import Ticket  # noqa: E402,F401
from app.models.user import User  # noqa: E402,F401
