from database.db import get_db
def create_user(email, password_hash, name=None):
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO users (email, password_hash, name)
        VALUES (?, ?, ?)
        """,
        (email, password_hash, name)
    )
    db.commit()
    user_id = cursor.lastrowid
    db.close()
    return user_id
def get_user_by_id(user_id):
    db = get_db()
    user = db.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    ).fetchone()
    db.close()
    return user
def save_onboarding(user_id, business_name, business_type):
    db = get_db()
    existing = db.execute(
        """
        SELECT id
        FROM onboarding
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()
    if existing:
        db.execute(
            """
            UPDATE onboarding
            SET business_name = ?,
                business_type = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (business_name, business_type, user_id)
        )
    else:
        db.execute(
            """
            INSERT INTO onboarding
            (user_id, business_name, business_type)
            VALUES (?, ?, ?)
            """,
            (user_id, business_name, business_type)
        )
    db.execute(
        """
        UPDATE users
        SET onboarding_completed = 1
        WHERE id = ?
        """,
        (user_id,)
    )
    db.commit()
    db.close()
def get_onboarding(user_id):
    db = get_db()
    onboarding = db.execute(
        """
        SELECT *
        FROM onboarding
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()
    db.close()
    return onboarding
def add_product(user_id, name, category, price, cost, quantity):
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO products
        (user_id, name, category, price, cost, quantity)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, name, category, price, cost, quantity)
    )

    db.commit()
    product_id = cursor.lastrowid
    db.close()

    return product_id


def get_products(user_id):
    db = get_db()

    products = db.execute(
        """
        SELECT *
        FROM products
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user_id,)
    ).fetchall()

    db.close()

    return products
def get_product(product_id, user_id):
    db = get_db()

    product = db.execute(
        """
        SELECT *
        FROM products
        WHERE id = ?
        AND user_id = ?
        """,
        (product_id, user_id)
    ).fetchone()

    db.close()

    return product
