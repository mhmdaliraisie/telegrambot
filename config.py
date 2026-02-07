"""
بارگذاری تنظیمات از متغیرهای محیطی یا فایل .env
"""
import os
from pathlib import Path

# بارگذاری از .env اگر وجود داشته باشد
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    with open(_env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
SPONSOR_CHANNEL_ID = os.environ.get("SPONSOR_CHANNEL_ID", "")
TARGET_CHANNEL_ID = os.environ.get("TARGET_CHANNEL_ID", "")
SPONSOR_CHANNEL_USERNAME = os.environ.get("SPONSOR_CHANNEL_USERNAME", "")

# ادمین‌ها: لیست آیدی عددی‌ها با کاما (مثال: "123,456")
ADMIN_IDS = os.environ.get("ADMIN_IDS", "")

# تگ انتهای پیام‌های کانال
FOOTER_TAG = os.environ.get("FOOTER_TAG", "@config2v")

# اختیاری: اگر تلگرام فیلتر است، آدرس پروکسی (مثلاً socks5://127.0.0.1:1080)
PROXY_URL = os.environ.get("PROXY_URL", "").strip() or None

# تایم‌اوت اتصال به API تلگرام (ثانیه) — در صورت فیلتر یا شبکه کند عدد بزرگ‌تر بگذارید
CONNECT_TIMEOUT = float(os.environ.get("CONNECT_TIMEOUT", "30"))
READ_TIMEOUT = float(os.environ.get("READ_TIMEOUT", "30"))
WRITE_TIMEOUT = float(os.environ.get("WRITE_TIMEOUT", "30"))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN در .env تنظیم نشده است.")
if not SPONSOR_CHANNEL_ID or not TARGET_CHANNEL_ID:
    raise ValueError("SPONSOR_CHANNEL_ID و TARGET_CHANNEL_ID را در .env تنظیم کنید.")
if not SPONSOR_CHANNEL_USERNAME:
    raise ValueError("SPONSOR_CHANNEL_USERNAME را در .env تنظیم کنید (مثال: @channel).")
