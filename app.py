import os
import re
import csv
import hashlib
import hmac
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from decimal import Decimal, InvalidOperation
from datetime import datetime

import mysql.connector
from mysql.connector import IntegrityError
from dotenv import load_dotenv

load_dotenv()

BUSINESS_TYPES = [
    "Grocery",
    "Clothing",
    "Electronics",
    "Pharmacy",
    "Restaurant",
    "Other"
]

CURRENCIES = [
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


def db_config():
    return {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DATABASE", "shopsight")
    }


def get_connection():
    return mysql.connector.connect(**db_config())


def fetch_one(query, params=()):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        return cursor.fetchone()
    finally:
        cursor.close()
        connection.close()


def fetch_all(query, params=()):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def execute_query(query, params=()):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(query, params)
        connection.commit()
        return cursor.lastrowid
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def password_hash(password):
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        200000
    )
    return f"pbkdf2_sha256$200000${salt.hex()}${digest.hex()}"


def verify_password(password, stored):
    try:
        algorithm, rounds_text, salt_hex, digest_hex = stored.split("$", 3)

        if algorithm != "pbkdf2_sha256":
            return False

        rounds = int(rounds_text)

        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            rounds
        )

        return hmac.compare_digest(
            actual,
            bytes.fromhex(digest_hex)
        )

    except (ValueError, TypeError):
        return False


def valid_email(email):
    return bool(
        re.fullmatch(
            r"[^\s@]+@[^\s@]+\.[^\s@]+",
            email
        )
    )


def get_user_by_email(email):
    return fetch_one(
        """
        SELECT id, email, password_hash, created_at
        FROM users
        WHERE email = %s
        """,
        (email,)
    )


def create_user(email, password_hash_value):
    return execute_query(
        """
        INSERT INTO users (email, password_hash)
        VALUES (%s, %s)
        """,
        (email, password_hash_value)
    )


def get_business_by_user_id(user_id):
    return fetch_one(
        """
        SELECT id, user_id, business_name, business_type,
               years_in_operation, currency, created_at
        FROM businesses
        WHERE user_id = %s
        """,
        (user_id,)
    )


def create_business(
    user_id,
    business_name,
    business_type,
    years,
    currency
):
    return execute_query(
        """
        INSERT INTO businesses
        (
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
            years,
            currency
        )
    )


def get_categories(business_id):
    return fetch_all(
        """
        SELECT id, name
        FROM categories
        WHERE business_id = %s
        ORDER BY name
        """,
        (business_id,)
    )


def get_suppliers(business_id):
    return fetch_all(
        """
        SELECT id, name, contact
        FROM suppliers
        WHERE business_id = %s
        ORDER BY name
        """,
        (business_id,)
    )


def get_or_create_category(business_id, name):
    if not name:
        return None

    existing = fetch_one(
        """
        SELECT id
        FROM categories
        WHERE business_id = %s AND name = %s
        """,
        (business_id, name)
    )

    if existing:
        return existing["id"]

    return execute_query(
        """
        INSERT INTO categories (business_id, name)
        VALUES (%s, %s)
        """,
        (business_id, name)
    )


def get_or_create_supplier(business_id, name):
    if not name:
        return None

    existing = fetch_one(
        """
        SELECT id
        FROM suppliers
        WHERE business_id = %s AND name = %s
        """,
        (business_id, name)
    )

    if existing:
        return existing["id"]

    return execute_query(
        """
        INSERT INTO suppliers (business_id, name)
        VALUES (%s, %s)
        """,
        (business_id, name)
    )


def create_product(
    business_id,
    product_name,
    category,
    purchase_price,
    selling_price,
    stock,
    minimum_stock,
    supplier
):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        category_id = None
        supplier_id = None

        if category:
            category_id = get_or_create_category(
                business_id,
                category
            )

        if supplier:
            supplier_id = get_or_create_supplier(
                business_id,
                supplier
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
                stock,
                minimum_stock,
                supplier_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                business_id,
                product_name,
                category_id,
                purchase_price,
                selling_price,
                stock,
                minimum_stock,
                supplier_id
            )
        )

        product_id = cursor.lastrowid

        if stock > 0:
            cursor.execute(
                """
                INSERT INTO stock_movements
                (
                    business_id,
                    product_id,
                    quantity_change,
                    movement_type
                )
                VALUES (%s, %s, %s, 'INITIAL_STOCK')
                """,
                (
                    business_id,
                    product_id,
                    stock
                )
            )

        connection.commit()
        return product_id

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


def get_products(business_id):
    return fetch_all(
        """
        SELECT
            p.id,
            p.product_name,
            COALESCE(c.name, '') AS category,
            COALESCE(s.name, '') AS supplier,
            p.purchase_price,
            p.selling_price,
            p.stock,
            p.minimum_stock,
            p.created_at,
            p.updated_at
        FROM products p
        LEFT JOIN categories c
            ON p.category_id = c.id
        LEFT JOIN suppliers s
            ON p.supplier_id = s.id
        WHERE p.business_id = %s
        ORDER BY p.id DESC
        """,
        (business_id,)
    )


def import_products(business_id, filename, rows):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        for row in rows:
            category_id = None
            supplier_id = None

            category = row.get("category", "").strip()
            supplier = row.get("supplier", "").strip()

            if category:
                cursor.execute(
                    """
                    SELECT id
                    FROM categories
                    WHERE business_id = %s
                    AND name = %s
                    """,
                    (business_id, category)
                )

                result = cursor.fetchone()

                if result:
                    category_id = result[0]
                else:
                    cursor.execute(
                        """
                        INSERT INTO categories
                        (business_id, name)
                        VALUES (%s, %s)
                        """,
                        (business_id, category)
                    )
                    category_id = cursor.lastrowid

            if supplier:
                cursor.execute(
                    """
                    SELECT id
                    FROM suppliers
                    WHERE business_id = %s
                    AND name = %s
                    """,
                    (business_id, supplier)
                )

                result = cursor.fetchone()

                if result:
                    supplier_id = result[0]
                else:
                    cursor.execute(
                        """
                        INSERT INTO suppliers
                        (business_id, name)
                        VALUES (%s, %s)
                        """,
                        (business_id, supplier)
                    )
                    supplier_id = cursor.lastrowid

            cursor.execute(
                """
                INSERT INTO products
                (
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
                    INSERT INTO stock_movements
                    (
                        business_id,
                        product_id,
                        quantity_change,
                        movement_type
                    )
                    VALUES (%s, %s, %s, 'INITIAL_STOCK')
                    """,
                    (
                        business_id,
                        product_id,
                        row["stock"]
                    )
                )

        cursor.execute(
            """
            INSERT INTO imports
            (
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
        connection.close()


def get_connection_test():
    connection = get_connection()
    try:
        return connection.is_connected()
    finally:
        connection.close()


class ShopSightApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ShopSight")
        self.root.geometry("1050x700")
        self.root.minsize(900, 600)

        self.user_id = None
        self.business_id = None
        self.current_currency = "INR"

        self.bg = "#F5F7FA"
        self.card = "#FFFFFF"
        self.primary = "#111827"
        self.secondary = "#6B7280"
        self.border = "#E5E7EB"
        self.accent = "#2563EB"
        self.success = "#15803D"
        self.danger = "#DC2626"

        self.root.configure(bg=self.bg)

        self.setup_styles()
        self.show_landing()

    def setup_styles(self):
        style = ttk.Style()

        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "TButton",
            font=("Arial", 11),
            padding=(16, 10)
        )

        style.configure(
            "Primary.TButton",
            font=("Arial", 11, "bold"),
            padding=(16, 10)
        )

        style.configure(
            "TEntry",
            padding=10,
            font=("Arial", 11)
        )

        style.configure(
            "TCombobox",
            padding=8,
            font=("Arial", 11)
        )

        style.configure(
            "Treeview",
            rowheight=36,
            font=("Arial", 10)
        )

        style.configure(
            "Treeview.Heading",
            font=("Arial", 10, "bold")
        )

    def clear(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def title_label(self, parent):
        label = tk.Label(
            parent,
            text="SHOP SIGHT",
            font=("Arial", 28, "bold"),
            fg=self.primary,
            bg=parent.cget("bg")
        )
        label.pack()

        subtitle = tk.Label(
            parent,
            text="Smarter decisions for your shop.",
            font=("Arial", 12),
            fg=self.secondary,
            bg=parent.cget("bg")
        )
        subtitle.pack(pady=(5, 25))

    def create_card(self, parent, width=600):
        frame = tk.Frame(
            parent,
            bg=self.card,
            highlightbackground=self.border,
            highlightthickness=1
        )
        frame.pack(
            padx=20,
            pady=15,
            ipadx=30,
            ipady=25
        )
        return frame

    def add_label(self, parent, text):
        label = tk.Label(
            parent,
            text=text,
            font=("Arial", 10, "bold"),
            fg=self.primary,
            bg=self.card,
            anchor="w"
        )
        label.pack(fill="x", pady=(10, 5))
        return label

    def add_entry(self, parent, show=""):
        entry = ttk.Entry(parent)
        if show:
            entry.configure(show=show)
        entry.pack(fill="x", ipady=2)
        return entry
        
    def show_landing(self):
        self.clear()

        container = tk.Frame(
            self.root,
            bg=self.bg
        )
        container.pack(
            expand=True,
            fill="both"
        )

        center = tk.Frame(
            container,
            bg=self.bg
        )
        center.place(
            relx=0.5,
            rely=0.5,
            anchor="center"
        )

        self.title_label(center)

        description = tk.Label(
            center,
            text="Manage your products and inventory\n"
                 "from one simple place.",
            font=("Arial", 12),
            fg=self.secondary,
            bg=self.bg,
            justify="center"
        )
        description.pack(pady=(0, 30))

        buttons = tk.Frame(
            center,
            bg=self.bg
        )
        buttons.pack()

        ttk.Button(
            buttons,
            text="LOG IN",
            style="Primary.TButton",
            command=self.show_login
        ).pack(
            side="left",
            padx=8
        )

        ttk.Button(
            buttons,
            text="CREATE ACCOUNT",
            command=self.show_signup
        ).pack(
            side="left",
            padx=8
        )

    def header(self, title, subtitle=None):
        top = tk.Frame(
            self.root,
            bg=self.card,
            height=80
        )
        top.pack(
            fill="x"
        )
        top.pack_propagate(False)

        left = tk.Frame(
            top,
            bg=self.card
        )
        left.pack(
            side="left",
            padx=30
        )

        tk.Label(
            left,
            text=title,
            font=("Arial", 20, "bold"),
            fg=self.primary,
            bg=self.card
        ).pack(
            anchor="w",
            pady=(14, 0)
        )

        if subtitle:
            tk.Label(
                left,
                text=subtitle,
                font=("Arial", 9),
                fg=self.secondary,
                bg=self.card
            ).pack(
                anchor="w"
            )

        ttk.Button(
            top,
            text="LOG OUT",
            command=self.logout
        ).pack(
            side="right",
            padx=25
        )

    def show_signup(self):
        self.clear()

        container = tk.Frame(
            self.root,
            bg=self.bg
        )
        container.pack(
            expand=True,
            fill="both"
        )

        card = self.create_card(container)

        self.title_label(card)

        tk.Label(
            card,
            text="CREATE YOUR ACCOUNT",
            font=("Arial", 18, "bold"),
            fg=self.primary,
            bg=self.card
        ).pack(pady=(0, 10))

        self.add_label(card, "Email")
        email = self.add_entry(card)

        self.add_label(card, "Password")
        password = self.add_entry(
            card,
            show="•"
        )

        self.add_label(card, "Confirm Password")
        confirm = self.add_entry(
            card,
            show="•"
        )

        message = tk.Label(
            card,
            text="",
            font=("Arial", 9),
            fg=self.danger,
            bg=self.card
        )
        message.pack(pady=8)

        def submit():
            email_value = email.get().strip().lower()
            password_value = password.get()
            confirm_value = confirm.get()

            if not email_value or not valid_email(email_value):
                message.config(
                    text="Please enter a valid email address."
                )
                return

            if len(password_value) < 6:
                message.config(
                    text="Password must be at least 6 characters."
                )
                return

            if password_value != confirm_value:
                message.config(
                    text="Passwords do not match."
                )
                return

            try:
                if get_user_by_email(email_value):
                    message.config(
                        text="An account with this email already exists."
                    )
                    return

                self.user_id = create_user(
                    email_value,
                    password_hash(password_value)
                )

                self.business_id = None

                self.show_onboarding()

            except IntegrityError:
                message.config(
                    text="An account with this email already exists."
                )

            except Exception:
                message.config(
                    text="Could not create your account."
                )

        ttk.Button(
            card,
            text="CREATE ACCOUNT",
            style="Primary.TButton",
            command=submit
        ).pack(
            fill="x",
            pady=5
        )

        ttk.Button(
            card,
            text="Already have an account? LOG IN",
            command=self.show_login
        ).pack(
            fill="x",
            pady=(8, 0)
        )

    def show_login(self):
        self.clear()

        container = tk.Frame(
            self.root,
            bg=self.bg
        )
        container.pack(
            expand=True,
            fill="both"
        )

        card = self.create_card(container)

        self.title_label(card)

        tk.Label(
            card,
            text="LOG IN",
            font=("Arial", 18, "bold"),
            fg=self.primary,
            bg=self.card
        ).pack(pady=(0, 10))

        self.add_label(card, "Email")
        email = self.add_entry(card)

        self.add_label(card, "Password")
        password = self.add_entry(
            card,
            show="•"
        )

        message = tk.Label(
            card,
            text="",
            font=("Arial", 9),
            fg=self.danger,
            bg=self.card
        )
        message.pack(pady=10)

        def submit():
            email_value = email.get().strip().lower()
            password_value = password.get()

            if not email_value or not password_value:
                message.config(
                    text="Email and password are required."
                )
                return

            try:
                user = get_user_by_email(email_value)

                if (
                    not user
                    or not verify_password(
                        password_value,
                        user["password_hash"]
                    )
                ):
                    message.config(
                        text="Invalid email or password."
                    )
                    return

                self.user_id = user["id"]

                business = get_business_by_user_id(
                    self.user_id
                )

                if business:
                    self.business_id = business["id"]
                    self.current_currency = business["currency"]
                    self.show_products()

                else:
                    self.business_id = None
                    self.show_onboarding()

            except Exception:
                message.config(
                    text="Could not complete login."
                )

        ttk.Button(
            card,
            text="LOG IN",
            style="Primary.TButton",
            command=submit
        ).pack(
            fill="x",
            pady=5
        )

        ttk.Button(
            card,
            text="Don't have an account? CREATE ACCOUNT",
            command=self.show_signup
        ).pack(
            fill="x",
            pady=(8, 0)
        )

    def show_onboarding(self):
        self.clear()

        self.header(
            "BUSINESS SETUP",
            "Tell us about your shop."
        )

        container = tk.Frame(
            self.root,
            bg=self.bg
        )
        container.pack(
            expand=True,
            fill="both"
        )

        card = self.create_card(container)

        tk.Label(
            card,
            text="Tell us about your shop.",
            font=("Arial", 20, "bold"),
            fg=self.primary,
            bg=self.card
        ).pack()

        tk.Label(
            card,
            text="A few details help ShopSight organize your inventory.",
            font=("Arial", 10),
            fg=self.secondary,
            bg=self.card
        ).pack(
            pady=(5, 20)
        )

        self.add_label(card, "Business name")
        business_name = self.add_entry(card)

        self.add_label(card, "Business type")

        business_type = ttk.Combobox(
            card,
            values=BUSINESS_TYPES,
            state="readonly"
        )
        business_type.current(0)
        business_type.pack(
            fill="x"
        )

        self.add_label(
            card,
            "Years in operation"
        )

        years = ttk.Spinbox(
            card,
            from_=0,
            to=200,
            increment=1
        )
        years.set("0")
        years.pack(
            fill="x"
        )

        self.add_label(card, "Currency")

        currency = ttk.Combobox(
            card,
            values=CURRENCIES,
            state="readonly"
        )
        currency.current(0)
        currency.pack(
            fill="x"
        )

        message = tk.Label(
            card,
            text="",
            font=("Arial", 9),
            fg=self.danger,
            bg=self.card
        )
        message.pack(pady=10)

        def submit():
            name = business_name.get().strip()

            if not name:
                message.config(
                    text="Business name is required."
                )
                return

            try:
                years_value = int(years.get())

                existing = get_business_by_user_id(
                    self.user_id
                )

                if existing:
                    self.business_id = existing["id"]
                    self.current_currency = existing["currency"]

                else:
                    self.business_id = create_business(
                        self.user_id,
                        name,
                        business_type.get(),
                        years_value,
                        currency.get()
                    )

                    self.current_currency = currency.get()

                self.show_products()

            except ValueError:
                message.config(
                    text="Years in operation must be a number."
                )

            except IntegrityError:
                message.config(
                    text="A business already exists for this account."
                )

            except Exception:
                message.config(
                    text="Could not save your business details."
                )

        ttk.Button(
            card,
            text="CONTINUE →",
            style="Primary.TButton",
            command=submit
        ).pack(
            fill="x",
            pady=5
        )

    def show_products(self):
        self.clear()

        self.header(
            "ADD YOUR PRODUCTS",
            "Add products manually or import your inventory."
        )

        container = tk.Frame(
            self.root,
            bg=self.bg
        )
        container.pack(
            expand=True,
            fill="both",
            padx=30,
            pady=25
        )

        products = get_products(
            self.business_id
        )

        top = tk.Frame(
            container,
            bg=self.bg
        )
        top.pack(
            fill="x",
            pady=(0, 15)
        )

        tk.Label(
            top,
            text=f"Products added: {len(products)}",
            font=("Arial", 13, "bold"),
            fg=self.primary,
            bg=self.bg
        ).pack(
            side="left"
        )

        buttons = tk.Frame(
            top,
            bg=self.bg
        )
        buttons.pack(
            side="right"
        )

        ttk.Button(
            buttons,
            text="+ ADD PRODUCT",
            style="Primary.TButton",
            command=self.show_manual_product
        ).pack(
            side="left",
            padx=5
        )

        ttk.Button(
            buttons,
            text="IMPORT CSV",
            command=self.show_csv_import
        ).pack(
            side="left",
            padx=5
        )

        if not products:
            empty = tk.Frame(
                container,
                bg=self.card,
                highlightbackground=self.border,
                highlightthickness=1
            )
            empty.pack(
                expand=True,
                fill="both"
            )

            tk.Label(
                empty,
                text="📦",
                font=("Arial", 36),
                bg=self.card,
                fg=self.secondary
            ).pack(
                pady=(70, 10)
            )

            tk.Label(
                empty,
                text="No products added yet",
                font=("Arial", 18, "bold"),
                bg=self.card,
                fg=self.primary
            ).pack()

            tk.Label(
                empty,
                text="Your product catalogue is empty.\n"
                     "Add your first product to get started.",
                font=("Arial", 11),
                bg=self.card,
                fg=self.secondary,
                justify="center"
            ).pack(
                pady=10
            )

            return

        table_frame = tk.Frame(
            container,
            bg=self.card
        )
        table_frame.pack(
            expand=True,
            fill="both"
        )

        columns = (
            "product",
            "category",
            "supplier",
            "purchase",
            "selling",
            "stock",
            "minimum"
        )

        tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings"
        )

        headings = {
            "product": "Product",
            "category": "Category",
            "supplier": "Supplier",
            "purchase": "Purchase Price",
            "selling": "Selling Price",
            "stock": "Stock",
            "minimum": "Minimum Stock"
        }

        widths = {
            "product": 180,
            "category": 120,
            "supplier": 140,
            "purchase": 120,
            "selling": 120,
            "stock": 90,
            "minimum": 110
        }

        for column in columns:
            tree.heading(
                column,
                text=headings[column]
            )
            tree.column(
                column,
                width=widths[column],
                anchor="center"
            )

        scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=tree.yview
        )

        tree.configure(
            yscrollcommand=scrollbar.set
        )

        tree.pack(
            side="left",
            expand=True,
            fill="both"
        )

        scrollbar.pack(
            side="right",
            fill="y"
        )

        for product in products:
            tree.insert(
                "",
                "end",
                values=(
                    product["product_name"],
                    product["category"],
                    product["supplier"],
                    f"{self.current_currency} {product['purchase_price']}",
                    f"{self.current_currency} {product['selling_price']}",
                    product["stock"],
                    product["minimum_stock"]
                )
            )

    def show_manual_product(self):
        self.clear()

        self.header(
            "ADD PRODUCT",
            "Enter the details for your product."
        )

        container = tk.Frame(
            self.root,
            bg=self.bg
        )
        container.pack(
            expand=True,
            fill="both"
        )

        card = self.create_card(container)

        self.add_label(card, "Product name")
        name = self.add_entry(card)

        self.add_label(card, "Category")

        categories = get_categories(
            self.business_id
        )

        category_names = [
            item["name"]
            for item in categories
        ]

        category_names.insert(
            0,
            "No category"
        )

        category = ttk.Combobox(
            card,
            values=category_names
        )
        category.current(0)
        category.pack(
            fill="x"
        )

        self.add_label(card, "Supplier")

        suppliers = get_suppliers(
            self.business_id
        )

        supplier_names = [
            item["name"]
            for item in suppliers
        ]

        supplier_names.insert(
            0,
            "No supplier"
        )

        supplier = ttk.Combobox(
            card,
            values=supplier_names
        )
        supplier.current(0)
        supplier.pack(
            fill="x"
        )

        self.add_label(card, "Purchase price")
        purchase = self.add_entry(card)

        self.add_label(card, "Selling price")
        selling = self.add_entry(card)

        self.add_label(card, "Current stock")
        stock = self.add_entry(card)

        self.add_label(card, "Minimum stock level")
        minimum = self.add_entry(card)
        minimum.insert(0, "10")

        message = tk.Label(
            card,
            text="",
            font=("Arial", 9),
            fg=self.danger,
            bg=self.card,
            wraplength=500
        )
        message.pack(
            pady=10
        )

        def submit():
            product_name = name.get().strip()

            if not product_name:
                message.config(
                    text="Product name is required."
                )
                return

            try:
                purchase_value = Decimal(
                    purchase.get().strip()
                )

                selling_value = Decimal(
                    selling.get().strip()
                )

                stock_value = Decimal(
                    stock.get().strip()
                )

                minimum_value = Decimal(
                    minimum.get().strip()
                )

                if (
                    purchase_value < 0
                    or selling_value < 0
                    or stock_value < 0
                    or minimum_value < 0
                ):
                    raise ValueError

                category_value = category.get().strip()

                supplier_value = supplier.get().strip()

                if category_value == "No category":
                    category_value = ""

                if supplier_value == "No supplier":
                    supplier_value = ""

                create_product(
                    self.business_id,
                    product_name,
                    category_value,
                    purchase_value,
                    selling_value,
                    stock_value,
                    minimum_value,
                    supplier_value
                )

                messagebox.showinfo(
                    "Product Saved",
                    "Product saved successfully."
                )

                self.show_products()

            except (InvalidOperation, ValueError):
                message.config(
                    text="Prices and stock must be valid non-negative numbers."
                )

            except Exception:
                message.config(
                    text="Could not save this product."
                )

        buttons = tk.Frame(
            card,
            bg=self.card
        )
        buttons.pack(
            fill="x",
            pady=5
        )

        ttk.Button(
            buttons,
            text="← BACK",
            command=self.show_products
        ).pack(
            side="left"
        )

        ttk.Button(
            buttons,
            text="SAVE PRODUCT",
            style="Primary.TButton",
            command=submit
        ).pack(
            side="right"
        )

    def show_csv_import(self):
        file_path = filedialog.askopenfilename(
            title="Choose CSV file",
            filetypes=[
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ]
        )

        if not file_path:
            return

        rows, errors, warnings = self.validate_csv(
            file_path
        )

        if errors:
            messagebox.showerror(
                "CSV Validation Error",
                "\n".join(errors[:20])
            )
            return

        if warnings:
            warning_text = "\n".join(
                warnings[:10]
            )

            if not messagebox.askyesno(
                "CSV Warnings",
                warning_text
                + "\n\nContinue with import?"
            ):
                return

        if not rows:
            messagebox.showerror(
                "CSV Import",
                "No valid product records were found."
            )
            return

        preview = (
            f"{len(rows)} valid product record(s) found.\n\n"
            "Do you want to import them?"
        )

        if not messagebox.askyesno(
            "Confirm Import",
            preview
        ):
            return

        try:
            filename = os.path.basename(
                file_path
            )

            imported = import_products(
                self.business_id,
                filename,
                rows
            )

            messagebox.showinfo(
                "Import Complete",
                f"Successfully imported {imported} product(s)."
            )

            self.show_products()

        except Exception:
            messagebox.showerror(
                "Import Failed",
                "The import failed and no partial changes were saved."
            )

    def validate_csv(self, file_path):
        errors = []
        warnings = []
        rows = []

        try:
            with open(
                file_path,
                "r",
                encoding="utf-8-sig",
                newline=""
            ) as file:

                reader = csv.DictReader(file)

                if not reader.fieldnames:
                    return [], ["The CSV file has no header."], []

                columns = {
                    str(column).strip().lower()
                    for column in reader.fieldnames
                    if column is not None
                }

                missing = (
                    REQUIRED_CSV_COLUMNS
                    - columns
                )

                if missing:
                    return (
                        [],
                        [
                            "Missing required columns: "
                            + ", ".join(
                                sorted(missing)
                            )
                        ],
                        []
                    )

                unknown = (
                    columns
                    - REQUIRED_CSV_COLUMNS
                    - OPTIONAL_CSV_COLUMNS
                )

                if unknown:
                    warnings.append(
                        "Ignored extra columns: "
                        + ", ".join(
                            sorted(unknown)
                        )
                    )

                for row_number, raw_row in enumerate(
                    reader,
                    start=2
                ):

                    row = {
                        str(key).strip().lower():
                        value
                        for key, value in raw_row.items()
                        if key is not None
                    }

                    product_name = (
                        row.get(
                            "product_name",
                            ""
                        )
                        or ""
                    ).strip()

                    if not product_name:
                        errors.append(
                            f"Row {row_number}: "
                            "product_name is required."
                        )
                        continue

                    parsed = {
                        "product_name": product_name
                    }

                    valid_row = True

                    for column in (
                        "purchase_price",
                        "selling_price",
                        "stock"
                    ):

                        value = (
                            row.get(
                                column,
                                ""
                            )
                            or ""
                        ).strip()

                        try:
                            number = Decimal(value)

                            if number < 0:
                                raise ValueError

                            parsed[column] = number

                        except (
                            InvalidOperation,
                            ValueError
                        ):
                            errors.append(
                                f"Row {row_number}: "
                                f"{column} must be a "
                                "non-negative number."
                            )
                            valid_row = False

                    minimum_value = (
                        row.get(
                            "minimum_stock",
                            ""
                        )
                        or ""
                    ).strip()

                    if not minimum_value:
                        minimum_value = "10"

                    try:
                        minimum = Decimal(
                            minimum_value
                        )

                        if minimum < 0:
                            raise ValueError

                        parsed["minimum_stock"] = minimum

                    except (
                        InvalidOperation,
                        ValueError
                    ):
                        errors.append(
                            f"Row {row_number}: "
                            "minimum_stock must be a "
                            "non-negative number."
                        )
                        valid_row = False

                    parsed["category"] = (
                        row.get(
                            "category",
                            ""
                        )
                        or ""
                    ).strip()

                    parsed["supplier"] = (
                        row.get(
                            "supplier",
                            ""
                        )
                        or ""
                    ).strip()

                    if (
                        valid_row
                        and parsed["selling_price"]
                        < parsed["purchase_price"]
                    ):
                        warnings.append(
                            f"Row {row_number}: "
                            "selling price is lower "
                            "than purchase price."
                        )

                    if valid_row:
                        rows.append(parsed)

        except UnicodeDecodeError:
            return (
                [],
                [
                    "The CSV file encoding could not "
                    "be read. Please save it as UTF-8."
                ],
                []
            )

        except Exception:
            return (
                [],
                [
                    "The CSV file could not be read."
                ],
                []
            )

        return rows, errors, warnings

    def logout(self):
        self.user_id = None
        self.business_id = None
        self.current_currency = "INR"
        self.show_landing()


def main():
    try:
        if not get_connection_test():
            raise RuntimeError(
                "MySQL connection failed."
            )
    except Exception as exc:
        root = tk.Tk()
        root.withdraw()

        messagebox.showerror(
            "ShopSight Database Error",
            "Could not connect to MySQL.\n\n"
            "Check your MYSQL_HOST, MYSQL_PORT, "
            "MYSQL_USER, MYSQL_PASSWORD and "
            "MYSQL_DATABASE environment variables.\n\n"
            f"Details: {exc}"
        )

        root.destroy()
        return

    root = tk.Tk()
    ShopSightApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()