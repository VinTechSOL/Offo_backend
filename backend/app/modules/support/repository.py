from sqlalchemy.orm import Session
from sqlalchemy import select

from app.modules.support.models import Ticket, Feedback

from app.modules.orders.models import (
    Order,
    OrderItem,
)

from app.modules.users.models import User

from app.modules.menu.models import MenuItem

from app.modules.vendor.models import CafeBranch


class SupportRepository:

    # =====================================================
    # TICKETS
    # =====================================================

    @staticmethod
    def create_ticket(
        db: Session,
        ticket: Ticket,
    ):
        db.add(ticket)
        db.flush()

        return ticket

    @staticmethod
    def get_ticket(
        db: Session,
        ticket_id: int,
    ):
        return db.get(
            Ticket,
            ticket_id,
        )

    @staticmethod
    def get_user_ticket(
        db: Session,
        user_id: int,
        ticket_id: int,
    ):
        stmt = (
            select(Ticket)
            .where(
                Ticket.ticket_id == ticket_id,
                Ticket.user_id == user_id,
            )
        )

        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_user_tickets(
        db: Session,
        user_id: int,
    ):
        return (
            db.query(Ticket)
            .filter(
                Ticket.user_id == user_id,
            )
            .order_by(
                Ticket.created_at.desc(),
            )
            .all()
        )

    @staticmethod
    def get_tickets_for_admin(
        db: Session,
    ):
        rows = (
            db.query(
                Ticket,
                Order,
                User,
                CafeBranch,
                OrderItem,
                MenuItem,
            )
            .join(
                Order,
                Order.order_id == Ticket.order_id,
            )
            .join(
                User,
                User.user_id == Ticket.user_id,
            )
            .join(
                CafeBranch,
                CafeBranch.branch_id == Order.branch_id,
            )
            .outerjoin(
                OrderItem,
                OrderItem.order_item_id == Ticket.order_item_id,
            )
            .outerjoin(
                MenuItem,
                MenuItem.item_id == OrderItem.item_id,
            )
            .order_by(
                Ticket.created_at.desc(),
            )
            .all()
        )

        return rows

    @staticmethod
    def get_ticket_for_admin(
        db: Session,
        ticket_id: int,
    ):
        return (
            db.query(
                Ticket,
                Order,
                User,
                CafeBranch,
                OrderItem,
                MenuItem,
            )
            .join(
                Order,
                Order.order_id == Ticket.order_id,
            )
            .join(
                User,
                User.user_id == Ticket.user_id,
            )
            .join(
                CafeBranch,
                CafeBranch.branch_id == Order.branch_id,
            )
            .outerjoin(
                OrderItem,
                OrderItem.order_item_id == Ticket.order_item_id,
            )
            .outerjoin(
                MenuItem,
                MenuItem.item_id == OrderItem.item_id,
            )
            .filter(
                Ticket.ticket_id == ticket_id,
            )
            .first()
        )

    @staticmethod
    def update_ticket_status(
        db: Session,
        ticket: Ticket,
        status: str,
    ):
        ticket.status = status

        db.flush()

        return ticket

    # =====================================================
    # ORDER OWNERSHIP / ORDER ITEM VALIDATION
    # =====================================================

    @staticmethod
    def get_order_for_user(
        db: Session,
        user_id: int,
        order_id: int,
    ):
        return (
            db.query(Order)
            .filter(
                Order.order_id == order_id,
                Order.user_id == user_id,
            )
            .first()
        )

    @staticmethod
    def get_order_item_for_order(
        db: Session,
        order_id: int,
        order_item_id: int,
    ):
        return (
            db.query(OrderItem)
            .filter(
                OrderItem.order_item_id == order_item_id,
                OrderItem.order_id == order_id,
            )
            .first()
        )

    # =====================================================
    # FEEDBACK
    # =====================================================

    @staticmethod
    def create_feedback(
        db: Session,
        feedback: Feedback,
    ):
        db.add(feedback)
        db.flush()

        return feedback

    @staticmethod
    def get_feedback(
        db: Session,
        feedback_id: int,
    ):
        return db.get(
            Feedback,
            feedback_id,
        )

    @staticmethod
    def get_user_feedback_for_order(
        db: Session,
        user_id: int,
        order_id: int,
    ):
        return (
            db.query(Feedback)
            .filter(
                Feedback.user_id == user_id,
                Feedback.order_id == order_id,
            )
            .first()
        )

    @staticmethod
    def get_user_feedbacks(
        db: Session,
        user_id: int,
    ):
        return (
            db.query(Feedback)
            .filter(
                Feedback.user_id == user_id,
            )
            .order_by(
                Feedback.created_at.desc(),
            )
            .all()
        )

    @staticmethod
    def get_feedback_for_admin(
        db: Session,
        feedback_id: int,
    ):
        return (
            db.query(
                Feedback,
                Order,
                User,
                CafeBranch,
            )
            .join(
                Order,
                Order.order_id == Feedback.order_id,
            )
            .join(
                User,
                User.user_id == Feedback.user_id,
            )
            .join(
                CafeBranch,
                CafeBranch.branch_id == Order.branch_id,
            )
            .filter(
                Feedback.feedback_id == feedback_id,
            )
            .first()
        )

    @staticmethod
    def get_feedbacks_for_admin(
        db: Session,
    ):
        return (
            db.query(
                Feedback,
                Order,
                User,
                CafeBranch,
            )
            .join(
                Order,
                Order.order_id == Feedback.order_id,
            )
            .join(
                User,
                User.user_id == Feedback.user_id,
            )
            .join(
                CafeBranch,
                CafeBranch.branch_id == Order.branch_id,
            )
            .order_by(
                Feedback.created_at.desc(),
            )
            .all()
        )