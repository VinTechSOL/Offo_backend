from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.support.models import (
    Ticket,
    Feedback,
)

from app.modules.support.repository import (
    SupportRepository,
)

from app.modules.support.constants import (
    TicketStatus,
)

from app.modules.orders.constants import (
    OrderStatus,
)

from app.modules.orders.repository import (
    OrderRepository,
)


class SupportService:

    # =====================================================
    # TICKETS
    # =====================================================

    @staticmethod
    def create_ticket(
        db: Session,
        user_id: int,
        data,
        image_url: str | None = None,
    ):

        # ---------------------------------------------
        # 1. Validate order ownership
        # ---------------------------------------------

        order = SupportRepository.get_order_for_user(
            db,
            user_id,
            data.order_id,
        )

        if not order:
            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        # ---------------------------------------------
        # 2. Ticket should only be raised for completed
        #    or otherwise terminal orders
        # ---------------------------------------------

        order_status = str(order.order_status).strip().upper()

        allowed_statuses = {
            OrderStatus.COMPLETED.value,
            OrderStatus.CANCELLED.value,
            OrderStatus.REJECTED.value,
        }

        if order_status not in allowed_statuses:
            raise HTTPException(
                status_code=400,
                detail="Tickets can only be raised for completed, cancelled, or rejected orders",
            )

        # ---------------------------------------------
        # 3. Validate selected order item
        # ---------------------------------------------

        order_item = None

        if data.order_item_id is not None:

            order_item = (
                SupportRepository
                .get_order_item_for_order(
                    db,
                    data.order_id,
                    data.order_item_id,
                )
            )

            if not order_item:
                raise HTTPException(
                    status_code=400,
                    detail="Selected item does not belong to this order",
                )

        # ---------------------------------------------
        # 4. Create ticket
        # ---------------------------------------------

        ticket = Ticket(
            user_id=user_id,
            order_id=order.order_id,
            order_item_id=(
                order_item.order_item_id
                if order_item
                else None
            ),
            issue_type=data.issue_type.value,
            description=data.description.strip(),
            image_url=image_url,
            status=TicketStatus.OPEN,
        )

        SupportRepository.create_ticket(
            db,
            ticket,
        )

        db.commit()
        db.refresh(ticket)

        return ticket

    @staticmethod
    def get_user_tickets(
        db: Session,
        user_id: int,
    ):
        return SupportRepository.get_user_tickets(
            db,
            user_id,
        )

    @staticmethod
    def get_user_ticket(
        db: Session,
        user_id: int,
        ticket_id: int,
    ):
        ticket = SupportRepository.get_user_ticket(
            db,
            user_id,
            ticket_id,
        )

        if not ticket:
            raise HTTPException(
                status_code=404,
                detail="Ticket not found",
            )

        return ticket

    # =====================================================
    # ADMIN TICKETS
    # =====================================================

    @staticmethod
    def get_admin_tickets(
        db: Session,
    ):
        rows = SupportRepository.get_tickets_for_admin(
            db,
        )

        result = []

        for (
            ticket,
            order,
            user,
            branch,
            order_item,
            menu_item,
        ) in rows:

            result.append({
                "ticket_id": ticket.ticket_id,

                "display_ticket_id":
                    f"TKT-{ticket.ticket_id:06d}",

                "order_id": order.order_id,

                "display_order_id":
                    OrderRepository.build_display_order_id(
                        order
                    ),

                "user_id": user.user_id,

                "customer_name":
                    f"{user.first_name} {user.last_name}".strip(),

                "cafe_id": order.cafe_id,

                "cafe_name": branch.branch_name,

                "branch_id": order.branch_id,

                "issue_type": ticket.issue_type,

                "description": ticket.description,

                "order_item_id":
                    ticket.order_item_id,

                "item_name":
                    menu_item.item_name
                    if menu_item
                    else None,

                "image_url": ticket.image_url,

                "status": ticket.status,

                "created_at": ticket.created_at,

                "updated_at": ticket.updated_at,
            })

        return result

    @staticmethod
    def get_admin_ticket(
        db: Session,
        ticket_id: int,
    ):
        row = SupportRepository.get_ticket_for_admin(
            db,
            ticket_id,
        )

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Ticket not found",
            )

        (
            ticket,
            order,
            user,
            branch,
            order_item,
            menu_item,
        ) = row

        return {
            "ticket_id": ticket.ticket_id,

            "display_ticket_id":
                f"TKT-{ticket.ticket_id:06d}",

            "order_id": order.order_id,

            "display_order_id":
                OrderRepository.build_display_order_id(
                    order
                ),

            "user_id": user.user_id,

            "customer_name":
                f"{user.first_name} {user.last_name}".strip(),

            "cafe_id": order.cafe_id,

            "cafe_name": branch.branch_name,

            "branch_id": order.branch_id,

            "issue_type": ticket.issue_type,

            "description": ticket.description,

            "order_item_id":
                ticket.order_item_id,

            "item_name":
                menu_item.item_name
                if menu_item
                else None,

            "image_url": ticket.image_url,

            "status": ticket.status,

            "created_at": ticket.created_at,

            "updated_at": ticket.updated_at,
        }

    @staticmethod
    def update_ticket_status(
        db: Session,
        ticket_id: int,
        status: TicketStatus,
    ):
        ticket = SupportRepository.get_ticket(
            db,
            ticket_id,
        )

        if not ticket:
            raise HTTPException(
                status_code=404,
                detail="Ticket not found",
            )

        SupportRepository.update_ticket_status(
            db,
            ticket,
            status.value,
        )

        db.commit()
        db.refresh(ticket)

        return ticket

    # =====================================================
    # FEEDBACK
    # =====================================================

    @staticmethod
    def create_feedback(
        db: Session,
        user_id: int,
        data,
    ):

        # ---------------------------------------------
        # 1. Validate order ownership
        # ---------------------------------------------

        order = SupportRepository.get_order_for_user(
            db,
            user_id,
            data.order_id,
        )

        if not order:
            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        # ---------------------------------------------
        # 2. Feedback only after completion
        # ---------------------------------------------

        if order.order_status != OrderStatus.COMPLETED.value:
            raise HTTPException(
                status_code=400,
                detail="Feedback can only be submitted for completed orders",
            )

        # ---------------------------------------------
        # 3. Prevent duplicate feedback
        # ---------------------------------------------

        existing = (
            SupportRepository
            .get_user_feedback_for_order(
                db,
                user_id,
                data.order_id,
            )
        )

        if existing:
            raise HTTPException(
                status_code=409,
                detail="Feedback has already been submitted for this order",
            )

        # ---------------------------------------------
        # 4. Create feedback
        # ---------------------------------------------

        feedback = Feedback(
            user_id=user_id,
            order_id=order.order_id,
            food_rating=data.food_rating,
            app_rating=data.app_rating,
            comments=(
                data.comments.strip()
                if data.comments
                else None
            ),
        )

        SupportRepository.create_feedback(
            db,
            feedback,
        )

        db.commit()
        db.refresh(feedback)

        return feedback

    @staticmethod
    def get_user_feedbacks(
        db: Session,
        user_id: int,
    ):
        return SupportRepository.get_user_feedbacks(
            db,
            user_id,
        )

    # =====================================================
    # ADMIN FEEDBACK
    # =====================================================

    @staticmethod
    def get_admin_feedbacks(
        db: Session,
    ):
        rows = SupportRepository.get_feedbacks_for_admin(
            db,
        )

        result = []

        for (
            feedback,
            order,
            user,
            branch,
        ) in rows:

            result.append({
                "feedback_id": feedback.feedback_id,

                "display_feedback_id":
                    f"FB-{feedback.feedback_id:06d}",

                "order_id": order.order_id,

                "display_order_id":
                    OrderRepository.build_display_order_id(
                        order
                    ),

                "user_id": user.user_id,

                "customer_name":
                    f"{user.first_name} {user.last_name}".strip(),

                "cafe_id": order.cafe_id,

                "cafe_name": branch.branch_name,

                "branch_id": order.branch_id,

                "food_rating": feedback.food_rating,

                "app_rating": feedback.app_rating,

                "comments": feedback.comments,

                "created_at": feedback.created_at,
            })

        return result

    @staticmethod
    def get_admin_feedback(
        db: Session,
        feedback_id: int,
    ):
        row = SupportRepository.get_feedback_for_admin(
            db,
            feedback_id,
        )

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Feedback not found",
            )

        (
            feedback,
            order,
            user,
            branch,
        ) = row

        return {
            "feedback_id": feedback.feedback_id,

            "display_feedback_id":
                f"FB-{feedback.feedback_id:06d}",

            "order_id": order.order_id,

            "display_order_id":
                OrderRepository.build_display_order_id(
                    order
                ),

            "user_id": user.user_id,

            "customer_name":
                f"{user.first_name} {user.last_name}".strip(),

            "cafe_id": order.cafe_id,

            "cafe_name": branch.branch_name,

            "branch_id": order.branch_id,

            "food_rating": feedback.food_rating,

            "app_rating": feedback.app_rating,

            "comments": feedback.comments,

            "created_at": feedback.created_at,
        }