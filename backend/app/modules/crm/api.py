from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.modules.crm.service import CrmService
from app.core.security import get_current_staff

router = APIRouter(prefix="/crm", tags=["CRM"])


@router.get("/customers")
def get_customers(
    db: Session = Depends(get_db),
    staff=Depends(get_current_staff),
):
    if not getattr(staff, "branch_id", None):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff not assigned to branch",
        )

    return CrmService.get_customers(db, staff.branch_id)


@router.get("/customers/{customer_id}/orders")
def get_customer_orders(
    customer_id: int,
    db: Session = Depends(get_db),
    staff=Depends(get_current_staff),
):
    if not getattr(staff, "branch_id", None):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff not assigned to branch",
        )

    return CrmService.get_customer_orders(db, staff.branch_id, customer_id)