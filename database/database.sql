CREATE DATABASE IF NOT EXISTS shopsight
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE shopsight;


-- =========================================================
-- 1. USERS
-- Stores account/login information
-- =========================================================

CREATE TABLE IF NOT EXISTS users (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB;


-- =========================================================
-- 2. BUSINESSES
-- Stores business onboarding information
-- One user = one business
-- =========================================================

CREATE TABLE IF NOT EXISTS businesses (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    business_name VARCHAR(255) NOT NULL,
    business_type VARCHAR(100) NOT NULL,
    years_in_operation INT UNSIGNED NOT NULL DEFAULT 0,
    currency CHAR(3) NOT NULL DEFAULT 'INR',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    UNIQUE KEY uq_businesses_user (user_id),
    KEY idx_businesses_user_id (user_id),

    CONSTRAINT fk_businesses_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;


-- =========================================================
-- 3. CATEGORIES
-- Product categories belonging to a business
-- =========================================================

CREATE TABLE IF NOT EXISTS categories (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    business_id BIGINT UNSIGNED NOT NULL,
    name VARCHAR(255) NOT NULL,

    PRIMARY KEY (id),

    UNIQUE KEY uq_categories_business_name (business_id, name),
    KEY idx_categories_business_id (business_id),

    CONSTRAINT fk_categories_business
        FOREIGN KEY (business_id)
        REFERENCES businesses(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;


-- =========================================================
-- 4. SUPPLIERS
-- Suppliers belonging to a business
-- =========================================================

CREATE TABLE IF NOT EXISTS suppliers (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    business_id BIGINT UNSIGNED NOT NULL,
    name VARCHAR(255) NOT NULL,
    contact VARCHAR(100) NULL,

    PRIMARY KEY (id),

    UNIQUE KEY uq_suppliers_business_name (business_id, name),
    KEY idx_suppliers_business_id (business_id),

    CONSTRAINT fk_suppliers_business
        FOREIGN KEY (business_id)
        REFERENCES businesses(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;


-- =========================================================
-- 5. PRODUCTS
-- Main inventory table
-- =========================================================

CREATE TABLE IF NOT EXISTS products (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    business_id BIGINT UNSIGNED NOT NULL,
    product_name VARCHAR(255) NOT NULL,

    category_id BIGINT UNSIGNED NULL,
    supplier_id BIGINT UNSIGNED NULL,

    purchase_price DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    selling_price DECIMAL(12, 2) NOT NULL DEFAULT 0.00,

    stock DECIMAL(12, 3) NOT NULL DEFAULT 0.000,
    minimum_stock DECIMAL(12, 3) NOT NULL DEFAULT 0.000,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    KEY idx_products_business_id (business_id),
    KEY idx_products_category_id (category_id),
    KEY idx_products_supplier_id (supplier_id),

    CONSTRAINT fk_products_business
        FOREIGN KEY (business_id)
        REFERENCES businesses(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_products_category
        FOREIGN KEY (category_id)
        REFERENCES categories(id)
        ON DELETE SET NULL,

    CONSTRAINT fk_products_supplier
        FOREIGN KEY (supplier_id)
        REFERENCES suppliers(id)
        ON DELETE SET NULL
) ENGINE=InnoDB;


-- =========================================================
-- 6. SALES
-- Stores each sale/transaction
-- =========================================================

CREATE TABLE IF NOT EXISTS sales (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    business_id BIGINT UNSIGNED NOT NULL,

    total_amount DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
    sale_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    KEY idx_sales_business_date (business_id, sale_date),

    CONSTRAINT fk_sales_business
        FOREIGN KEY (business_id)
        REFERENCES businesses(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;


-- =========================================================
-- 7. SALE ITEMS
-- Individual products contained in a sale
-- =========================================================

CREATE TABLE IF NOT EXISTS sale_items (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    sale_id BIGINT UNSIGNED NOT NULL,
    product_id BIGINT UNSIGNED NOT NULL,

    quantity DECIMAL(12, 3) NOT NULL,
    price DECIMAL(12, 2) NOT NULL,

    PRIMARY KEY (id),

    KEY idx_sale_items_sale_id (sale_id),
    KEY idx_sale_items_product_id (product_id),

    CONSTRAINT fk_sale_items_sale
        FOREIGN KEY (sale_id)
        REFERENCES sales(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_sale_items_product
        FOREIGN KEY (product_id)
        REFERENCES products(id)
        ON DELETE RESTRICT
) ENGINE=InnoDB;


-- =========================================================
-- 8. STOCK MOVEMENTS
-- Keeps a history of every inventory change
-- =========================================================

CREATE TABLE IF NOT EXISTS stock_movements (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,

    business_id BIGINT UNSIGNED NOT NULL,
    product_id BIGINT UNSIGNED NOT NULL,

    quantity_change DECIMAL(12, 3) NOT NULL,

    movement_type ENUM(
        'INITIAL_STOCK',
        'PURCHASE',
        'SALE',
        'ADJUSTMENT',
        'RETURN'
    ) NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    KEY idx_stock_movements_business_id (business_id),
    KEY idx_stock_movements_product_created (product_id, created_at),

    CONSTRAINT fk_stock_movements_business
        FOREIGN KEY (business_id)
        REFERENCES businesses(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_stock_movements_product
        FOREIGN KEY (product_id)
        REFERENCES products(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;


-- =========================================================
-- 9. IMPORTS
-- Keeps track of CSV/Excel imports
-- =========================================================

CREATE TABLE IF NOT EXISTS imports (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMEfilename business_id BIGINT UNSIGNED NOT NULL,
    filename VARCHAR(255) NOT NULL,

    rows_imported INT UNSIGNED NOT NULL DEFAULT 0,

    imported_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    KEY idx_imports_business_date (business_id, imported_at),

    CONSTRAINT fk_imports_business
        FOREIGN KEY (business_id)
        REFERENCES businesses(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;
