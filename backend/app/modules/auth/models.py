from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    BigInteger,
    String,
    Boolean,
    DateTime,
    ForeignKey,
)
from datetime import datetime, timezone

from app.core.database import Base


class SignupSession(Base):
    __tablename__ = "signup_sessions"
    __table_args__ = {"schema": "core"}

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    phone: Mapped[str] = mapped_column(
        String(15),
        nullable=False,
    )

    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    otp: Mapped[str] = mapped_column(
        String(6),
        nullable=False,
    )

    verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class RefreshSession(Base):
    __tablename__ = "refresh_sessions"
    __table_args__ = {"schema": "core"}

    session_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "core.users.user_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # SHA-256 hash of the refresh token.
    # The raw refresh token is NEVER stored in the database.
    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )