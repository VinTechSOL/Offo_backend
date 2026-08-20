from fastapi import APIRouter, Depends,HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.users.schemas import UserProfileUpdate, AddressCreate, UserOrderDetailResponse
from app.modules.users.service import UserService
from app.modules.users.order_service import UserOrderService
from app.modules.orders.repository import OrderRepository
from app.modules.orders.schemas import OrderResponse,OrderTimelineItem
from app.modules.locations.service import UserContextService
from app.modules.locations.schemas import UserContextCreateRequest
from app.modules.orders.service import OrderService

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


@router.get("/orders/active")
def get_my_active_orders(
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    orders = UserOrderService.list_orders(db, user.user_id)
    return [
        o for o in orders
        if o["classification"] == "ONGOING"
    ]

@router.get("/orders/scheduled")
def get_my_scheduled_orders(
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    orders = UserOrderService.list_orders(
        db,
        user.user_id,
    )

    return [
        order
        for order in orders
        if order["classification"] == "SCHEDULED"
    ]

@router.get("/orders")
def list_my_orders(
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    return UserOrderService.list_orders(db, user.user_id)


@router.get("/orders/{order_id}", response_model=UserOrderDetailResponse)
def get_my_order(
    order_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    return UserOrderService.get_order(db, user.user_id, order_id)


@router.post("/{order_id}/cancel")
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    """
    User can cancel only when order is still CREATED.
    """
    return OrderService.cancel_order_by_user(
        db=db,
        order_id=order_id,
        user_id=user.user_id,
    )


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


@router.post("/context")
def set_user_context(
    data: UserContextCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    UserContextService.set_context(
        db,
        user_id=user.user_id,
        city_id=data.city_id,
        campus_id=data.campus_id,
        building_id=data.building_id,
    )
    return {"status": "context_set"}


@router.get("/context")
def get_user_context(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return UserContextService.get_context(db, user.user_id)


@router.get("/context/details")
def get_user_context_details(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    data = UserContextService.get_context_details(db, user.user_id)

    if not data:
        raise HTTPException(status_code=404, detail="User context not set")

    return data