from database.DB_connect import get_connection

class ProductDAO:
    def get_all(self):
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products")
        products = cursor.fetchall()
        conn.close()
        return products

    def get_by_id(self, id):
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products WHERE id = %s", (id,))
        product = cursor.fetchone()
        conn.close()
        return product

    # --- MỚI: THÊM SẢN PHẨM ---
    def add_product(self, name, price, description, image):
        conn = get_connection()
        cursor = conn.cursor()
        sql = "INSERT INTO products (name, price, description, image) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (name, price, description, image))
        conn.commit()
        conn.close()

    # --- MỚI: SỬA SẢN PHẨM ---
    def update_product(self, id, name, price, description, image=None):
        conn = get_connection()
        cursor = conn.cursor()
        
        if image: # Nếu có chọn ảnh mới
            sql = "UPDATE products SET name=%s, price=%s, description=%s, image=%s WHERE id=%s"
            cursor.execute(sql, (name, price, description, image, id))
        else: # Nếu không đổi ảnh (giữ ảnh cũ)
            sql = "UPDATE products SET name=%s, price=%s, description=%s WHERE id=%s"
            cursor.execute(sql, (name, price, description, id))
            
        conn.commit()
        conn.close()

    # --- MỚI: XÓA SẢN PHẨM ---
    def delete_product(self, id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products WHERE id = %s", (id,))
        conn.commit()
        conn.close()