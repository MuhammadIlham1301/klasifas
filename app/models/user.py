"""Model pengguna internal dan peran RBAC."""
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

# Peran resmi. Akun reporter dibuat melalui CLI lokal, bukan registrasi publik.
# Baris reporter lama boleh tanpa password hash, tetapi login reporter
# mewajibkan hash yang valid.
USER_ROLES = ("reporter", "admin_sarpras", "teknisi", "pimpinan")

ROLE_CHECK_SQL = (
    "role IN ('reporter', 'admin_sarpras', 'teknisi', 'pimpinan')"
)
PASSWORD_CHECK_SQL = "role = 'reporter' OR password_hash IS NOT NULL"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)

    # Reporter boleh tanpa password; staf wajib memiliki hash (ditegakkan CHECK).
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    role: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true", index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    assigned_tickets: Mapped[list] = relationship(
        "Ticket",
        back_populates="assigned_technician",
        foreign_keys="Ticket.assigned_technician_id",
    )
    reported_tickets: Mapped[list] = relationship(
        "Ticket",
        back_populates="reporter",
        foreign_keys="Ticket.reporter_id",
    )
    audit_entries: Mapped[list] = relationship(
        "AuditLog", back_populates="actor", foreign_keys="AuditLog.actor_user_id"
    )

    __table_args__ = (
        CheckConstraint(ROLE_CHECK_SQL, name="ck_users_role"),
        CheckConstraint(PASSWORD_CHECK_SQL, name="ck_users_password_hash"),
    )

    def __repr__(self) -> str:  # pragma: no cover - representation only
        return f"<User id={self.id} username={self.username!r} role={self.role!r}>"
