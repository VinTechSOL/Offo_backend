from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import BigInteger, String, Boolean, TIMESTAMP,ForeignKey
from datetime import time
from sqlalchemy.sql import func
from app.core.database import Base

class Cafeteria(Base):
    __tablename__ = "cafeteria"
    __table_args__ = {"schema": "core"}

    cafe_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    cafe_name: Mapped[str] = mapped_column(String, nullable=False)
    phone_number: Mapped[str] = mapped_column(String, nullable=False)
    email_id: Mapped[str | None]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[str] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )


class CafeBranch(Base):
    __tablename__ = "cafe_branch"
    __table_args__ = {"schema": "core"}

    branch_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    cafe_id: Mapped[int] = mapped_column(BigInteger)
    branch_name: Mapped[str]

    city_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("locations.cities.city_id"), nullable=False
    )
    campus_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("locations.campuses.campus_id"), nullable=False
    )
    building_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("locations.buildings.building_id")
    )

    opens_at: Mapped[time] = mapped_column(nullable=False)
    closes_at: Mapped[time] = mapped_column(nullable=False)

    image_url: Mapped[str | None]

    latitude: Mapped[float | None]
    longitude: Mapped[float | None]

    is_active: Mapped[bool]
