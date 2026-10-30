import csv
import os
from models.naive_bayes import NaiveBayes
from models.preprocessor import TextPreprocessor


class SentimentService:

    def __init__(self, train_path="data/train.csv", stopwords_path="data/stopwords.txt"):
        # Lấy đường dẫn tuyệt đối đến thư mục gốc backend/
        services_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.abspath(os.path.join(services_dir, ".."))

        # Nếu tham số truyền vào là đường dẫn tương đối, tự động ghép vào backend/
        if not os.path.isabs(stopwords_path):
            stopwords_path = os.path.join(backend_dir, stopwords_path)

        if not os.path.isabs(train_path):
            train_path = os.path.join(backend_dir, train_path)

        self.preprocessor = TextPreprocessor(stopwords_path)
        self.model = NaiveBayes()
        self.train_path = train_path
        self._train_model()

    def _load_data(self):
        data = []
        with open(self.train_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                review = row.get("review", "")
                label = (row.get("label") or "").strip().lower()
                if not review or label not in ["positive", "negative"]:
                    continue
                tokens = self.preprocessor.preprocess(review)
                data.append((tokens, label))
        return data

    def _train_model(self):
        self.model.train(self._load_data())
        print("[OK] Naive Bayes model trained successfully!")

    def analyze(self, review, rating=None):
        tokens = self.preprocessor.preprocess(review)
        label, probs = self.model.predict_with_prob(tokens)

        # Cơ chế lai (Hybrid): Kết hợp số sao rating từ sàn TMĐT cho các câu phức tạp / ranh giới
        if rating is not None:
            try:
                r = float(rating)
                # Khách hàng cho 4-5 sao nhưng Naive Bayes có độ tự tin thấp hoặc câu trung lập
                if r >= 4 and label == "negative":
                    hard_negatives = {"lỗi", "hỏng", "hư", "tệ", "kém", "lừa đảo", "đổi trả", "thất vọng", "rởm"}
                    # Nếu bình luận không chứa từ lỗi thực sự, ưu tiên nhận diện tích cực
                    if not any(w in tokens for w in hard_negatives):
                        label = "positive"
                        pos_score = max(0.85, probs.get("positive", 0.5))
                        probs = {"positive": pos_score, "negative": round(1 - pos_score, 4)}
                elif r <= 2 and label == "positive":
                    hard_positives = {"tuyệt vời", "xuất sắc", "rất tốt", "ưng ý", "quá hài lòng"}
                    if not any(w in tokens for w in hard_positives):
                        label = "negative"
                        neg_score = max(0.85, probs.get("negative", 0.5))
                        probs = {"negative": neg_score, "positive": round(1 - neg_score, 4)}
            except (ValueError, TypeError):
                pass

        return {
            "sentiment": label,
            "confidence": probs
        }

    def predict(self, review, rating=None):
        return self.analyze(review, rating=rating)