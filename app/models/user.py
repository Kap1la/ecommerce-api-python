from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from schemas import UserCreate, UserUpdate, UserRoleUpdate


# Create
def create_user(
    conn: psycopg2.extensions.connection, data: UserCreate
) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO users (name, email, role, is_active)
            VALUES (%s, %s, %s, %s)
            RETURNING *;
            """,
            (data.name, data.email, data.role, data.is_active),
        )
        row = cur.fetchone()
        conn.commit()
        return row

# Read
def get_all_users(conn: psycopg2.extensions.connection) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM users ORDER BY id;")
        return cur.fetchall()
    
def get_user_by_id(
    conn: psycopg2.extensions.connection, user_id: int
) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM users WHERE id = %s;", (user_id))
        return cur.fetchone()

# Update
def update_user(
    conn: psycopg2.extensions.connection, user_id: int, data: UserUpdate | UserRoleUpdate
) -> dict | None:
    
    fields = data.model_dump(exclude_unset=True)
    if not fields:
        return get_user_by_id(conn, user_id)
    
    set_clause = ", ".join(f"{key} = %s" for key in fields)
    values = list(fields.values()) + [user_id]

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"UPDATE users SET {set_clause} WHERE id = %s RETURNING *;",
            values,
        )
        row = cur.fetchone()
    conn.commit()
    return row

# Rather than delete a user, it is better logically to deactivate it,
# so that records remain intelligible and users can be restored if needed
def set_user_active_status(
   conn: psycopg2.extensions.connection, user_id: int, is_active: bool, force: bool = False 
) -> dict | None:
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            
            # Check if user exists
            cur.execute(
                "SELECT * FROM users WHERE id = %s;",
                (user_id,)
            )
            user = cur.fetchone()
            if user is None:
                return None

            # Check if deactivating, if so, check if pending order belonging to this user
            if not is_active:
                cur.execute(
                    """
                    SELECT po.id as sales_order_id
                    FROM sales_orders po
                    WHERE po.user_id = %s
                    AND po.status = 'pending';
                    """,
                    (user_id,)
                )
                blocking_sales = cur.fetchall()

                cur.execute(
                    """
                    SELECT ro.id as restock_order_id
                    FROM restock_orders ro
                    WHERE ro.user_id = %s
                    AND ro.status = 'pending';
                    """,
                    (user_id,)
                )
                blocking_restock = cur.fetchall()

                # if blocking orders exist, and force is not selected,
                # display blocking order ids and inform of force option
                if (blocking_sales or blocking_restock) and not force:
                    
                    # create error message
                    error_msg = f"user {user_id} is referenced by pending "
                    if blocking_sales:
                        sales_order_ids = list({row["sales_order_id"] for row in blocking_sales})
                        error_msg += f"sales orders: {sales_order_ids}. "
                    if blocking_restock:
                        restock_order_ids = list({row["restock_order_id"] for row in blocking_restock})
                        error_msg += f"restock orders: {restock_order_ids}. "
                    error_msg += f"Use force=true to force deactivation."

                    raise ValueError(error_msg)

                # if blocking orders and force enabled
                # cancel all orders referencing the user
                if (blocking_sales or blocking_restock) and force:
                    # process for sales orders
                    if blocking_sales:
                        order_ids = list({row["order_id"] for row in blocking_sales})

                        # strike out sales orders for this user
                        cur.execute(
                            """
                            UPDATE sales_orders
                            SET status = 'cancelled'
                            WHERE id = ANY(%s);
                            """,
                            (order_ids)
                        )

                    # process for restock orders
                    if blocking_restock:
                        order_ids = list({row["order_id"] for row in blocking_restock})

                        # strike out restock orders for this user
                        cur.execute(
                            """
                            UPDATE restock_orders
                            SET status = 'cancelled'
                            WHERE id = ANY(%s);
                            """,
                            (order_ids)
                        )

            cur.execute(
                """
                UPDATE users
                SET is_active = %s
                WHERE id = %s
                RETURNING *;
                """,
                (is_active, user_id),
            )
            updated = cur.fetchone()
        
        conn.commit()
        return updated

    except Exception:
        conn.rollback()
        raise
