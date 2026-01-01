from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db, engine
from app.core.redis import redis_client

from app.modules.auth.api import router as auth_router
from app.modules.users.api import router as users_router
from app.modules.vendor.api import router as vendor_router

from app.modules.menu.api import router as menu_router
from app.modules.cart.api import router as cart_router
from app.modules.orders.api import router as orders_router


app = FastAPI(
    title="OFFO Backend",
    version="1.0.0"
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(vendor_router)
app.include_router(menu_router)
app.include_router(cart_router)
app.include_router(orders_router)

@app.get("/health")
def health():
    return {"status": "ok"}

