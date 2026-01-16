from fastapi import Depends, HTTPException, status
from app.core.security import get_current_staff

def require_roles(*allowed_roles: str):
    def checker(staff = Depends(get_current_staff)):
        role_name = staff.role.role_name

        if role_name not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return staff
    return checker
