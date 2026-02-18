from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, String, ForeignKey, Float,DateTime
from app.core.database import Base
from datetime import datetime,timezone


class City(Base):
    __tablename__ = "cities"
    __table_args__ = {"schema": "locations"}

    city_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    city_name: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    campuses = relationship("Campus", back_populates="city")


class Campus(Base):
    __tablename__ = "campuses"
    __table_args__ = {"schema": "locations"}

    campus_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    city_id: Mapped[int] = mapped_column(
        ForeignKey("locations.cities.city_id"), nullable=False
    )
    campus_name: Mapped[str] = mapped_column(String, nullable=False)

    city = relationship("City", back_populates="campuses")
    buildings = relationship("Building", back_populates="campus")


class Building(Base):
    __tablename__ = "buildings"
    __table_args__ = {"schema": "locations"}

    building_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    campus_id: Mapped[int] = mapped_column(
        ForeignKey("locations.campuses.campus_id"), nullable=False
    )
    building_name: Mapped[str] = mapped_column(String, nullable=False)

    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)

    campus = relationship("Campus", back_populates="buildings")


class UserContext(Base):
    __tablename__ = "user_context"
    __table_args__ = {"schema": "core"}

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("core.users.user_id", ondelete="CASCADE"),
        primary_key=True,
    )

    city_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("locations.cities.city_id"),
        nullable=False,
    )

    campus_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("locations.campuses.campus_id"),
        nullable=False,
    )

    building_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("locations.buildings.building_id"),
        nullable=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )