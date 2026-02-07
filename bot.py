import json
import os
import re

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

# -------------------- Conversation States --------------------
CHOOSE_TYPE, ASK_NAME, ASK_OPERATOR, ASK_PAYLOAD = range(4)

TYPE_PROXY = "proxy"
TYPE_V2RAY = "v2ray"

OPERATORS = [
    ("📶 ایرانسل", "irancell"),
    ("📡 همراه اول", "mci"),
    ("📲 رایتل", "rightel"),
    ("🛰 سامان‌تل", "samantel"),
    ("🏠 نت خانگی", "home"),
]

BANNED_FILE = "banned.json"
STATE_FILE = "bot_state.json"


# -------------------- Persistence --------------------
def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


banned_users = set(load_json(BANNED_FILE, []))
bot_state = load_json(STATE_FILE, {"enabled": True})


# -------------------- Helpers --------------------
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def escape_html(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def clean_sender_name(name: str) -> str:
    n = (name or "").strip()
    n = re.sub(r"\s+", " ", n)
    if not n:
        return ""
    if len(n) > 40:
        n = n[:40] + "…"
    return n


def pretty_operator(op_key: str) -> str:
    for label, key in OPERATORS:
        if key == op_key:
            return label
    return op_key


def is_proxy(text: str) -> bool:
    t = (text or "").strip()
    return bool(
        re.match(r"^tg://(proxy|socks)\?", t)
        or re.match(r"^https://t\.me/(proxy|socks)\?", t)
        or re.match(r"^t\.me/(proxy|socks)\?", t)
    )


def is_config(text: str) -> bool:
    t = (text or "").strip()
    # v2ray + subscription links
    return bool(
        re.match(r"^(vmess|vless|trojan|ss|ssr)://", t, re.IGNORECASE)
        or re.match(r"^https?://", t, re.IGNORECASE)
    )


def build_main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔐 ارسال پروکسی", callback_data=f"type:{TYPE_PROXY}"),
            InlineKeyboardButton("⚡️ ارسال کانفیگ V2Ray", callback_data=f"type:{TYPE_V2RAY}"),
        ]
    ])


async def show_main_menu(chat_id: int, context: ContextTypes.DEFAULT_TYPE, text: str = "چی می‌خوای ارسال کنی؟"):
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=build_main_menu(),
    )


def channel_footer(operator_label: str, sender_name: str) -> str:
    # انتهای پیام کانال
    return (
        f"📶 <b>اپراتور:</b> {escape_html(operator_label)}\n"
        f"👤 <b>ارسال‌کننده:</b> {escape_html(sender_name)}\n"
        f"{escape_html(FOOTER_TAG)}"
    )


# -------------------- Conversation Flow --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id in banned_users:
        return ConversationHandler.END

    if not bot_state["enabled"] and not is_admin(user_id):
        await update.message.reply_text("ربات فعلاً خاموشه ❌")
        return ConversationHandler.END

    context.user_data.clear()
    await show_main_menu(update.effective_chat.id, context, "سلام 👋\nچی می‌خوای ارسال کنی؟")
    return CHOOSE_TYPE


async def choose_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    data = q.data or ""
    if not data.startswith("type:"):
        await show_main_menu(q.message.chat_id, context)
        return CHOOSE_TYPE

    chosen = data.split(":", 1)[1]
    if chosen not in (TYPE_PROXY, TYPE_V2RAY):
        await show_main_menu(q.message.chat_id, context)
        return CHOOSE_TYPE

    context.user_data["send_type"] = chosen

    await q.message.reply_text(
        "✅ عالی!\n"
        "حالا بگو با چه اسمی منتشر بشه؟\n\n"
        "مثال‌ها:\n"
        "• `Ali`\n"
        "• `@mychannel`\n"
        "• `کانالِ من`",
        parse_mode=ParseMode.MARKDOWN,
    )
    return ASK_NAME


async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = clean_sender_name(update.message.text)
    if not name:
        await update.message.reply_text("❌ یک اسم معتبر بفرست (حداقل ۱ حرف).")
        return ASK_NAME

    context.user_data["sender_name"] = name

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data=f"op:{key}")]
        for (label, key) in OPERATORS
    ])

    await update.message.reply_text("📡 با کدوم اپراتور وصلی؟", reply_markup=kb)
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
            "🔐 حالا لینک پروکسی رو بفرست:\n\n"
            "✅ نمونه‌ها:\n"
            "`tg://proxy?server=...&port=...&secret=...`\n"
            "`https://t.me/proxy?server=...`\n\n"
            "اگر چیز دیگه‌ای بفرستی قبول نمی‌کنم."
        )
    else:
        hint = (
            "⚡️ حالا کانفیگ V2Ray رو بفرست:\n\n"
            "✅ نمونه‌ها:\n"
            "`vmess://...`\n"
            "`vless://...`\n"
            "`trojan://...`\n\n"
            "اگر چیز بی‌ربط بفرستی رد می‌شه."
        )

    await q.message.reply_text(hint, parse_mode=ParseMode.MARKDOWN)
    return ASK_PAYLOAD


async def receive_payload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in banned_users:
        return ConversationHandler.END

    if not bot_state["enabled"] and not is_admin(user_id):
        return ConversationHandler.END

    payload = (update.message.text or "").strip()
    send_type = context.user_data.get("send_type")
    sender_name = context.user_data.get("sender_name", "ناشناس")
    op_key = context.user_data.get("operator", "unknown")
    op_label = pretty_operator(op_key)

    # -------------------- PROXY --------------------
    if send_type == TYPE_PROXY:
        if not is_proxy(payload):
            await update.message.reply_text("❌ این لینک، پروکسی معتبر نیست. لطفاً دوباره بفرست.")
            return ASK_PAYLOAD

        tag = "#پروکسی"
        footer = channel_footer(op_label, sender_name)

        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔗 اتصال به پروکسی", url=payload)]]
        )

        channel_text = (
            f"{tag}\n"
            f"━━━━━━━━━━━━━━\n"
            f"🔐 <b>لینک پروکسی</b>\n"
            f"<code>{escape_html(payload)}</code>\n\n"
            f"👇 <i>برای اتصال، روی دکمه پایین کلیک کنید.</i>\n"
            f"━━━━━━━━━━━━━━\n"
            f"{footer}"
        )

        await context.bot.send_message(
            chat_id=TARGET_CHANNEL_ID,
            text=channel_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )

        await update.message.reply_text("✅ پروکسی با موفقیت منتشر شد.")

        # برگشت به منوی اصلی
        context.user_data.clear()
        await show_main_menu(update.effective_chat.id, context)
        return CHOOSE_TYPE

    # -------------------- V2RAY --------------------
    if not is_config(payload):
        await update.message.reply_text("❌ این متن کانفیگ معتبر نیست. لطفاً دوباره بفرست.")
        return ASK_PAYLOAD

    tag = "#v2ray"
    footer = channel_footer(op_label, sender_name)

    channel_text = (
        f"{tag}\n"
        f"━━━━━━━━━━━━━━\n"
        f"⚡️ <b>کانفیگ V2Ray</b>\n"
        f"<code>{escape_html(payload)}</code>\n"
        f"━━━━━━━━━━━━━━\n"
        f"{footer}"
    )

    await context.bot.send_message(
        chat_id=TARGET_CHANNEL_ID,
        text=channel_text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )

    await update.message.reply_text("✅ کانفیگ با موفقیت منتشر شد.")

    # برگشت به منوی اصلی
    context.user_data.clear()
    await show_main_menu(update.effective_chat.id, context)
    return CHOOSE_TYPE


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("لغو شد.")
    await show_main_menu(update.effective_chat.id, context)
    return CHOOSE_TYPE


# -------------------- Admin Commands --------------------
async def admin_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text(
        f"📊 وضعیت ربات: {'روشن ✅' if bot_state['enabled'] else 'خاموش ❌'}\n"
        f"⛔ بن‌شده‌ها: {len(banned_users)}"
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


# -------------------- Main --------------------
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

    # admin handlers
    app.add_handler(CommandHandler("status", admin_status))
    app.add_handler(CommandHandler("off", admin_off))
    app.add_handler(CommandHandler("on", admin_on))
    app.add_handler(CommandHandler("ban", admin_ban))
    app.add_handler(CommandHandler("unban", admin_unban))

    print("Bot started...")
    app.run_polling()


if __name__ == "__main__":
    main()
