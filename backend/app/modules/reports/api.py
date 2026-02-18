from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.modules.reports.service import ReportsService
from app.core.security import get_current_staff

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/overview")
def get_overview(
    db: Session = Depends(get_db),
    staff = Depends(get_current_staff),
):
    if not staff.branch_id:
        raise HTTPException(403, "Staff not assigned to branch")

    return ReportsService.get_overview(db, staff.branch_id)


@router.get("/menu-performance")
def get_menu_performance(
    db: Session = Depends(get_db),
    staff = Depends(get_current_staff),
):
    if not staff.branch_id:
        raise HTTPException(403, "Staff not assigned to branch")

    return ReportsService.get_menu_performance(db, staff.branch_id)


@router.get("/customer-insights")
def get_customer_insights(
    db: Session = Depends(get_db),
    staff = Depends(get_current_staff),
):
    if not staff.branch_id:
        raise HTTPException(403, "Staff not assigned to branch")

    return ReportsService.get_customer_insights(db, staff.branch_id)
