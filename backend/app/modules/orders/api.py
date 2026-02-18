from fastapi import APIRouter, Depends,HTTPException,Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_staff,get_current_user
from app.modules.orders.schemas import PlaceOrderRequest, PlaceOrderResponse
from app.modules.orders.service import OrderService
from app.modules.orders.service import VendorOrderService
from app.modules.orders.repository import OrderRepository
from app.modules.orders.constants import OrderStatus
from app.modules.staff.auth import require_permission
from app.modules.orders.priority import calculate_priority

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/place", response_model=PlaceOrderResponse)
def place_order(
    data: PlaceOrderRequest,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    order = OrderService.place_order(db, user.user_id, data)
    return {
        "order_id": order.order_id,
        "status": order.order_status
    }

@router.get("/incoming")
def get_incoming_orders(
    db: Session = Depends(get_db),
    staff = Depends(get_current_staff),
):
    require_permission(staff,"VIEW_ORDERS")

    if not staff.branch_id:
        raise HTTPException(403, "Staff not assigned to branch")

    return OrderRepository.get_incoming_orders_for_branch(
        db, staff.branch_id
    )

@router.post("/{order_id}/accept")
def accept_order(
    order_id: int,
    db: Session = Depends(get_db),
    staff = Depends(get_current_staff),
):
    require_permission(staff,"ACCEPT_ORDER")
    return VendorOrderService.accept_order(
        db, order_id, staff
    )


@router.post("/{order_id}/reject")
def reject_order(
    order_id: int,
    db: Session = Depends(get_db),
    staff = Depends(get_current_staff),
):
    return VendorOrderService.reject_order(
        db, order_id, staff
    )

@router.post("/{order_id}/move")
def move_order(
    order_id: int,
    status: OrderStatus,   # now VALID
    db: Session = Depends(get_db),
    staff = Depends(get_current_staff),
):
    return VendorOrderService.move_order(
        db=db, order_id=order_id, staff=staff, next_status=status,
    )


@router.get("/live")
def get_live_orders(
    db: Session = Depends(get_db),
    staff = Depends(get_current_staff)
):
    if not staff.branch_id:
        raise HTTPException(403, "Staff not assigned to branch")
    
    return OrderRepository.get_live_orders(db, staff.branch_id)


@router.get("/scheduled")
def get_all_scheduled_orders(
    db: Session = Depends(get_db),
    staff = Depends(get_current_staff),):
    if not staff.branch_id:
        raise HTTPException(403, "Staff not assigned to branch")
    
    return OrderRepository.get_all_scheduled_orders(db,staff.branch_id)

    


'''
@router.get("/scheduled")
def scheduled_orders(
    filter: str = Query(..., enum=["today", "tomorrow", "date"]),
    date_param: date | None = Query(None, alias="date"),
    db: Session = Depends(get_db),
    staff = Depends(get_current_staff)
):
    today = date.today()

    if filter == "today":
        target_date = today
    elif filter == "tomorrow":
        target_date = today + timedelta(days=1)
    else:
        if not date_param:
            raise HTTPException(400, "date required")
        target_date = date_param

    return OrderRepository.get_scheduled_orders_for_date(
        db,
        staff.branch_id,
        target_date
    )
'''


    
   