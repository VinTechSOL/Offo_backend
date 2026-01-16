from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import BigInteger, String, Text, ForeignKey
from app.core.database import Base

class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = {"schema": "core"}

    permission_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    permission_code: Mapped[str] = mapped_column(String(50), unique=True)
    description: Mapped[str | None] = mapped_column(Text)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = {"schema": "core"}

    role_id = mapped_column(
        ForeignKey("core.staff_roles.role_id"),
        primary_key=True
    )
    permission_id = mapped_column(
        ForeignKey("core.permissions.permission_id"),
        primary_key=True
    )
