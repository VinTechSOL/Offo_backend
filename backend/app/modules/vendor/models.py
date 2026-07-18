from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import BigInteger, String, Boolean, TIMESTAMP,ForeignKey, Float, Text
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

    cafe_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("core.cafeteria.cafe_id"),
        nullable=False,
    )

    # ---------------- Basic ----------------

    branch_name: Mapped[str]

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
    )

    opens_at: Mapped[time] = mapped_column(nullable=False)
    closes_at: Mapped[time] = mapped_column(nullable=False)

    image_url: Mapped[str | None]

    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)

    # ---------------- Business ----------------

    registered_address: Mapped[str | None] = mapped_column(Text)

    business_address: Mapped[str | None] = mapped_column(Text)

    business_type: Mapped[str | None] = mapped_column(String(50))

    fssai_license_number: Mapped[str | None] = mapped_column(String(100))

    fssai_license_document_url: Mapped[str | None]

    gst_registration_number: Mapped[str | None] = mapped_column(String(100))

    gst_registration_document_url: Mapped[str | None]

    # ---------------- Bank ----------------

    bank_account_number: Mapped[str | None] = mapped_column(String(50))

    ifsc_code: Mapped[str | None] = mapped_column(String(30))

    account_holder_name: Mapped[str | None] = mapped_column(String(150))

    bank_passbook_url: Mapped[str | None]

    # ---------------- Owner ----------------

    registered_owner_name: Mapped[str | None] = mapped_column(String(150))

    owner_phone_number: Mapped[str | None] = mapped_column(String(20))

    owner_email: Mapped[str | None] = mapped_column(String(255))

    owner_proof_document_url: Mapped[str | None]

    # ---------------- Status ----------------

    is_active: Mapped[bool]




class BranchDocument(Base):
    __tablename__ = "branch_documents"
    __table_args__ = {"schema": "core"}

    document_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    branch_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("core.cafe_branch.branch_id", ondelete="CASCADE"),
        nullable=False,
    )

    document_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    document_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[str] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
    )
