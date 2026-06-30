from typing import Any
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor

from schemas import RestockOrderStatusUpdate, RestockOrderResponse, RestockOrderItemCreate, RestockOrderItemUpdate, RestockOrderItemResponse
from product import get_active_product_by_id, increment_stock


order_status_state_machine = {
    "cancelled": {"pending"},
    "pending": {"cancelled", "confirmed"},
    "confirmed": {"shipped"},
    "shipped": {"delivered"},
    "delivered": {},
}

shipping_statuses = {"shipped", "delivered"}

# Create
def create_restock_order(
    conn: psycopg2.extensions.connection,
    user_id: int
) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO restock_orders (user_id, status)
            VALUES (%s, %s)
            RETURNING *;
            """,
            (user_id, 'pending')
        )
        row = cur.fetchone()
    conn.commit()
    return row

def add_restock_order_item(
    conn: psycopg2.extensions.connection,
    data: RestockOrderItemCreate,
    user_id: int,
) -> dict | None:
    try:
        # Verify that a restock order with the specified id exists for the spcified user
        # and that its status is pending
        restock_order = get_restock_order_by_user_and_id(conn, user_id, data.restock_order_id) is None
        
        if restock_order is None:
            raise NameError(f"Restock order {data.restock_order_id} not found for user {user_id}.")
        if restock_order.status != 'pending':
            raise ValueError(f"Restock order is finalized and cannot be edited.")
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO restock_order_items (restock_order_id, product_id, quantity)
                VALUES (%s, %s, %s)
                RETURNING *;
                """,
                (data.restock_order_id, data.product_id, data.quantity)
            )
            row = cur.fetchone()
        conn.commit()
        return row
        
    except Exception as e:
        print(e)        

# Read
def get_all_restock_orders(
    conn: psycopg2.extensions.connection
) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT * FROM restock_orders ORDER BY id;
            """
        )
        return cur.fetchall()


def get_restock_orders_by_user(
    conn: psycopg2.extensions.connection,
    user_id: int
) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT * FROM restock_orders WHERE user_id = %s;
            """,
            (user_id,)
        )
        return cur.fetchall()


def get_restock_order_by_user_and_id(
    conn: psycopg2.extensions.connection,
    user_id: int,
    restock_order_id: int
) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT * FROM restock_orders WHERE user_id = %s
            AND id = %s;
            """,
            (user_id, restock_order_id)
        )
        return cur.fetchone()
        

def get_restock_order_by_id(
    conn: psycopg2.extensions.connection,
    restock_order_id: int
) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT * FROM restock_orders WHERE id = %s;
            """,
            (restock_order_id,)
        )
        return cur.fetchone()

def get_restock_order_items_by_restock_order(
    conn: psycopg2.extensions.connection,
    restock_order_id: int
) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT * FROM restock_order_items WHERE restock_order_id = %s;
            """,
            (restock_order_id,)
        )
        return cur.fetchall()


def get_restock_order_and_items_by_id(
    conn: psycopg2.extensions.connection,
    restock_order_id: int
) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT * 
            FROM restock_orders r
            JOIN restock_order_items i
            ON r.id = restock_order_items.restock_order_id
            WHERE restock_order_id = %s;
            """,
            (restock_order_id,)
        )
        return cur.fetchall()


def get_restock_order_item_for_restock_order_by_product(
    conn: psycopg2.extensions.connection,
    restock_order_id: int,
    product_id: int
) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT * FROM restock_orders WHERE restock_order_id = %s
            AND product_id = %s;
            """,
            (restock_order_id, product_id)
        )
        return cur.fetchone()


# Update
def update_restock_order_status(
    conn: psycopg2.extensions.connection,
    status: str,
    restock_order_id: int,
) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:        
        cur.execute(
            """
            UPDATE restock_orders
            SET status = %s
            WHERE id = %s AND user_id = %s
            RETURNING *;
            """,
            (status, restock_order_id),
        )
        return cur.fetchone()
    # don't commit here, this is a helper


def update_restock_order_shipping_status(
    conn: psycopg2.extensions.connection,
    restock_order_id: int,
    data: RestockOrderStatusUpdate,
    admin: bool
) -> dict | None:
                
    restock_order = get_restock_order_by_id(conn, restock_order_id)

    # Check if restock order exists 
    # and that user has sufficient permissions
    if restock_order is None or not admin:
        return None # TODO raise error
        
    # Check if requested status change is a valid transitions
    # and if it is a shipping status
    if (data.status not in shipping_statuses or 
            data.status not in order_status_state_machine[restock_order["status"]]):
        return None # TODO raise error
        
        
    row = update_restock_order_status(conn, data.status, restock_order_id)
    
    if row is None:
        conn.rollback()
        return None # TODO raise error
    
    conn.commit()
    return row


def confirm_restock_order(
    conn: psycopg2.extensions.connection,
    restock_order_id: int,
    user_id: int,
    admin: bool
) -> dict | None:
        
    restock_order = get_restock_order_by_id(conn, restock_order_id)

    # Check if restock order exists 
    # and that user has sufficient permissions
    # and that the order is pending
    if (restock_order is None or 
        (restock_order["user_id"] != user_id and not admin) or 
        restock_order["status"] != "pending"):
        return None # TODO raise error
        
    restock_order_items = get_restock_order_items_by_restock_order(conn, restock_order_id)

    for item in restock_order_items:
        if item["struck_out"]:
            continue

        product = get_active_product_by_id(conn, item["product_id"])

        if (product is None 
            or product["stock"] < item["quantity"]):
            conn.rollback()
            return None # TODO raise error
            
        incr = increment_stock(conn, item["product_id"], item["quantity"])
        if incr is None:
            conn.rollback()
            return None # TODO raise error
        
    row = update_restock_order_status(conn, "confirmed", restock_order_id)
    
    if row is None:
        conn.rollback()
        return None # TODO raise error
    
    conn.commit()
    return row


def set_restock_order_cancelled(
    conn: psycopg2.extensions.connection,
    restock_order_id: int,
    user_id: int,
    admin: bool,
    is_cancel: bool
) -> dict | None:
        
    restock_order = get_restock_order_by_id(conn, restock_order_id)

    # Check if restock order exists or if user has sufficient permissions
    if restock_order is None or (restock_order["user_id"] != user_id and not admin):
        return None # TODO raise error
        
    status = "cancelled" if is_cancel else "pending"

    if status not in order_status_state_machine[restock_order["status"]]:
        return None # TODO raise error
        
    row = update_restock_order_status(conn, status, restock_order_id)
    
    if row is None:
        conn.rollback()
        return None # TODO raise error
    
    conn.commit()
    return row


def update_restock_order_item(
    conn: psycopg2.extensions.connection,
    data: RestockOrderItemUpdate,
    product_id: int,
    restock_order_id: int,
    user_id: int,
    admin: bool
) -> dict | None:
    
    restock_order = get_restock_order_by_user_and_id(conn, user_id, restock_order_id)

    if restock_order is None or (restock_order["user_id"] != user_id and not admin):
        return None
    
    restock_order_item = get_restock_order_item_for_restock_order_by_product(conn, restock_order_id, product_id)
    
    if restock_order_item is None:
        return None
    
    fields = data.model_dump(exclude_unset=True)
    if not fields:
        return restock_order_item
    
    set_clause = ", ".join(f"{key} = %s" for key in fields)
    values = list(fields.values()) + [restock_order_item["id"]]

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"UPDATE restock_order_items SET {set_clause} WHERE id = %s RETURNING *;",
            values,
        )
        row = cur.fetchone()
    
    if row is None:
        conn.rollback()
        return None
        
    conn.commit()
    return row
