import os
import re
import json
import requests
from pathlib import Path
from playwright.sync_api import sync_playwright

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

LOGIN_URL = "https://makerstore.vip/"
TARGET_URL = "https://makerstore.vip/"

USERNAME = os.environ["SITE_USERNAME"]
PASSWORD = os.environ["SITE_PASSWORD"]

STATE_FILE = Path("state.json")


def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=30)


def load_old_data():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_new_data(stock, amount):
    data = {
        "stock": stock,
        "amount": amount
    }
    STATE_FILE.write_text(json.dumps(data), encoding="utf-8")


def extract_data(text):
    stock = None
    amount = None

    stock_match = re.search(
        r"Available\s*Stock.*?(\d+)\s+accounts",
        text,
        re.IGNORECASE | re.DOTALL
    )
    if stock_match:
        stock = int(stock_match.group(1))

    amount_match = re.search(
        r"Total\s*Amount.*?(\d+(?:\.\d+)?)",
        text,
        re.IGNORECASE | re.DOTALL
    )
    if amount_match:
        amount = amount_match.group(1)

    return stock, amount


def login_if_needed(page):
    page.goto(LOGIN_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    body_text = page.inner_text("body")

    if "Access Your Account" in body_text or "Sign In" in body_text:
        page.fill('input[name="username"]', USERNAME)
        page.fill('input[name="password"]', PASSWORD)
        page.click('button:has-text("Sign In")')
        page.wait_for_timeout(5000)

    page.goto(TARGET_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(5000)


def get_data():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        login_if_needed(page)

        text = page.inner_text("body")
        browser.close()

        return extract_data(text)


def build_message(new_stock, new_amount, old_stock):
    price_with_profit = round(float(new_amount) + 0.14, 2)

    if new_stock == 0:
    return """❌ OUT OF STOCK

CapCut Premium is currently out of stock.

Stay tuned for restock.
"""

    if old_stock == 0 and new_stock > 0:
        return f"""🚀 STOCK IS BACK!

📦 Available Stock: {new_stock} Accounts
💰 Price: ${price_with_profit:.2f} / Account

🌐 Order:
speedboostx.com
"""

    if new_stock < 10:
        return f"""⚠️ LOW STOCK

Only {new_stock} accounts left.

💰 Price: ${price_with_profit:.2f} / Account
🌐 Order: speedboostx.com
"""

    return f"""⚡ CapCut Premium Stock Update

📦 Available Stock: {new_stock} Accounts
💰 Price: ${price_with_profit:.2f} / Account

🔄 Auto Update: Every 5 Minutes

🌐 Order / Website:
speedboostx.com
"""


def main():
    old_data = load_old_data()
    old_stock = old_data.get("stock")
    old_amount = old_data.get("amount")

    new_stock, new_amount = get_data()

    if new_stock is None or new_amount is None:
        send_telegram("فشل قراءة Available Stock أو Total Amount من الصفحة.")
        return

    if old_stock is None and old_amount is None:
        save_new_data(new_stock, new_amount)
        send_telegram(build_message(new_stock, new_amount, 0))
        return

    if new_stock != old_stock or new_amount != old_amount:
        send_telegram(build_message(new_stock, new_amount, old_stock))
        save_new_data(new_stock, new_amount)


if __name__ == "__main__":
    main()
