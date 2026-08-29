from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.support.models import (
    Ticket,
    Feedback,
    TicketMessage,
    VendorTicket,
    VendorTicketMessage,
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

from app.modules.notifications.service import (
    NotificationService,
)

from app.modules.notifications.constants import (
    NotificationRecipient,
    NotificationPriority,
    NotificationEvent,
)


class SupportService:

    # =====================================================
    # USER TICKETS
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
        # 2. Ticket only for terminal orders
        # ---------------------------------------------

        order_status = str(
            order.order_status
        ).strip().upper()

        allowed_statuses = {
            OrderStatus.COMPLETED.value,
            OrderStatus.CANCELLED.value,
            OrderStatus.REJECTED.value,
        }

        if order_status not in allowed_statuses:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Tickets can only be raised for "
                    "completed, cancelled, or rejected orders"
                ),
            )

        # ---------------------------------------------
        # 3. Validate order item
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
                    detail=(
                        "Selected item does not belong "
                        "to this order"
                    ),
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
            status=TicketStatus.OPEN.value,
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

        messages = (
            SupportRepository.get_ticket_messages(
                db,
                ticket.ticket_id,
            )
        )

        return {
            "ticket_id": ticket.ticket_id,
            "order_id": ticket.order_id,
            "order_item_id": ticket.order_item_id,
            "issue_type": ticket.issue_type,
            "description": ticket.description,
            "image_url": ticket.image_url,
            "status": ticket.status,
            "created_at": ticket.created_at,
            "updated_at": ticket.updated_at,
            "messages": messages,
        }

    @staticmethod
    def create_user_ticket_message(
        db: Session,
        user_id: int,
        ticket_id: int,
        message_text: str,
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

        if ticket.status == TicketStatus.CLOSED.value:
            raise HTTPException(
                status_code=400,
                detail="This ticket is closed",
            )

        message_text = message_text.strip()

        if not message_text:
            raise HTTPException(
                status_code=400,
                detail="Message cannot be empty",
            )

        message = TicketMessage(
            ticket_id=ticket.ticket_id,
            sender_type="USER",
            sender_id=user_id,
            message=message_text,
        )

        SupportRepository.create_ticket_message(
            db,
            message,
        )

        ticket.updated_at = datetime.now(
            timezone.utc
        )

        db.commit()
        db.refresh(message)

        return message

    # =====================================================
    # ADMIN - USER TICKETS
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
                    f"{user.first_name} "
                    f"{user.last_name}".strip(),

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

        messages = (
            SupportRepository.get_ticket_messages(
                db,
                ticket.ticket_id,
            )
        )

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
                f"{user.first_name} "
                f"{user.last_name}".strip(),

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

            "messages": messages,
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

        old_status = ticket.status

        SupportRepository.update_ticket_status(
            db,
            ticket,
            status.value,
        )

        db.commit()
        db.refresh(ticket)

        if old_status != ticket.status:

            display_ticket_id = (
                f"TKT-{ticket.ticket_id:06d}"
            )

            NotificationService.trigger(
                db,
                event=NotificationEvent.TICKET_STATUS_CHANGED,
                recipient_type=NotificationRecipient.USER,
                recipient_id=ticket.user_id,
                title="Support Ticket Updated",
                message=(
                    f"Hey! Your support ticket "
                    f"{display_ticket_id} is now "
                    f"{ticket.status}."
                ),
                priority=NotificationPriority.MEDIUM,
                order_id=ticket.order_id,
            )

            db.commit()

        return ticket

    @staticmethod
    def create_admin_ticket_message(
        db: Session,
        staff,
        ticket_id: int,
        message_text: str,
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

        if ticket.status == TicketStatus.CLOSED.value:
            raise HTTPException(
                status_code=400,
                detail="This ticket is closed",
            )

        message_text = message_text.strip()

        if not message_text:
            raise HTTPException(
                status_code=400,
                detail="Message cannot be empty",
            )

        message = TicketMessage(
            ticket_id=ticket.ticket_id,
            sender_type="ADMIN",
            sender_id=staff.staff_id,
            message=message_text,
        )

        SupportRepository.create_ticket_message(
            db,
            message,
        )

        ticket.updated_at = datetime.now(
            timezone.utc
        )

        db.commit()
        db.refresh(message)

        display_ticket_id = (
            f"TKT-{ticket.ticket_id:06d}"
        )

        NotificationService.trigger(
            db=db,
            event=NotificationEvent.TICKET_MESSAGE_RECEIVED,
            recipient_type=NotificationRecipient.USER,
            recipient_id=ticket.user_id,
            title="Support Ticket Reply",
            message=(
                f"Admin replied to your support ticket "
                f"{display_ticket_id}."
            ),
            priority=NotificationPriority.MEDIUM,
            order_id=ticket.order_id,
        )

        db.commit()

        return message

    # =====================================================
    # VENDOR - CREATE TICKET
    # =====================================================

    @staticmethod
    def create_vendor_ticket(
        db: Session,
        staff,
        data,
        image_url: str | None = None,
    ):
        # -------------------------------------------------
        # 1. Validate vendor account
        # -------------------------------------------------

        if staff.role.role_name != "VENDOR":
            raise HTTPException(
                status_code=403,
                detail="Only vendors can create vendor support tickets",
            )

        # -------------------------------------------------
        # 2. Vendor must belong to a branch
        # -------------------------------------------------

        if staff.branch_id is None:
            raise HTTPException(
                status_code=400,
                detail="Vendor is not assigned to a branch",
            )

        # -------------------------------------------------
        # 3. Clean input
        # -------------------------------------------------

        subject = data.subject.strip()
        description = data.description.strip()

        if not subject:
            raise HTTPException(
                status_code=400,
                detail="Subject cannot be empty",
            )

        if not description:
            raise HTTPException(
                status_code=400,
                detail="Description cannot be empty",
            )

        affected_order_ids = (
            data.affected_order_ids.strip()
            if data.affected_order_ids
            else None
        )

        # -------------------------------------------------
        # 4. Create vendor ticket
        # -------------------------------------------------

        ticket = VendorTicket(
            vendor_staff_id=staff.staff_id,
            category=data.category.strip(),
            severity=data.severity.strip().upper(),
            affected_order_ids=affected_order_ids,
            subject=subject,
            description=description,
            image_url=image_url,
            status=TicketStatus.OPEN.value,
        )

        SupportRepository.create_vendor_ticket(
            db,
            ticket,
        )

        # -------------------------------------------------
        # 5. Create initial conversation message
        # -------------------------------------------------

        message = VendorTicketMessage(
            vendor_ticket_id=ticket.vendor_ticket_id,
            sender_type="VENDOR",
            sender_id=staff.staff_id,
            message=description,
        )

        SupportRepository.create_vendor_ticket_message(
            db,
            message,
        )

        # -------------------------------------------------
        # 6. Commit ticket + initial message
        # -------------------------------------------------

        db.commit()

        db.refresh(ticket)

        # -------------------------------------------------
        # 7. Return API response
        # -------------------------------------------------

        return {
            "vendor_ticket_id": ticket.vendor_ticket_id,
            "display_ticket_id": f"TKT-{ticket.vendor_ticket_id:06d}",
            "vendor_staff_id": ticket.vendor_staff_id,
            "category": ticket.category,
            "severity": ticket.severity,
            "affected_order_ids": ticket.affected_order_ids,
            "subject": ticket.subject,
            "description": ticket.description,
            "image_url": ticket.image_url,
            "status": ticket.status,
            "created_at": ticket.created_at,
            "updated_at": ticket.updated_at,
        }

    # =====================================================
    # VENDOR - GET TICKETS
    # =====================================================

    @staticmethod
    def get_vendor_tickets(
        db: Session,
        staff,
    ):
        if staff.role.role_name != "VENDOR":
            raise HTTPException(
                status_code=403,
                detail=(
                    "Only vendors can access "
                    "vendor tickets"
                ),
            )

        tickets = SupportRepository.get_vendor_tickets(
            db,
            staff.staff_id,
        )

        result = []

        for ticket in tickets:

            result.append({
                "vendor_ticket_id":
                    ticket.vendor_ticket_id,

                "display_ticket_id":
                    f"TKT-{ticket.vendor_ticket_id:06d}",

                "vendor_staff_id":
                    ticket.vendor_staff_id,

                "category":
                    ticket.category,

                "severity":
                    ticket.severity,

                "affected_order_ids":
                    ticket.affected_order_ids,

                "subject":
                    ticket.subject,

                "description":
                    ticket.description,

                "image_url":
                    ticket.image_url,

                "status":
                    ticket.status,

                "created_at":
                    ticket.created_at,

                "updated_at":
                    ticket.updated_at,
            })

        return result

    # =====================================================
    # VENDOR - GET SINGLE TICKET
    # =====================================================

    @staticmethod
    def get_vendor_ticket(
        db: Session,
        staff,
        vendor_ticket_id: int,
    ):
        if staff.role.role_name != "VENDOR":
            raise HTTPException(
                status_code=403,
                detail=(
                    "Only vendors can access "
                    "vendor tickets"
                ),
            )

        ticket = SupportRepository.get_vendor_ticket(
            db,
            staff.staff_id,
            vendor_ticket_id,
        )

        if not ticket:
            raise HTTPException(
                status_code=404,
                detail="Ticket not found",
            )

        messages = (
            SupportRepository.get_vendor_ticket_messages(
                db,
                ticket.vendor_ticket_id,
            )
        )

        return {
            "vendor_ticket_id":
                ticket.vendor_ticket_id,

            "display_ticket_id":
                f"TKT-{ticket.vendor_ticket_id:06d}",

            "vendor_staff_id":
                ticket.vendor_staff_id,

            "category":
                ticket.category,

            "severity":
                ticket.severity,

            "affected_order_ids":
                ticket.affected_order_ids,

            "subject":
                ticket.subject,

            "description":
                ticket.description,

            "image_url":
                ticket.image_url,

            "status":
                ticket.status,

            "created_at":
                ticket.created_at,

            "updated_at":
                ticket.updated_at,

            "messages":
                messages,
        }

    # =====================================================
    # VENDOR - REPLY
    # =====================================================

    @staticmethod
    def create_vendor_ticket_message(
        db: Session,
        staff,
        vendor_ticket_id: int,
        message_text: str,
    ):
        if staff.role.role_name != "VENDOR":
            raise HTTPException(
                status_code=403,
                detail=(
                    "Only vendors can reply "
                    "to vendor tickets"
                ),
            )

        ticket = SupportRepository.get_vendor_ticket(
            db,
            staff.staff_id,
            vendor_ticket_id,
        )

        if not ticket:
            raise HTTPException(
                status_code=404,
                detail="Ticket not found",
            )

        if ticket.status == TicketStatus.CLOSED.value:
            raise HTTPException(
                status_code=400,
                detail="This ticket is closed",
            )

        message_text = message_text.strip()

        if not message_text:
            raise HTTPException(
                status_code=400,
                detail="Message cannot be empty",
            )

        message = VendorTicketMessage(
            vendor_ticket_id=ticket.vendor_ticket_id,
            sender_type="VENDOR",
            sender_id=staff.staff_id,
            message=message_text,
        )

        SupportRepository.create_vendor_ticket_message(
            db,
            message,
        )

        ticket.updated_at = datetime.now(
            timezone.utc
        )

        db.commit()
        db.refresh(message)

        return message

    # =====================================================
    # VENDOR - FEEDBACK
    # =====================================================

    @staticmethod
    def get_vendor_feedbacks(
        db: Session,
        staff,
    ):
        if staff.role.role_name != "VENDOR":
            raise HTTPException(
                status_code=403,
                detail=(
                    "Only vendors can access "
                    "branch feedback"
                ),
            )

        if staff.branch_id is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Vendor is not assigned "
                    "to a branch"
                ),
            )

        rows = SupportRepository.get_feedbacks_for_vendor(
            db,
            staff.branch_id,
        )

        result = []

        for (
            feedback,
            order,
            user,
            branch,
        ) in rows:

            result.append({
                "feedback_id":
                    feedback.feedback_id,

                "display_feedback_id":
                    f"FB-{feedback.feedback_id:06d}",

                "order_id":
                    order.order_id,

                "display_order_id":
                    OrderRepository.build_display_order_id(
                        order
                    ),

                "user_id":
                    user.user_id,

                "customer_name":
                    f"{user.first_name} "
                    f"{user.last_name}".strip(),

                "food_rating":
                    feedback.food_rating,

                "comments":
                    feedback.comments,

                "created_at":
                    feedback.created_at,
            })

        return result

    # =====================================================
    # ADMIN - GET ALL VENDOR TICKETS
    # =====================================================

    @staticmethod
    def get_admin_vendor_tickets(
        db: Session,
        staff,
    ):
        # ---------------------------------------------
        # 1. Validate admin access
        # ---------------------------------------------

        if staff.role.role_name not in {
            "SUPER_ADMIN",
            "VENDOR_ADMIN",
        }:
            raise HTTPException(
                status_code=403,
                detail="Access denied",
            )

        # ---------------------------------------------
        # 2. Get tickets
        # ---------------------------------------------

        rows = (
            SupportRepository
            .get_vendor_tickets_for_admin(
                db,
            )
        )

        result = []

        for (
            ticket,
            vendor,
            branch,
        ) in rows:

            result.append({
                "vendor_ticket_id":
                    ticket.vendor_ticket_id,

                "display_ticket_id":
                    f"TKT-{ticket.vendor_ticket_id:06d}",

                "vendor_staff_id":
                    vendor.staff_id,

                "vendor_name":
                    f"{vendor.first_name} "
                    f"{vendor.last_name}".strip(),

                "vendor_username":
                    vendor.username,

                "cafe_id":
                    branch.cafe_id
                    if branch
                    else None,

                "cafe_name":
                    branch.branch_name
                    if branch
                    else None,

                "branch_id":
                    branch.branch_id
                    if branch
                    else None,

                "branch_name":
                    branch.branch_name
                    if branch
                    else None,

                "category":
                    ticket.category,

                "severity":
                    ticket.severity,

                "affected_order_ids":
                    ticket.affected_order_ids,

                "subject":
                    ticket.subject,

                "description":
                    ticket.description,

                "image_url":
                    ticket.image_url,

                "status":
                    ticket.status,

                "created_at":
                    ticket.created_at,

                "updated_at":
                    ticket.updated_at,
            })

        return result

    # =====================================================
    # ADMIN - GET SINGLE VENDOR TICKET
    # =====================================================

    @staticmethod
    def get_admin_vendor_ticket(
        db: Session,
        staff,
        vendor_ticket_id: int,
    ):
        # ---------------------------------------------
        # 1. Validate admin access
        # ---------------------------------------------

        if staff.role.role_name not in {
            "SUPER_ADMIN",
            "VENDOR_ADMIN",
        }:
            raise HTTPException(
                status_code=403,
                detail="Access denied",
            )

        # ---------------------------------------------
        # 2. Get ticket + vendor + branch
        # ---------------------------------------------

        row = (
            SupportRepository
            .get_vendor_ticket_for_admin(
                db,
                vendor_ticket_id,
            )
        )

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Vendor ticket not found",
            )

        (
            ticket,
            vendor,
            branch,
        ) = row

        # ---------------------------------------------
        # 3. Get conversation
        # ---------------------------------------------

        messages = (
            SupportRepository
            .get_vendor_ticket_messages(
                db,
                ticket.vendor_ticket_id,
            )
        )

        # ---------------------------------------------
        # 4. Return detail
        # ---------------------------------------------

        return {
            "vendor_ticket_id":
                ticket.vendor_ticket_id,

            "display_ticket_id":
                f"TKT-{ticket.vendor_ticket_id:06d}",

            "vendor_staff_id":
                vendor.staff_id,

            "vendor_name":
                f"{vendor.first_name} "
                f"{vendor.last_name}".strip(),

            "vendor_username":
                vendor.username,

            "cafe_id":
                branch.cafe_id
                if branch
                else None,

            "cafe_name":
                branch.branch_name
                if branch
                else None,

            "branch_id":
                branch.branch_id
                if branch
                else None,

            "branch_name":
                branch.branch_name
                if branch
                else None,

            "category":
                ticket.category,

            "severity":
                ticket.severity,

            "affected_order_ids":
                ticket.affected_order_ids,

            "subject":
                ticket.subject,

            "description":
                ticket.description,

            "image_url":
                ticket.image_url,

            "status":
                ticket.status,

            "created_at":
                ticket.created_at,

            "updated_at":
                ticket.updated_at,

            "messages":
                messages,
        }

    # =====================================================
    # ADMIN - REPLY TO VENDOR TICKET
    # =====================================================

    @staticmethod
    def create_admin_vendor_ticket_message(
        db: Session,
        staff,
        vendor_ticket_id: int,
        message_text: str,
    ):
        # ---------------------------------------------
        # 1. Validate admin access
        # ---------------------------------------------

        if staff.role.role_name not in {
            "SUPER_ADMIN",
            "VENDOR_ADMIN",
        }:
            raise HTTPException(
                status_code=403,
                detail="Access denied",
            )

        # ---------------------------------------------
        # 2. Get ticket
        # ---------------------------------------------

        row = (
            SupportRepository
            .get_vendor_ticket_for_admin(
                db,
                vendor_ticket_id,
            )
        )

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Vendor ticket not found",
            )

        (
            ticket,
            vendor,
            branch,
        ) = row

        # ---------------------------------------------
        # 3. Closed tickets cannot receive messages
        # ---------------------------------------------

        if ticket.status == TicketStatus.CLOSED.value:
            raise HTTPException(
                status_code=400,
                detail="This ticket is closed",
            )

        # ---------------------------------------------
        # 4. Validate message
        # ---------------------------------------------

        message_text = message_text.strip()

        if not message_text:
            raise HTTPException(
                status_code=400,
                detail="Message cannot be empty",
            )

        # ---------------------------------------------
        # 5. Create message
        # ---------------------------------------------

        message = VendorTicketMessage(
            vendor_ticket_id=ticket.vendor_ticket_id,
            sender_type="ADMIN",
            sender_id=staff.staff_id,
            message=message_text,
        )

        SupportRepository.create_vendor_ticket_message(
            db,
            message,
        )

        # ---------------------------------------------
        # 6. Update ticket timestamp
        # ---------------------------------------------

        ticket.updated_at = datetime.now(
            timezone.utc
        )

        # ---------------------------------------------
        # 7. Commit
        # ---------------------------------------------

        db.commit()
        db.refresh(message)

        return message

    # =====================================================
    # ADMIN - UPDATE VENDOR TICKET STATUS
    # =====================================================

    @staticmethod
    def update_vendor_ticket_status(
        db: Session,
        staff,
        vendor_ticket_id: int,
        status: TicketStatus,
    ):
        # ---------------------------------------------
        # 1. Validate admin access
        # ---------------------------------------------

        if staff.role.role_name not in {
            "SUPER_ADMIN",
            "VENDOR_ADMIN",
        }:
            raise HTTPException(
                status_code=403,
                detail="Access denied",
            )

        # ---------------------------------------------
        # 2. Get ticket + vendor + branch
        # ---------------------------------------------

        row = (
            SupportRepository
            .get_vendor_ticket_for_admin(
                db,
                vendor_ticket_id,
            )
        )

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Vendor ticket not found",
            )

        (
            ticket,
            vendor,
            branch,
        ) = row

        # ---------------------------------------------
        # 3. Closed tickets cannot be changed
        # ---------------------------------------------

        if ticket.status == TicketStatus.CLOSED.value:
            raise HTTPException(
                status_code=400,
                detail="This ticket is already closed",
            )

        # ---------------------------------------------
        # 4. No-op if status is already the same
        # ---------------------------------------------

        if ticket.status == status.value:
            return ticket

        # ---------------------------------------------
        # 5. Update status
        # ---------------------------------------------

        SupportRepository.update_vendor_ticket_status(
            db=db,
            ticket=ticket,
            status=status.value,
        )

        ticket.updated_at = datetime.now(
            timezone.utc
        )

        # ---------------------------------------------
        # 6. Commit
        # ---------------------------------------------

        db.commit()
        db.refresh(ticket)

        return ticket

    # =====================================================
    # USER FEEDBACK
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
        # 2. Validate order status
        # ---------------------------------------------

        order_status = str(
            order.order_status
        ).strip().upper()

        allowed_statuses = {
            OrderStatus.COMPLETED.value,
            OrderStatus.CANCELLED.value,
            OrderStatus.REJECTED.value,
        }

        if order_status not in allowed_statuses:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Feedback can only be submitted "
                    "for completed, cancelled or "
                    "rejected orders"
                ),
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
                detail=(
                    "Feedback has already been "
                    "submitted for this order"
                ),
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
                "feedback_id":
                    feedback.feedback_id,

                "display_feedback_id":
                    f"FB-{feedback.feedback_id:06d}",

                "order_id":
                    order.order_id,

                "display_order_id":
                    OrderRepository.build_display_order_id(
                        order
                    ),

                "user_id":
                    user.user_id,

                "customer_name":
                    f"{user.first_name} "
                    f"{user.last_name}".strip(),

                "cafe_id":
                    order.cafe_id,

                "cafe_name":
                    branch.branch_name,

                "branch_id":
                    order.branch_id,

                "food_rating":
                    feedback.food_rating,

                "app_rating":
                    feedback.app_rating,

                "comments":
                    feedback.comments,

                "created_at":
                    feedback.created_at,
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
            "feedback_id":
                feedback.feedback_id,

            "display_feedback_id":
                f"FB-{feedback.feedback_id:06d}",

            "order_id":
                order.order_id,

            "display_order_id":
                OrderRepository.build_display_order_id(
                    order
                ),

            "user_id":
                user.user_id,

            "customer_name":
                f"{user.first_name} "
                f"{user.last_name}".strip(),

            "cafe_id":
                order.cafe_id,

            "cafe_name":
                branch.branch_name,

            "branch_id":
                order.branch_id,

            "food_rating":
                feedback.food_rating,

            "app_rating":
                feedback.app_rating,

            "comments":
                feedback.comments,

            "created_at":
                feedback.created_at,
        }