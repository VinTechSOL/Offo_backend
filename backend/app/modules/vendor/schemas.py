from datetime import time
from pydantic import BaseModel, EmailStr


# =========================================================
# CAFETERIA
# =========================================================

class CafeteriaCreate(BaseModel):
    cafe_name: str
    phone_number: str
    email_id: EmailStr | None = None


# =========================================================
# CREATE BRANCH
# =========================================================

class CafeBranchCreate(BaseModel):

    # ---------- Basic ----------
    cafe_id: int

    branch_name: str

    city_id: int
    campus_id: int
    building_id: int | None = None

    opens_at: time
    closes_at: time

    latitude: float | None = None
    longitude: float | None = None

    image_url: str | None = None

    # ---------- Business ----------

    registered_address: str | None = None

    business_address: str | None = None

    business_type: str | None = None

    fssai_license_number: str | None = None

    fssai_license_document_url: str | None = None

    gst_registration_number: str | None = None

    gst_registration_document_url: str | None = None

    # ---------- Bank ----------

    bank_account_number: str | None = None

    ifsc_code: str | None = None

    account_holder_name: str | None = None

    bank_passbook_url: str | None = None

    # ---------- Owner ----------

    registered_owner_name: str | None = None

    owner_phone_number: str | None = None

    owner_email: EmailStr | None = None

    owner_proof_document_url: str | None = None

    # ---------- Status ----------

    is_active: bool = True


# =========================================================
# UPDATE BRANCH
# =========================================================

class UpdateBranchRequest(BaseModel):

    # ---------- Basic ----------

    branch_name: str | None = None

    city_id: int | None = None
    campus_id: int | None = None
    building_id: int | None = None

    opens_at: time | None = None
    closes_at: time | None = None

    latitude: float | None = None
    longitude: float | None = None

    image_url: str | None = None

    # ---------- Business ----------

    registered_address: str | None = None
    business_address: str | None = None
    business_type: str | None = None

    # ---------- Compliance ----------

    fssai_license_number: str | None = None
    fssai_license_document_url: str | None = None

    gst_registration_number: str | None = None
    gst_registration_document_url: str | None = None

    # ---------- Bank ----------

    bank_account_number: str | None = None
    ifsc_code: str | None = None
    account_holder_name: str | None = None
    bank_passbook_url: str | None = None

    # ---------- Owner ----------

    registered_owner_name: str | None = None
    owner_phone_number: str | None = None
    owner_email: EmailStr | None = None
    owner_proof_document_url: str | None = None

    # ---------- Status ----------

    is_active: bool | None = None

class BranchDocumentResponse(BaseModel):
    document_id: int
    document_name: str
    document_url: str

    class Config:
        from_attributes = True


class BranchDetailsResponse(BaseModel):
    branch_id: int
    cafe_id: int

    branch_name: str

    city_id: int
    city_name: str | None = None

    campus_id: int
    campus_name: str | None = None

    building_id: int | None = None
    building_name: str | None = None

    opens_at: time
    closes_at: time

    image_url: str | None = None

    latitude: float | None = None
    longitude: float | None = None

    registered_address: str | None = None
    business_address: str | None = None
    business_type: str | None = None

    fssai_license_number: str | None = None
    fssai_license_document_url: str | None = None

    gst_registration_number: str | None = None
    gst_registration_document_url: str | None = None

    bank_account_number: str | None = None
    ifsc_code: str | None = None
    account_holder_name: str | None = None
    bank_passbook_url: str | None = None

    registered_owner_name: str | None = None
    owner_phone_number: str | None = None
    owner_email: EmailStr | None = None
    owner_proof_document_url: str | None = None

    is_active: bool

    documents: list[BranchDocumentResponse] = []


# =========================================================
# UPDATE STATUS
# =========================================================

class UpdateBranchStatusRequest(BaseModel):
    is_active: bool


# =========================================================
# USER CAFE RESPONSE
# =========================================================

class CafeForUserResponse(BaseModel):
    branch_id: int
    branch_name: str
    image_url: str | None
    building_name: str | None
    campus_name: str
    city_name: str
    opens_at: time
    closes_at: time
    is_open: bool

    class Config:
        from_attributes = True