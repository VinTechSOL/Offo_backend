from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.orders.schemas import PlaceOrderRequest, PlaceOrderResponse
from app.modules.orders.service import OrderService
from app.modules.orders.service import VendorOrderService
from app.modules.orders.repository import OrderRepository
from app.modules.orders.constants import OrderStatus

router = APIRouter(prefix="/vendor/orders", tags=["Vendor Orders"])

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/place", response_model=PlaceOrderResponse)
def place_order(
    data: PlaceOrderRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    order = OrderService.place_order(db, user.user_id, data)
    return {"order_id": order.order_id, "status": order.order_status}


@router.get("/incoming")
def get_incoming_orders(
    db: Session = Depends(get_db),
    vendor = Depends(get_current_user)
):
    return OrderRepository.get_incoming_orders_for_branch(
        db, vendor.branch_id
    )


@router.post("/{order_id}/accept")
def accept_order(
    order_id: int,
    db: Session = Depends(get_db),
    vendor = Depends(get_current_user)
):
    return VendorOrderService.accept_order(
        db, order_id, vendor.branch_id
    )


@router.post("/{order_id}/reject")
def reject_order(
    order_id: int,
    db: Session = Depends(get_db),
    vendor = Depends(get_current_user)
):
    return VendorOrderService.reject_order(
        db, order_id, vendor.branch_id
    )


@router.post("/{order_id}/move")
def move_order(
    order_id: int,
    status: str,
    db: Session = Depends(get_db),
    vendor = Depends(get_current_user)
):
    return VendorOrderService.move_order(
        db, order_id, vendor.branch_id, status
    )
