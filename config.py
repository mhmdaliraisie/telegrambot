import os
from dotenv import load_dotenv

load_dotenv()

def must_get(name: str):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value

BOT_TOKEN = must_get("BOT_TOKEN")

TARGET_CHANNEL_ID = int(must_get("TARGET_CHANNEL_ID"))
SPONSOR_CHANNEL_ID = int(must_get("SPONSOR_CHANNEL_ID"))
SPONSOR_CHANNEL_USERNAME = must_get("SPONSOR_CHANNEL_USERNAME")

# ادمین‌ها (آیدی عددی، جدا شده با کاما)
ADMIN_IDS = [
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
]

# تگ آخر پیام کانال
FOOTER_TAG = os.getenv("FOOTER_TAG", "@config2v")

# تایم‌اوت‌ها
CONNECT_TIMEOUT = int(os.getenv("CONNECT_TIMEOUT", "20"))
READ_TIMEOUT = int(os.getenv("READ_TIMEOUT", "20"))
WRITE_TIMEOUT = int(os.getenv("WRITE_TIMEOUT", "20"))

PROXY_URL = os.getenv("PROXY_URL")
