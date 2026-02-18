from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import BigInteger, String, Boolean, TIMESTAMP,ForeignKey,DateTime
from datetime import datetime,timezone
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "core"}

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    first_name: Mapped[str | None] = mapped_column(String)
    last_name: Mapped[str | None] = mapped_column(String)
    mobile_number: Mapped[str] = mapped_column(String, unique=True)
    is_otp_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[str] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[str] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UserAddress(Base):
    __tablename__ = "user_addresses"
    __table_args__ = {"schema": "core"}

    address_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    address_line_1: Mapped[str | None]
    address_line_2: Mapped[str | None]
    city: Mapped[str | None]
    state: Mapped[str | None]
    country: Mapped[str | None]
    pincode: Mapped[str | None]



