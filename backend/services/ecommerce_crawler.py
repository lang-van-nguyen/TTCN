"""
ecommerce_crawler.py
--------------------
Module cào bình luận sản phẩm từ sàn thương mại điện tử.

Hỗ trợ:
  - Tiki.vn  (PRIMARY): REST API công khai, không cần đăng nhập, trả JSON trực tiếp.
  - Shopee   (NOTE):    API yêu cầu đăng nhập từ 2024 → không hỗ trợ headless tự động.

Cấu trúc dữ liệu đầu ra mỗi đánh giá:
  {
    "author"    : str  – Tên người dùng
    "rating"    : int  – Số sao (1-5)
    "comment"   : str  – Nội dung bình luận
    "created_at": str  – Thời gian đăng (YYYY-MM-DD HH:MM)
    "source_url": str  – URL sản phẩm nguồn
  }

Không sử dụng bất kỳ thư viện học máy bên ngoài nào.
"""

import re
import time
import logging
from typing import Optional
from urllib.parse import urlparse, parse_qs

import requests

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_DEFAULT_HEADERS = {
    "User-Agent":      _USER_AGENT,
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
    "Referer":         "https://tiki.vn/",
    "Origin":          "https://tiki.vn",
}


# ===========================================================================
# Platform detector
# ===========================================================================
def _detect_platform(url: str) -> str:
    """Nhận diện nền tảng từ URL linh hoạt ('tiki' | 'shopee' | 'unknown')."""
    url_lower = url.lower().strip()
    if "tiki.vn" in url_lower or "tiki" in url_lower:
        return "tiki"
    if "shopee.vn" in url_lower or "shopee" in url_lower:
        return "shopee"
    return "unknown"

# ===========================================================================
# Tiki helper
# ===========================================================================
def _parse_tiki_product_id(product_url: str) -> int:
    """
    Trích product_id từ URL Tiki.
    Hỗ trợ mọi định dạng:
      https://tiki.vn/samsung-galaxy-s24-p246399965.html -> 246399965
      tiki.vn/p246399965.html                            -> 246399965
      https://tiki.vn/product-p246399965.html?spid=123   -> 246399965
    """
    url_clean = product_url.strip()
    if not url_clean.startswith(("http://", "https://")):
        url_clean = "https://" + url_clean

    # Match ID dạng -p123456 hoặc /p123456
    match = re.search(r'[/-]p(\d+)(?:\.html)?', url_clean)
    if match:
        return int(match.group(1))

    # Match ID dạng p123456
    match_fallback = re.search(r'p(\d+)', url_clean)
    if match_fallback:
        return int(match_fallback.group(1))

    # Fallback query string ?id=... hoặc ?spid=...
    qs = parse_qs(urlparse(url_clean).query)
    if "id" in qs:
        return int(qs["id"][0])
    if "spid" in qs:
        return int(qs["spid"][0])

    raise ValueError(
        f"Không trích được product_id từ URL Tiki: {product_url}\n"
        "URL phải chứa mã dạng ...p{{product_id}}.html"
    )
    """
    Trích product_id từ URL Tiki.
    Ví dụ:
      https://tiki.vn/samsung-galaxy-s24-p246399965.html  → 246399965
      https://tiki.vn/p246399965.html                     → 246399965
    """
    match = re.search(r'[/-]p(\d+)(?:\.html)?', product_url)
    if match:
        return int(match.group(1))
    # Fallback: query string ?id=...
    qs = parse_qs(urlparse(product_url).query)
    if "id" in qs:
        return int(qs["id"][0])
    raise ValueError(
        f"Không trích được product_id từ URL Tiki: {product_url}\n"
        "URL phải có dạng .../...p{{product_id}}.html"
    )


# ===========================================================================
# TikiCrawler (internal helper)
# ===========================================================================
class _TikiCrawler:
    """
    Cào bình luận từ Tiki.vn qua REST API công khai.

    Endpoint:
      GET https://tiki.vn/api/v2/reviews
          ?product_id={id}&page={n}&limit={lim}&sort=newest
    """

    _API_URL = "https://tiki.vn/api/v2/reviews"
    _PAGE_SIZE = 20    # Tiki cho phép tối đa 20 review/trang

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(_DEFAULT_HEADERS)

    def _fetch_page(self, product_id: int, page: int) -> dict:
        """Gọi API một lần, trả về toàn bộ JSON response."""
        params = {
            "product_id": product_id,
            "page":        page,
            "limit":       self._PAGE_SIZE,
            "sort":        "newest",
        }
        try:
            resp = self._session.get(self._API_URL, params=params, timeout=self.timeout)
            logger.info(f"  Tiki API page={page} → HTTP {resp.status_code}")
            if resp.status_code == 200:
                return resp.json()
            logger.warning(f"  Tiki API lỗi {resp.status_code}: {resp.text[:150]}")
        except Exception as e:
            logger.error(f"  Lỗi gọi Tiki API: {e}")
        return {}

    @staticmethod
    def _normalize(raw: dict, source_url: str) -> Optional[dict]:
        """
        Chuẩn hoá một review thô từ Tiki API → định dạng chuẩn 5 trường.

        Cấu trúc JSON Tiki (lược bỏ bớt):
        {
          "id": 123,
          "rating": 5,
          "content": "Sản phẩm tốt ...",
          "created_at": "2024-03-20 14:32:00",
          "created_by": { "name": "anon_user", "full_name": "Nguyễn V. A" },
          "title": "..."
        }
        """
        comment = (raw.get("content") or raw.get("title") or "").strip()
        if not comment:
            return None

        created_by = raw.get("created_by") or {}
        author = (
            created_by.get("full_name")
            or created_by.get("name")
            or "Nguoi dung an danh"
        )
        rating = int(raw.get("rating", 0))
        created_at = str(raw.get("created_at") or "")[:16]   # "YYYY-MM-DD HH:MM"

        return {
            "author":     author,
            "rating":     rating,
            "comment":    comment,
            "created_at": created_at,
            "source_url": source_url,
        }

    def crawl(self, product_url: str, max_reviews: int) -> list:
        """Cào tối đa max_reviews bình luận từ URL sản phẩm Tiki."""
        try:
            product_id = _parse_tiki_product_id(product_url)
        except ValueError as e:
            logger.error(str(e))
            return []

        logger.info(f"[Tiki] product_id={product_id} | max={max_reviews}")

        reviews = []
        page = 1

        while len(reviews) < max_reviews:
            logger.info(f"  Đang tải trang {page} | Đã có: {len(reviews)}/{max_reviews}")
            data = self._fetch_page(product_id, page)

            if not data:
                logger.warning("  API trả rỗng, dừng.")
                break

            raw_list = data.get("data", [])
            if not raw_list:
                logger.info("  Hết trang review.")
                break

            for raw in raw_list:
                if len(reviews) >= max_reviews:
                    break
                normalized = self._normalize(raw, product_url)
                if normalized:
                    reviews.append(normalized)
                    logger.debug(
                        f"  + [{normalized['rating']}★] "
                        f"{normalized['author']}: "
                        f"{normalized['comment'][:60]}..."
                    )

            # Kiểm tra pagination
            paging = data.get("paging", {})
            total_pages = paging.get("last_page", paging.get("total_pages", 1))
            if page >= total_pages:
                logger.info(f"  Đã duyệt hết {total_pages} trang.")
                break

            page += 1
            time.sleep(0.8)   # Delay lịch sự tránh rate-limit

        logger.info(f"[Tiki] Hoàn tất: {len(reviews)} bình luận.")
        return reviews


# ===========================================================================
# EcommerceCrawler – public interface (không đổi)
# ===========================================================================
class EcommerceCrawler:
    """
    Crawler bình luận sản phẩm đa nền tảng.

    Hiện hỗ trợ:
      - Tiki.vn : API công khai, không cần đăng nhập, nhanh và ổn định.
      - Shopee  : Tạm thời không hỗ trợ tự động (API yêu cầu đăng nhập
                  từ cuối 2024). Sẽ được bổ sung khi có giải pháp cookie
                  được inject từ session người dùng thật.

    Interface hoàn toàn tương thích với phần còn lại của hệ thống:
        crawler = EcommerceCrawler()
        reviews = crawler.crawl_reviews(product_url, max_reviews=20)

    Args:
        headless: Giữ lại để tương thích API cũ (không dùng khi chỉ gọi Tiki).
        timeout:  Giây chờ tối đa cho mỗi request HTTP.
    """

    def __init__(self, headless: bool = True, timeout: int = 15):
        self.headless = headless
        self.timeout  = timeout

    def crawl_reviews(self, product_url: str, max_reviews: int = 20) -> list:
        """
        Cào bình luận sản phẩm từ URL.

        Args:
            product_url: URL sản phẩm (Tiki hoặc Shopee).
            max_reviews: Số bình luận tối đa cần lấy.

        Returns:
            List[Dict] với keys: author, rating, comment, created_at, source_url.

        Raises:
            ValueError: Nếu nền tảng không được hỗ trợ.
        """
        if not product_url or not product_url.strip():
            raise ValueError("product_url không được để trống.")

        logger.info("=" * 58)
        logger.info(f"CRAWL START | max={max_reviews}")
        logger.info(f"URL: {product_url}")
        logger.info("=" * 58)

        platform = _detect_platform(product_url)
        logger.info(f"Nền tảng phát hiện: {platform.upper()}")

        if platform == "tiki":
            crawler = _TikiCrawler(timeout=self.timeout)
            reviews = crawler.crawl(product_url, max_reviews)

        elif platform == "shopee":
            logger.warning(
                "Shopee hiện yêu cầu đăng nhập để gọi API đánh giá (lỗi 90309999).\n"
                "Tính năng cào Shopee sẽ được bổ sung khi có session người dùng thật.\n"
                "Hãy dùng URL Tiki.vn để kiểm thử."
            )
            reviews = []

        else:
            raise ValueError(
                f"Nền tảng '{platform}' chưa được hỗ trợ.\n"
                "Hỗ trợ hiện tại: tiki.vn"
            )

        logger.info(f"CRAWL DONE | {len(reviews)} bình luận.")
        return reviews


# ---------------------------------------------------------------------------
# Chạy thử trực tiếp
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    # Samsung Galaxy S24 trên Tiki – URL thật, có nhiều đánh giá
    TEST_URL = (
        "https://tiki.vn/dien-thoai-samsung-galaxy-s24-5g-8gb-256gb"
        "-p309938567.html"
    )

    crawler = EcommerceCrawler()
    results = crawler.crawl_reviews(TEST_URL, max_reviews=5)

    print(f"\n{'='*60}")
    print(f"Tong so binh luan: {len(results)}")
    print(f"{'='*60}")
    print(json.dumps(results, ensure_ascii=False, indent=2))
