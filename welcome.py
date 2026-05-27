from telegram import Update, ChatMemberUpdated, ChatMember
from telegram.ext import ContextTypes, CommandHandler, ChatMemberHandler, ConversationHandler, MessageHandler, filters
from telegram.error import TelegramError
import asyncio

import database as db
from utils.decorators import admin_only, group_only, error_handler
from utils.helpers import send_and_delete, user_mention, auto_delete

WAITING_WELCOME = 1
WAITING_RULES = 2


@error_handler
async def on_member_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if not result:
        return

    chat_id = result.chat.id
    old_status = result.old_chat_member.status
    new_status = result.new_chat_member.status
    user = result.new_chat_member.user

    if old_status in (ChatMember.LEFT, ChatMember.BANNED) and new_status == ChatMember.MEMBER:
        settings = db.get_group_settings(chat_id)
        if not settings.get("welcome_enabled", 1):
            return

        if db.is_in_kill_list(chat_id, user.id):
            try:
                await context.bot.ban_chat_member(chat_id, user.id)
                db.add_to_ban_list(chat_id, user.id)
                msg = await context.bot.send_message(
                    chat_id,
                    f"☠️ {user_mention(user)} در کیل‌لیست بود و بن شد.",
                    parse_mode="HTML"
                )
                asyncio.create_task(auto_delete(msg))
                return
            except TelegramError:
                pass

        if db.is_in_blacklist(chat_id, user.id):
            try:
                await context.bot.ban_chat_member(chat_id, user.id)
                msg = await context.bot.send_message(
                    chat_id,
                    f"⛔ {user_mention(user)} در بلک‌لیست بود و بن شد.",
                    parse_mode="HTML"
                )
                asyncio.create_task(auto_delete(msg))
                return
            except TelegramError:
                pass

        welcome_msg = settings.get("welcome_msg", "")
        if welcome_msg:
            text = welcome_msg.replace("{name}", user_mention(user)).replace("{username}", f"@{user.username}" if user.username else user.first_name)
        else:
            text = f"👋 به {user_mention(user)} خوش آمدید!\n\nبرای مشاهده قوانین: /rules"

        try:
            msg = await context.bot.send_message(chat_id, text, parse_mode="HTML")
            asyncio.create_task(auto_delete(msg, delay=120))
        except TelegramError:
            pass


@error_handler
@group_only
@admin_only()
async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        text = " ".join(context.args)
        db.set_group_setting(update.effective_chat.id, "welcome_msg", text)
        await send_and_delete(update, context,
            "✅ پیام خوشامد تنظیم شد.\n"
            "متغیرها:\n• {name} — نام کاربر\n• {username} — یوزرنیم"
        )
        return

    await update.message.reply_text(
        "✏️ پیام خوشامد جدید را بنویسید:\n\n"
        "متغیرها:\n• {name} — نام کاربر\n• {username} — یوزرنیم\n\n"
        "برای لغو: /cancel"
    )
    return WAITING_WELCOME


async def receive_welcome_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "/cancel":
        await send_and_delete(update, context, "❌ لغو شد.")
        return ConversationHandler.END

    db.set_group_setting(update.effective_chat.id, "welcome_msg", text)
    await send_and_delete(update, context, "✅ پیام خوشامد ذخیره شد.")
    return ConversationHandler.END


@error_handler
@group_only
@admin_only()
async def set_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        text = " ".join(context.args)
        db.set_group_setting(update.effective_chat.id, "rules_msg", text)
        await send_and_delete(update, context, "✅ قوانین گروه تنظیم شد.")
        return

    await update.message.reply_text("✏️ قوانین گروه را بنویسید:\n\nبرای لغو: /cancel")
    return WAITING_RULES


async def receive_rules_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "/cancel":
        await send_and_delete(update, context, "❌ لغو شد.")
        return ConversationHandler.END

    db.set_group_setting(update.effective_chat.id, "rules_msg", text)
    await send_and_delete(update, context, "✅ قوانین ذخیره شد.")
    return ConversationHandler.END


@error_handler
@group_only
async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    settings = db.get_group_settings(chat_id)
    rules = settings.get("rules_msg", "")
    if not rules:
        await send_and_delete(update, context, "📭 قوانینی تنظیم نشده است.")
        return
    await send_and_delete(update, context, f"📜 <b>قوانین گروه:</b>\n\n{rules}", parse_mode="HTML", delay=120)


def get_handlers():
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("setwelcome", set_welcome),
            CommandHandler("setrules", set_rules),
        ],
        states={
            WAITING_WELCOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_welcome_text)],
            WAITING_RULES: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_rules_text)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
    )
    return [
        conv_handler,
        CommandHandler("rules", show_rules),
        ChatMemberHandler(on_member_join, ChatMemberHandler.CHAT_MEMBER),
    ]
