from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.modules.cart.repository import CartRepository

class CartService:

    @staticmethod
    def add_to_cart(db: Session, user_id: int, data):
        cart = CartRepository.get_active_cart(db, user_id)

        if cart and cart.branch_id != data.branch_id:
            cart.status = "ABANDONED"
            db.commit()
            cart = None

        if not cart:
            cart = CartRepository.create_cart(db, user_id, data.branch_id)

        branch_item = CartRepository.get_branch_item(
            db, data.branch_id, data.item_id
        )

        if not branch_item:
            raise HTTPException(400, "Item not available")

        CartRepository.add_item(
            db,
            cart.cart_id,
            data.branch_id,
            data.item_id,
            branch_item.price,
            data.quantity
        )

        return cart
