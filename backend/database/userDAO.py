from database.DB_connect import get_connection

class UserDAO:
    def get_all_users(self):
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        sql = "SELECT * FROM users ORDER BY role ASC, id DESC"
        cursor.execute(sql)
        users = cursor.fetchall()
        conn.close()
        return users


    def delete_user(self, user_id):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM reviews WHERE user_id = %s", (user_id,))
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
        except Exception as e:
            print(f"Lỗi xóa user: {e}")
        finally:
            conn.close()

 
    def add_user(self, full_name, email, password, role):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            sql = "INSERT INTO users (full_name, email, password, role) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (full_name, email, password, role))
            conn.commit()
        except Exception as e:
            print(f"Lỗi thêm user: {e}")
        finally:
            conn.close()

    
    def update_user(self, id, full_name, email, role, password=None):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            if password: 
                sql = "UPDATE users SET full_name=%s, email=%s, role=%s, password=%s WHERE id=%s"
                cursor.execute(sql, (full_name, email, role, password, id))
            else: 
                sql = "UPDATE users SET full_name=%s, email=%s, role=%s WHERE id=%s"
                cursor.execute(sql, (full_name, email, role, id))
            conn.commit()
        except Exception as e:
            print(f"Lỗi sửa user: {e}")
        finally:
            conn.close()