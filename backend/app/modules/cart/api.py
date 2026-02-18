from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.cart.schemas import AddToCartRequest,CartDetailResponse,UpdateCartItemRequest
from app.modules.cart.service import CartService

router = APIRouter(prefix="/cart", tags=["Cart"])

@router.post("/add")
def add_to_cart(
    data: AddToCartRequest,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    return CartService.add_to_cart(db, user.user_id, data)

@router.get("/active", response_model=CartDetailResponse | None)
def get_active_cart(
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    data = CartService.get_active_cart_summary(db,user.user_id)
    return data

@router.patch("/item")
def update_cart_item(
    data: UpdateCartItemRequest,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    return CartService.update_cart_item(db, user.user_id, data)


@router.delete("/clear")
def clear_cart(
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    return CartService.clear_cart(db, user.user_id)
