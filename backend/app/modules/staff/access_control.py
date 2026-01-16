from fastapi import HTTPException


def validate_branch_access(staff, branch_id: int):
    role = staff.role.role_name

    if role == "SUPER_ADMIN":
        return

    if role == "VENDOR_ADMIN":
        # Vendor admin works across cafe branches
        return

    if role == "VENDOR":
        if staff.branch_id != branch_id:
            raise HTTPException(403, "Branch access denied")
