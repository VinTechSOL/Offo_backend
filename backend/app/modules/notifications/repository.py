from sqlalchemy.orm import Session
from sqlalchemy import select,update
from app.modules.notifications.models import Notification,NotificationRecipient


class NotificationRepository:

    @staticmethod
    def create(db: Session, notification: Notification):
        db.add(notification)
        db.commit()
        db.refresh(notification)
        return notification

    @staticmethod
    def get_for_user(db: Session, recipient_type: str, recipient_id: int):
        return (
            db.query(Notification)
            .filter(
                Notification.recipient_type == recipient_type,
                Notification.recipient_id == recipient_id
            )
            .order_by(Notification.created_at.desc())
            .all()
        )
    
    @staticmethod
    def get_for_staff(db: Session, branch_id: int):
        stmt = (
            select(Notification)
            .where(
                Notification.recipient_type == NotificationRecipient.STAFF.value,
                Notification.recipient_id == branch_id,
            )
            .order_by(Notification.created_at.desc())
        )
        return db.execute(stmt).scalars().all()
    
    @staticmethod
    def mark_all_read_for_staff(db: Session, branch_id: int):
        db.execute(
            update(Notification)
            .where(
                Notification.recipient_type == NotificationRecipient.STAFF,
                Notification.recipient_id == branch_id,
                Notification.is_read == False,
            )
            .values(is_read=True)
        )
        db.commit()

    @staticmethod
    def mark_read(db: Session, notification_id: int):
        notification = db.get(Notification, notification_id)
        if notification:
            notification.is_read = True
            db.commit()
        return notification
