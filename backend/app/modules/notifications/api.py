from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user,get_current_staff
from app.modules.notifications.repository import NotificationRepository
from app.modules.notifications.schemas import NotificationResponse
from app.modules.notifications.service import NotificationRecipient

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/user", response_model=list[NotificationResponse])
def my_notifications(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    print(f"📥 [USER NOTIFICATIONS] user_id={user.user_id}")

    return NotificationRepository.get_for_user(
        db,
        recipient_type=NotificationRecipient.USER,
        recipient_id=user.user_id,
    )


@router.get("/staff")
def get_staff_notifications(
    db: Session = Depends(get_db),
    staff=Depends(get_current_staff),
):
    print(
        f"📥 [STAFF NOTIFICATIONS] "
        f"staff_id={staff.staff_id} branch_id={staff.branch_id}"
    )

    notifications = NotificationRepository.get_for_staff(
        db,
        branch_id=staff.branch_id,
    )

    print(f"📦 [FOUND] {len(notifications)} notifications")

    return notifications


@router.post("/staff/mark-read")
def mark_staff_notifications_read(
    db: Session = Depends(get_db),
    staff=Depends(get_current_staff),
):
    print(f"✅ [MARK READ] branch_id={staff.branch_id}")

    NotificationRepository.mark_all_read_for_staff(
        db,
        branch_id=staff.branch_id,
    )

    db.commit()
    return {"status": "ok"}