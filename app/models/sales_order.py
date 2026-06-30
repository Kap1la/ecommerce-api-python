from typing import Any
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor

from schemas import SalesOrderStatusUpdate, SalesOrderResponse, SalesOrderItemCreate, SalesOrderItemUpdate, SalesOrderItemResponse
from product import get_active_product_by_id, decrement_stock


order_status_state_machine = {
    "cancelled": {"pending"},
    "pending": {"cancelled", "confirmed"},
    "confirmed": {"shipped"},
    "shipped": {"delivered"},
    "delivered": {},
}

shipping_statuses = {"shipped", "delivered"}

# Create
def create_sales_order(
    conn: psycopg2.extensions.connection,
    user_id: int
) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO sales_orders (user_id, status)
            VALUES (%s, %s)
            RETURNING *;
            """,
            (user_id, 'pending')
        )
        row = cur.fetchone()
    conn.commit()
    return row

def add_sales_order_item(
    conn: psycopg2.extensions.connection,
    data: SalesOrderItemCreate,
    user_id: int,
) -> dict | None:
    try:
        # Verify that a sales order with the specified id exists for the spcified user
        # and that its status is pending
        sales_order = get_sales_order_by_user_and_id(conn, user_id, data.sales_order_id) is None
        
        if sales_order is None:
            raise NameError(f"Sales order {data.sales_order_id} not found for user {user_id}.")
        if sales_order.status != 'pending':
            raise ValueError(f"Sales order is finalized and cannot be edited.")
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO sales_order_items (sales_order_id, product_id, quantity, unit_price, discount_total)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *;
                """,
                (data.sales_order_id, data.product_id, data.quantity, data.unit_price, data.discount_total)
            )
            row = cur.fetchone()
        conn.commit()
        return row
        
    except Exception as e:
        print(e)        

# Read
def get_all_sales_orders(
    conn: psycopg2.extensions.connection
) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT * FROM sales_orders ORDER BY id;
            """
        )
        return cur.fetchall()


def get_sales_orders_by_user(
    conn: psycopg2.extensions.connection,
    user_id: int
) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT * FROM sales_orders WHERE user_id = %s;
            """,
            (user_id,)
        )
        return cur.fetchall()


def get_sales_order_by_user_and_id(
    conn: psycopg2.extensions.connection,
    user_id: int,
    sales_order_id: int
) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT * FROM sales_orders WHERE user_id = %s
            AND id = %s;
            """,
            (user_id, sales_order_id)
        )
        return cur.fetchone()
        

def get_sales_order_by_id(
    conn: psycopg2.extensions.connection,
    sales_order_id: int
) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT * FROM sales_orders WHERE id = %s;
            """,
            (sales_order_id,)
        )
        return cur.fetchone()

def get_sales_order_items_by_sales_order(
    conn: psycopg2.extensions.connection,
    sales_order_id: int
) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT * FROM sales_order_items WHERE sales_order_id = %s;
            """,
            (sales_order_id,)
        )
        return cur.fetchall()


def get_sales_order_and_items_by_id(
    conn: psycopg2.extensions.connection,
    sales_order_id: int
) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT * 
            FROM sales_orders s
            JOIN sales_order_items i
            ON s.id = sales_order_items.sales_order_id
            WHERE sales_order_id = %s;
            """,
            (sales_order_id,)
        )
        return cur.fetchall()


def get_sales_order_item_for_sales_order_by_product(
    conn: psycopg2.extensions.connection,
    sales_order_id: int,
    product_id: int
) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT * FROM sales_orders WHERE sales_order_id = %s
            AND product_id = %s;
            """,
            (sales_order_id, product_id)
        )
        return cur.fetchone()


# Update
def update_sales_order_status(
    conn: psycopg2.extensions.connection,
    status: str,
    sales_order_id: int,
) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:        
        cur.execute(
            """
            UPDATE sales_orders
            SET status = %s
            WHERE id = %s AND user_id = %s
            RETURNING *;
            """,
            (status, sales_order_id),
        )
        return cur.fetchone()
    # don't commit here, this is a helper


def update_sales_order_shipping_status(
    conn: psycopg2.extensions.connection,
    sales_order_id: int,
    data: SalesOrderStatusUpdate,
    admin: bool
) -> dict | None:
                
    sales_order = get_sales_order_by_id(conn, sales_order_id)

    # Check if sales order exists 
    # and that user has sufficient permissions
    if sales_order is None or not admin:
        return None # TODO raise error
        
    # Check if requested status change is a valid transitions
    # and if it is a shipping status
    if (data.status not in shipping_statuses or 
            data.status not in order_status_state_machine[sales_order["status"]]):
        return None # TODO raise error
        
        
    row = update_sales_order_status(conn, data.status, sales_order_id)
    
    if row is None:
        conn.rollback()
        return None # TODO raise error
    
    conn.commit()
    return row


def confirm_sales_order(
    conn: psycopg2.extensions.connection,
    sales_order_id: int,
    user_id: int,
    admin: bool
) -> dict | None:
        
    sales_order = get_sales_order_by_id(conn, sales_order_id)

    # Check if sales order exists 
    # and that user has sufficient permissions
    # and that the order is pending
    if (sales_order is None or 
        (sales_order["user_id"] != user_id and not admin) or 
        sales_order["status"] != "pending"):
        return None # TODO raise error
        
    sales_order_items = get_sales_order_items_by_sales_order(conn, sales_order_id)

    expected_total = Decimal(0.00)

    for item in sales_order_items:
        if item["struck_out"]:
            continue

        product = get_active_product_by_id(conn, item["product_id"])

        if (product is None 
            or product["price"] != item["unit_price"]
            or product["stock"] < item["quantity"]):
            conn.rollback()
            return None # TODO raise error
            
        decr = decrement_stock(conn, item["product_id"], item["quantity"])
        if decr is None:
            conn.rollback()
            return None # TODO raise error
            
        total += (item["quantity"] * item["unit_price"] - item["discount_total"])
        
    # Check that total was correct
    if total != sales_order["total"]:
        conn.rollback()
        return None # TODO raise error
        
    row = update_sales_order_status(conn, "confirmed", sales_order_id)
    
    if row is None:
        conn.rollback()
        return None # TODO raise error
    
    conn.commit()
    return row


def set_sales_order_cancelled(
    conn: psycopg2.extensions.connection,
    sales_order_id: int,
    user_id: int,
    admin: bool,
    is_cancel: bool
) -> dict | None:
        
    sales_order = get_sales_order_by_id(conn, sales_order_id)

    # Check if sales order exists or if user has sufficient permissions
    if sales_order is None or (sales_order["user_id"] != user_id and not admin):
        return None # TODO raise error
        
    status = "cancelled" if is_cancel else "pending"

    if status not in order_status_state_machine[sales_order["status"]]:
        return None # TODO raise error
        
    row = update_sales_order_status(conn, status, sales_order_id)
    
    if row is None:
        conn.rollback()
        return None # TODO raise error
    
    conn.commit()
    return row


def update_sales_order_item(
    conn: psycopg2.extensions.connection,
    data: SalesOrderItemUpdate,
    product_id: int,
    sales_order_id: int,
    user_id: int,
    admin: bool
) -> dict | None:
    
    sales_order = get_sales_order_by_user_and_id(conn, user_id, sales_order_id)

    if sales_order is None or (sales_order["user_id"] != user_id and not admin):
        return None
    
    sales_order_item = get_sales_order_item_for_sales_order_by_product(conn, sales_order_id, product_id)
    
    if sales_order_item is None:
        return None
    
    fields = data.model_dump(exclude_unset=True)
    if not fields:
        return sales_order_item
    
    set_clause = ", ".join(f"{key} = %s" for key in fields)
    values = list(fields.values()) + [sales_order_item["id"]]

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"UPDATE sales_order_items SET {set_clause} WHERE id = %s RETURNING *;",
            values,
        )
        row = cur.fetchone()
    
    if row is None:
        conn.rollback()
        return None
        
    conn.commit()
    return row
