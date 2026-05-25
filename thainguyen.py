import sqlite3
import gradio as gr
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

# =====================================================================
# 1. KHỞI TẠO CƠ SỞ DỮ LIỆU & DỮ LIỆU GIẢ LẬP (SQLite)
# =====================================================================
def init_db():
    conn = sqlite3.connect("store_standalone.db")
    cursor = conn.cursor()
    
    # Bảng Sản phẩm (Products)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            category TEXT,
            price REAL,
            stock INTEGER,
            image_url TEXT
        )
    ''')
    
    # Bảng Đơn hàng (Orders)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            product_id INTEGER,
            quantity INTEGER,
            total_price REAL,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    ''')
    
    # Nạp dữ liệu mẫu ban đầu nếu bảng trống
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        products_data = [
            ('Laptop ASUS ROG', 'Điện tử', 15000000, 10, 'https://images.unsplash.com/photo-1603302576837-37561b2e2302?w=500&auto=format&fit=crop&q=60'),
            ('iPhone 15 Pro', 'Điện tử', 22000000, 5, 'https://images.unsplash.com/photo-1695048133142-1a20484d2569?w=500&auto=format&fit=crop&q=60'),
            ('Bàn phím cơ RGB', 'Phụ kiện', 1200000, 20, 'https://images.unsplash.com/photo-1618384887929-16ec33fab9ef?w=500&auto=format&fit=crop&q=60'),
            ('Chuột Gaming không dây', 'Phụ kiện', 800000, 15, 'https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=500&auto=format&fit=crop&q=60'),
            ('Tai nghe Sony WH-1000XM4', 'Âm thanh', 3500000, 8, 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500&auto=format&fit=crop&q=60')
        ]
        cursor.executemany("INSERT INTO products (name, category, price, stock, image_url) VALUES (?, ?, ?, ?, ?)", products_data)
        
        orders_data = [
            ('Lê Hoàng Hải', 1, 1, 15000000),
            ('Trần Ngô Thái Nguyên', 3, 2, 2400000),
            ('Quách Văn Trường', 2, 1, 22000000),
            ('Lê Đức Thiện', 4, 1, 800000),
            ('Hồ Ngọc Thành', 5, 2, 7000000)
        ]
        cursor.executemany("INSERT INTO orders (customer_name, product_id, quantity, total_price) VALUES (?, ?, ?, ?)", orders_data)
        
    conn.commit()
    conn.close()

init_db()

# =====================================================================
# 2. CÁC HÀM XỬ LÝ DỮ LIỆU (Xem, Thêm, Xóa & Mua Hàng)
# =====================================================================
def view_products():
    conn = sqlite3.connect("store_standalone.db")
    df = pd.read_sql_query("SELECT * FROM products", conn)
    conn.close()
    return df

def get_gallery_data():
    conn = sqlite3.connect("store_standalone.db")
    cursor = conn.cursor()
    cursor.execute("SELECT image_url, name || ' - ' || CAST(price AS INT) || ' VNĐ (Kho: ' || stock || ')' FROM products")
    rows = cursor.fetchall()
    conn.close()
    return [(row[0], row[1]) for row in rows if row[0]]

def get_product_list():
    conn = sqlite3.connect("store_standalone.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM products")
    names = [row[0] for row in cursor.fetchall()]
    conn.close()
    return gr.Dropdown(choices=names, update=True)

def view_orders():
    conn = sqlite3.connect("store_standalone.db")
    query = """
        SELECT orders.id, orders.customer_name, products.name AS product_name, 
               orders.quantity, orders.total_price 
        FROM orders 
        JOIN products ON orders.product_id = products.id
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def add_product(name, category, price, stock, image_url):
    if not name or not category:
        return "Vui lòng điền đầy đủ thông tin!", view_products(), get_gallery_data(), get_product_list()
    if not image_url:
        image_url = "https://images.unsplash.com/photo-1531403009284-440f080d1e12?w=500&auto=format&fit=crop&q=60"
        
    conn = sqlite3.connect("store_standalone.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO products (name, category, price, stock, image_url) VALUES (?, ?, ?, ?, ?)", 
                   (name, category, price, stock, image_url))
    conn.commit()
    conn.close()
    return f"✅ Đã thêm thành công: {name}", view_products(), get_gallery_data(), get_product_list()

def delete_product(product_id):
    if product_id is None:
        return "Vui lòng nhập ID sản phẩm cần xóa!", view_products(), get_gallery_data(), get_product_list()
    
    conn = sqlite3.connect("store_standalone.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM products WHERE id = ?", (int(product_id),))
    row = cursor.fetchone()
    
    if row is None:
        conn.close()
        return f"❌ Không tìm thấy sản phẩm có ID = {product_id}!", view_products(), get_gallery_data(), get_product_list()
    
    product_name = row[0]
    cursor.execute("DELETE FROM products WHERE id = ?", (int(product_id),))
    conn.commit()
    conn.close()
    
    return f"❌ Đã xóa sản phẩm: {product_name}", view_products(), get_gallery_data(), get_product_list()

# HÀM MUA HÀNG KIỂU SHOPEE (TRỪ TỒN KHO & TẠO ĐƠN)
def buy_product(customer_name, product_name, quantity):
    if not customer_name or not product_name or not quantity or quantity <= 0:
        return "⚠️ Vui lòng nhập đầy đủ tên khách hàng và số lượng hợp lệ!", view_products(), get_gallery_data(), view_orders()
    
    conn = sqlite3.connect("store_standalone.db")
    cursor = conn.cursor()
    
    # Lấy thông tin giá tiền và số lượng tồn kho của sản phẩm chọn mua
    cursor.execute("SELECT id, price, stock FROM products WHERE name = ?", (product_name,))
    product = cursor.fetchone()
    
    if not product:
        conn.close()
        return "❌ Sản phẩm không tồn tại!", view_products(), get_gallery_data(), view_orders()
    
    p_id, p_price, p_stock = product
    
    # Kiểm tra kho hàng
    if p_stock < quantity:
        conn.close()
        return f"🛍️ Không đủ hàng! Kho chỉ còn {p_stock} sản phẩm.", view_products(), get_gallery_data(), view_orders()
    
    # Tính tổng tiền của đơn hàng
    total_price = p_price * quantity
    
    # 1. Trừ số lượng tồn kho của sản phẩm (SQL UPDATE)
    new_stock = p_stock - quantity
    cursor.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, p_id))
    
    # 2. Thêm đơn hàng mới vào bảng orders (SQL INSERT)
    cursor.execute("INSERT INTO orders (customer_name, product_id, quantity, total_price) VALUES (?, ?, ?, ?)",
                   (customer_name, p_id, quantity, total_price))
    
    conn.commit()
    conn.close()
    
    return f"🎉 Đặt hàng thành công! Đơn hàng của [{customer_name}] mua [{quantity}x {product_name}] hết tổng cộng {int(total_price):,} VNĐ.", view_products(), get_gallery_data(), view_orders()

# =====================================================================
# 3. CHỨC NĂNG AI PHÂN LOẠI KHÁCH HÀNG
# =====================================================================
def train_and_predict_customer(quantity, total_price):
    X_train = [
        [1, 15000000], [2, 2400000], [1, 22000000], [1, 800000], [2, 7000000],
        [5, 4000000], [1, 500000], [3, 45000000], [1, 1200000], [4, 32000000]
    ]
    y_train = [1, 0, 1, 0, 0, 1, 0, 1, 0, 1] 
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    model.fit(X_train, y_train)
    prediction = model.predict([[quantity, total_price]])
    return "✨ KHÁCH HÀNG VIP (Ưu đãi giảm giá 10% cho đơn sau)" if prediction[0] == 1 else "👤 KHÁCH HÀNG TIÊU CHUẨN"

# =====================================================================
# 4. THIẾT GIAO DIỆN CHỢ MUA BÁN SHOPEE + QUẢN LÝ
# =====================================================================
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🛍️ TRANG MUA SẮM SHOPEE & HỆ THỐNG QUẢN LÝ CỬA HÀNG")
    
    with gr.Tabs():
        # TAB 1: GIAO DIỆN CHỢ MUA SẮM DÀNH CHO KHÁCH HÀNG
        with gr.TabItem("🍊 Chợ Shopee Mua Hàng"):
            gr.Markdown("### 🌟 KHÔNG GIAN MUA SẮM SẢN PHẨM TRỰC TUYẾN")
            product_gallery = gr.Gallery(value=get_gallery_data(), label="Sản phẩm đang bày bán", columns=3, rows=2, object_fit="contain", height=300)
            
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### 🛒 Đặt mua sản phẩm nhanh")
                    buy_user = gr.Textbox(label="Tên của bạn (Người mua)")
                    
                    # Lấy danh sách tên sản phẩm đưa vào Dropdown lựa chọn giống Shopee
                    conn_init = sqlite3.connect("store_standalone.db")
                    cursor_init = conn_init.cursor()
                    cursor_init.execute("SELECT name FROM products")
                    initial_choices = [r[0] for r in cursor_init.fetchall()]
                    conn_init.close()
                    
                    buy_prod_dropdown = gr.Dropdown(choices=initial_choices, label="Chọn sản phẩm muốn mua")
                    buy_qty = gr.Number(label="Số lượng đặt mua", value=1, precision=0)
                    btn_buy = gr.Button("🧡 Bấm Mua Ngay (Shopee Buy)", variant="primary")
                with gr.Column():
                    gr.Markdown("### 🔔 Trạng thái đơn hàng")
                    shopee_msg = gr.Textbox(label="Thông báo từ hệ thống Shopee", interactive=False)

        # TAB 2: QUẢN LÝ KHO HÀNG (DÀNH CHO CHỦ SHOP - THÊM XÓA)
        with gr.TabItem("📦 Quản lý Kho sản phẩm"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("#### 📝 Thêm mặt hàng mới")
                    p_name = gr.Textbox(label="Tên sản phẩm")
                    p_cat = gr.Dropdown(["Điện tử", "Phụ kiện", "Âm thanh"], label="Danh mục")
                    p_price = gr.Number(label="Giá tiền (VNĐ)", value=100000)
                    p_stock = gr.Number(label="Số lượng nhập kho", value=10)
                    p_img = gr.Textbox(label="Link ảnh sản phẩm (URL)")
                    btn_add = gr.Button("Thêm sản phẩm", variant="primary")
                    
                    gr.Markdown("---")
                    gr.Markdown("#### ❌ Xóa sản phẩm lỗi")
                    p_id_delete = gr.Number(label="Nhập ID sản phẩm cần xóa", value=None, precision=0)
                    btn_delete = gr.Button("Xóa sản phẩm", variant="stop")
                    
                    gr.Markdown("---")
                    msg_output = gr.Textbox(label="Trạng thái kho")
                
                with gr.Column(scale=2):
                    gr.Markdown("#### 📊 Bảng dữ liệu quản lý tồn kho")
                    table_products = gr.Dataframe(value=view_products(), interactive=False)
            
            # Sự kiện cập nhật đồng bộ dữ liệu
            btn_add.click(add_product, inputs=[p_name, p_cat, p_price, p_stock, p_img], outputs=[msg_output, table_products, product_gallery, buy_prod_dropdown])
            btn_delete.click(delete_product, inputs=[p_id_delete], outputs=[msg_output, table_products, product_gallery, buy_prod_dropdown])

        # TAB 3: DANH SÁCH ĐƠN HÀNG ĐÃ ĐẶT (SQL JOIN)
        with gr.TabItem("📋 Danh sách Đơn hàng (Orders)"):
            gr.Markdown("#### 📋 Nhật ký hệ thống đơn hàng đã mua thành công")
            table_orders = gr.Dataframe(value=view_orders(), interactive=False)
            
            # Liên kết nút Mua hàng để cập nhật luôn cả Bảng sản phẩm, Ảnh Gallery và Bảng đơn hàng này
            btn_buy.click(buy_product, inputs=[buy_user, buy_prod_dropdown, buy_qty], outputs=[shopee_msg, table_products, product_gallery, table_orders])

        # TAB 4: MÔ HÌNH AI PHÂN LOẠI KHÁCH HÀNG VIP
        with gr.TabItem("🤖 Mô hình AI"):
            gr.Markdown("#### Phân loại nhóm khách hàng bằng Học Máy (Machine Learning)")
            with gr.Row():
                input_qty = gr.Number(label="Số lượng sản phẩm khách mua", value=1)
                input_total = gr.Number(label="Tổng số tiền đơn hàng (VNĐ)", value=15000000)
            btn_predict = gr.Button("🧠 Chạy mô hình dự đoán", variant="secondary")
            ai_output = gr.Textbox(label="Kết quả phân loại từ mô hình AI", interactive=False)
            btn_predict.click(train_and_predict_customer, inputs=[input_qty, input_total], outputs=ai_output)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)