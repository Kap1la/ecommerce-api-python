"""
Manages a psycopg2 connection pool
FastAPI dependency 'get_db()' yields one connection / request
and returns it to the pool upon request completion
"""


from contextlib import contextmanager
from typing import Generator
 
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

from app.config import settings
 
# Connection pool (min=1, max=10 connections)
_pool: pool.SimpleConnectionPool | None = None
 
 
def get_pool() -> pool.SimpleConnectionPool:
    # Lazily create and return the global connection pool
    global _pool
    if _pool is None:
        _pool = pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            host=settings.db_host,
            port=settings.db_port,
            dbname=settings.db_name,
            user=settings.db_user,
            password=settings.db_password,
        )
    return _pool
 
 
def close_pool() -> None:
    # Close all connections in the pool (called on app shutdown)
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None
 
 
# FastAPI dependency
@contextmanager
def _db_connection():
    # Context manager that checks out / returns a connection
    connection = get_pool().getconn()
    try:
        yield connection
    except Exception:
        connection.rollback()
        raise
    finally:
        get_pool().putconn(connection)
 
 
def get_db() -> Generator:
    """
    FastAPI dependency.  Use in route functions like:
 
        def my_route(db=Depends(get_db)):
            with db.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(...)
    """
    with _db_connection() as conn:
        yield conn


