import hashlib
import hmac
import io
import logging
import os
import re
from decimal import Decimal,InvalidOperation
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from mysql.connector import IntegrityError
import database
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger=logging.getLogger("shopsight")
BUSINESS_TYPES=["Grocery","Clothing","Electronics","Pharmacy","Restaurant","Other"]
CURRENCIES=["INR","USD","AED"]
REQUIRED_CSV_COLUMNS={"product_name","purchase_price","selling_price","stock"}
OPTIONAL_CSV_COLUMNS={"category","minimum_stock","supplier"}
def init_session()->None:
    defaults={"user_id":None,"business_id":None,"current_screen":"landing","product_mode":None}
    for key,value in defaults.items():
        if key not in st.session_state:
            st.session_state[key]=value
def password_hash(password:str)->str:
    salt=os.urandom(16)
    digest=hashlib.pbkdf2_hmac("sha256",password.encode(),salt,200000)
    return f"pbkdf2_sha256$200000${salt.hex()}${digest.hex()}"
def verify_password(password:str,stored:str)->bool:
    try:
        algorithm,rounds_text,salt_hex,digest_hex=stored.split("$",3)
        if algorithm!="pbkdf2_sha256":
            return False
        rounds=int(rounds_text)
        actual=hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(salt_hex),rounds)
        return hmac.compare_digest(actual,bytes.fromhex(digest_hex))
    except (ValueError,TypeError):
        return False
def valid_email(email:str)->bool:
    return bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+",email))
def logout()->None:
    st.session_state.user_id=None
    st.session_state.business_id=None
    st.session_state.current_screen="landing"
    st.session_state.product_mode=None
    st.rerun()
def safe_error(message:str,exc:Exception|None=None)->None:
    if exc:
        logger.exception("ShopSight operation failed")
    st.error(message)
def page_header(show_logout:bool=True)->None:
    left,right=st.columns([4,1])
    with left:
        st.title("SHOP SIGHT")
        st.caption("Smarter decisions for your shop.")
    with right:
        if show_logout and st.session_state.user_id and st.button("LOG OUT",use_container_width=True):
            logout()
def landing_screen()->None:
    st.title("SHOP SIGHT")
    st.subheader("Smarter decisions for your shop.")
    st.write("Manage your products and inventory from one simple place.")
    st.divider()
    col1,col2=st.columns(2)
    with col1:
        if st.button("LOG IN",use_container_width=True,type="primary"):
            st.session_state.current_screen="login"
            st.rerun()
    with col2:
        if st.button("CREATE ACCOUNT",use_container_width=True):
            st.session_state.current_screen="signup"
            st.rerun()
def signup_screen()->None:
    page_header(False)
    st.header("CREATE YOUR ACCOUNT")
    with st.form("signup_form"):
        email=st.text_input("Email")
        password=st.text_input("Password",type="password")
        confirm=st.text_input("Confirm Password",type="password")
        submitted=st.form_submit_button("CREATE ACCOUNT",type="primary")
    if submitted:
        email=email.strip().lower()
        if not email or not valid_email(email):
            st.error("Please enter a valid email address.")
        elif len(password)<6:
            st.error("Password must be at least 6 characters long.")
        elif password!=confirm:
            st.error("Passwords do not match.")
        else:
            try:
                if database.get_user_by_email(email):
                    st.error("An account with that email already exists.")
                else:
                    st.session_state.user_id=database.create_user(email,password_hash(password))
                    st.session_state.business_id=None
                    st.session_state.current_screen="onboarding"
                    st.session_state.product_mode=None
                    st.rerun()
            except IntegrityError:
                st.error("An account with that email already exists.")
            except Exception as exc:
                safe_error("We could not create your account. Please try again.",exc)
    if st.button("Already have an account? LOG IN"):
        st.session_state.current_screen="login"
        st.rerun()
def login_screen()->None:
    page_header(False)
    st.header("LOG IN")
    with st.form("login_form"):
        email=st.text_input("Email")
        password=st.text_input("Password",type="password")
        submitted=st.form_submit_button("LOG IN",type="primary")
    if submitted:
        email=email.strip().lower()
        if not email or not password:
            st.error("Email and password are required.")
            return
        try:
            user=database.get_user_by_email(email)
            if not user or not verify_password(password,user["password_hash"]):
                st.error("Invalid email or password.")
                return
            business=database.get_business_by_user_id(user["id"])
            st.session_state.user_id=user["id"]
            st.session_state.business_id=business["id"] if business else None
            st.session_state.current_screen="products" if business else "onboarding"
            st.session_state.product_mode=None
            st.rerun()
        except Exception as exc:
            safe_error("We could not complete the login. Please try again.",exc)
    if st.button("Don't have an account? CREATE ACCOUNT"):
        st.session_state.current_screen="signup"
        st.rerun()
def onboarding_screen()->None:
    page_header()
    st.header("Tell us about your shop.")
    st.write("A few details help ShopSight organize your inventory.")
    st.progress(25,text="1/4 Setup")
    with st.form("business_form"):
        business_name=st.text_input("Business name")
        business_type=st.selectbox("Business type",BUSINESS_TYPES)
        years=st.number_input("Years in operation",min_value=0,max_value=200,value=0,step=1)
        currency=st.selectbox("Currency",CURRENCIES)
        submitted=st.form_submit_button("CONTINUE →",type="primary")
    if submitted:
        business_name=business_name.strip()
        if not business_name:
            st.error("Business name is required.")
            return
        try:
            existing=database.get_business_by_user_id(st.session_state.user_id)
            if existing:
                st.session_state.business_id=existing["id"]
            else:
                st.session_state.business_id=database.create_business(st.session_state.user_id,business_name,business_type,int(years),currency)
            st.session_state.current_screen="products"
            st.session_state.product_mode=None
            st.rerun()
        except IntegrityError:
            st.error("A business is already associated with this account.")
        except Exception as exc:
            safe_error("We could not save your business details.",exc)
def validate_product_values(name:str,purchase:float,selling:float,stock:float,minimum:float)->str|None:
    if not name.strip():
        return "Product name is required."
    if purchase<0 or selling<0 or stock<0 or minimum<0:
        return "Prices and stock values cannot be negative."
    return None
def product_form()->None:
    st.subheader("ADD PRODUCT")
    categories=database.get_categories(st.session_state.business_id)
    suppliers=database.get_suppliers(st.session_state.business_id)
    category_options=[""]+[x["name"] for x in categories]
    supplier_options=[""]+[x["name"] for x in suppliers]
    with st.form("product_form"):
        name=st.text_input("Product name")
        category=st.selectbox("Category",category_options,format_func=lambda x:x or "No category")
        supplier=st.selectbox("Supplier",supplier_options,format_func=lambda x:x or "No supplier")
        purchase=st.number_input("Purchase price",min_value=0.0,value=0.0,step=0.01,format="%.2f")
        selling=st.number_input("Selling price",min_value=0.0,value=0.0,step=0.01,format="%.2f")
        stock=st.number_input("Current stock",min_value=0.0,value=0.0,step=1.0)
        minimum=st.number_input("Minimum stock level",min_value=0.0,value=10.0,step=1.0)
        submitted=st.form_submit_button("SAVE PRODUCT",type="primary")
    if submitted:
        error=validate_product_values(name,purchase,selling,stock,minimum)
        if error:
            st.error(error)
            return
        try:
            database.create_product(st.session_state.business_id,name.strip(),category.strip(),Decimal(str(purchase)),Decimal(str(selling)),Decimal(str(stock)),Decimal(str(minimum)),supplier.strip())
            st.success("Product saved successfully.")
            st.session_state.product_mode=None
            st.rerun()
        except Exception as exc:
            safe_error("We could not save this product.",exc)
def validate_csv(uploaded_file)->tuple[list[dict],list[str],list[str]]:
    errors=[]
    warnings=[]
    try:
        df=pd.read_csv(io.BytesIO(uploaded_file.getvalue()))
    except Exception:
        return [],["The CSV file could not be read. Please check its format."],[]
    df.columns=[str(c).strip().lower() for c in df.columns]
    missing=REQUIRED_CSV_COLUMNS-set(df.columns)
    if missing:
        return [],["Missing required columns: "+", ".join(sorted(missing))],[]
    unknown=set(df.columns)-REQUIRED_CSV_COLUMNS-OPTIONAL_CSV_COLUMNS
    if unknown:
        warnings.append("Ignored extra columns: "+", ".join(sorted(unknown)))
    rows=[]
    for index,record in df.iterrows():
        row_number=index+2
        product_name=str(record.get("product_name","")).strip()
        if not product_name or product_name.lower()=="nan":
            errors.append(f"Row {row_number}: product_name is required.")
            continue
        parsed={"product_name":product_name}
        for column in ("purchase_price","selling_price","stock"):
            value=record.get(column)
            try:
                if pd.isna(value) or str(value).strip()=="":
                    raise ValueError
                number=Decimal(str(value).strip())
                if number<0:
                    raise ValueError
                parsed[column]=number
            except (InvalidOperation,ValueError,TypeError):
                errors.append(f"Row {row_number}: {column} must be a non-negative number.")
        minimum_value=record.get("minimum_stock",10)
        try:
            if pd.isna(minimum_value) or str(minimum_value).strip()=="":
                minimum_value=10
            minimum=Decimal(str(minimum_value).strip())
            if minimum<0:
                raise ValueError
            parsed["minimum_stock"]=minimum
        except (InvalidOperation,ValueError,TypeError):
            errors.append(f"Row {row_number}: minimum_stock must be a non-negative number.")
        category=record.get("category","")
        supplier=record.get("supplier","")
        parsed["category"]="" if pd.isna(category) else str(category).strip()
        parsed["supplier"]="" if pd.isna(supplier) else str(supplier).strip()
        if all(key in parsed for key in ("purchase_price","selling_price","stock","minimum_stock")):
            if parsed["selling_price"]<parsed["purchase_price"]:
                warnings.append(f"Row {row_number}: selling price is lower than purchase price.")
            rows.append(parsed)
    return rows,errors,warnings
def csv_import_screen()->None:
    st.subheader("IMPORT CSV")
    st.write("Upload a CSV containing your existing product catalogue.")
    st.info("Required columns: product_name, purchase_price, selling_price, stock. Optional: category, minimum_stock, supplier.")
    uploaded=st.file_uploader("Choose a CSV file",type=["csv"])
    if uploaded is None:
        return
    rows,errors,warnings=validate_csv(uploaded)
    if errors:
        st.error("The file needs attention before it can be imported.")
        for error in errors[:20]:
            st.write(f"• {error}")
        if len(errors)>20:
            st.write(f"• And {len(errors)-20} more errors.")
        return
    for warning in warnings:
        st.warning(warning)
    st.success(f"{len(rows)} valid product record(s) found.")
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
    if st.button(f"IMPORT {len(rows)} PRODUCTS",type="primary",disabled=not rows):
        try:
            imported=database.import_products(st.session_state.business_id,uploaded.name,rows)
            st.success(f"Successfully imported {imported} product(s).")
            st.session_state.product_mode=None
            st.rerun()
        except Exception as exc:
            safe_error("The import failed and no partial changes were saved.",exc)
def products_screen()->None:
    page_header()
    st.header("Add your products")
    st.write("Add products manually or import them from a CSV file.")
    st.progress(100,text="PRODUCT SETUP")
    try:
        products=database.get_products(st.session_state.business_id)
    except Exception as exc:
        safe_error("We could not load your products.",exc)
        return
    st.metric("Products added",len(products))
    mode=st.session_state.product_mode
    if mode in ("manual","csv"):
        if st.button("← BACK TO PRODUCTS"):
            st.session_state.product_mode=None
            st.rerun()
        if mode=="manual":
            product_form()
        else:
            csv_import_screen()
        return
    if not products:
        st.info("No products yet.\n\nYour product catalogue is empty. Add your first product to get started.")
    else:
        business=database.get_business_by_user_id(st.session_state.user_id)
        currency=business["currency"] if business else ""
        display=pd.DataFrame(products)
        for column in ("Purchase Price","Selling Price"):
            display[column]=display[column].map(lambda value:f"{currency} {value}")
        st.dataframe(display,use_container_width=True,hide_index=True)
    col1,col2=st.columns(2)
    with col1:
        if st.button("+ ADD PRODUCT",use_container_width=True,type="primary"):
            st.session_state.product_mode="manual"
            st.rerun()
    with col2:
        if st.button("IMPORT CSV",use_container_width=True):
            st.session_state.product_mode="csv"
            st.rerun()
def route()->None:
    if st.session_state.user_id:
        if not st.session_state.business_id:
            try:
                business=database.get_business_by_user_id(st.session_state.user_id)
                if business:
                    st.session_state.business_id=business["id"]
            except Exception as exc:
                safe_error("We could not load your business information.",exc)
        if st.session_state.current_screen=="onboarding" or not st.session_state.business_id:
            onboarding_screen()
        else:
            products_screen()
        return
    screen=st.session_state.current_screen
    if screen=="signup":
        signup_screen()
    elif screen=="login":
        login_screen()
    else:
        landing_screen()
def main()->None:
    st.set_page_config(page_title="ShopSight",page_icon="🛍️",layout="centered")
    init_session()
    route()
if __name__=="__main__":
    main()
