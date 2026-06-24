from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from schemas.product import ProductCreate, ProductUpdate


# Create
def create_product(
    conn: psycopg2.extensions.connection, data: ProductCreate
) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO products (name, description, price, stock)
            VALUES (%s, %s, %s, %s)
            RETURNING *;
            """,
            (data.name, data.description, data.price, data.stock),
        )
        row = cur.fetchone()
        conn.commit()
        return row

# Read
def get_all_products(conn: psycopg2.extensions.connection) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM products ORDER BY id;")
        return cur.fetchall()

def get_product_by_id(
    conn: psycopg2.extensions.connection, product_id: int
) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM products WHERE id = %s;", (product_id))
        return cur.fetchone()

# Update
def update_product(
    conn: psycopg2.extensions.connection, product_id: int, data: ProductUpdate
) -> dict | None:
    
    fields = data.model_dump(exclude_unset=True)
    if not fields:
        return get_product_by_id(conn, product_id)
    
    set_clause = ", ".join(f"{key} = %s" for key in fields)
    values = list(fields.values()) + [product_id]

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"UPDATE products SET {set_clause} WHERE id = %s RETURNING *;",
            values,
        )
        row = cur.fetchone()
        conn.commit()
        return row

def decrement_stock(
    conn: psycopg2.extensions.connection, product_id: int, quantity: int
) -> dict | None:
    """
    Atomically decrease stock. Returns None if the product exists not
    or there's insufficient stock -> caller should rollback
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            UPDATE products
            SET stock = stock - %s
            WHERE id = %s AND stock >= %s
            RETURNING *;
            """,
            (quantity, product_id, quantity),
        )
        return cur.fetchone()


def increment_stock(
    conn: psycopg2.extensions.connection, product_id: int, quantity: int
) -> dict | None:
    """
    Atomically increase stock. Returns None if the product exists not
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            UPDATE products
            SET stock = stock + %s
            WHERE id = %s
            RETURNING *;
            """,
            (quantity, product_id),
        )
        return cur.fetchone()


# Rather than delete a product, it is better logically to deactivate it,
# so that records remain intelligible and products can be restored if needed
def deactivate_product(
   conn: psycopg2.extensions.connection, product_id: int 
) -> bool:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            UPDATE products
            SET is_active = FALSE
            WHERE id = %s
            RETURNING *;
            """,
            (product_id),
        )
        return cur.fetchone()

    

def reactivate_product(
   conn: psycopg2.extensions.connection, product_id: int 
) -> bool:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            UPDATE products
            SET is_active = TRUE
            WHERE id = %s
            RETURNING *;
            """,
            (product_id),
        )
        return cur.fetchone()