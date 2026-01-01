from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.cart.schemas import AddToCartRequest
from app.modules.cart.service import CartService

router = APIRouter(prefix="/cart", tags=["Cart"])

@router.post("/add")
def add_to_cart(
    data: AddToCartRequest,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    return CartService.add_to_cart(db, user.user_id, data)
