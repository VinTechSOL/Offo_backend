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
    TicketStatusUpdate,
    FeedbackCreate,
    FeedbackResponse,
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
    delete_file
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
                content_type=image.content_type
                or "application/octet-stream",
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
        # If an image was uploaded but validation/business
        # logic failed afterward, clean it up.
        if image_url:
            delete_file(image_url)

        raise

    except Exception:
        # DB/S3/unexpected failure
        if image_url:
            delete_file(image_url)

        raise HTTPException(
            status_code=500,
            detail="Unable to raise ticket. Please try again.",
        )


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


@router.get(
    "/tickets/{ticket_id}",
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
# ADMIN TICKETS
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
# ADMIN FEEDBACK
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