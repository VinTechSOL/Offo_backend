from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    Form,
    HTTPException,
)
from sqlalchemy.orm import Session

from app.core.database import get_db

from app.core.security import (
    get_current_user,
    get_current_staff,
)

from app.modules.support.schemas import (
    TicketCreate,
    TicketResponse,
    TicketDetailResponse,
    TicketMessageCreate,
    TicketMessageResponse,
    TicketStatusUpdate,
    FeedbackCreate,
    FeedbackResponse,
    VendorTicketCreate,
    VendorTicketResponse,
    VendorTicketDetailResponse,
    VendorTicketMessageCreate,
    VendorTicketMessageResponse,
    VendorFeedbackResponse,
    AdminVendorTicketResponse,
    AdminVendorTicketDetailResponse,
    AdminVendorTicketMessageResponse,
)

from app.modules.support.service import (
    SupportService,
)

from app.modules.support.constants import (
    TicketIssueType,
    TicketStatus,
)

from app.core.s3_service import (
    upload_file,
    validate_upload,
    IMAGE_TYPES,
    MAX_IMAGE_SIZE,
    delete_file,
)


router = APIRouter(
    prefix="/support",
    tags=["Support"],
)


# =========================================================
# USER TICKETS
# =========================================================


@router.post(
    "/tickets",
    response_model=TicketResponse,
)
async def create_ticket(
    order_id: int = Form(...),

    order_item_id: int | None = Form(
        default=None,
    ),

    issue_type: TicketIssueType = Form(...),

    description: str = Form(...),

    image: UploadFile | None = File(
        default=None,
    ),

    db: Session = Depends(get_db),

    user=Depends(get_current_user),
):
    image_url: str | None = None

    try:
        # -------------------------------------------------
        # 1. Validate image
        # -------------------------------------------------

        if image:
            validate_upload(
                image,
                allowed_types=IMAGE_TYPES,
                max_size=MAX_IMAGE_SIZE,
            )

        # -------------------------------------------------
        # 2. Prepare ticket data
        # -------------------------------------------------

        data = TicketCreate(
            order_id=order_id,
            order_item_id=order_item_id,
            issue_type=issue_type,
            description=description,
        )

        # -------------------------------------------------
        # 3. Upload image to S3
        # -------------------------------------------------

        if image:
            image_url = upload_file(
                file_obj=image.file,
                filename=image.filename,
                content_type=(
                    image.content_type
                    or "application/octet-stream"
                ),
                folder="support/tickets",
            )

        # -------------------------------------------------
        # 4. Create ticket
        # -------------------------------------------------

        ticket = SupportService.create_ticket(
            db=db,
            user_id=user.user_id,
            data=data,
            image_url=image_url,
        )

        return ticket

    except HTTPException:
        # S3 upload succeeded but ticket creation failed.
        if image_url:
            delete_file(image_url)

        raise

    except Exception:
        # Unexpected DB/S3/application error.
        if image_url:
            delete_file(image_url)

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to raise ticket. "
                "Please try again."
            ),
        )


# =========================================================
# USER - GET TICKETS
# =========================================================


@router.get(
    "/tickets",
)
def get_my_tickets(
    db: Session = Depends(get_db),

    user=Depends(get_current_user),
):
    return SupportService.get_user_tickets(
        db,
        user.user_id,
    )


# =========================================================
# USER - GET SINGLE TICKET
# =========================================================


@router.get(
    "/tickets/{ticket_id}",
    response_model=TicketDetailResponse,
)
def get_my_ticket(
    ticket_id: int,

    db: Session = Depends(get_db),

    user=Depends(get_current_user),
):
    return SupportService.get_user_ticket(
        db,
        user.user_id,
        ticket_id,
    )


# =========================================================
# USER - TICKET MESSAGE
# =========================================================


@router.post(
    "/tickets/{ticket_id}/messages",
    response_model=TicketMessageResponse,
)
def create_user_ticket_message(
    ticket_id: int,

    data: TicketMessageCreate,

    db: Session = Depends(get_db),

    user=Depends(get_current_user),
):
    return SupportService.create_user_ticket_message(
        db=db,
        user_id=user.user_id,
        ticket_id=ticket_id,
        message_text=data.message,
    )


# =========================================================
# USER FEEDBACK
# =========================================================


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
)
def create_feedback(
    data: FeedbackCreate,

    db: Session = Depends(get_db),

    user=Depends(get_current_user),
):
    return SupportService.create_feedback(
        db=db,
        user_id=user.user_id,
        data=data,
    )


@router.get(
    "/feedback",
)
def get_my_feedback(
    db: Session = Depends(get_db),

    user=Depends(get_current_user),
):
    return SupportService.get_user_feedbacks(
        db,
        user.user_id,
    )


# =========================================================
# VENDOR TICKETS
# =========================================================
#
# Vendor can upload ONE image only while creating
# the ticket.
#
# Vendor replies do NOT support image uploads.
# =========================================================


@router.post(
    "/vendor/tickets",
    response_model=VendorTicketResponse,
)
async def create_vendor_ticket(
    category: str = Form(...),

    severity: str = Form(...),

    affected_order_ids: str | None = Form(
        default=None,
    ),

    subject: str = Form(...),

    description: str = Form(...),

    image: UploadFile | None = File(
        default=None,
    ),

    db: Session = Depends(get_db),

    staff=Depends(get_current_staff),
):
    image_url: str | None = None

    try:
        # -------------------------------------------------
        # 1. Validate image
        # -------------------------------------------------

        if image:
            validate_upload(
                image,
                allowed_types=IMAGE_TYPES,
                max_size=MAX_IMAGE_SIZE,
            )

        # -------------------------------------------------
        # 2. Prepare vendor ticket data
        # -------------------------------------------------

        data = VendorTicketCreate(
            category=category,
            severity=severity,
            affected_order_ids=affected_order_ids,
            subject=subject,
            description=description,
        )

        # -------------------------------------------------
        # 3. Upload image to S3
        # -------------------------------------------------

        if image:
            image_url = upload_file(
                file_obj=image.file,
                filename=image.filename,
                content_type=(
                    image.content_type
                    or "application/octet-stream"
                ),
                folder="support/vendor-tickets",
            )

        # -------------------------------------------------
        # 4. Create vendor ticket
        # -------------------------------------------------

        ticket = SupportService.create_vendor_ticket(
            db=db,
            staff=staff,
            data=data,
            image_url=image_url,
        )

        return ticket

    except HTTPException:
        # S3 upload succeeded but ticket creation failed.
        if image_url:
            delete_file(image_url)

        raise

    except Exception as e:
        # Unexpected DB/S3/application error.
        if image_url:
            delete_file(image_url)

        db.rollback()

        print("create vendor ticket", repr(e))

        raise


# =========================================================
# VENDOR - GET TICKETS
# =========================================================


@router.get(
    "/vendor/tickets",
    response_model=list[VendorTicketResponse],
)
def get_vendor_tickets(
    db: Session = Depends(get_db),

    staff=Depends(get_current_staff),
):
    return SupportService.get_vendor_tickets(
        db=db,
        staff=staff,
    )


# =========================================================
# VENDOR - GET SINGLE TICKET
# =========================================================


@router.get(
    "/vendor/tickets/{vendor_ticket_id}",
    response_model=VendorTicketDetailResponse,
)
def get_vendor_ticket(
    vendor_ticket_id: int,

    db: Session = Depends(get_db),

    staff=Depends(get_current_staff),
):
    return SupportService.get_vendor_ticket(
        db=db,
        staff=staff,
        vendor_ticket_id=vendor_ticket_id,
    )


# =========================================================
# VENDOR - REPLY TO TICKET
# =========================================================
#
# IMPORTANT:
# No image field here.
#
# Vendor can upload image ONLY when creating the ticket.
# =========================================================


@router.post(
    "/vendor/tickets/{vendor_ticket_id}/messages",
    response_model=VendorTicketMessageResponse,
)
def create_vendor_ticket_message(
    vendor_ticket_id: int,

    data: VendorTicketMessageCreate,

    db: Session = Depends(get_db),

    staff=Depends(get_current_staff),
):
    return SupportService.create_vendor_ticket_message(
        db=db,
        staff=staff,
        vendor_ticket_id=vendor_ticket_id,
        message_text=data.message,
    )


# =========================================================
# VENDOR FEEDBACK
# =========================================================


@router.get(
    "/vendor/feedback",
    response_model=list[VendorFeedbackResponse],
)
def get_vendor_feedback(
    db: Session = Depends(get_db),

    staff=Depends(get_current_staff),
):
    return SupportService.get_vendor_feedbacks(
        db=db,
        staff=staff,
    )


# =========================================================
# ADMIN - USER TICKETS
# =========================================================


@router.get(
    "/admin/tickets",
)
def get_admin_tickets(
    db: Session = Depends(get_db),

    staff=Depends(get_current_staff),
):
    return SupportService.get_admin_tickets(
        db,
    )


@router.get(
    "/admin/tickets/{ticket_id}",
)
def get_admin_ticket(
    ticket_id: int,

    db: Session = Depends(get_db),

    staff=Depends(get_current_staff),
):
    return SupportService.get_admin_ticket(
        db,
        ticket_id,
    )


# =========================================================
# ADMIN - USER TICKET MESSAGE
# =========================================================


@router.post(
    "/admin/tickets/{ticket_id}/messages",
    response_model=TicketMessageResponse,
)
def create_admin_ticket_message(
    ticket_id: int,

    data: TicketMessageCreate,

    db: Session = Depends(get_db),

    staff=Depends(get_current_staff),
):
    return SupportService.create_admin_ticket_message(
        db=db,
        staff=staff,
        ticket_id=ticket_id,
        message_text=data.message,
    )


# =========================================================
# ADMIN - UPDATE USER TICKET STATUS
# =========================================================


@router.patch(
    "/admin/tickets/{ticket_id}/status",
)
def update_ticket_status(
    ticket_id: int,

    data: TicketStatusUpdate,

    db: Session = Depends(get_db),

    staff=Depends(get_current_staff),
):
    return SupportService.update_ticket_status(
        db=db,
        ticket_id=ticket_id,
        status=data.status,
    )


# =========================================================
# ADMIN - VENDOR TICKETS
# =========================================================


@router.get(
    "/admin/vendor-tickets",
    response_model=list[AdminVendorTicketResponse],
)
def get_admin_vendor_tickets(
    db: Session = Depends(get_db),

    staff=Depends(get_current_staff),
):
    return SupportService.get_admin_vendor_tickets(
        db=db,
        staff=staff,
    )


# =========================================================
# ADMIN - GET SINGLE VENDOR TICKET
# =========================================================


@router.get(
    "/admin/vendor-tickets/{vendor_ticket_id}",
    response_model=AdminVendorTicketDetailResponse,
)
def get_admin_vendor_ticket(
    vendor_ticket_id: int,

    db: Session = Depends(get_db),

    staff=Depends(get_current_staff),
):
    return SupportService.get_admin_vendor_ticket(
        db=db,
        staff=staff,
        vendor_ticket_id=vendor_ticket_id,
    )


# =========================================================
# ADMIN - REPLY TO VENDOR TICKET
# =========================================================
#
# Admin reply is text-only.
# =========================================================


@router.post(
    "/admin/vendor-tickets/{vendor_ticket_id}/messages",
    response_model=AdminVendorTicketMessageResponse,
)
def create_admin_vendor_ticket_message(
    vendor_ticket_id: int,

    data: TicketMessageCreate,

    db: Session = Depends(get_db),

    staff=Depends(get_current_staff),
):
    return SupportService.create_admin_vendor_ticket_message(
        db=db,
        staff=staff,
        vendor_ticket_id=vendor_ticket_id,
        message_text=data.message,
    )


# =========================================================
# ADMIN - UPDATE VENDOR TICKET STATUS
# =========================================================


@router.patch(
    "/admin/vendor-tickets/{vendor_ticket_id}/status",
)
def update_vendor_ticket_status(
    vendor_ticket_id: int,

    data: TicketStatusUpdate,

    db: Session = Depends(get_db),

    staff=Depends(get_current_staff),
):
    return SupportService.update_vendor_ticket_status(
        db=db,
        staff=staff,
        vendor_ticket_id=vendor_ticket_id,
        status=data.status,
    )


# =========================================================
# ADMIN - FEEDBACK
# =========================================================


@router.get(
    "/admin/feedback",
)
def get_admin_feedbacks(
    db: Session = Depends(get_db),

    staff=Depends(get_current_staff),
):
    return SupportService.get_admin_feedbacks(
        db,
    )


@router.get(
    "/admin/feedback/{feedback_id}",
)
def get_admin_feedback(
    feedback_id: int,

    db: Session = Depends(get_db),

    staff=Depends(get_current_staff),
):
    return SupportService.get_admin_feedback(
        db,
        feedback_id,
    )