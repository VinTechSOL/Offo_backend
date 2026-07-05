from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_staff
from app.modules.reports.service import ReportsService


router = APIRouter(
    prefix="/reports",
    tags=["Reports"]
)


@router.get("/overview")
def get_overview(
    filter_by: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db),
    staff = Depends(get_current_staff),
):

    if not staff.branch_id:
        raise HTTPException(
            403,
            "Staff not assigned to branch"
        )

    return ReportsService.get_overview(
        db=db,
        branch_id=staff.branch_id,
        filter_by=filter_by,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/menu-performance")
def get_menu_performance(
    filter_by: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db),
    staff = Depends(get_current_staff),
):

    if not staff.branch_id:
        raise HTTPException(
            403,
            "Staff not assigned to branch"
        )

    return ReportsService.get_menu_performance(
        db=db,
        branch_id=staff.branch_id,
        filter_by=filter_by,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/customer-insights")
def get_customer_insights(
    filter_by: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db),
    staff = Depends(get_current_staff),
):

    if not staff.branch_id:
        raise HTTPException(
            403,
            "Staff not assigned to branch"
        )

    return ReportsService.get_customer_insights(
        db=db,
        branch_id=staff.branch_id,
        filter_by=filter_by,
        start_date=start_date,
        end_date=end_date,
    )