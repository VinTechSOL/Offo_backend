from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.support.models import (
    Ticket,
    Feedback,
    TicketMessage,
    VendorTicket,
    VendorTicketMessage,
)

from app.modules.orders.models import (
    Order,
    OrderItem,
)

from app.modules.users.models import User

from app.modules.menu.models import MenuItem

from app.modules.staff.models import Staff

from app.modules.vendor.models import CafeBranch


class SupportRepository:

    # =====================================================
    # USER TICKETS
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

    # =====================================================
    # ADMIN - USER TICKETS
    # =====================================================

    @staticmethod
    def get_tickets_for_admin(
        db: Session,
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
            .order_by(
                Ticket.created_at.desc(),
            )
            .all()
        )

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
    # USER TICKET MESSAGES
    # =====================================================

    @staticmethod
    def create_ticket_message(
        db: Session,
        message: TicketMessage,
    ):
        db.add(message)
        db.flush()

        return message

    @staticmethod
    def get_ticket_messages(
        db: Session,
        ticket_id: int,
    ):
        return (
            db.query(TicketMessage)
            .filter(
                TicketMessage.ticket_id == ticket_id,
            )
            .order_by(
                TicketMessage.created_at.asc(),
                TicketMessage.message_id.asc(),
            )
            .all()
        )

    # =====================================================
    # VENDOR TICKETS
    # =====================================================

    @staticmethod
    def create_vendor_ticket(
        db: Session,
        ticket: VendorTicket,
    ):
        db.add(ticket)
        db.flush()

        return ticket

    @staticmethod
    def get_vendor_ticket(
        db: Session,
        vendor_staff_id: int,
        vendor_ticket_id: int,
    ):
        return (
            db.query(VendorTicket)
            .filter(
                VendorTicket.vendor_ticket_id == vendor_ticket_id,
                VendorTicket.vendor_staff_id == vendor_staff_id,
            )
            .first()
        )

    @staticmethod
    def get_vendor_tickets(
        db: Session,
        vendor_staff_id: int,
    ):
        return (
            db.query(VendorTicket)
            .filter(
                VendorTicket.vendor_staff_id == vendor_staff_id,
            )
            .order_by(
                VendorTicket.created_at.desc(),
            )
            .all()
        )

    # =====================================================
    # VENDOR TICKET MESSAGES
    # =====================================================

    @staticmethod
    def create_vendor_ticket_message(
        db: Session,
        message: VendorTicketMessage,
    ):
        db.add(message)
        db.flush()

        return message

    @staticmethod
    def get_vendor_ticket_messages(
        db: Session,
        vendor_ticket_id: int,
    ):
        return (
            db.query(VendorTicketMessage)
            .filter(
                VendorTicketMessage.vendor_ticket_id
                == vendor_ticket_id,
            )
            .order_by(
                VendorTicketMessage.created_at.asc(),
                VendorTicketMessage.message_id.asc(),
            )
            .all()
        )

    # =====================================================
    # VENDOR TICKETS - ADMIN
    # =====================================================

    @staticmethod
    def get_vendor_tickets_for_admin(
        db: Session,
    ):
        return (
            db.query(
                VendorTicket,
                Staff,
                CafeBranch,
            )
            .join(
                Staff,
                Staff.staff_id
                == VendorTicket.vendor_staff_id,
            )
            .outerjoin(
                CafeBranch,
                CafeBranch.branch_id
                == Staff.branch_id,
            )
            .order_by(
                VendorTicket.created_at.desc(),
            )
            .all()
        )

    @staticmethod
    def get_vendor_ticket_for_admin(
        db: Session,
        vendor_ticket_id: int,
    ):
        return (
            db.query(
                VendorTicket,
                Staff,
                CafeBranch,
            )
            .join(
                Staff,
                Staff.staff_id
                == VendorTicket.vendor_staff_id,
            )
            .outerjoin(
                CafeBranch,
                CafeBranch.branch_id
                == Staff.branch_id,
            )
            .filter(
                VendorTicket.vendor_ticket_id
                == vendor_ticket_id,
            )
            .first()
        )

    @staticmethod
    def update_vendor_ticket_status(
        db: Session,
        ticket: VendorTicket,
        status: str,
    ):
        ticket.status = status

        db.flush()

        return ticket

    # =====================================================
    # VENDOR FEEDBACK
    # =====================================================

    @staticmethod
    def get_feedbacks_for_vendor(
        db: Session,
        branch_id: int,
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
                Order.branch_id == branch_id,
            )
            .order_by(
                Feedback.created_at.desc(),
            )
            .all()
        )

    @staticmethod
    def get_feedback_for_vendor(
        db: Session,
        branch_id: int,
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
                Order.branch_id == branch_id,
            )
            .first()
        )

    # =====================================================
    # USER FEEDBACK
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

    # =====================================================
    # ADMIN FEEDBACK
    # =====================================================

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