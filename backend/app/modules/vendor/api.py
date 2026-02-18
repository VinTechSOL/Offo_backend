from fastapi import APIRouter, Depends,HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user,get_current_staff
from app.modules.vendor.schemas import CafeteriaCreate, CafeBranchCreate
from app.modules.vendor.service import VendorService,CafeService
from app.modules.vendor.schemas import CafeForUserResponse
from app.modules.vendor.models import CafeBranch,Cafeteria


router = APIRouter(prefix="/vendors", tags=["Vendors"])

@router.post("/cafeterias")
def create_cafeteria(
    data: CafeteriaCreate,
    db: Session = Depends(get_db)
):
    return VendorService.create_cafeteria(db, data)

@router.get("/cafeterias")
def list_cafeterias(db: Session = Depends(get_db)):
    return VendorService.list_cafeterias(db)

@router.post("/branches")
def create_branch(
    data: CafeBranchCreate,
    db: Session = Depends(get_db)
):
    return VendorService.create_branch(db, data)

@router.get("/cafeterias/{cafe_id}/branches")
def list_branches(
    cafe_id: int,
    db: Session = Depends(get_db)
):
    return VendorService.list_branches(db, cafe_id)

@router.get("/settings/profile")
def get_profile(
    db: Session = Depends(get_db),
    staff = Depends(get_current_staff),
):
    if not staff.branch_id:
        raise HTTPException(403, "Staff not assigned to branch")

    branch = db.get(CafeBranch, staff.branch_id)

    if not branch:
        raise HTTPException(404, "Branch not found")

    cafe = db.get(Cafeteria, branch.cafe_id)

    if not cafe:
        raise HTTPException(404, "Cafe not found")

    return {
        "cafe_name": cafe.cafe_name,
        "branch_name": branch.branch_name,
        "phone_number": cafe.phone_number,
    }



@router.get("/cafes/for-user", response_model=list[CafeForUserResponse],)
def cafes_for_user(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return CafeService.get_for_user(db, user.user_id)

