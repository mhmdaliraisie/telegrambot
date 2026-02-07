# -*- coding: utf-8 -*-
"""
ربات تلگرام: دریافت کانفیگ V2Ray و پروکسی و ارسال به کانال
"""
import logging
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ChatMemberStatus
from telegram.request import HTTPXRequest
import config

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# کلیدهای حالت کاربر
STATE_CONFIG_LINK = "config_link"
STATE_CONFIG_NAME = "config_name"
STATE_CONFIG_OPERATOR = "config_operator"
STATE_PROXY_LINK = "proxy_link"
STATE_PROXY_NAME = "proxy_name"
STATE_PROXY_OPERATOR = "proxy_operator"

OPERATORS = [
    ("ایرانسل", "ایرانسل"),
    ("همراه اول", "همراه اول"),
    ("رایتل", "رایتل"),
    ("سامان تل", "سامان تل"),
    ("نت خانگی", "نت خانگی"),
]


def get_sponsor_channel_id():
    cid = config.SPONSOR_CHANNEL_ID.strip()
    if cid.lstrip("-").isdigit():
        return int(cid)
    return cid


def get_target_channel_id():
    cid = config.TARGET_CHANNEL_ID.strip()
    if cid.lstrip("-").isdigit():
        return int(cid)
    return cid


async def is_member_of_sponsor(application: Application, user_id: int) -> bool:
    """بررسی عضویت کاربر در کانال اسپانسر"""
    try:
        member = await application.bot.get_chat_member(
            get_sponsor_channel_id(), user_id
        )
        return member.status in (
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        )
    except Exception as e:
        logger.warning("check sponsor membership: %s", e)
        return False


def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📤 ارسال کانفیگ", callback_data="send_config"),
            InlineKeyboardButton("📤 ارسال پروکسی", callback_data="send_proxy"),
        ],
    ])


def operator_keyboard(prefix: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(op[0], callback_data=f"{prefix}_{op[1]}")]
        for op in OPERATORS
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return
    context.user_data.clear()

    is_member = await is_member_of_sponsor(context.application, user.id)
    sponsor_username = config.SPONSOR_CHANNEL_USERNAME.strip()
    if not sponsor_username.startswith("@"):
        sponsor_username = "@" + sponsor_username

    if not is_member:
        await update.message.reply_text(
            "👋 برای استفاده از ربات، ابتدا در کانال اسپانسر ما عضو شوید:\n\n"
            f"➡️ {sponsor_username}\n\n"
            "بعد از عضویت روی /start بزنید.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("عضویت در کانال", url=f"https://t.me/{sponsor_username.lstrip('@')}")],
                [InlineKeyboardButton("✅ عضو شدم", callback_data="check_join")],
            ]),
        )
        return

    await update.message.reply_text(
        "✅ به ربات خوش آمدید.\n\nیکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=main_menu_keyboard(),
    )


async def check_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if query.data != "check_join":
        return
    user = update.effective_user
    if not user:
        return

    is_member = await is_member_of_sponsor(context.application, user.id)
    if not is_member:
        await query.edit_message_text(
            "❌ هنوز در کانال عضو نشدید. پس از عضویت روی دکمه زیر بزنید.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("عضویت در کانال", url=f"https://t.me/{config.SPONSOR_CHANNEL_USERNAME.strip().lstrip('@')}")],
                [InlineKeyboardButton("✅ عضو شدم", callback_data="check_join")],
            ]),
        )
        return

    await query.edit_message_text(
        "✅ به ربات خوش آمدید.\n\nیکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=main_menu_keyboard(),
    )


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    if not user:
        return

    is_member = await is_member_of_sponsor(context.application, user.id)
    if not is_member:
        await query.edit_message_text(
            "❌ برای ادامه باید در کانال اسپانسر عضو باشید. /start"
        )
        return

    if query.data == "send_config":
        context.user_data["state"] = STATE_CONFIG_LINK
        await query.edit_message_text(
            "📤 یک لینک یا متن کانفیگ V2Ray خود را ارسال کنید (یک پیام)."
        )
    elif query.data == "send_proxy":
        context.user_data["state"] = STATE_PROXY_LINK
        await query.edit_message_text(
            "📤 پروکسی تلگرام خود را ارسال کنید (یک پیام)."
        )


async def handle_config_operator(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    if not data.startswith("config_"):
        return
    operator = data.replace("config_", "", 1)
    context.user_data["config_operator"] = operator
    context.user_data.pop("state", None)

    link = context.user_data.get("config_link", "")
    name = context.user_data.get("config_name", "")
    channel_id = get_target_channel_id()
    sender_username = update.effective_user.username if update.effective_user else ""
    sender_id = update.effective_user.id if update.effective_user else 0

    header = f'کانفیگ #v2ray ارسالی از "{html.escape(name)}"'
    body = html.escape(link)
    footer = f"اپراتور: {operator} | ارسال‌کننده: @{sender_username or 'ناشناس'} (ID: {sender_id})"
    full_text = f"{header}\n\n<code>{body}</code>\n\n{footer}"

    try:
        await context.bot.send_message(
            chat_id=channel_id,
            text=full_text,
            parse_mode="HTML",
        )
    except Exception as e:
        logger.exception("send config to channel: %s", e)
        await query.edit_message_text(
            "❌ ارسال به کانال با خطا مواجه شد. لطفاً بعداً تلاش کنید."
        )
        await query.message.reply_text("منوی اصلی:", reply_markup=main_menu_keyboard())
        context.user_data.clear()
        return

    await query.edit_message_text("✅ کانفیگ شما با موفقیت در کانال ثبت شد.")
    await query.message.reply_text("منوی اصلی:", reply_markup=main_menu_keyboard())
    context.user_data.clear()


async def handle_proxy_operator(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    if not data.startswith("proxy_"):
        return
    operator = data.replace("proxy_", "", 1)
    context.user_data["proxy_operator"] = operator
    context.user_data.pop("state", None)

    link = context.user_data.get("proxy_link", "")
    name = context.user_data.get("proxy_name", "")
    sender_username = update.effective_user.username if update.effective_user else ""
    sender_id = update.effective_user.id if update.effective_user else 0

    header = f'پروکسی #پروکسی ارسالی از "{html.escape(name)}"'
    body = html.escape(link)
    footer = f"اپراتور: {operator} | ارسال‌کننده: @{sender_username or 'ناشناس'} (ID: {sender_id})"
    full_text = f"{header}\n\n<code>{body}</code>\n\n{footer}"

    try:
        await context.bot.send_message(
            chat_id=get_target_channel_id(),
            text=full_text,
            parse_mode="HTML",
        )
    except Exception as e:
        logger.exception("send proxy to channel: %s", e)
        await query.edit_message_text(
            "❌ ارسال به کانال با خطا مواجه شد. لطفاً بعداً تلاش کنید."
        )
        await query.message.reply_text("منوی اصلی:", reply_markup=main_menu_keyboard())
        context.user_data.clear()
        return

    await query.edit_message_text("✅ پروکسی شما با موفقیت در کانال ثبت شد.")
    await query.message.reply_text("منوی اصلی:", reply_markup=main_menu_keyboard())
    context.user_data.clear()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    msg = update.message
    text = (msg.text or msg.caption or "").strip()
    state = context.user_data.get("state")

    if state == STATE_CONFIG_LINK:
        if not text:
            await update.message.reply_text("لطفاً یک کانفیگ V2Ray معتبر ارسال کنید.")
            return
        context.user_data["config_link"] = text
        context.user_data["state"] = STATE_CONFIG_NAME
        await update.message.reply_text(
            "نامی که دوست دارید این کانفیگ با آن منتشر شود را بنویسید (مثلاً آیدی کانال یا یک نام دلخواه):"
        )
        return

    if state == STATE_CONFIG_NAME:
        context.user_data["config_name"] = text
        context.user_data["state"] = STATE_CONFIG_OPERATOR
        await update.message.reply_text(
            "با چه اینترنتی متصل بودید؟",
            reply_markup=operator_keyboard("config"),
        )
        return

    if state == STATE_PROXY_LINK:
        if not text:
            await update.message.reply_text("لطفاً پروکسی تلگرام را ارسال کنید.")
            return
        context.user_data["proxy_link"] = text
        context.user_data["state"] = STATE_PROXY_NAME
        await update.message.reply_text(
            "نامی که دوست دارید این پروکسی با آن منتشر شود را بنویسید (مثلاً آیدی کانال یا یک نام دلخواه):"
        )
        return

    if state == STATE_PROXY_NAME:
        context.user_data["proxy_name"] = text
        context.user_data["state"] = STATE_PROXY_OPERATOR
        await update.message.reply_text(
            "با چه اینترنتی متصل بودید؟",
            reply_markup=operator_keyboard("proxy"),
        )
        return

    # اگر در هیچ جریان خاصی نبود، منو نشان بده
    is_member = await is_member_of_sponsor(context.application, update.effective_user.id)
    if is_member:
        await update.message.reply_text(
            "یکی از گزینه‌ها را انتخاب کنید:",
            reply_markup=main_menu_keyboard(),
        )
    else:
        await update.message.reply_text(
            "برای شروع /start را بزنید و در کانال اسپانسر عضو شوید."
        )


def main() -> None:
    request = HTTPXRequest(
        connect_timeout=config.CONNECT_TIMEOUT,
        read_timeout=config.READ_TIMEOUT,
        write_timeout=config.WRITE_TIMEOUT,
        proxy=config.PROXY_URL,
    )
    app = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .request(request)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_join_callback, pattern="^check_join$"))
    app.add_handler(CallbackQueryHandler(handle_config_operator, pattern="^config_"))
    app.add_handler(CallbackQueryHandler(handle_proxy_operator, pattern="^proxy_"))
    app.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^(send_config|send_proxy)$"))
    app.add_handler(
        MessageHandler(
            (filters.TEXT | filters.CAPTION) & ~filters.COMMAND,
            handle_message,
        )
    )

    logger.info("Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
