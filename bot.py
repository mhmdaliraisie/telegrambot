import json
import os
import re
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)

from config import BOT_TOKEN, TARGET_CHANNEL_ID, ADMIN_IDS, FOOTER_TAG

# --------- states ----------
CHOOSE_TYPE, ASK_NAME, ASK_OPERATOR, ASK_PAYLOAD = range(4)

TYPE_PROXY = "proxy"
TYPE_V2RAY = "v2ray"

OPERATORS = [
    ("ایرانسل", "irancell"),
    ("همراه اول", "mci"),
    ("رایتل", "rightel"),
    ("سامان‌تل", "samantel"),
    ("نت خانگی", "home"),
]

BANNED_FILE = "banned.json"
STATE_FILE = "bot_state.json"


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


banned_users = set(load_json(BANNED_FILE, []))
bot_state = load_json(STATE_FILE, {"enabled": True})


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def is_proxy(text: str) -> bool:
    t = text.strip()
    return bool(
        re.match(r"^tg://(proxy|socks)\?", t)
        or re.match(r"^https://t\.me/(proxy|socks)\?", t)
        or re.match(r"^t\.me/(proxy|socks)\?", t)
    )


def is_config(text: str) -> bool:
    t = text.strip()
    # لینک‌های v2ray رایج + لینک اشتراک
    return bool(
        re.match(r"^(vmess|vless|trojan|ss|ssr)://", t, re.IGNORECASE)
        or re.match(r"^https?://", t, re.IGNORECASE)
    )


def clean_sender_name(name: str) -> str:
    n = name.strip()
    # خیلی طولانی نشه
    if len(n) > 40:
        n = n[:40] + "…"
    return n


def pretty_operator(op_key: str) -> str:
    for label, key in OPERATORS:
        if key == op_key:
            return label
    return op_key


def escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id in banned_users:
        return

    if not bot_state["enabled"] and not is_admin(user_id):
        await update.message.reply_text("ربات فعلاً خاموشه ❌")
        return

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔐 ارسال پروکسی", callback_data=f"type:{TYPE_PROXY}"),
            InlineKeyboardButton("⚡️ ارسال کانفیگ V2Ray", callback_data=f"type:{TYPE_V2RAY}"),
        ]
    ])

    await update.message.reply_text(
        "سلام 👋\nچی می‌خوای ارسال کنی؟",
        reply_markup=kb
    )
    return CHOOSE_TYPE


async def choose_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    data = q.data or ""
    if not data.startswith("type:"):
        return CHOOSE_TYPE

    chosen = data.split(":", 1)[1]
    context.user_data["send_type"] = chosen

    await q.message.reply_text(
        "اسم/نامی که می‌خوای باهاش منتشر بشه رو بفرست.\n"
        "مثال: `Ali` یا `@mychannel` یا `کانالِ من`",
        parse_mode=ParseMode.MARKDOWN
    )
    return ASK_NAME


async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = clean_sender_name(update.message.text)
    if not name:
        await update.message.reply_text("یک اسم معتبر بفرست.")
        return ASK_NAME

    context.user_data["sender_name"] = name

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data=f"op:{key}")]
        for (label, key) in OPERATORS
    ])

    await update.message.reply_text(
        "با کدوم اپراتور وصلی؟",
        reply_markup=kb
    )
    return ASK_OPERATOR


async def ask_operator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data or ""
    if not data.startswith("op:"):
        return ASK_OPERATOR

    op_key = data.split(":", 1)[1]
    context.user_data["operator"] = op_key

    send_type = context.user_data.get("send_type")
    if send_type == TYPE_PROXY:
        hint = (
            "لینک پروکسی رو بفرست ✅\n"
            "نمونه:\n"
            "`tg://proxy?server=...&port=...&secret=...`\n"
            "یا\n"
            "`https://t.me/proxy?server=...`"
        )
    else:
        hint = (
            "کانفیگ V2Ray رو بفرست ✅\n"
            "نمونه:\n"
            "`vmess://...` یا `vless://...` یا `trojan://...`"
        )

    await q.message.reply_text(hint, parse_mode=ParseMode.MARKDOWN)
    return ASK_PAYLOAD


async def receive_payload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in banned_users:
        return ConversationHandler.END

    if not bot_state["enabled"] and not is_admin(user_id):
        return ConversationHandler.END

    text = update.message.text.strip()
    send_type = context.user_data.get("send_type")
    sender_name = context.user_data.get("sender_name", "ناشناس")
    op_key = context.user_data.get("operator", "unknown")
    op_label = pretty_operator(op_key)

    # validate
    if send_type == TYPE_PROXY:
        if not is_proxy(text):
            await update.message.reply_text("❌ این لینک، پروکسی معتبر نیست. دوباره بفرست.")
            return ASK_PAYLOAD

        # message to channel
        tag = "#پروکسی"
        sender_line = f"ارسال‌کننده: {escape_html(sender_name)}"
        op_line = f"اپراتور: {escape_html(op_label)}"

        button = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔗 اتصال به پروکسی", url=text)]]
        )

        channel_text = (
            f"{tag}\n\n"
            f"🔐 <b>Proxy Link</b>:\n"
            f"<code>{escape_html(text)}</code>\n\n"
            f"{op_line}\n"
            f"{sender_line}\n"
            f"{escape_html(FOOTER_TAG)}"
        )

        await context.bot.send_message(
            chat_id=TARGET_CHANNEL_ID,
            text=channel_text,
            parse_mode=ParseMode.HTML,
            reply_markup=button,
            disable_web_page_preview=True,
        )

        await update.message.reply_text("✅ پروکسی منتشر شد.")
        return ConversationHandler.END

    # v2ray config
    if not is_config(text):
        await update.message.reply_text("❌ این متن کانفیگ معتبر نیست. دوباره بفرست.")
        return ASK_PAYLOAD

    tag = "#v2ray"
    sender_line = f"ارسال‌کننده: {escape_html(sender_name)}"
    op_line = f"اپراتور: {escape_html(op_label)}"

    channel_text = (
        f"{tag}\n\n"
        f"⚡️ <b>V2Ray Config</b>:\n"
        f"<code>{escape_html(text)}</code>\n\n"
        f"{op_line}\n"
        f"{sender_line}\n"
        f"{escape_html(FOOTER_TAG)}"
    )

    await context.bot.send_message(
        chat_id=TARGET_CHANNEL_ID,
        text=channel_text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )

    await update.message.reply_text("✅ کانفیگ منتشر شد.")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("لغو شد.")
    return ConversationHandler.END


# --------- admin commands ----------
async def admin_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text(
        f"وضعیت ربات: {'روشن ✅' if bot_state['enabled'] else 'خاموش ❌'}\n"
        f"بن‌شده‌ها: {len(banned_users)}"
    )


async def admin_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    bot_state["enabled"] = False
    save_json(STATE_FILE, bot_state)
    await update.message.reply_text("ربات خاموش شد ❌")


async def admin_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    bot_state["enabled"] = True
    save_json(STATE_FILE, bot_state)
    await update.message.reply_text("ربات روشن شد ✅")


async def admin_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("مثال: /ban 123456789")
        return
    uid = int(context.args[0])
    banned_users.add(uid)
    save_json(BANNED_FILE, list(banned_users))
    await update.message.reply_text(f"کاربر {uid} بن شد ⛔")


async def admin_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("مثال: /unban 123456789")
        return
    uid = int(context.args[0])
    banned_users.discard(uid)
    save_json(BANNED_FILE, list(banned_users))
    await update.message.reply_text(f"کاربر {uid} آنبن شد ✅")


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_TYPE: [CallbackQueryHandler(choose_type, pattern=r"^type:")],
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_OPERATOR: [CallbackQueryHandler(ask_operator, pattern=r"^op:")],
            ASK_PAYLOAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_payload)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv)

    # admin
    app.add_handler(CommandHandler("status", admin_status))
    app.add_handler(CommandHandler("off", admin_off))
    app.add_handler(CommandHandler("on", admin_on))
    app.add_handler(CommandHandler("ban", admin_ban))
    app.add_handler(CommandHandler("unban", admin_unban))

    print("Bot started...")
    app.run_polling()


if __name__ == "__main__":
    main()
