from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, String, Text, Integer, DateTime
from datetime import datetime, timezone
from app.core.database import Base


class StaffRole(Base):
    __tablename__ = "staff_roles"
    __table_args__ = {"schema": "core"}

    role_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # NULL → super admin
    cafe_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    role_name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    staff_members = relationship(
        "Staff",
        back_populates="role",
        lazy="selectin"
    )
