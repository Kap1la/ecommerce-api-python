# FastAPI router for CRUD operations on products

from typing import Annotated

import psycopg2
from fastapi import APIRouter, Depends, HTTPException, status

from database import get_db
from models.product import (
    create_product,
    get_all_products,
    get_product_by_id,
    update_product,
    decrement_stock,
    increment_stock,
    deactivate_product,
    reactivate_product,
)
from schemas.product import ProductCreate, ProductResponse, ProductUpdate

router = APIRouter(prefix="/products", tags=["Products"])

DbDep = Annotated[psycopg2.extensions.connection, Depends(get_db)]


# Create
@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def add_product(data: ProductCreate, db: DbDep):
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
def edit_product(product_id: int, data: ProductUpdate, db: DbDep):
    # (Partially) update a product.
    product = update_product(db, product_id, data)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found.")
    return product

@router.patch("/{product_id}/deactivate", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_product(product_id: int, db: DbDep):
    # Deactivate a product
    if not deactivate_product(db, product_id):
        raise HTTPException(status_code=404, detail="Product not found.")

@router.patch("/{product_id}/reactivate", status_code=status.HTTP_204_NO_CONTENT)
def reactivate_product(product_id: int, db: DbDep):
    # Reactivate a product
    if not reactivate_product(db, product_id):
        raise HTTPException(status_code=404, detail="Product not found.")
    
@router.patch("/{product_id}/stock/{quantity}", response_model=ProductResponse)
def stock_product(product_id: int, quantity: int, db: DbDep):
    # Restock a product
    product = increment_stock(db, product_id, quantity)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    return product