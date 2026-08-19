from .db import get_connection


def create_user(email, password_hash, name=None):
    with get_connection() as connection:
        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO users
                    (email, password_hash, name)
                VALUES
                    (%s, %s, %s)
                """,
                (email, password_hash, name)
            )

            connection.commit()
            return cursor.lastrowid

        finally:
            cursor.close()


def get_user_by_id(user_id):
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute(
                """
                SELECT
                    id,
                    email,
                    password_hash,
                    name,
                    onboarding_completed,
                    created_at
                FROM users
                WHERE id = %s
                """,
                (user_id,)
            )

            return cursor.fetchone()

        finally:
            cursor.close()


def get_user_by_email(email):
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute(
                """
                SELECT
                    id,
                    email,
                    password_hash,
                    name,
                    onboarding_completed,
                    created_at
                FROM users
                WHERE email = %s
                """,
                (email,)
            )

            return cursor.fetchone()

        finally:
            cursor.close()


def update_auth_token(user_id, auth_token):
    with get_connection() as connection:
        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                UPDATE users
                SET auth_token = %s
                WHERE id = %s
                """,
                (auth_token, user_id)
            )

            connection.commit()

        finally:
            cursor.close()


def get_user_by_token(auth_token):
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute(
                """
                SELECT
                    id,
                    email,
                    password_hash,
                    name,
                    onboarding_completed,
                    created_at
                FROM users
                WHERE auth_token = %s
                """,
                (auth_token,)
            )

            return cursor.fetchone()

        finally:
            cursor.close()


def save_onboarding(
    user_id,
    business_name,
    business_type,
    years_in_operation=0,
    currency="INR"
):
    with get_connection() as connection:
        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO businesses
                    (
                        user_id,
                        business_name,
                        business_type,
                        years_in_operation,
                        currency
                    )
                VALUES
                    (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    business_name = VALUES(business_name),
                    business_type = VALUES(business_type),
                    years_in_operation = VALUES(years_in_operation),
                    currency = VALUES(currency)
                """,
                (
                    user_id,
                    business_name,
                    business_type,
                    years_in_operation,
                    currency
                )
            )

            cursor.execute(
                """
                UPDATE users
                SET onboarding_completed = TRUE
                WHERE id = %s
                """,
                (user_id,)
            )

            connection.commit()

        finally:
            cursor.close()


def get_onboarding(user_id):
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute(
                """
                SELECT
                    business_name,
                    business_type,
                    years_in_operation,
                    currency
                FROM businesses
                WHERE user_id = %s
                LIMIT 1
                """,
                (user_id,)
            )

            return cursor.fetchone()

        finally:
            cursor.close()


def _get_category_id(cursor, business_id, category):
    if not category:
        return None

    cursor.execute(
        """
        INSERT INTO categories
            (business_id, name)
        VALUES
            (%s, %s)
        ON DUPLICATE KEY UPDATE
            id = LAST_INSERT_ID(id)
        """,
        (business_id, category)
    )

    return cursor.lastrowid


def add_product(
    user_id,
    name,
    category,
    price,
    cost,
    quantity
):
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute(
                """
                SELECT id
                FROM businesses
                WHERE user_id = %s
                LIMIT 1
                """,
                (user_id,)
            )

            business = cursor.fetchone()

            if not business:
                raise ValueError(
                    "User has not completed onboarding."
                )

            business_id = business["id"]

            category_id = _get_category_id(
                cursor,
                business_id,
                category
            )

            cursor.execute(
                """
                INSERT INTO products
                    (
                        business_id,
                        product_name,
                        category_id,
                        purchase_price,
                        selling_price,
                        stock
                    )
                VALUES
                    (%s, %s, %s, %s, %s, %s)
                """,
                (
                    business_id,
                    name,
                    category_id,
                    cost or 0,
                    price or 0,
                    quantity or 0
                )
            )

            product_id = cursor.lastrowid

            if quantity and quantity > 0:
                cursor.execute(
                    """
                    INSERT INTO stock_movements
                        (
                            business_id,
                            product_id,
                            quantity_change,
                            movement_type
                        )
                    VALUES
                        (%s, %s, %s, 'INITIAL_STOCK')
                    """,
                    (
                        business_id,
                        product_id,
                        quantity
                    )
                )

            connection.commit()
            return product_id

        finally:
            cursor.close()


def get_products(user_id):
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute(
                """
                SELECT
                    p.id,
                    p.product_name AS name,
                    COALESCE(c.name, '') AS category,
                    p.selling_price AS price,
                    p.purchase_price AS cost,
                    p.stock AS quantity
                FROM products p
                JOIN businesses b
                    ON b.id = p.business_id
                LEFT JOIN categories c
                    ON c.id = p.category_id
                WHERE b.user_id = %s
                ORDER BY p.id DESC
                """,
                (user_id,)
            )

            return cursor.fetchall()

        finally:
            cursor.close()


def update_product(
    user_id,
    product_id,
    name,
    category,
    price,
    cost,
    quantity
):
    with get_connection() as connection:
        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                UPDATE products p
                JOIN businesses b
                    ON b.id = p.business_id
                SET
                    p.product_name = %s,
                    p.selling_price = %s,
                    p.purchase_price = %s,
                    p.stock = %s
                WHERE
                    p.id = %s
                    AND b.user_id = %s
                """,
                (
                    name,
                    price or 0,
                    cost or 0,
                    quantity or 0,
                    product_id,
                    user_id
                )
            )

            connection.commit()

        finally:
            cursor.close()


def delete_product(user_id, product_id):
    with get_connection() as connection:
        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                DELETE p
                FROM products p
                JOIN businesses b
                    ON b.id = p.business_id
                WHERE
                    p.id = %s
                    AND b.user_id = %s
                """,
                (product_id, user_id)
            )

            connection.commit()

        finally:
            cursor.close()
            
