from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import BigInteger, String, Boolean, Numeric, TIMESTAMP,ForeignKey,UniqueConstraint,Index
from sqlalchemy.sql import func
from app.core.database import Base

class MenuCategory(Base):
    __tablename__ = "menu_categories"
    __table_args__ = (UniqueConstraint(
            "branch_id",
            "category_name",
            name="uq_menu_category_branch_name",
        ),
        {"schema": "catalog"},
    )

    category_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    cafe_id: Mapped[int] = mapped_column(BigInteger)
    branch_id: Mapped[int] = mapped_column(BigInteger)
    parent_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    category_name: Mapped[str] = mapped_column(String, nullable=False)
    category_description: Mapped[str | None]
    category_image: Mapped[str | None]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[str] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )


class MenuItem(Base):
    __tablename__ = "menu_items"
    __table_args__ = {"schema": "catalog"}

    item_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    item_name: Mapped[str] = mapped_column(String, nullable=False)
    item_description: Mapped[str | None]
    item_type_id: Mapped[int] = mapped_column(BigInteger,ForeignKey("catalog.item_types.item_type_id"),nullable=False)
    image_url: Mapped[str | None]
    created_at: Mapped[str] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )


class BranchMenuItem(Base):
    __tablename__ = "branch_menu_items"
    __table_args__ = (UniqueConstraint(
            "branch_id",
            "item_id",
            name="uq_branch_item"
        ),
        Index("ix_branch_menu_items_branch_id","branch_id"),
        
        {"schema": "catalog"} )

    branch_menu_item_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    branch_id: Mapped[int] = mapped_column(BigInteger)
    item_id: Mapped[int] = mapped_column(BigInteger)
    category_id: Mapped[int] = mapped_column(BigInteger)
    price: Mapped[float] = mapped_column(Numeric(10, 2))
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[str] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

class ItemType(Base):
    __tablename__ = "item_types"
    __table_args__ = {"schema": "catalog"}

    item_type_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False,unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean,default=True)


