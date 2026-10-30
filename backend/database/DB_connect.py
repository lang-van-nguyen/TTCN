import mysql.connector
from mysql.connector import Error

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        port=3306,          
        user="root",
        password="",       
        database="smart_reviews",
        charset="utf8mb4"
    )
if __name__ == "__main__":
    try:
        conn = get_connection()
        if conn.is_connected():
            print("[OK] Ket noi MySQL thanh cong!")
            print("Server info:", conn.get_server_info())
        else:
            print("[FAIL] Khong ket noi duoc MySQL")
    except Error as e:
        print("[ERROR] Loi ket noi MySQL:", e)
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()
            print("[INFO] Da dong ket noi")