from datetime import datetime, timedelta, timezone
from jose import jwt
from app.core.config import settings
from sqlalchemy import select
from app.modules.staff.models import Staff
from app.modules.staff_roles.models import StaffRole
from app.modules.permissions.models import Permission
from app.core.database import SessionLocal


def create_staff_jwt(staff: Staff) -> str:
    db = SessionLocal()

    permissions = db.execute(
        select(Permission.permission_code)
        .join_from(Permission, StaffRole, Permission.permission_id == Permission.permission_id)
    ).scalars().all()

    payload = {
        "staff_id": staff.staff_id,
        "role_id": staff.role_id,
        "branch_id": staff.branch_id,
        "permissions": permissions,
        "exp": datetime.now(timezone.utc) + timedelta(hours=8),
        "iat": datetime.now(timezone.utc),
        "type": "STAFF"
    }

    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)