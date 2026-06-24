# FastAPI router for CRUD operations on products

from typing import Annotated

import psycopg2
from fastapi import APIRouter, Query, Depends, HTTPException, status

from database import get_db
from models.product import (
    create_product,
    get_all_products,
    get_product_by_id,
    update_product,
    set_product_active_status,
)
from schemas import ProductCreate, ProductResponse, ProductUpdate

router = APIRouter(prefix="/products", tags=["Products"])

DbDep = Annotated[psycopg2.extensions.connection, Depends(get_db)]


# Create
@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def add_product(
    data: ProductCreate, 
    db: DbDep, 
    admin=Depends(require_admin),
):
    # Create a new product.
    return create_product(db, data)

# Read
@router.get("/", response_model=list[ProductResponse])
def list_products(db: DbDep):
    # Return all products
    return get_all_products(db);


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: DbDep):
    # Return a single product by ID
    product = get_product_by_id(db, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found.")
    return product

# Update
@router.patch("/{product_id}", response_model=ProductResponse)
def edit_product(
    product_id: int, 
    data: ProductUpdate, 
    db: DbDep, 
    admin=Depends(require_admin),
):
    # (Partially) update a product.
    product = update_product(db, product_id, data)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found.")
    return product

@router.patch("/{product_id}/active", response_model=ProductResponse, status_code=status.HTTP_200_OK)
def set_product_active(
    product_id: int,
    is_active: bool = Query(...),
    force: bool = Query(default=False),
    db=Depends(get_db),
    admin=Depends(require_admin),
):
    try:
        product = set_product_active_status(db, product_id, is_active, force)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found.")

    return product