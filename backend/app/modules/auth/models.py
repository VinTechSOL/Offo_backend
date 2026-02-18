from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, DateTime
from datetime import datetime, timezone
from app.core.database import Base

class SignupSession(Base):
    __tablename__ = "signup_sessions"
    __table_args__ = {"schema": "core"}  

    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(15), nullable=False)

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)

    otp: Mapped[str] = mapped_column(String(6), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)

    expires_at: Mapped[datetime]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
