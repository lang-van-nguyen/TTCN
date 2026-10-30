import sys
import os
import json

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
from services.sentiment_service import SentimentService
from services.ecommerce_crawler import EcommerceCrawler
from database.reviewDAO import ReviewDAO
from database.productDAO import ProductDAO
from database.userDAO import UserDAO
from database.DB_connect import get_connection 
from werkzeug.utils import secure_filename
import os
from google import genai
import os

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend', 'templates'))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend', 'static'))

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.secret_key = 'KEY_BAO_MAT_CUA_BAN'
CORS(app)

UPLOAD_FOLDER = os.path.join(static_dir, 'img')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

sentiment_service = SentimentService(
    train_path="data/train.csv",
    stopwords_path="data/stopwords.txt"
)
review_dao = ReviewDAO()
product_dao = ProductDAO()
user_dao = UserDAO()

@app.route("/", methods=["GET"])
def home_page():
    all_products = product_dao.get_all()
    featured_products = all_products[:8]
    return render_template("User/index.html", products=featured_products)

@app.route("/danh-gia-link", methods=["GET"])
def analyze_link_page():
    return render_template("User/analyze.html")

@app.route("/api/analyze-link", methods=["POST"])
def api_analyze_link():
    data = request.get_json()
    product_url = data.get("url", "").strip()
    max_reviews = int(data.get("max_reviews", 20))

    if not product_url:
        return jsonify({"success": False, "message": "Vui lòng nhập đường dẫn sản phẩm!"}), 400

    try:
        # 1. Thu thập dữ liệu qua Crawler
        crawler = EcommerceCrawler()
        raw_reviews = crawler.crawl_reviews(product_url, max_reviews=max_reviews)

        if not raw_reviews:
            return jsonify({"success": False, "message": "Không tìm thấy bình luận nào hoặc đường dẫn không hợp lệ!"})

        # 2. Đưa qua Thuật toán Naive Bayes gốc để phân tích
        positive_count = 0
        negative_count = 0
        analyzed_reviews = []

        for item in raw_reviews:
            comment = item.get("comment", "").strip()
            if not comment:
                continue

            # Phân tích bằng Naive Bayes kết hợp Rating
            rating_val = item.get("rating", 5)
            result = sentiment_service.analyze(comment, rating=rating_val)
            sentiment = result.get("sentiment", "positive")
            confidence_dict = result.get("confidence", {})
            confidence_val = confidence_dict.get(sentiment, 0)

            if sentiment in ["positive", "Tích cực"]:
                positive_count += 1
            else:
                negative_count += 1

            analyzed_reviews.append({
                "author": item.get("author", "Ẩn danh"),
                "rating": item.get("rating", 5),
                "comment": comment,
                "created_at": item.get("created_at", ""),
                "sentiment": sentiment,
                "confidence": round(confidence_val * 100, 1)
            })

        # 3. Tính điểm RealTrustScore
        total_analyzed = len(analyzed_reviews)
        trust_score = round((positive_count / total_analyzed) * 100) if total_analyzed > 0 else 0

        return jsonify({
            "success": True,
            "data": {
                "trust_score": trust_score,
                "total_reviews": total_analyzed,
                "positive_count": positive_count,
                "negative_count": negative_count,
                "reviews": analyzed_reviews
            }
        })

    except Exception as e:
        return jsonify({"success": False, "message": f"Lỗi hệ thống: {str(e)}"}), 500
@app.route("/api/ai-summary", methods=["POST"])
@app.route("/api/summarize", methods=["POST"])
def api_ai_summary():
    data = request.get_json() or {}
    reviews = data.get("reviews", [])
    product_id = data.get("product_id")

    # Lấy danh sách bình luận nếu truyền product_id
    if not reviews and product_id:
        db_reviews = review_dao.get_reviews_by_product_id(product_id)
        reviews = [r.get("comment", "") if isinstance(r, dict) else getattr(r, "comment", str(r)) for r in db_reviews]

    # Trích xuất nội dung văn bản bình luận
    comments = []
    for r in reviews:
        if isinstance(r, dict):
            c = r.get("comment") or r.get("text") or ""
        else:
            c = str(r)
        if c.strip():
            comments.append(c.strip())

    if not comments:
        return jsonify({"success": False, "message": "Không có bình luận nào để tóm tắt!"}), 400

    # Kiểm tra API Key đã được cung cấp chưa
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
        return jsonify({
            "success": False,
            "message": "Vui lòng cấu hình API Key Google Gemini trong file backend/app.py!"
        }), 400

    # TỐI ƯU 1: Lọc ra 12 bình luận dài nhất (chứa nhiều thông tin nhất)
    valid_comments = sorted([c for c in comments if len(c) > 10], key=len, reverse=True)
    sample_comments = valid_comments[:12] if valid_comments else comments[:12]
    reviews_text = "\n- ".join(sample_comments)

    prompt = f"""Phân tích các đánh giá sau và TRẢ VỀ ĐÚNG ĐỊNH DẠNG JSON:
{{
    "summary": "Tóm tắt chung 1-2 câu xem sản phẩm có đáng mua không.",
    "pros": ["Ưu điểm 1", "Ưu điểm 2"],
    "cons": ["Nhược điểm 1", "Nhược điểm 2"]
}}
Đánh giá:
- {reviews_text}"""

    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "max_output_tokens": 2000,  # TỐI ƯU 2: Giới hạn token để phản hồi siêu tốc
                "temperature": 0.1         # TỐI ƯU 3: Giảm độ sáng tạo, đi thẳng vào đáp án
            }
        )

        # Đọc dữ liệu JSON từ AI
        ai_data = json.loads(response.text)

        # Bóc tách dữ liệu
        summary_text = ai_data.get("summary", "Không có đánh giá chung.")
        pros_list = "<br>".join([f"• {p}" for p in ai_data.get("pros", [])]) or "• Không có ưu điểm nổi bật."
        cons_list = "<br>".join([f"• {c}" for c in ai_data.get("cons", [])]) or "• Không có nhược điểm đáng kể."

        # Định dạng chuỗi văn bản chuẩn chứa ** để khớp với hàm replace ở HTML/JS
        formatted_summary = (
            f"**Đánh giá chung:** {summary_text}<br><br>"
            f"**Ưu điểm nổi bật:**<br>{pros_list}<br><br>"
            f"**Nhược điểm cần lưu ý:**<br>{cons_list}"
        )

        # Trả về key "summary" cho file HTML xử lý không bị lỗi replace
        return jsonify({
            "success": True,
            "summary": formatted_summary, 
            "total_analyzed": len(sample_comments)
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Lỗi khi gọi Google AI: {str(e)}"
        }), 500
    
@app.route("/san-pham/<int:id>", methods=["GET"])
def view_product(id):
    product = product_dao.get_by_id(id)
    if not product:
        return render_template("404.html"), 404 
        
    reviews = review_dao.get_reviews_by_product_id(id)
    return render_template("User/single.html", product=product, reviews=reviews)

@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()
    text = data.get("text", "")
    product_id = data.get("product_id")
    user_id = data.get("user_id")

    if not product_id:
        return jsonify({"error": "Missing Product ID"}), 400

    result = sentiment_service.analyze(text)
    sentiment = result["sentiment"]
    confidence_dict = result["confidence"]
    confidence_value = confidence_dict.get(sentiment, 0)
    review_dao.save_review(product_id, user_id, text, sentiment, confidence_value)

    user_name = "Khách ẩn danh"
    if user_id: 
        if 'user_name' in session:
            user_name = session['user_name']
        else:
            user_name = "Thành viên" 

    return jsonify({
        "status": "success",
        "sentiment": sentiment,
        "confidence": confidence_value,
        "user_name": user_name 
    })
  
  

@app.route("/admin")
def admin_page():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login_page'))

    return render_template("Admin/dashboard.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name")
        email = request.form.get("email")
        password = request.form.get("password")
        
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (full_name, email, password, role) VALUES (%s, %s, %s, 'user')", 
                           (full_name, email, password))
            conn.commit()
            conn.close()
            return render_template("login.html", success="Đăng ký thành công! Hãy đăng nhập.")
        except Exception as e:
            conn.close()
            return render_template("register.html", error="Email này đã tồn tại!")

    return render_template("register.html")

 

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_page'))
        else:
            return redirect(url_for('home_page'))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM users WHERE email=%s AND password=%s", (email, password))
        user = cursor.fetchone()
        conn.close()

        if not user:
            return render_template("login.html", error="Sai email hoặc mật khẩu!")
        session['user_id'] = user['id']
        session['user_name'] = user['full_name']
        session['role'] = user['role']  
        if user['role'] == 'admin':
            print(f"Admin {user['full_name']} đã đăng nhập -> Vào Dashboard")
            return redirect(url_for('admin_page')) 
        else:
            print(f"User {user['full_name']} đã đăng nhập -> Vào Trang chủ")
            return redirect(url_for('home_page'))  

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('home_page'))

@app.route("/admin/reviews", methods=["GET"])
def admin_reviews():
    if 'user_id' not in session or session.get('role') != 'admin': 
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"data": review_dao.get_all_reviews()})

@app.route("/admin/reviews/<int:id>", methods=["DELETE"])
def delete_review(id):
    if 'user_id' not in session or session.get('role') != 'admin': 
        return jsonify({"error": "Unauthorized"}), 401
    review_dao.delete_review(id)
    return jsonify({"success": True})

@app.route("/admin/stats", methods=["GET"])
def admin_stats():
    if 'user_id' not in session or session.get('role') != 'admin': 
        return jsonify({"error": "Unauthorized"}), 401
    
    reviews = review_dao.get_all_reviews()
    total = len(reviews)
    positive = sum(1 for r in reviews if r["sentiment"] in ["Tích cực", "positive"])
    negative = sum(1 for r in reviews if r["sentiment"] in ["Tiêu cực", "negative"])
    
    return jsonify({
        "total": total,
        "positive": positive,
        "negative": negative,
        "positive_rate": round(positive / total * 100, 2) if total > 0 else 0
    })

@app.route("/api/products", methods=["GET"])
def get_products_api():
    return jsonify(product_dao.get_all())

@app.route("/api/products/<int:id>", methods=["GET"])
def get_product_detail_api(id):
    return jsonify(product_dao.get_by_id(id))


@app.route("/admin/product/add", methods=["POST"])
def add_product():
    if session.get('role') != 'admin': return redirect(url_for('home_page'))

    name = request.form['name']
    price = request.form['price']
    description = request.form['description']
    
    file = request.files['image']
    filename = "default.jpg" 
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    product_dao.add_product(name, price, description, filename)
    return redirect(url_for('admin_page'))

@app.route("/admin/product/update", methods=["POST"])
def update_product():
    if session.get('role') != 'admin': return redirect(url_for('home_page'))

    id = request.form['id']
    name = request.form['name']
    price = request.form['price']
    description = request.form['description']
    
    file = request.files['image']
    filename = None
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    product_dao.update_product(id, name, price, description, filename)
    return redirect(url_for('admin_page'))

@app.route("/admin/product/delete/<int:id>", methods=["GET"])
def delete_product(id):
    if session.get('role') != 'admin': return redirect(url_for('home_page'))
    product_dao.delete_product(id)
    return redirect(url_for('admin_page'))



@app.route("/api/users", methods=["GET"])
def get_users_api():
    if session.get('role') != 'admin': 
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify(user_dao.get_all_users())

@app.route("/admin/user/add", methods=["POST"])
def add_user():
    if session.get('role') != 'admin': return redirect(url_for('home_page'))
    
    full_name = request.form['full_name']
    email = request.form['email']
    password = request.form['password']
    role = request.form['role']
    
    user_dao.add_user(full_name, email, password, role)
    return redirect(url_for('admin_page'))

@app.route("/admin/user/update", methods=["POST"])
def update_user():
    if session.get('role') != 'admin': return redirect(url_for('home_page'))
    
    id = request.form['id']
    full_name = request.form['full_name']
    email = request.form['email']
    role = request.form['role']
    password = request.form.get('password') 
    
    user_dao.update_user(id, full_name, email, role, password)
    return redirect(url_for('admin_page'))

@app.route("/admin/user/delete/<int:id>", methods=["GET"])
def delete_user(id):
    if session.get('role') != 'admin': return redirect(url_for('home_page'))
    if id == session.get('user_id'): return redirect(url_for('admin_page'))
    return redirect(url_for('admin_page'))

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)