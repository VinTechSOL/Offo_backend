from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Boolean, ForeignKey, DateTime,BigInteger
from datetime import datetime, timezone
from app.core.database import Base


class Staff(Base):
    __tablename__ = "staff"
    __table_args__ = {"schema": "core"}

    staff_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))

    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    role_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("core.staff_roles.role_id"),nullable=False
    )

    branch_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    role = relationship(
        "StaffRole",
        back_populates="staff_members",
        lazy="joined"
    )
