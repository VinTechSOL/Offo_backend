from fastapi import HTTPException, status
from app.modules.staff.permission_map import ROLE_PERMISSIONS

def require_permission(staff, permission: str):
    role = staff.role.role_name

    allowed = ROLE_PERMISSIONS.get(role, set())

    if permission not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied",
        )
