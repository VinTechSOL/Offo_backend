from fastapi import APIRouter, Depends,HTTPException,File,UploadFile,Form
from datetime import time
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user,get_current_staff
from app.modules.vendor.schemas import CafeteriaCreate, CafeBranchCreate, UpdateBranchRequest
from app.modules.vendor.service import VendorService,CafeService
from app.modules.vendor.schemas import CafeForUserResponse,UpdateBranchStatusRequest
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
    # ---------------- Basic ----------------
    cafe_id: int = Form(...),
    branch_name: str = Form(...),

    city_id: int = Form(...),
    campus_id: int = Form(...),
    building_id: int | None = Form(None),

    opens_at: time = Form(...),
    closes_at: time = Form(...),

    latitude: float | None = Form(None),
    longitude: float | None = Form(None),

    # ---------------- Business ----------------
    registered_address: str | None = Form(None),
    business_address: str | None = Form(None),
    business_type: str | None = Form(None),

    fssai_license_number: str | None = Form(None),
    gst_registration_number: str | None = Form(None),

    # ---------------- Bank ----------------
    bank_account_number: str | None = Form(None),
    ifsc_code: str | None = Form(None),
    account_holder_name: str | None = Form(None),

    # ---------------- Owner ----------------
    registered_owner_name: str | None = Form(None),
    owner_phone_number: str | None = Form(None),
    owner_email: str | None = Form(None),

    # ---------------- Status ----------------
    is_active: bool = Form(True),

    # ---------------- Files ----------------
    image: UploadFile | None = File(None),

    fssai_document: UploadFile | None = File(None),
    gst_document: UploadFile | None = File(None),
    owner_document: UploadFile | None = File(None),
    bank_passbook: UploadFile | None = File(None),

    other_documents: list[UploadFile] | None = File(None),

    db: Session = Depends(get_db),
):
    payload = CafeBranchCreate(
        cafe_id=cafe_id,
        branch_name=branch_name,

        city_id=city_id,
        campus_id=campus_id,
        building_id=building_id,

        opens_at=opens_at,
        closes_at=closes_at,

        latitude=latitude,
        longitude=longitude,

        registered_address=registered_address,
        business_address=business_address,
        business_type=business_type,

        fssai_license_number=fssai_license_number,
        gst_registration_number=gst_registration_number,

        bank_account_number=bank_account_number,
        ifsc_code=ifsc_code,
        account_holder_name=account_holder_name,

        registered_owner_name=registered_owner_name,
        owner_phone_number=owner_phone_number,
        owner_email=owner_email,

        is_active=is_active,
    )

    return VendorService.create_branch(
        db=db,
        data=payload,
        image=image,
        fssai_document=fssai_document,
        gst_document=gst_document,
        owner_document=owner_document,
        bank_passbook=bank_passbook,
        other_documents=other_documents,
    )

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
        "cafe_image": branch.image_url,
        "opens_at": branch.opens_at,
        "closes_at": branch.closes_at,
        "is_active": branch.is_active
    }

@router.patch("/settings/status")
def update_branch_status(
    payload: UpdateBranchStatusRequest,
    db: Session = Depends(get_db),
    staff = Depends(get_current_staff),
):
    if not staff.branch_id:
        raise HTTPException(status_code=403, detail="Staff not assigned to branch")

    branch = db.get(CafeBranch, staff.branch_id)

    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    # Update branch status
    branch.is_active = payload.is_active

    db.commit()
    db.refresh(branch)

    return {
        "message": "Branch status updated successfully",
        "is_active": branch.is_active
    }


@router.get("/cafes/for-user", response_model=list[CafeForUserResponse],)
def cafes_for_user(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return CafeService.get_for_user(db, user.user_id)


@router.get("/branches/{branch_id}")
def get_branch(
    branch_id: int,
    db: Session = Depends(get_db),
    staff=Depends(get_current_staff),
):
    if staff.role.role_name != "SUPER_ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Access denied",
        )

    return VendorService.get_branch_by_id(
        db=db,
        branch_id=branch_id,
    )


@router.patch("/branches/{branch_id}")
def update_branch(
    branch_id: int,

    # ---------------- Basic ----------------
    branch_name: str = Form(...),

    city_id: int = Form(...),
    campus_id: int = Form(...),
    building_id: int | None = Form(None),

    opens_at: time = Form(...),
    closes_at: time = Form(...),

    latitude: float | None = Form(None),
    longitude: float | None = Form(None),

    # ---------------- Business ----------------
    registered_address: str | None = Form(None),
    business_address: str | None = Form(None),
    business_type: str | None = Form(None),

    # ---------------- Compliance ----------------
    fssai_license_number: str | None = Form(None),
    gst_registration_number: str |None = Form(None),

    # ---------------- Bank ----------------
    bank_account_number: str | None = Form(None),
    ifsc_code: str | None = Form(None),
    account_holder_name: str | None = Form(None),

    # ---------------- Owner ----------------
    registered_owner_name: str | None = Form(None),
    owner_phone_number: str | None = Form(None),
    owner_email: str | None = Form(None),

    # ---------------- Status ----------------
    is_active: bool = Form(True),

    # ---------------- Files ----------------
    image: UploadFile | None = File(None),

    fssai_document: UploadFile | None = File(None),
    gst_document: UploadFile | None = File(None),
    owner_document: UploadFile | None = File(None),
    bank_passbook: UploadFile |None = File(None),

    other_documents: list[UploadFile] | None = File(None),

    db: Session = Depends(get_db),
    staff=Depends(get_current_staff),
):

    if staff.role.role_name != "SUPER_ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Access denied",
        )

    payload = UpdateBranchRequest(
        branch_name=branch_name,

        city_id=city_id,
        campus_id=campus_id,
        building_id=building_id,

        opens_at=opens_at,
        closes_at=closes_at,

        latitude=latitude,
        longitude=longitude,

        registered_address=registered_address,
        business_address=business_address,
        business_type=business_type,

        fssai_license_number=fssai_license_number,
        gst_registration_number=gst_registration_number,

        bank_account_number=bank_account_number,
        ifsc_code=ifsc_code,
        account_holder_name=account_holder_name,

        registered_owner_name=registered_owner_name,
        owner_phone_number=owner_phone_number,
        owner_email=owner_email,

        is_active=is_active,
    )

    return VendorService.update_branch(
        db=db,
        branch_id=branch_id,
        data=payload,
        image=image,
        fssai_document=fssai_document,
        gst_document=gst_document,
        owner_document=owner_document,
        bank_passbook=bank_passbook,
        other_documents=other_documents,
    )

@router.patch("/branches/{branch_id}/status")
def update_branch_status(
    branch_id: int,
    payload: UpdateBranchStatusRequest,
    db: Session = Depends(get_db),
    staff=Depends(get_current_staff),
):
    if staff.role.role_name != "SUPER_ADMIN":
        raise HTTPException(403, "Access denied")

    branch = db.get(CafeBranch, branch_id)
    if not branch:
        raise HTTPException(404, "Branch not found")

    branch.is_active = payload.is_active
    db.commit()
    db.refresh(branch)

    return branch

