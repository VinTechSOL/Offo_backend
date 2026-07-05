from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from contextlib import asynccontextmanager
from app.core.database import get_db, engine
from app.core.redis import redis_client
import os
from app.modules.auth.api import router as auth_router
from app.modules.users.api import router as users_router
from app.modules.vendor.api import router as vendor_router
from app.modules.menu.api import router as menu_router
from app.modules.cart.api import router as cart_router
from app.modules.orders.api import router as orders_router
from app.modules.notifications.api import router as notifications_router
from app.modules.staff.api import router as staff_auth_router
from app.modules.payments.api import router as payments_router
from app.modules.locations.api import router as locations_router
from app.workers.dev_scheduler import start_scheduler,shutdown_scheduler
from app.modules.payments.gateways.phonepe.webhook import router as phonepe_webhook_router
from app.modules.reports.api import router as reports_router
from app.modules.crm.api import router as crm_router
from app.middlewares.rate_limit import RateLimitMiddleware




'''
@asynccontextmanager
async def lifespan(app: FastAPI):
    #Startup
    
    print("application start")
    start_scheduler()
    yield
    #Shutdown
    print("application stop")
    shutdown_scheduler()
'''
app = FastAPI(
    title="OFFO Backend",
    version="1.0.0",
    #lifespan=lifespan
)

app.include_router(auth_router)
app.include_router(staff_auth_router)
app.include_router(users_router)
app.include_router(vendor_router)
app.include_router(menu_router)
app.include_router(cart_router)
app.include_router(orders_router)
app.include_router(payments_router)
app.include_router(notifications_router)
app.include_router(phonepe_webhook_router)
app.include_router(locations_router)
app.include_router(reports_router)
app.include_router(crm_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001"
        
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware)


@app.get("/health")
def health():
    return {"status": "ok"}





