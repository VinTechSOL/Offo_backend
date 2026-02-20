from fastapi import APIRouter, Depends,HTTPException,File,UploadFile,Form
from datetime import time
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user,get_current_staff
from app.modules.vendor.schemas import CafeteriaCreate, CafeBranchCreate
from app.modules.vendor.service import VendorService,CafeService
from app.modules.vendor.schemas import CafeForUserResponse
from app.modules.vendor.models import CafeBranch,Cafeteria
from app.core.s3_service import upload_image
import uuid

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
    cafe_id: int = Form(...),
    branch_name: str = Form(...),
    city_id: int = Form(...),
    campus_id: int = Form(...),
    building_id: int = Form(None),
    opens_at: time = Form(...),
    closes_at: time = Form(...),
    is_active: bool = Form(True),
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    image_url = None

    if image:
        ext = image.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{ext}"

        image_url = upload_image(
            file_obj=image.file,
            filename=filename,
            content_type=image.content_type,
            folder="cafe"   # 🔥 IMPORTANT
        )

    branch = CafeBranch(
        cafe_id=cafe_id,
        branch_name=branch_name,
        city_id=city_id,
        campus_id=campus_id,
        building_id=building_id,
        opens_at=opens_at,
        closes_at=closes_at,
        is_active=is_active,
        image_url=image_url,
    )

    db.add(branch)
    db.commit()
    db.refresh(branch)

    return branch

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

