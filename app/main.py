"""
FastAPI app entrypoint

Run wiþ:
    uvicorn app.main:app --reload

Interactive docs available at:
    http://127.0.0.1:8000/docs   (Swagger UI)
    http://127.0.0.1:8000/redoc  (ReDoc)
"""

from contextlib import asynccontextmanager
 
from fastapi import FastAPI
from fastapi.responses import JSONResponse
 
from app.database import close_pool, get_pool
from app.routers.user import router as users_router
from app.routers.sales_order import router as sales_orders_router
from app.routers.restock_order import router as restock_orders_router
from app.routers.product import router as products_router
from app.routers.auth import router as auth_router

# Lifespan: warm-up pool on start, close on shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    get_pool()      # eager pool init
    yield
    close_pool()    # clean shutdown

# APP
app = FastAPI(
    title="Headless Ecommerce API",
    description=(
        "A headless RESTful ecommerce backend built with FastAPI + PostgreSQL. "
        "Manages products, customers, and orders with full CRUD support."
    ),
    version="1.0.0",
    lifespan=lifespan,
)
 
# Include routers
app.include_router(products_router)
app.include_router(users_router)
app.include_router(sales_orders_router)
app.include_router(restock_orders_router)
app.include_router(auth_router)

# Root healthcheck
@app.get("/", tags=["Health"])
def root():
    return JSONResponse({"status": "ok", "message": "Ecommerce API is running."})

