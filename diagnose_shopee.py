"""
diagnose_shopee.py - Script chan doan cau truc HTML thuc te cua Shopee
Muc dich: Tim dung CSS selector cho khu vuc danh gia
Chay: python diagnose_shopee.py
"""
import sys
import os
import time
import re

# Fix encoding UTF-8 cho terminal Windows (cp1258 khong ho tro tieng Viet)
if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ─── Shopee product URL (dùng URL chuẩn format) ───────────────────────────────
# URL thực tế của Samsung Galaxy S24 trên Shopee
TEST_URL = "https://shopee.vn/Samsung-Galaxy-S24-8GB-256GB-H%C3%A0ng-Ch%C3%ADnh-H%C3%A3ng-i.26276759.21835179776"

def build_driver():
    opts = Options()
    # headless=False để quan sát
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1366,768")
    opts.add_argument("--disable-notifications")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"},
    )
    return driver

def scroll_down(driver, pause=0.6):
    total = driver.execute_script("return document.body.scrollHeight")
    pos = 0
    while pos < total:
        pos = min(pos + 500, total)
        driver.execute_script(f"window.scrollTo(0, {pos});")
        time.sleep(pause)
        total = driver.execute_script("return document.body.scrollHeight")

def diagnose():
    print("=" * 70)
    print("  SHOPEE HTML DIAGNOSTICS")
    print("=" * 70)
    print(f"URL: {TEST_URL}\n")

    driver = build_driver()
    try:
        driver.get(TEST_URL)
        # Chờ 5 giây để trang JS render
        time.sleep(5)

        # ── 1. Tiêu đề trang ──────────────────────────────────────────────
        print(f"[Tieu de trang] {driver.title}\n")

        # ── 2. Cuộn trang ────────────────────────────────────────────────
        print("[*] Dang cuon trang...")
        scroll_down(driver)
        time.sleep(3)
        print("[*] Cuon xong. Cho them 3s...\n")

        # ── 3. Thử hàng loạt selector phổ biến ──────────────────────────
        candidate_selectors = [
            # Shopee các phiên bản cũ
            "div.product-ratings",
            "div.product-ratings-overview",
            # Shopee phiên bản mới (2024+)
            "div[class*='ratings']",
            "div[class*='review']",
            "div[class*='Rating']",
            "div[class*='Review']",
            # Section chứa review items
            "div.shopee-product-rating",
            "div[class*='shopee-product-rating']",
            # Data attribute
            "[data-sqe='review']",
            "[data-sqe='rating']",
            # Generic
            "section[class*='rating']",
            "section[class*='review']",
        ]

        print("[*] Kiem tra cac selector:")
        print("-" * 50)
        found_any = False
        for sel in candidate_selectors:
            try:
                elems = driver.find_elements(By.CSS_SELECTOR, sel)
                if elems:
                    print(f"  [FOUND x{len(elems)}] Selector: {sel}")
                    found_any = True
                else:
                    print(f"  [  ---  ] Selector: {sel}")
            except Exception as e:
                print(f"  [  ERR  ] Selector: {sel} -> {e}")

        # ── 4. Tìm tất cả class chứa từ "rating" hoặc "review" ──────────
        print("\n" + "-" * 50)
        print("[*] Tìm các class/id chứa 'rating' hoặc 'review' trong DOM:")
        source = driver.page_source
        # Tìm class names chứa keyword
        rating_classes = set(re.findall(r'class="([^"]*(?:rating|review|Rating|Review)[^"]*)"', source))
        if rating_classes:
            for cls in sorted(rating_classes)[:20]:  # giới hạn 20 kết quả đầu
                print(f"  class=\"{cls}\"")
        else:
            print("  Khong tim thay class nao chua 'rating' hoac 'review'")

        # ── 5. Lấy URL hiện tại (kiểm tra redirect) ─────────────────────
        print(f"\n[URL hien tai sau khi load] {driver.current_url}")

        # ── 6. Lưu ảnh chụp màn hình ─────────────────────────────────────
        screenshot_path = os.path.join(os.path.dirname(__file__), "diagnose_screenshot.png")
        driver.save_screenshot(screenshot_path)
        print(f"\n[Screenshot] Da luu: {screenshot_path}")

        # ── 7. Lưu một đoạn HTML (body 5000 ký tự đầu) ───────────────────
        body_html = driver.find_element(By.TAG_NAME, "body").get_attribute("innerHTML")
        html_path = os.path.join(os.path.dirname(__file__), "diagnose_page.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(body_html)
        print(f"[HTML dump] Da luu: {html_path} ({len(body_html)} ky tu)")

        if not found_any:
            print("\n[!] Khong tim thay selector nao. Shopee co the:")
            print("    1. Hien thi captcha / dang nhap")
            print("    2. Dung ten class hash dong (e.g. _abc123)")
            print("    3. Redirect sang trang khac")
            print("    -> Kiem tra Screenshot va HTML dump de xac nhan.")

    finally:
        time.sleep(3)  # Để người dùng quan sát
        driver.quit()
        print("\n[*] Trinh duyet da dong. Ket thuc diagnostics.")

if __name__ == "__main__":
    diagnose()
