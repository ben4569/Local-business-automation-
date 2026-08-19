from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request, jsonify
import flask
import csv
import io

from database.db import init_db
from database.queries import (
    create_user,
    get_user_by_id,
    update_auth_token,
    get_user_by_token,
    save_onboarding,
    get_onboarding,
    get_user_by_email,
    add_product,
    get_products,
    update_product,
    delete_product
)

app = Flask(__name__)

init_db()

# -------------------------
# HOME
# -------------------------

@app.route("/")
def home():
    return jsonify({
        "status": "running",
        "message": "Inventory backend is running"
    })
def get_authenticated_user():
    token = request.headers.get("Authorization")

    if not token:
        return None

    if token.startswith("Bearer "):
        token = token[7:]

    return get_user_by_token(token)

# -------------------------
# SIGNUP
# -------------------------

@app.route("/signup", methods=["POST"])
def signup():

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "Request body is required"
        }), 400

    email = data.get("email")
    password = data.get("password")
    name = data.get("name")

    if not email or not password:
        return jsonify({
            "error": "Email and password are required"
        }), 400

    password_hash = generate_password_hash(password)

    try:
        user_id = create_user(
            email,
            password_hash,
            name
        )

    except Exception:
        return jsonify({
            "error": "An account with this email already exists"
        }), 400
    auth_token = secrets.token_urlsafe(32)

    update_auth_token(
        user_id,
        auth_token
    )

    return jsonify({
        "message": "Account created",
        "user_id": user_id,
        "auth_token": auth_token
    }), 201
# -------------------------
# LOGIN
# -------------------------

@app.route("/login", methods=["POST"])
def login():

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "Request body is required"
        }), 400

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({
            "error": "Email and password are required"
        }), 400

    user = get_user_by_email(email)

    if not user:
        return jsonify({
            "error": "Invalid email or password"
        }), 401

    if not check_password_hash(
        user["password_hash"],
        password
    ):
        return jsonify({
            "error": "Invalid email or password"
        }), 401
    auth_token = secrets.token_urlsafe(32)

    update_auth_token(
        user["id"],
        auth_token
    )
    return jsonify({
        "message": "Login successful",
        "user_id": user["id"],
        "name": user["name"],
        "onboarding_completed": bool(
            user["onboarding_completed"]
        ),
        "auth_token": auth_token
    })

# -------------------------
# GET USER
# -------------------------

@app.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):

    user = get_user_by_id(user_id)

    if not user:
        return jsonify({
            "error": "User not found"
        }), 404

    return jsonify({
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "onboarding_completed": bool(
            user["onboarding_completed"]
        )
    })


# -------------------------
# GET PRODUCTS
# -------------------------
@app.route("/products", methods=["GET"])
def products():
    user_id = "2"
    products = get_products(user_id)

    return jsonify([
        dict(product)
        for product in products
    ])
# ADD PRODUCT
# -----------------------
@app.route("/products", methods=["POST"])
def create_product():

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "Request body is required"
        }), 400

    # Temporary user for Phase 1
    user_id = 2

    name = data.get("name")
    category = data.get("category")
    price = data.get("price")
    cost = data.get("cost")
    quantity = data.get("quantity", 0)

    if not name:
        return jsonify({
            "error": "Product name is required"
        }), 400

    product_id = add_product(
        user_id,
        name,
        category,
        price,
        cost,
        quantity
    )

    return jsonify({
        "message": "Product created",
        "product_id": product_id
    }), 201
# -------------------------
# UPDATE PRODUCT
# --------------------;---------
@app.route("/products/<int:product_id>", methods=["PUT"])
def edit_product(product_id):

    user = get_authenticated_user()

    if not user:
        return jsonify({
            "error": "Authentication required"
        }), 401

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "Request body is required"
        }), 400

    update_product(
        user["id"],
        product_id,
        data.get("name"),
        data.get("category"),
        data.get("price"),
        data.get("cost"),
        data.get("quantity", 0)
    )

    return jsonify({
        "message": "Product updated"
    })
@app.route("/products/import", methods=["POST"])
def import_products():

    if "file" not in request.files:
        return jsonify({
            "error": "CSV file is required"
        }), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({
            "error": "No file selected"
        }), 400

    if not file.filename.lower().endswith(".csv"):
        return jsonify({
            "error": "Only CSV files are allowed"
        }), 400

    user_id = 2

    required_columns = {
        "name",
        "category",
        "price",
        "cost",
        "quantity"
    }

    try:
        content = file.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))

        if not reader.fieldnames:
            return jsonify({
                "error": "CSV file is empty"
            }), 400

        columns = set(reader.fieldnames)

        missing_columns = required_columns - columns

        if missing_columns:
            return jsonify({
                "error": "Missing columns",
                "columns": sorted(missing_columns)
            }), 400

        imported = 0
        skipped = []

        for row_number, row in enumerate(reader, start=2):

            name = (row.get("name") or "").strip()
            category = (row.get("category") or "").strip()
            price_value = (row.get("price") or "").strip()
            cost_value = (row.get("cost") or "").strip()
            quantity_value = (row.get("quantity") or "").strip()

            # Product name
            if not name:
                skipped.append({
                    "row": row_number,
                    "error": "Product name is required"
                })
                continue

            # Price
            try:
                price = float(price_value)
                if price < 0:
                    raise ValueError
            except ValueError:
                skipped.append({
                    "row": row_number,
                    "error": "Invalid price"
                })
                continue

            # Cost
            try:
                cost = float(cost_value)
                if cost < 0:
                    raise ValueError
            except ValueError:
                skipped.append({
                    "row": row_number,
                    "error": "Invalid cost"
                })
                continue

            # Quantity
            try:
                quantity = int(quantity_value)

                if quantity < 0:
                    raise ValueError

            except ValueError:
                skipped.append({
                    "row": row_number,
                    "error": "Invalid quantity"
                })
                continue

            add_product(
                user_id,
                name,
                category,
                price,
                cost,
                quantity
            )

            imported += 1

        return jsonify({
            "message": "CSV import completed",
            "imported": imported,
            "skipped": len(skipped),
            "errors": skipped
        })

    except UnicodeDecodeError:
        return jsonify({
            "error": "CSV must use UTF-8 encoding"
        }), 400

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 400
# -------------------------
# DELETE PRODUCT
# -------------------------
@app.route("/products/<int:product_id>", methods=["DELETE"])
def remove_product(product_id):

    user = get_authenticated_user()

    if not user:
        return jsonify({
            "error": "Authentication required"
        }), 401

    delete_product(
        user["id"],
        product_id
    )

    return jsonify({
        "message": "Product deleted"
    })
# -------------------------
# ONBOARDING
# -------------------------

@app.route("/onboarding", methods=["GET"])
def onboarding():

    user_id = 2

    onboarding_data = get_onboarding(user_id)

    if not onboarding_data:
        return jsonify({
            "onboarding_completed": False
        })

    return jsonify({
        "onboarding_completed": True,
        "business_name": onboarding_data["business_name"],
        "business_type": onboarding_data["business_type"]
    })


@app.route("/onboarding", methods=["POST"])
def complete_onboarding():

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "Request body is required"
        }), 400

    business_name = data.get("business_name")
    business_type = data.get("business_type")

    if not business_name or not business_type:
        return jsonify({
            "error": "Business name and business type are required"
        }), 400

    # Temporary user until authentication is implemented
    user_id = 2

    save_onboarding(
        user_id,
        business_name,
        business_type
    )

    return jsonify({
        "message": "Onboarding completed",
        "user_id": user_id,
        "onboarding_completed": True
    })

# -------------------------
# RUN APP
# -------------------------

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
)
