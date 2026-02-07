import json
import os
import re
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from config import (
    BOT_TOKEN,
    TARGET_CHANNEL_ID,
    SPONSOR_CHANNEL_ID,
    SPONSOR_CHANNEL_USERNAME,
    ADMIN_IDS,
    FOOTER_TAG,
)

BANNED_FILE = "banned.json"
BOT_STATE_FILE = "bot_state.json"


# ---------- utils ----------
def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


banned_users = set(load_json(BANNED_FILE, []))
bot_state = load_json(BOT_STATE_FILE, {"enabled": True})


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def is_config(text: str) -> bool:
    return bool(
        re.match(
            r"^(vmess|vless|trojan|ss|ssr)://", text.strip(), re.IGNORECASE
        )
        or re.match(r"^https?://", text.strip())
    )


def is_proxy(text: str) -> bool:
    return bool(
        re.match(r"^tg://(proxy|socks)\?", text.strip())
        or re.match(r"^https://t\.me/(proxy|socks)\?", text.strip())
        or re.match(r"^t\.me/(proxy|socks)\?", text.strip())
    )


# ---------- handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام 👋\nکانفیگ یا لینک پروکسی معتبر بفرست."
    )


async def admin_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text(
        f"وضعیت ربات: {'روشن ✅' if bot_state['enabled'] else 'خاموش ❌'}\n"
        f"تعداد بن‌شده‌ها: {len(banned_users)}"
    )


async def admin_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    bot_state["enabled"] = False
    save_json(BOT_STATE_FILE, bot_state)
    await update.message.reply_text("ربات خاموش شد ❌")


async def admin_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    bot_state["enabled"] = True
    save_json(BOT_STATE_FILE, bot_state)
    await update.message.reply_text("ربات روشن شد ✅")


async def admin_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("آیدی عددی کاربر رو بده.")
        return
    uid = int(context.args[0])
    banned_users.add(uid)
    save_json(BANNED_FILE, list(banned_users))
    await update.message.reply_text(f"کاربر {uid} بن شد ⛔")


async def admin_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("آیدی عددی کاربر رو بده.")
        return
    uid = int(context.args[0])
    banned_users.discard(uid)
    save_json(BANNED_FILE, list(banned_users))
    await update.message.reply_text(f"کاربر {uid} آنبن شد ✅")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id in banned_users:
        return

    if not bot_state["enabled"] and not is_admin(user_id):
        return

    if is_proxy(text):
        button = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔗 اتصال به پروکسی", url=text)]]
        )
        await context.bot.send_message(
            chat_id=TARGET_CHANNEL_ID,
            text=f"🔐 پروکسی:\n\n{ text }\n\n{FOOTER_TAG}",
            reply_markup=button,
        )
        await update.message.reply_text("پروکسی ارسال شد ✅")
        return

    if is_config(text):
        await context.bot.send_message(
            chat_id=TARGET_CHANNEL_ID,
            text=f"<code>{text}</code>\n\n{FOOTER_TAG}",
            parse_mode="HTML",
        )
        await update.message.reply_text("کانفیگ ارسال شد ✅")
        return

    await update.message.reply_text("❌ متن ارسال‌شده کانفیگ یا پروکسی معتبر نیست.")


# ---------- main ----------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(CommandHandler("status", admin_status))
    app.add_handler(CommandHandler("off", admin_off))
    app.add_handler(CommandHandler("on", admin_on))
    app.add_handler(CommandHandler("ban", admin_ban))
    app.add_handler(CommandHandler("unban", admin_unban))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot started...")
    app.run_polling()


if __name__ == "__main__":
    main()
