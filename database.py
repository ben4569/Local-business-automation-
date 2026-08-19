import os
from contextlib import contextmanager
from decimal import Decimal
from typing import Any, Iterable, Optional

from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error, IntegrityError

load_dotenv()

BUSINESS_TYPES = [
    "Grocery",
    "Clothing",
    "Electronics",
    "Pharmacy",
    "Restaurant",
    "Other"
]

import = [
    "INR",
    "USD",
    "AED"
]

REQUIRED_CSV_COLUMNS = {
    "product_name",
    "purchase_price",
    "selling_price",
    "stock"
}

OPTIONAL_CSV_COLUMNS = {
    "category",
    "minimum_stock",
    "supplier"
}
class DatabaseError(RuntimeError):
    pass


@contextmanager
def get_connection():
    connection = None

    try:
        connection = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "127.0.0.1"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER", ""),
            password=os.getenv("MYSQL_PASSWORD", ""),
            database=os.getenv("MYSQL_DATABASE", "shopsight")
        )

        yield connection

    except Error as exc:
        raise DatabaseError(
            "Unable to connect to the database."
        ) from exc

    finally:
        if connection is not None and connection.is_connected():
            connection.close()


def execute(
    sql: str,
    params: Iterable[Any] = (),
    *,
    commit: bool = False
) -> int:
    try:
        with get_connection() as connection:
            cursor = connection.cursor()

            try:
                cursor.execute(sql, tuple(params))

                if commit:
                    connection.commit()

                return cursor.lastrowid

            finally:
                cursor.close()

    except IntegrityError:
        raise

    except DatabaseError:
        raise

    except Error as exc:
        raise DatabaseError(
            "The database operation failed."
        ) from exc


def fetch_one(
    sql: str,
    params: Iterable[Any] = ()
) -> Optional[dict]:
    try:
        with get_connection() as connection:
            cursor = connection.cursor(dictionary=True)

            try:
                cursor.execute(sql, tuple(params))
                return cursor.fetchone()

            finally:
                cursor.close()

    except DatabaseError:
        raise

    except Error as exc:
        raise DatabaseError(
            "The database query failed."
        ) from exc


def fetch_all(
    sql: str,
    params: Iterable[Any] = ()
) -> list[dict]:
    try:
        with get_connection() as connection:
            cursor = connection.cursor(dictionary=True)

            try:
                cursor.execute(sql, tuple(params))
                return cursor.fetchall()

            finally:
                cursor.close()

    except DatabaseError:
        raise

    except Error as exc:
        raise DatabaseError(
            "The database query failed."
        ) from exc


def get_user_by_email(email: str) -> Optional[dict]:
    return fetch_one(
        """
        SELECT id, email, password_hash, created_at
        FROM users
        WHERE email = %s
        """,
        (email,)
    )


def create_user(
    email: str,
    password_hash: str
) -> int:
    return execute(
        """
        INSERT INTO users (
            email,
            password_hash
        )
        VALUES (%s, %s)
        """,
        (
            email,
            password_hash
        ),
        commit=True
    )


def get_business_by_user_id(
    user_id: int
) -> Optional[dict]:
    return fetch_one(
        """
        SELECT
            id,
            user_id,
            business_name,
            business_type,
            years_in_operation,
            currency,
            created_at
        FROM businesses
        WHERE user_id = %s
        LIMIT 1
        """,
        (user_id,)
    )


def create_business(
    user_id: int,
    business_name: str,
    business_type: str,
    years_in_operation: int,
    currency: str
) -> int:
    return execute(
        """
        INSERT INTO businesses (
            user_id,
            business_name,
            business_type,
            years_in_operation,
            currency
        )
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            user_id,
            business_name,
            business_type,
            years_in_operation,
            currency
        ),
        commit=True
    )


def get_categories(
    business_id: int
) -> list[dict]:
    return fetch_all(
        """
        SELECT id, name
        FROM categories
        WHERE business_id = %s
        ORDER BY name
        """,
        (business_id,)
    )


def get_suppliers(
    business_id: int
) -> list[dict]:
    return fetch_all(
        """
        SELECT id, name
        FROM suppliers
        WHERE business_id = %s
        ORDER BY name
        """,
        (business_id,)
    )


def _get_or_create_category(
    cursor,
    business_id: int,
    name: str
) -> Optional[int]:
    name = name.strip()

    if not name:
        return None

    cursor.execute(
        """
        INSERT INTO categories (
            business_id,
            name
        )
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE
            id = LAST_INSERT_ID(id)
        """,
        (
            business_id,
            name
        )
    )

    return cursor.lastrowid


def _get_or_create_supplier(
    cursor,
    business_id: int,
    name: str
) -> Optional[int]:
    name = name.strip()

    if not name:
        return None

    cursor.execute(
        """
        INSERT INTO suppliers (
            business_id,
            name
        )
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE
            id = LAST_INSERT_ID(id)
        """,
        (
            business_id,
            name
        )
    )

    return cursor.lastrowid


def _insert_product(
    cursor,
    business_id: int,
    row: dict
) -> int:
    category_id = _get_or_create_category(
        cursor,
        business_id,
        row.get("category", "")
    )

    supplier_id = _get_or_create_supplier(
        cursor,
        business_id,
        row.get("supplier", "")
    )

    cursor.execute(
        """
        INSERT INTO products (
            business_id,
            product_name,
            category_id,
            purchase_price,
            selling_price,
            stock,
            minimum_stock,
            supplier_id
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            business_id,
            row["product_name"],
            category_id,
            row["purchase_price"],
            row["selling_price"],
            row["stock"],
            row["minimum_stock"],
            supplier_id
        )
    )

    product_id = cursor.lastrowid

    if row["stock"] > 0:
        cursor.execute(
            """
            INSERT INTO stock_movements (
                product_id,
                quantity_change,
                movement_type
            )
            VALUES (%s, %s, 'INITIAL_STOCK')
            """,
            (
                product_id,
                row["stock"]
            )
        )

    return product_id


def create_product(
    business_id: int,
    product_name: str,
    category_name: str,
    purchase_price: Decimal,
    selling_price: Decimal,
    stock: Decimal,
    minimum_stock: Decimal,
    supplier_name: str
) -> int:
    row = {
        "product_name": product_name,
        "category": category_name,
        "supplier": supplier_name,
        "purchase_price": purchase_price,
        "selling_price": selling_price,
        "stock": stock,
        "minimum_stock": minimum_stock
    }

    try:
        with get_connection() as connection:
            cursor = connection.cursor()

            try:
                connection.start_transaction()

                product_id = _insert_product(
                    cursor,
                    business_id,
                    row
                )

                connection.commit()

                return product_id

            except Exception:
                connection.rollback()
                raise

            finally:
                cursor.close()

    except IntegrityError:
        raise

    except DatabaseError:
        raise

    except Error as exc:
        raise DatabaseError(
            "Could not save the product."
        ) from exc


def import_products(
    business_id: int,
    filename: str,
    rows: list[dict]
) -> int:
    try:
        with get_connection() as connection:
            cursor = connection.cursor()

            try:
                connection.start_transaction()

                for row in rows:
                    _insert_product(
                        cursor,
                        business_id,
                        row
                    )

                cursor.execute(
                    """
                    INSERT INTO imports (
                        business_id,
                        filename,
                        rows_imported
                    )
                    VALUES (%s, %s, %s)
                    """,
                    (
                        business_id,
                        filename,
                        len(rows)
                    )
                )

                connection.commit()

                return len(rows)

            except Exception:
                connection.rollback()
                raise

            finally:
                cursor.close()

    except IntegrityError:
        raise

    except DatabaseError:
        raise

    except Error as exc:
        raise DatabaseError(
            "Could not import the products."
        ) from exc


def get_products(
    business_id: int
) -> list[dict]:
    return fetch_all(
        """
        SELECT
            p.id,
            p.product_name AS Product,
            COALESCE(c.name, '') AS Category,
            COALESCE(s.name, '') AS Supplier,
            p.purchase_price AS `Purchase Price`,
            p.selling_price AS `Selling Price`,
            p.stock AS Stock,
            p.minimum_stock AS `Minimum Stock`
        FROM products p
        LEFT JOIN categories c
            ON c.id = p.category_id
        LEFT JOIN suppliers s
            ON s.id = p.supplier_id
        WHERE p.business_id = %s
        ORDER BY p.product_name
        """,
        (business_id,)
    )


def count_products(
    business_id: int
) -> int:
    row = fetch_one(
        """
        SELECT COUNT(*) AS total
        FROM products
        WHERE business_id = %s
        """,
        (business_id,)
    )

    return int(row["total"]) if row else 0


def get_connection_test() -> bool:
    with get_connection() as connection:
        cursor = connection.cursor()

        try:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()

            return bool(
                result and result[0] == 1
            )

        finally:
            cursor.close()
