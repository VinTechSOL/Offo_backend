from fastapi import APIRouter, Depends,HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.users.schemas import UserProfileUpdate, AddressCreate
from app.modules.users.service import UserService
from app.modules.users.order_service import UserOrderService
from app.modules.orders.repository import OrderRepository
from app.modules.orders.schemas import OrderResponse,OrderTimelineItem
router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me")
def get_me(
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    return user

@router.put("/me")
def update_profile(
    data: UserProfileUpdate,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    return UserService.update_profile(db, user, data)

@router.post("/address")
def add_address(
    data: AddressCreate,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    return UserService.add_address(db, user.user_id, data)


@router.get("/orders/active", response_model=list[OrderResponse])
def get_my_active_orders(
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    return OrderRepository.get_active_orders_for_user(
        db,
        user.user_id
    )

@router.get("/orders")
def list_my_orders(
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    return UserOrderService.list_orders(db, user.user_id)


@router.get("/orders/{order_id}")
def get_my_order(
    order_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    return UserOrderService.get_order(db, user.user_id, order_id)


@router.get(
    "/orders/{order_id}/timeline",
    response_model=list[OrderTimelineItem]
)
def get_order_timeline(
    order_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    order = OrderRepository.get_order(db, order_id)

    if not order or order.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Order not found")

    return OrderRepository.get_order_timeline(db, order_id)
