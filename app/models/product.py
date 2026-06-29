from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from schemas import ProductCreate, ProductUpdate


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
    
def get_all_active_products(conn: psycopg2.extensions.connection) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM products WHERE is_active = TRUE ORDER BY id;")
        return cur.fetchall()

def get_product_by_id(
    conn: psycopg2.extensions.connection, product_id: int
) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM products WHERE id = %s;", (product_id,))
        return cur.fetchone()

def get_active_product_by_id(
    conn: psycopg2.extensions.connection, product_id: int
) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM products WHERE id = %s AND is_active = TRUE;", (product_id,))
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

        if row is None:
            conn.rollback()
            return None
        
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
        # don't commit here, this is a helper


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
        # don't commit here, this is a helper


# Rather than delete a product, it is better logically to deactivate it,
# so that records remain intelligible and products can be restored if needed
def set_product_active_status(
   conn: psycopg2.extensions.connection, product_id: int, is_active: bool, force: bool = False 
) -> dict | None:
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            
            # Check if product exists
            cur.execute(
                "SELECT * FROM products WHERE id = %s;",
                (product_id,)
            )
            product = cur.fetchone()
            if product is None:
                return None

            # Check if deactivating, if so, check if pending order involving this product
            if not is_active:
                cur.execute(
                    """
                    SELECT po.id as sales_order_id, poi.id as s_o_item_id
                    FROM sales_order_items poi
                    JOIN sales_orders po ON po.id = poi.sales_order_id
                    WHERE poi.product_id = %s
                    AND po.status = 'pending';
                    """,
                    (product_id,)
                )
                blocking_sales = cur.fetchall()

                cur.execute(
                    """
                    SELECT ro.id as restock_order_id, roi.id as r_o_item_id
                    FROM restock_order_items roi
                    JOIN restock_orders ro ON ro.id = roi.restock_order_id
                    WHERE roi.product_id = %s
                    AND ro.status = 'pending';
                    """,
                    (product_id,)
                )
                blocking_restock = cur.fetchall()

                # if blocking orders exist, and force is not selected,
                # display blocking order ids and inform of force option
                if (blocking_sales or blocking_restock) and not force:
                    
                    # create error message
                    error_msg = f"Product {product_id} is referenced by pending "
                    if blocking_sales:
                        sales_order_ids = list({row["sales_order_id"] for row in blocking_sales})
                        error_msg += f"sales orders: {sales_order_ids}. "
                    if blocking_restock:
                        restock_order_ids = list({row["restock_order_id"] for row in blocking_restock})
                        error_msg += f"restock orders: {restock_order_ids}. "
                    error_msg += f"Use force=true to force deactivation."

                    raise ValueError(error_msg)

                # if blocking orders and force enabled
                # remove all order items referencing the product from the blocking orders
                if (blocking_sales or blocking_restock) and force:
                    # process for sales orders
                    if blocking_sales:
                        item_ids = [row["s_o_item_id"] for row in blocking_sales]
                        order_ids = list({row["sales_order_id"] for row in blocking_sales})

                        # strike out sales order items for this product
                        cur.execute(
                            """
                            UPDATE sales_order_items
                            SET struck_out = TRUE
                            WHERE id = ANY(%s);
                            """,
                            #"DELETE FROM sales_order_items WHERE id = ANY(%s);",
                            (item_ids,)
                        )
                        # cancel sales orders that no longer have any associated valid sales order items
                        cur.execute(
                            """
                            UPDATE sales_orders
                            SET status = 'cancelled'
                            WHERE id = ANY(%s)
                            AND NOT EXISTS (
                                SELECT 1 FROM sales_order_items
                                WHERE sales_order_id = sales_orders.id
                                AND struck_out = FALSE
                            );
                            """,
                            (order_ids,)
                        )

                    # process for restock orders
                    if blocking_restock:
                        item_ids = [row["r_o_item_id"] for row in blocking_restock]
                        order_ids = list({row["restock_order_id"] for row in blocking_restock})

                        # strike out restock order items for this product
                        cur.execute(
                            """
                            UPDATE restock_order_items
                            SET struck_out = TRUE
                            WHERE id = ANY(%s);
                            """,
                            #"DELETE FROM restock_order_items WHERE id = ANY(%s);",
                            (item_ids,)
                        )
                        # cancel restock orders that no longer have any associated valid restock order items
                        cur.execute(
                            """
                            UPDATE restock_orders
                            SET status = 'cancelled'
                            WHERE id = ANY(%s)
                            AND NOT EXISTS (
                                SELECT 1 FROM restock_order_items
                                WHERE restock_order_id = restock_orders.id
                                AND struck_out = FALSE
                            );
                            """,
                            (order_ids,)
                        )

            cur.execute(
                """
                UPDATE products
                SET is_active = %s
                WHERE id = %s
                RETURNING *;
                """,
                (is_active, product_id),
            )
            updated = cur.fetchone()
        
        conn.commit()
        return updated

    except Exception:
        conn.rollback()
        raise
