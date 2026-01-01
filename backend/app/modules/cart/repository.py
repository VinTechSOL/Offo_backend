from sqlalchemy.orm import Session
from sqlalchemy import select
from app.modules.cart.models import Cart, CartItem
from app.modules.menu.models import BranchMenuItem

class CartRepository:

    @staticmethod
    def get_active_cart(db: Session, user_id: int):
        return db.execute(
            select(Cart)
            .where(Cart.user_id == user_id, Cart.status == "ACTIVE")
        ).scalar_one_or_none()
    
    @staticmethod
    def get_cart_items(db, cart_id: int):
        return db.execute(
            select(CartItem).where(CartItem.cart_id == cart_id)
        ).scalars().all()   
  
    @staticmethod
    def create_cart(db: Session, user_id: int, branch_id: int):
        cart = Cart(user_id=user_id, branch_id=branch_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
        return cart
    
    @staticmethod
    def mark_cart_checked_out(db, cart):
        cart.status = "CHECKED_OUT"
        db.add(cart)
        db.flush()

    @staticmethod
    def get_branch_item(db: Session, branch_id: int, item_id: int):
        return db.execute(
            select(BranchMenuItem)
            .where(
                BranchMenuItem.branch_id == branch_id,
                BranchMenuItem.item_id == item_id,
                BranchMenuItem.is_available == True
            )
        ).scalar_one_or_none()

    @staticmethod
    def add_item(db: Session, cart_id: int, branch_id: int, item_id: int, price: float, quantity: int):
        item = CartItem(
            cart_id=cart_id,
            branch_id=branch_id,
            item_id=item_id,
            price_at_time=price,
            quantity=quantity
        )
        db.add(item)
        db.commit()
        return item
