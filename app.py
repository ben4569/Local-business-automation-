import csv
import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from decimal import Decimal, InvalidOperation

from database import (
    get_user_by_email,
    create_user,
    get_business_by_user_id,
    create_business,
    get_products,
    create_product,
    import_products,
    get_connection_test,
    BUSINESS_TYPES,
    CURRENCIES,
    REQUIRED_CSV_COLUMNS,
    OPTIONAL_CSV_COLUMNS,
)


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

    # --------------------------------------------------
    # STYLES
    # --------------------------------------------------

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
            padding=8,
            font=("Arial", 11)
        )

        style.configure(
            "TCombobox",
            padding=8,
            font=("Arial", 11)
        )

        style.configure(
            "Treeview",
            rowheight=35,
            font=("Arial", 10)
        )

        style.configure(
            "Treeview.Heading",
            font=("Arial", 10, "bold")
        )

    # --------------------------------------------------
    # HELPERS
    # --------------------------------------------------

    def clear(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def valid_email(self, email):
        return bool(
            re.fullmatch(
                r"[^\s@]+@[^\s@]+\.[^\s@]+",
                email
            )
        )

    def title_label(self, parent):
        tk.Label(
            parent,
            text="SHOP SIGHT",
            font=("Arial", 28, "bold"),
            fg=self.primary,
            bg=parent.cget("bg")
        ).pack()

        tk.Label(
            parent,
            text="Smarter decisions for your shop.",
            font=("Arial", 12),
            fg=self.secondary,
            bg=parent.cget("bg")
        ).pack(pady=(5, 25))

    def create_card(self, parent):
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
        tk.Label(
            parent,
            text=text,
            font=("Arial", 10, "bold"),
            fg=self.primary,
            bg=self.card,
            anchor="w"
        ).pack(
            fill="x",
            pady=(10, 5)
        )

    def add_entry(self, parent, show=None):
        entry = ttk.Entry(parent)

        if show:
            entry.configure(show=show)

        entry.pack(
            fill="x",
            ipady=2
        )

        return entry

    # --------------------------------------------------
    # LANDING
    # --------------------------------------------------

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

        tk.Label(
            center,
            text="Manage your products and inventory\n"
                 "from one simple place.",
            font=("Arial", 12),
            fg=self.secondary,
            bg=self.bg,
            justify="center"
        ).pack(pady=(0, 30))

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

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def header(self, title, subtitle=None):
        top = tk.Frame(
            self.root,
            bg=self.card,
            height=80
        )

        top.pack(fill="x")
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
            ).pack(anchor="w")

        ttk.Button(
            top,
            text="LOG OUT",
            command=self.logout
        ).pack(
            side="right",
            padx=25
        )

    # --------------------------------------------------
    # SIGN UP
    # --------------------------------------------------

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
            show="*"
        )

        self.add_label(card, "Confirm Password")
        confirm = self.add_entry(
            card,
            show="*"
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

            if not self.valid_email(email_value):
                message.config(
                    text="Please enter a valid email."
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
                    password_value
                )

                self.business_id = None

                self.show_onboarding()

            except Exception as exc:
                message.config(
                    text=f"Could not create account: {exc}"
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
            text="BACK TO LOGIN",
            command=self.show_login
        ).pack(
            fill="x",
            pady=5
        )

    # --------------------------------------------------
    # LOGIN
    # --------------------------------------------------

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
            show="*"
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

            try:
                user = get_user_by_email(email_value)

                if not user:
                    message.config(
                        text="Invalid email or password."
                    )
                    return

                # database.py supports the password verification
                # through the stored PBKDF2 hash.
                from database import verify_password

                if not verify_password(
                    password_value,
                    user["password_hash"]
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
                    self.show_dashboard()
                else:
                    self.show_onboarding()

            except Exception as exc:
                message.config(
                    text=f"Login failed: {exc}"
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
            text="CREATE ACCOUNT",
            command=self.show_signup
        ).pack(
            fill="x",
            pady=5
        )

    # --------------------------------------------------
    # ONBOARDING
    # --------------------------------------------------

    def show_onboarding(self):
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
            text="BUSINESS SETUP",
            font=("Arial", 18, "bold"),
            fg=self.primary,
            bg=self.card
        ).pack(pady=(0, 10))

        self.add_label(card, "Business Name")
        business_name = self.add_entry(card)

        self.add_label(card, "Business Type")

        business_type = ttk.Combobox(
            card,
            values=BUSINESS_TYPES,
            state="readonly"
        )

        business_type.pack(
            fill="x"
        )

        business_type.set(BUSINESS_TYPES[0])

        self.add_label(card, "Years in Operation")

        years = self.add_entry(card)
        years.insert(0, "0")

        self.add_label(card, "Currency")

        currency = ttk.Combobox(
            card,
            values=CURRENCIES,
            state="readonly"
        )

        currency.pack(fill="x")
        currency.set("INR")

        message = tk.Label(
            card,
            text="",
            font=("Arial", 9),
            fg=self.danger,
            bg=self.card
        )

        message.pack(pady=8)

        def submit():
            name = business_name.get().strip()
            btype = business_type.get()
            currency_value = currency.get()

            try:
                years_value = int(
                    years.get().strip()
                )

                if years_value < 0:
                    raise ValueError

            except ValueError:
                message.config(
                    text="Years must be a valid number."
                )
                return

            if not name:
                message.config(
                    text="Business name is required."
                )
                return

            try:
                self.business_id = create_business(
                    self.user_id,
                    name,
                    btype,
                    years_value,
                    currency_value
                )

                self.current_currency = currency_value

                self.show_dashboard()

            except Exception as exc:
                message.config(
                    text=f"Could not save business: {exc}"
                )

        ttk.Button(
            card,
            text="CONTINUE",
            style="Primary.TButton",
            command=submit
        ).pack(
            fill="x",
            pady=5
        )

    # --------------------------------------------------
    # DASHBOARD
    # --------------------------------------------------

    def show_dashboard(self):
        self.clear()

        self.header(
            "ShopSight",
            "Inventory Dashboard"
        )

        body = tk.Frame(
            self.root,
            bg=self.bg
        )

        body.pack(
            expand=True,
            fill="both",
            padx=30,
            pady=25
        )

        top = tk.Frame(
            body,
            bg=self.bg
        )

        top.pack(
            fill="x",
            pady=(0, 15)
        )

        ttk.Button(
            top,
            text="ADD PRODUCT",
            style="Primary.TButton",
            command=self.add_product_window
        ).pack(side="left")

        ttk.Button(
            top,
            text="IMPORT CSV",
            command=self.import_csv
        ).pack(side="left", padx=10)

        ttk.Button(
            top,
            text="REFRESH",
            command=self.show_dashboard
        ).pack(side="right")

        columns = (
            "Product",
            "Category",
            "Supplier",
            "Purchase",
            "Selling",
            "Stock",
            "Minimum"
        )

        tree = ttk.Treeview(
            body,
            columns=columns,
            show="headings"
        )

        for column in columns:
            tree.heading(
                column,
                text=column
            )

            tree.column(
                column,
                width=130,
                anchor="center"
            )

        tree.pack(
            expand=True,
            fill="both"
        )

        try:
            products = get_products(
                self.business_id
            )

            for product in products:
                tree.insert(
                    "",
                    "end",
                    values=(
                        product["product_name"],
                        product["category"],
                        product["supplier"],
                        product["purchase_price"],
                        product["selling_price"],
                        product["stock"],
                        product["minimum_stock"]
                    )
                )

        except Exception as exc:
            messagebox.showerror(
                "Database Error",
                str(exc)
            )

    # --------------------------------------------------
    # ADD PRODUCT
    # --------------------------------------------------

    def add_product_window(self):
        window = tk.Toplevel(self.root)

        window.title("Add Product")
        window.geometry("500x650")
        window.configure(bg=self.bg)

        card = self.create_card(window)

        tk.Label(
            card,
            text="ADD PRODUCT",
            font=("Arial", 18, "bold"),
            fg=self.primary,
            bg=self.card
        ).pack(pady=(0, 10))

        self.add_label(card, "Product Name")
        name = self.add_entry(card)

        self.add_label(card, "Category")
        category = self.add_entry(card)

        self.add_label(card, "Supplier")
        supplier = self.add_entry(card)

        self.add_label(card, "Purchase Price")
        purchase = self.add_entry(card)

        self.add_label(card, "Selling Price")
        selling = self.add_entry(card)

        self.add_label(card, "Stock")
        stock = self.add_entry(card)

        self.add_label(card, "Minimum Stock")
        minimum = self.add_entry(card)

        message = tk.Label(
            card,
            text="",
            fg=self.danger,
            bg=self.card
        )

        message.pack(pady=8)

        def save():
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
                    raise InvalidOperation

            except InvalidOperation:
                message.config(
                    text="Please enter valid positive numbers."
                )
                return

            try:
                create_product(
                    self.business_id,
                    product_name,
                    category.get().strip(),
                    purchase_value,
                    selling_value,
                    stock_value,
                    minimum_value,
                    supplier.get().strip()
                )

                window.destroy()

                self.show_dashboard()
            except Exception as exc:
                message.config(
                    text=f"Could not save: {exc}"
                )

        ttk.Button(
            card,
            text="SAVE PRODUCT",
            style="Primary.TButton",
            command=save
        ).pack(
            fill="x",
            pady=5
        )

    # --------------------------------------------------
    # CSV IMPORT
    # --------------------------------------------------

    def import_csv(self):
        filename = filedialog.askopenfilename(
            title="Select CSV file",
            filetypes=[
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ]
        )

        if not filename:
            return

        try:
            with open(
                filename,
                "r",
                encoding="utf-8-sig",
                newline=""
            ) as file:

                reader = csv.DictReader(file)

                if not reader.fieldnames:
                    messagebox.showerror(
                        "Import Error",
                        "CSV file is empty."
                    )
                    return

                missing = (
                    REQUIRED_CSV_COLUMNS
                    - set(reader.fieldnames)
                )

                if missing:
                    messagebox.showerror(
                        "Import Error",
                        "Missing columns:\n"
                        + "\n".join(sorted(missing))
                    )
                    return

                rows = []

                for row_number, row in enumerate(
                    reader,
                    start=2
                ):
                    try:
                        purchase = Decimal(
                            row["purchase_price"]
                        )

                        selling = Decimal(
                            row["selling_price"]
                        )

                        stock = Decimal(
                            row["stock"]
                        )

                        minimum = Decimal(
                            row.get(
                                "minimum_stock",
                                "0"
                            ) or "0"
                        )

                        if (
                            purchase < 0
                            or selling < 0
                            or stock < 0
                            or minimum < 0
                        ):
                            raise InvalidOperation

                        product_name = (
                            row["product_name"]
                            .strip()
                        )

                        if not product_name:
                            raise ValueError(
                                "Product name is empty"
                            )

                        rows.append({
                            "product_name": product_name,
                            "purchase_price": purchase,
                            "selling_price": selling,
                            "stock": stock,
                            "minimum_stock": minimum,
                            "category": (
                                row.get(
                                    "category",
                                    ""
                                ) or ""
                            ).strip(),
                            "supplier": (
                                row.get(
                                    "supplier",
                                    ""
                                ) or ""
                            ).strip()
                        })

                    except Exception as exc:
                        messagebox.showerror(
                            "Import Error",
                            f"Error on CSV row "
                            f"{row_number}:\n{exc}"
                        )
                        return

            if not rows:
                messagebox.showwarning(
                    "Import",
                    "No products found in the CSV."
                )
                return

            imported = import_products(
                self.business_id,
                filename,
                rows
            )

            messagebox.showinfo(
                "Import Complete",
                f"{imported} products imported."
            )

            self.show_dashboard()

        except Exception as exc:
            messagebox.showerror(
                "Import Error",
                str(exc)
            )

    # --------------------------------------------------
    # LOGOUT
    # --------------------------------------------------

    def logout(self):
        self.user_id = None
        self.business_id = None
        self.current_currency = "INR"

        self.show_landing()


# ------------------------------------------------------
# START APPLICATION
# ------------------------------------------------------

if __name__ == "__main__":
    root = tk.Tk()
    app = ShopSightApp(root)
    root.mainloop() 
