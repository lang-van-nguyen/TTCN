"""
test_crawler.py - Smoke test cho module EcommerceCrawler (Tiki API Strategy)
Chay: python -X utf8 test_crawler.py
"""
import sys
import os
import json
import time
import logging

# Fix encoding UTF-8 cho terminal Windows
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Them thu muc backend vao sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from services.ecommerce_crawler import EcommerceCrawler

# ─── Cau hinh logging ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("SmokeTest")

# ─── URL san pham Tiki mau (Co nhieu danh gia) ───────────────────────────────
TEST_URL = "https://tiki.vn/cay-cam-ngot-cua-toi-p74021317.html"
MAX_REVIEWS = 5


def run_smoke_test():
    logger.info("=" * 60)
    logger.info("  SMOKE TEST - EcommerceCrawler (Tiki API Strategy)")
    logger.info("=" * 60)
    logger.info(f"URL        : {TEST_URL}")
    logger.info(f"max_reviews: {MAX_REVIEWS}")
    logger.info("=" * 60)

    crawler = EcommerceCrawler()

    start = time.time()
    reviews = crawler.crawl_reviews(TEST_URL, max_reviews=MAX_REVIEWS)
    elapsed = round(time.time() - start, 2)

    logger.info("=" * 60)
    logger.info(f"XONG | Thoi gian: {elapsed}s | Ket qua: {len(reviews)} binh luan")
    logger.info("=" * 60)

    if reviews:
        print("\n[KET QUA JSON - PRETTY PRINT]\n")
        print(json.dumps(reviews, ensure_ascii=False, indent=2))
    else:
        print("\n[CANH BAO] Khong cao duoc binh luan nao.")
        print("Hay kiem tra lai code trong file backend/services/ecommerce_crawler.py")


if __name__ == "__main__":
    run_smoke_test()