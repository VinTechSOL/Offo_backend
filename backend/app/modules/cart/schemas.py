from pydantic import BaseModel

class AddToCartRequest(BaseModel):
    branch_id: int
    item_id: int
    quantity: int = 1


class UpdateCartItem(BaseModel):
    quantity: int


class CartResponse(BaseModel):
    cart_id: int
    status: str
