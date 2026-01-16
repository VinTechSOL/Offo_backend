from sqlalchemy.orm import Session
from sqlalchemy import select
from .models import Permission, RolePermission

class PermissionRepository:

    @staticmethod
    def create_permission(db: Session, permission: Permission):
        db.add(permission)
        db.commit()
        db.refresh(permission)
        return permission

    @staticmethod
    def assign_permission(db: Session, role_id: int, permission_id: int):
        rp = RolePermission(role_id=role_id, permission_id=permission_id)
        db.add(rp)
        db.commit()
