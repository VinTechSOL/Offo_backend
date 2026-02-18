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
        
        existing_item = CartRepository.get_cart_item(db, cart.cart_id,data.item_id)

        if existing_item:
            existing_item.quantity += data.quantity
        else:
            CartRepository.add_item(
            db,
            cart.cart_id,
            data.branch_id,
            data.item_id,
            branch_item.price,
            data.quantity
        )

        
        db.commit()
        return cart
    

    @staticmethod
    def get_active_cart_summary(db, user_id: int):
        cart = CartRepository.get_active_cart(db, user_id)

        if not cart:
            return None

        rows = CartRepository.get_cart_items(db, cart.cart_id)

        items = []
        subtotal = 0

        for r in rows:
           line_total = float(r.price_at_time) * r.quantity
           subtotal += line_total

           items.append({
              "item_id": r.item_id,
              "name": r.name,
              "image": r.image,
              "quantity": r.quantity,
              "price_at_time": float(r.price_at_time)
           })

        convenience_fee = 6
        total = subtotal + convenience_fee

        return {
            "cart_id": cart.cart_id,
            "branch_id": cart.branch_id,
            "status": cart.status,
            "items": items,
            "subtotal": subtotal,
            "convenience_fee": convenience_fee,
            "total": total,
        }
    

    @staticmethod
    def update_cart_item(db, user_id: int, data):
       cart = CartRepository.get_active_cart(db, user_id)
  
       if not cart:
        raise HTTPException(404, "No active cart")

       cart_item = CartRepository.get_cart_item(
        db, cart.cart_id, data.item_id
       )

       if not cart_item:
        raise HTTPException(404, "Item not found")

       if data.quantity <= 0:
        db.delete(cart_item)
       else:
        cart_item.quantity = data.quantity

       db.commit()
       return {"status":"updated!"}
    

    @staticmethod
    def clear_cart(db: Session, user_id: int):
      cart = CartRepository.get_active_cart(db, user_id)
      if not cart:
        return {"success": True}

      cart.status = "ABANDONED"
      db.commit()
      return {"success": True}


