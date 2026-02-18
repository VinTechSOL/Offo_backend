from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.modules.crm.service import CrmService
from app.core.security import get_current_staff

router = APIRouter(prefix="/crm", tags=["CRM"])


@router.get("/customers")
def get_customers(
    db: Session = Depends(get_db),
    staff = Depends(get_current_staff),
):
    if not staff.branch_id:
        raise HTTPException(403, "Staff not assigned to branch")

    return CrmService.get_customers(db, staff.branch_id)
