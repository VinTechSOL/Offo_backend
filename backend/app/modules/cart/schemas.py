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

class CartItemResponse(BaseModel):
    item_id: int
    name: str
    image: str | None
    quantity: int
    price_at_time: float

    class Config:
        from_attributes = True

class CartDetailResponse(BaseModel):
    cart_id: int
    branch_id: int
    status: str
    items: list[CartItemResponse]
    subtotal: float
    convenience_fee: float
    total: float

class UpdateCartItemRequest(BaseModel):
    item_id: int
    quantity: int
