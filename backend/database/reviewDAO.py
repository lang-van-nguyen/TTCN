from database.DB_connect import get_connection

class ReviewDAO:

    # =========================
    # 1. SAVE REVIEW (Lưu đánh giá)
    # =========================
    def save_review(self, product_id, user_id, review_text, sentiment, confidence):
        conn = get_connection()
        cursor = conn.cursor()

        sql = """
            INSERT INTO reviews (product_id, user_id, review_text, sentiment, confidence, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """

        try:
            cursor.execute(sql, (
                product_id,
                user_id,        # Có thể là None nếu khách chưa đăng nhập
                review_text,
                sentiment,
                float(confidence)
            ))
            conn.commit()
            print(f"✔ Review saved for Product ID: {product_id}")
        except Exception as e:
            print(f"❌ Error saving review: {e}")
        finally:
            cursor.close()
            conn.close()

    # =========================
    # 2. DELETE REVIEW (Xóa đánh giá)
    # =========================
    def delete_review(self, review_id):
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM reviews WHERE id = %s", (review_id,))
            conn.commit()
            print(f"🗑 Review {review_id} deleted")
        except Exception as e:
            print(f"❌ Error deleting review: {e}")
        finally:
            cursor.close()
            conn.close()

    # =========================
    # 3. GET ALL REVIEWS (Dùng cho Admin Dashboard)
    # =========================
    def get_all_reviews(self):
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # CẬP NHẬT: Join cả bảng products (lấy tên SP) VÀ bảng users (lấy tên người dùng)
        sql = """
            SELECT r.id, r.review_text, r.sentiment, r.confidence, r.created_at, 
                   p.name as product_name,
                   u.full_name as user_name
            FROM reviews r
            LEFT JOIN products p ON r.product_id = p.id
            LEFT JOIN users u ON r.user_id = u.id
            ORDER BY r.created_at DESC
        """
        
        cursor.execute(sql)
        reviews = cursor.fetchall()

        # Xử lý tên hiển thị cho Admin dễ nhìn
        for review in reviews:
            if not review['user_name']:
                review['user_name'] = "Khách ẩn danh"
            if review['created_at']:
                review['created_at'] = review['created_at'].strftime('%d/%m/%Y %H:%M')

        cursor.close()
        conn.close()
        return reviews

    # =========================
    # 4. GET REVIEWS BY PRODUCT (Dùng cho trang single.html)
    # =========================
    def get_reviews_by_product_id(self, product_id):
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # CẬP NHẬT: Dùng LEFT JOIN để lấy tên người dùng (Hiệu năng tốt hơn subquery)
        sql = """
            SELECT r.*, u.full_name as user_name 
            FROM reviews r
            LEFT JOIN users u ON r.user_id = u.id
            WHERE r.product_id = %s
            ORDER BY r.created_at DESC
        """

        cursor.execute(sql, (product_id,))
        reviews = cursor.fetchall()
        
        # Xử lý format dữ liệu trước khi trả về web
        for review in reviews:
            # Nếu không có tên (khách vãng lai) -> Gán là "Khách ẩn danh"
            if not review['user_name']:
                review['user_name'] = "Khách ẩn danh"
            
            # Format ngày tháng đẹp (VD: 25/10/2025 14:30)
            if review['created_at']:
                review['created_at'] = review['created_at'].strftime('%d/%m/%Y %H:%M')

        cursor.close()
        conn.close()
        return reviews