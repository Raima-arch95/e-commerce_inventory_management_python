import pandas as pd
import streamlit as st
import plotly.express as px
import requests
import uuid
import sqlite3

# Telegram credentials
TELEGRAM_BOT_TOKEN = "7299989631:AAHhTyw9VvmsiXCkapYzU08Qz6FGTIdyeUc"
TELEGRAM_CHAT_ID = "7005860166"

# Send Telegram message
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, data=data)
    except:
        pass

# Initialize SQLite Database
def init_db():
    conn = sqlite3.connect('ecommerce_inventory.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (
                    id TEXT PRIMARY KEY,
                    product_name TEXT,
                    category TEXT,
                    quantity INTEGER,
                    price REAL)''')
    conn.commit()
    conn.close()

# Insert product into DB
def add_product(product_name, category, quantity, price):
    conn = sqlite3.connect('ecommerce_inventory.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO inventory (id, product_name, category, quantity, price) VALUES (?, ?, ?, ?, ?)",
                  (str(uuid.uuid4()), product_name, category, int(quantity), float(price)))
        conn.commit()
        st.session_state["add_success"] = f"✅ '{product_name}' added successfully"
    except Exception as e:
        st.error(f"Error adding product: {e}")
    conn.close()

# Fetch all inventory
def get_inventory():
    conn = sqlite3.connect('ecommerce_inventory.db')
    df = pd.read_sql_query("SELECT * FROM inventory", conn)
    conn.close()
    return df

# Clear all inventory
def clear_inventory():
    conn = sqlite3.connect('ecommerce_inventory.db')
    c = conn.cursor()
    c.execute("DELETE FROM inventory")
    conn.commit()
    conn.close()
    st.session_state["clear_success"] = "All inventory cleared."

# Delete a specific product
def delete_product(product_id):
    conn = sqlite3.connect('ecommerce_inventory.db')
    c = conn.cursor()
    c.execute("DELETE FROM inventory WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    st.session_state["delete_success"] = "🗑️   Product deleted successfully"

# Update product quantity and/or price
def update_product_details(product_id, new_quantity=None, new_price=None):
    conn = sqlite3.connect('ecommerce_inventory.db')
    c = conn.cursor()
    if new_quantity is not None:
        c.execute("UPDATE inventory SET quantity = ? WHERE id = ?", (new_quantity, product_id))
    if new_price is not None:
        c.execute("UPDATE inventory SET price = ? WHERE id = ?", (new_price, product_id))
    conn.commit()
    conn.close()
    st.session_state["update_success"] = "✅ Product updated successfully"

# Load from DummyJSON API
def insert_products_from_api():
    url = "https://dummyjson.com/products"
    response = requests.get(url)
    if response.status_code == 200:
        products = response.json().get("products", [])
        for product in products:
            try:
                product_name = str(product.get('title', 'Unknown'))
                category = str(product.get('category', 'Uncategorized'))
                quantity = int(product.get('stock', 100))
                raw_price = product.get('price', 0)
                if isinstance(raw_price, (int, float, str)):
                    price = float(str(raw_price).replace('$', '').replace(',', '').strip())
                else:
                    raise ValueError(f"Invalid price format: {raw_price}")

                add_product(product_name, category, quantity, price)
            except Exception as e:
                st.warning(f"⛔ Skipped product: {product.get('title', 'Unknown')} → {e}")
        st.session_state["api_success"] = True

# Load from user-uploaded file
def insert_products_from_file(uploaded_file):
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            df = df[['product_name', 'category', 'quantity', 'price']]
            df['id'] = [str(uuid.uuid4()) for _ in range(len(df))]
            records = df[['id', 'product_name', 'category', 'quantity', 'price']].values.tolist()

            conn = sqlite3.connect('ecommerce_inventory.db')
            c = conn.cursor()
            c.executemany(
                "INSERT INTO inventory (id, product_name, category, quantity, price) VALUES (?, ?, ?, ?, ?)",
                records
            )
            conn.commit()
            conn.close()
            st.session_state["file_success"] = True
        except Exception as e:
            st.error(f"Failed to upload data: {e}")

# UI Styling
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');
        html, body, [class*="css"]  {
            font-family: 'Poppins', sans-serif !important;
        }
        .stApp {
            background-image: url("https://img.freepik.com/free-photo/abstract-digital-grid-black-background_53876-97647.jpg");
            background-size: cover;
            background-repeat: no-repeat;
            background-attachment: fixed;
            background-position: center;
            color: #ffffff;
        }
        .reportview-container .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🛒 E-commerce Inventory Management")
init_db()

tab1, tab2, tab3, tab4 = st.tabs(["Inventory Dashboard", "Add/Delete Products", "Update Stock/Price", "Low Stock Reminder"])

# --- Tab 1 ---
with tab1:
    st.header("📦 Inventory Overview")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📥 Load Data From Dummy API")
        if st.button("Load Dummy Data from API"):
            insert_products_from_api()
            st.rerun()

    with col2:
        st.subheader("📤 Upload Your Own Inventory File")
        uploaded_file = st.file_uploader("Upload CSV", type=['csv'])
        if uploaded_file and not st.session_state.get("uploaded"):
            insert_products_from_file(uploaded_file)
            st.session_state["uploaded"] = True
            st.rerun()

    for key in ["api_success", "file_success", "clear_success"]:
        if st.session_state.get(key):
            st.success(st.session_state[key])
            del st.session_state[key]
            if key == "file_success":
                del st.session_state["uploaded"]

    if st.button("Clear All Inventory"):
        clear_inventory()
        st.rerun()

    df = get_inventory()
    if not df.empty:
        renamed_df = df.rename(columns={
            'product_name': '🛍️   Product Name',
            'category': '📂 Category',
            'quantity': '📦 Quantity',
            'price': '💲 Price ($)'
        })
        st.dataframe(renamed_df)

        st.subheader("📊 Category-wise Stock Distribution")
        st.plotly_chart(px.bar(df, x='category', y='quantity', color='category'))

        st.subheader("💰 Average Product Price per Category")
        avg_prices = df.groupby('category', as_index=False)['price'].mean()
        st.plotly_chart(px.pie(avg_prices, names='category', values='price'))

# --- Tab 2 ---
with tab2:
    st.header("➕ Add or ❌ Delete Products")
    with st.form("add_form"):
        pname = st.text_input("Product Name")
        pcat = st.text_input("Category")
        pqty = st.number_input("Quantity", min_value=0)
        pprice = st.number_input("Price", min_value=0.0, format="%.2f")
        if st.form_submit_button("Add Product"):
            add_product(pname, pcat, pqty, pprice)
            st.rerun()

    if st.session_state.get("add_success"):
        st.success(st.session_state["add_success"])
        del st.session_state["add_success"]

    df = get_inventory()
    if not df.empty:
        product_options = [f"{row.product_name} ({row.id})" for row in df.itertuples()]
        selected = st.selectbox("Select a Product to Delete", product_options)
        if st.button("Delete Product"):
            pid = selected.split('(')[-1].strip(')')
            delete_product(pid)
            st.rerun()

    if st.session_state.get("delete_success"):
        st.success(st.session_state["delete_success"])
        del st.session_state["delete_success"]

# --- Tab 3 ---
with tab3:
    st.header("✏️ Update Stock or Price")
    df = get_inventory()
    if not df.empty:
        product_options = [f"{row.product_name} ({row.id})" for row in df.itertuples()]
        selected = st.selectbox("Select Product to Update", product_options)
        pid = selected.split('(')[-1].strip(')')
        new_qty = st.number_input("New Quantity", min_value=0, value=0)
        new_price = st.number_input("New Price", min_value=0.0, value=0.0, format="%.2f")
        if st.button("Update"):
            update_product_details(pid, new_quantity=new_qty if new_qty > 0 else None, new_price=new_price if new_price > 0 else None)
            st.rerun()

    if st.session_state.get("update_success"):
        st.success(st.session_state["update_success"])
        del st.session_state["update_success"]

# --- Tab 4 ---
# --- Tab 4: Low Stock Reminder --- #
with tab4:
    st.header("🔔 Low Stock Alerts")

    # Ensure a threshold is explicitly set
    if "threshold_set" not in st.session_state:
        st.session_state["threshold_set"] = False
    if "enable_alerts" not in st.session_state:
        st.session_state["enable_alerts"] = False

    low_stock_threshold = st.slider("Set Stock Threshold", min_value=1, max_value=100, value=10, key="threshold_slider")
    enable_alerts = st.checkbox("Enable Telegram Alert", value=st.session_state.get("enable_alerts", False))

    if st.button("Apply Threshold"):
        st.session_state["threshold_value"] = low_stock_threshold
        st.session_state["threshold_set"] = True
        st.session_state["enable_alerts"] = enable_alerts
        st.session_state["notified_products"] = []  # Reset when threshold changes
        st.success(f"Threshold of {low_stock_threshold} applied.")

    if st.session_state["threshold_set"]:
        df = get_inventory()
        threshold = st.session_state.get("threshold_value", 10)
        low_stock_df = df[df["quantity"] < threshold]

        current_low_stock_ids = set(low_stock_df["id"].tolist())
        previous_notified_ids = set(st.session_state.get("notified_products", []))

        if st.session_state.get("enable_alerts", False):
            if current_low_stock_ids != previous_notified_ids and not low_stock_df.empty:
                # Telegram Notification
                message_lines = [f"🚨 The following products are low in stock (Threshold: {threshold}):"]
                for row in low_stock_df.itertuples():
                    message_lines.append(f"- {row.product_name} ({row.category}): {row.quantity} left")
                final_message = "\n".join(message_lines)
                send_telegram_message(final_message)
                st.info("📤 Notification sent to Telegram.")
                st.session_state["notified_products"] = list(current_low_stock_ids)

        if not low_stock_df.empty:
            st.warning(f"🚨 {len(low_stock_df)} product(s) are below the stock threshold!")
            st.dataframe(low_stock_df.rename(columns={
                'product_name': '🛍️   Product Name',
                'category': '📂 Category',
                'quantity': '📦 Quantity',
                'price': '💲 Price ($)'
            }))
        else:
            st.success("✅ All products are sufficiently stocked.")

