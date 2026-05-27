"""
Persian report system.
Users reply to a message with گزارش → admins notified with action buttons.
Anti-abuse: cooldown per user per group.

Deletion policy:
  The user's گزارش message obeys auto_delete_bot (schedule_delete).
  Bot hint/confirmation messages also obey the same setting.
  Admin DM action messages are never deleted (they are in private chats).
"""
from __future__ import annotations
import asyncio
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.error import TelegramError

import database as db
from config import logger
from utils.decorators import error_handler
from utils.helpers import schedule_delete, user_mention, MUTE_PERMISSIONS, UNMUTE_PERMISSIONS, auto_delete

COOLDOWN_SECONDS = 120
_last_report: dict[tuple[int, int], float] = {}


def _report_action_keyboard(chat_id: int, reported_user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔇 سکوت کاربر", callback_data=f"rpt_mute_{chat_id}_{reported_user_id}"),
            InlineKeyboardButton("🚫 بن کاربر",   callback_data=f"rpt_ban_{chat_id}_{reported_user_id}"),
        ],
        [InlineKeyboardButton("✅ نادیده گرفتن", callback_data=f"rpt_ign_{chat_id}_{reported_user_id}")],
    ])


async def _notify_admins(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    chat_title: str,
    reported_user: object,
    reported_msg: Message,
) -> None:
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
    except TelegramError as e:
        logger.error(f"Cannot get admins: {e}")
        return

    msg_link = ""
    if reported_msg.chat.username:
        msg_link = f"https://t.me/{reported_msg.chat.username}/{reported_msg.message_id}"
    elif str(chat_id).startswith("-100"):
        pure_id = str(chat_id)[4:]
        msg_link = f"https://t.me/c/{pure_id}/{reported_msg.message_id}"

    link_line = f'\n🔗 <a href="{msg_link}">مشاهده پیام</a>' if msg_link else ""

    report_text = (
        f"🚨 <b>گزارش جدید</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 گروه: <b>{chat_title}</b>\n"
        f"👤 گزارش‌دهنده: <b>ناشناس</b>\n"
        f"🎯 کاربر گزارش‌شده: {user_mention(reported_user)}"
        f"{link_line}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 <b>متن پیام:</b>"
    )

    keyboard = _report_action_keyboard(chat_id, reported_user.id)

    for admin in admins:
        if admin.user.is_bot:
            continue
        try:
            await context.bot.send_message(
                admin.user.id, report_text, parse_mode="HTML", reply_markup=keyboard,
            )
            if reported_msg.text:
                await context.bot.send_message(
                    admin.user.id,
                    f"<blockquote>{reported_msg.text[:1000]}</blockquote>",
                    parse_mode="HTML",
                )
            elif reported_msg.caption:
                await context.bot.send_message(
                    admin.user.id,
                    f"<blockquote>{reported_msg.caption[:1000]}</blockquote>",
                    parse_mode="HTML",
                )
        except TelegramError:
            pass


async def _handle_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user    = update.effective_user
    chat    = update.effective_chat

    if not message or not user or not chat:
        return
    if chat.type not in ("group", "supergroup"):
        return

    chat_id = chat.id

    if not message.reply_to_message:
        hint = await message.reply_text(
            "🚨 برای گزارش، روی پیام مورد نظر ریپلای کنید و بنویسید:\n<b>گزارش</b>",
            parse_mode="HTML",
        )
        schedule_delete(chat_id, message)
        schedule_delete(chat_id, hint)
        return

    reported_msg  = message.reply_to_message
    reported_user = reported_msg.from_user
    user_id       = user.id

    if reported_user and reported_user.id == user_id:
        hint = await message.reply_text("❌ نمی‌توانید پیام خودتان را گزارش دهید.")
        schedule_delete(chat_id, message)
        schedule_delete(chat_id, hint)
        return

    if reported_user and reported_user.is_bot:
        hint = await message.reply_text("❌ نمی‌توان پیام ربات را گزارش داد.")
        schedule_delete(chat_id, message)
        schedule_delete(chat_id, hint)
        return

    cooldown_key = (chat_id, user_id)
    now       = time.time()
    remaining = COOLDOWN_SECONDS - (now - _last_report.get(cooldown_key, 0))
    if remaining > 0:
        mins = int(remaining // 60)
        secs = int(remaining % 60)
        time_str = f"{mins} دقیقه و {secs} ثانیه" if mins > 0 else f"{secs} ثانیه"
        hint = await message.reply_text(f"⏳ لطفاً {time_str} دیگر صبر کنید.")
        schedule_delete(chat_id, message)
        schedule_delete(chat_id, hint)
        return

    _last_report[cooldown_key] = now
    schedule_delete(chat_id, message)

    notif = await context.bot.send_message(
        chat_id,
        "✅ گزارش شما به صورت <b>ناشناس</b> برای ادمین‌ها ارسال شد.",
        parse_mode="HTML",
    )
    schedule_delete(chat_id, notif)

    await _notify_admins(
        context, chat_id, chat.title or str(chat_id),
        reported_user, reported_msg,
    )


@error_handler
async def report_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _handle_report(update, context)


@error_handler
async def report_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _handle_report(update, context)


@error_handler
async def report_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()

    data       = query.data or ""
    admin_user = update.effective_user

    if data == "rpt_prompt":
        await query.answer(
            "روی پیامی که می‌خواهید گزارش دهید ریپلای کنید و بنویسید: گزارش",
            show_alert=True,
        )
        return

    parts = data.split("_")
    if len(parts) < 4:
        return

    action = parts[1]
    try:
        chat_id          = int(parts[2])
        reported_user_id = int(parts[3])
    except (ValueError, IndexError):
        return

    try:
        member   = await context.bot.get_chat_member(chat_id, admin_user.id)
        is_admin = member.status in ("administrator", "creator")
    except TelegramError:
        is_admin = False

    if not is_admin:
        if not db.get_rank(chat_id, admin_user.id):
            await query.answer("❌ فقط ادمین‌ها می‌توانند اقدام کنند.", show_alert=True)
            return

    if action == "ign":
        await query.edit_message_text(
            query.message.text + f"\n\n✅ نادیده گرفته شد توسط {admin_user.mention_html()}",
            parse_mode="HTML",
        )

    elif action == "mute":
        try:
            await context.bot.restrict_chat_member(chat_id, reported_user_id, MUTE_PERMISSIONS)
            db.add_to_mute_list(chat_id, reported_user_id)
            await query.edit_message_text(
                query.message.text + f"\n\n🔇 ساکت شد توسط {admin_user.mention_html()}",
                parse_mode="HTML",
            )
            await query.answer("🔇 کاربر ساکت شد.")
            try:
                await context.bot.send_message(chat_id, "🔇 یک کاربر بر اساس گزارش ساکت شد.")
            except TelegramError:
                pass
        except TelegramError as e:
            await query.answer(f"⚠️ خطا: {e}", show_alert=True)

    elif action == "ban":
        try:
            await context.bot.ban_chat_member(chat_id, reported_user_id)
            db.add_to_ban_list(chat_id, reported_user_id)
            db.reset_warns(chat_id, reported_user_id)
            await query.edit_message_text(
                query.message.text + f"\n\n🚫 بن شد توسط {admin_user.mention_html()}",
                parse_mode="HTML",
            )
            await query.answer("🚫 کاربر بن شد.")
            try:
                await context.bot.send_message(chat_id, "🚫 یک کاربر بر اساس گزارش بن شد.")
            except TelegramError:
                pass
        except TelegramError as e:
            await query.answer(f"⚠️ خطا: {e}", show_alert=True)


def get_handlers():
    return [
        CommandHandler("report", report_cmd),
        MessageHandler(
            filters.Regex(r"^گزارش$") & filters.TEXT & ~filters.COMMAND,
            report_text,
        ),
        CallbackQueryHandler(report_callback, pattern=r"^rpt_"),
    ]
