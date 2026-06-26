-- ============================================================
-- PostgreSQL Schema
-- Run the following once to initialize the database:
-- psql -U <user> -d <dbname> -f init_db.sql
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(255)        NOT NULL,
    email               VARCHAR(255) UNIQUE NOT NULL,
    password_hash       VARCHAR(255)        NOT NULL,
    role                VARCHAR(20)         NOT NULL DEFAULT 'customer'
                            CHECK (role IN ('customer', 'admin')), 
    is_active           BOOLEAN             NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMP           NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS products (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(255)        NOT NULL,
    description         TEXT,
    price               NUMERIC(10, 2)      NOT NULL CHECK (price >= 0),
    stock               INTEGER             NOT NULL DEFAULT 0 CHECK (stock >= 0),
    is_active           BOOLEAN             NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMP           NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS purchase_orders (
    id                  SERIAL PRIMARY KEY,
    user_id                                 NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status              VARCHAR(50)         NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending', 'confirmed', 'shipped', 'delivered', 'cancelled')),
    total               NUMERIC(10, 2)      NOT NULL DEFAULT 0.00,
    created_at          TIMESTAMP           NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS purchase_order_items (
    id                  SERIAL PRIMARY KEY,
    purchase_order_id   INTEGER             NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
    product_id          INTEGER             NOT NULL REFERENCES products(id),
    quantity            INTEGER             NOT NULL CHECK (quantity > 0),
    unit_price          NUMERIC(10, 2)      NOT NULL REFERENCES products(price) ON DELETE CASCADE,
    discount_total      NUMERIC(10, 2)      NOT NULL CHECK (discount_total >= 0),
    struck_out          BOOLEAN             NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS restock_orders (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER             NOT NULL REFERENCES users(id) ON DELETE CASCADE
                            CHECK (users()),
    status              VARCHAR(50)         NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending', 'confirmed', 'shipped', 'delivered', 'cancelled')),
    created_at          TIMESTAMP           NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS restock_order_items (
    id                  SERIAL PRIMARY KEY,
    restock_order_id    INTEGER             NOT NULL REFERENCES restock_orders(id) ON DELETE CASCADE,
    product_id          INTEGER             NOT NULL REFERENCES products(id),
    quantity            INTEGER             NOT NULL CHECK (quantity > 0),
    struck_out          BOOLEAN             NOT NULL DEFAULT FALSE
);