import re


class TextPreprocessor:
    """
    Xử lý văn bản tiếng Việt cho bài toán phân loại cảm xúc thương mại điện tử
    Tích hợp:
    1. Chuẩn hóa Teencode / Từ viết tắt thường gặp trên sàn TMĐT
    2. Xử lý Phủ định (Negation Handling): ghép và đảo nghĩa từ phủ định
    3. Loại bỏ stopwords hợp lý (bảo tồn từ phủ định)
    """

    # Bảng chuẩn hóa teencode & từ ngữ đánh giá TMĐT
    TEENCODE_DICT = {
        "ko": "không",
        "k": "không",
        "kh": "không",
        "khg": "không",
        "khong": "không",
        "kg": "không",
        "hok": "không",
        "hong": "không",
        "kô": "không",
        "chua": "chưa",
        "sài": "dùng",
        "xài": "dùng",
        "dc": "được",
        "đc": "được",
        "sp": "sản phẩm",
        "đth": "điện thoại",
        "dt": "điện thoại",
        "dth": "điện thoại",
        "tks": "cảm ơn",
        "thanks": "cảm ơn",
        "tk": "cảm ơn",
        "cam on": "cảm ơn",
        "shop": "cửa hàng",
        "ok": "tốt",
        "oki": "tốt",
        "oke": "tốt",
        "okey": "tốt",
        "tot": "tốt",
        "dep": "đẹp",
        "on": "ổn",
        "nhah": "nhanh",
        "chuan": "chuẩn",
        "thich": "thích",
        "ngon": "ngon",
        "re": "rẻ",
        "ồn ào": "ồn",
        "tiếng động": "tiếng_động",
        "giật lag": "lag",
        "lag lag": "lag",
        "chắc chắn": "chắc_chắn",
        "nhỏ gọn": "nhỏ_gọn",
        "đáng tiền": "đáng_tiền",
        "an tâm": "an_tâm",
        "hài lòng": "hài_lòng",
    }

    NEGATION_WORDS = {"không", "chưa", "chẳng", "chả"}

    # Phủ định của từ ngữ tiêu cực -> Mang sắc thái TÍCH CỰC
    POS_NEG_MAP = {
        "không_ồn": "tốt",
        "không_ồn_ào": "tốt",
        "không_tiếng_động": "êm",
        "không_lag": "mượt",
        "không_giật": "mượt",
        "không_lỗi": "tốt",
        "không_hư": "tốt",
        "không_hỏng": "tốt",
        "không_trầy": "tốt",
        "không_xước": "tốt",
        "không_móp": "tốt",
        "không_chê": "thích",
        "không_thất_vọng": "hài_lòng",
        "không_chậm": "nhanh",
        "không_đắt": "rẻ",
    }

    # Phủ định của từ ngữ tích cực -> Mang sắc thái TIÊU CỰC
    NEG_NEG_MAP = {
        "không_tốt": "tệ",
        "không_ổn": "tệ",
        "không_đẹp": "xấu",
        "không_mượt": "lag",
        "không_êm": "ồn",
        "không_hài_lòng": "thất_vọng",
        "không_đáng_tiền": "đắt",
        "không_giống": "sai",
        "không_thích": "ghét",
        "không_dùng_được": "hỏng",
        "không_nhận": "lỗi",
        "không_lên": "hỏng",
        "chưa_tốt": "kém",
        "chưa_ổn": "kém",
        "chưa_hài_lòng": "thất_vọng",
    }

    def __init__(self, stopwords_path=None):
        self.stopwords = set()
        if stopwords_path:
            self.load_stopwords(stopwords_path)
        # Đảm bảo các từ phủ định không bao giờ bị loại bỏ làm stopword
        for neg in self.NEGATION_WORDS:
            self.stopwords.discard(neg)

    def load_stopwords(self, path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                word = line.strip().lower()
                if word and word not in self.NEGATION_WORDS:
                    self.stopwords.add(word)

    def normalize_teencode(self, text):
        # 1. Chuẩn hóa cụm từ dài trước
        for k, v in self.TEENCODE_DICT.items():
            if " " in k:
                text = re.sub(r"\b" + re.escape(k) + r"\b", v, text)
        # 2. Chuẩn hóa từ đơn
        for k, v in self.TEENCODE_DICT.items():
            if " " not in k:
                text = re.sub(r"\b" + re.escape(k) + r"\b", v, text)
        return text

    def clean_text(self, text):
        text = text.lower()
        text = self.normalize_teencode(text)
        # Giữ lại các chữ cái tiếng Việt và dấu gạch dưới (để bảo toàn cụm từ ghép)
        text = re.sub(r"[^a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễ"
                      r"ìíịỉĩ"
                      r"òóọỏõôồốộổỗơờớợởỡ"
                      r"ùúụủũưừứựửữ"
                      r"ỳýỵỷỹđ_\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def handle_negations(self, tokens):
        """
        Ghép từ phủ định với từ tiếp theo để tránh bóc tách sai cảm xúc
        Ví dụ: 'không' + 'ồn' -> 'không_ồn' -> 'tốt' (Tích cực)
        """
        new_tokens = []
        i = 0
        n = len(tokens)
        while i < n:
            token = tokens[i]
            if token in self.NEGATION_WORDS and i + 1 < n:
                next_token = tokens[i + 1]
                combo = f"{token}_{next_token}"
                if combo in self.POS_NEG_MAP:
                    new_tokens.append(self.POS_NEG_MAP[combo])
                    i += 2
                    continue
                elif combo in self.NEG_NEG_MAP:
                    new_tokens.append(self.NEG_NEG_MAP[combo])
                    i += 2
                    continue
                else:
                    new_tokens.append(combo)
                    i += 2
                    continue
            new_tokens.append(token)
            i += 1
        return new_tokens

    def tokenize(self, text):
        tokens = text.split()
        return self.handle_negations(tokens)

    def remove_stopwords(self, tokens):
        if not self.stopwords:
            return tokens
        return [word for word in tokens if word not in self.stopwords]

    def preprocess(self, text):
        text = self.clean_text(text)
        tokens = self.tokenize(text)
        tokens = self.remove_stopwords(tokens)
        return tokens
