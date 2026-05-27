from __future__ import annotations
import re
from telegram import Update, Message
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from telegram.error import TelegramError

import database as db
from config import LOCK_TYPES, LOCK_LABELS, logger
from utils.decorators import admin_only, group_only, error_handler
from utils.helpers import send_and_delete, safe_delete, user_mention


def _build_locks_text(locks: dict) -> str:
    lines = ["🔒 <b>وضعیت قفل‌های گروه:</b>\n"]
    for lt in LOCK_TYPES:
        info = locks.get(lt, {})
        status = "✅ فعال" if info.get("enabled") else "❌ غیرفعال"
        warn_c = info.get("warn_count", 1)
        label = LOCK_LABELS.get(lt, lt)
        lines.append(f"{label}: {status} (اخطار: {warn_c})")
    return "\n".join(lines)


@error_handler
@group_only
@admin_only()
async def lock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        chat_id = update.effective_chat.id
        locks = db.get_locks(chat_id)
        await send_and_delete(update, context, _build_locks_text(locks), parse_mode="HTML", delay=60)
        return
    lock_type = context.args[0].lower()
    if lock_type not in LOCK_TYPES:
        await send_and_delete(update, context, f"❌ انواع قفل: {', '.join(LOCK_TYPES)}")
        return
    db.set_lock(update.effective_chat.id, lock_type, True)
    await send_and_delete(update, context, f"🔒 {LOCK_LABELS.get(lock_type, lock_type)} قفل شد.")


@error_handler
@group_only
@admin_only()
async def unlock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await send_and_delete(update, context, "❗ مثال: /unlock link")
        return
    lock_type = context.args[0].lower()
    if lock_type not in LOCK_TYPES:
        await send_and_delete(update, context, f"❌ انواع قفل: {', '.join(LOCK_TYPES)}")
        return
    db.set_lock(update.effective_chat.id, lock_type, False)
    await send_and_delete(update, context, f"🔓 {LOCK_LABELS.get(lock_type, lock_type)} باز شد.")


@error_handler
@group_only
@admin_only()
async def set_warn_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await send_and_delete(update, context, "❗ مثال: /setwarn link 2")
        return
    lock_type = context.args[0].lower()
    if lock_type not in LOCK_TYPES:
        await send_and_delete(update, context, f"❌ انواع: {', '.join(LOCK_TYPES)}")
        return
    try:
        count = int(context.args[1])
        if count < 1:
            raise ValueError
    except ValueError:
        await send_and_delete(update, context, "❌ تعداد باید عدد مثبت باشد.")
        return
    db.set_lock_warn_count(update.effective_chat.id, lock_type, count)
    await send_and_delete(update, context,
        f"✅ اخطار {LOCK_LABELS.get(lock_type, lock_type)} به {count} تغییر یافت.")


@error_handler
@group_only
async def locks_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    locks = db.get_locks(update.effective_chat.id)
    await send_and_delete(update, context, _build_locks_text(locks), parse_mode="HTML", delay=60)


USERNAME_PATTERN = re.compile(r"@[a-zA-Z0-9_]{5,}")


async def _handle_lock_violation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    lock_type: str,
    reason: str,
):
    message = update.effective_message
    user = update.effective_user
    chat_id = update.effective_chat.id

    if db.is_in_whitelist(chat_id, user.id):
        return

    try:
        member = await context.bot.get_chat_member(chat_id, user.id)
        if member.status in ("administrator", "creator"):
            return
    except TelegramError:
        pass

    await safe_delete(message)

    from handlers.warns import apply_lock_warn
    await apply_lock_warn(update, context, lock_type, reason)


async def check_locks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message or not update.effective_chat or not update.effective_user:
        return

    chat_id = update.effective_chat.id
    user = update.effective_user

    if db.is_in_whitelist(chat_id, user.id):
        return

    try:
        member = await context.bot.get_chat_member(chat_id, user.id)
        if member.status in ("administrator", "creator"):
            return
    except TelegramError:
        return

    locks = db.get_locks(chat_id)

    if message.forward_date and locks.get("forward", {}).get("enabled"):
        await _handle_lock_violation(update, context, "forward", "🚫 فوروارد ممنوع است")
        return

    if message.sticker and locks.get("sticker", {}).get("enabled"):
        await _handle_lock_violation(update, context, "sticker", "🎭 استیکر ممنوع است")
        return

    if message.animation and locks.get("gif", {}).get("enabled"):
        await _handle_lock_violation(update, context, "gif", "🎬 گیف ممنوع است")
        return

    if message.photo and locks.get("photo", {}).get("enabled"):
        await _handle_lock_violation(update, context, "photo", "🖼 ارسال عکس ممنوع است")
        return

    if message.video and locks.get("video", {}).get("enabled"):
        await _handle_lock_violation(update, context, "video", "📹 ارسال ویدیو ممنوع است")
        return

    if message.voice and locks.get("voice", {}).get("enabled"):
        await _handle_lock_violation(update, context, "voice", "🎤 ارسال ویس ممنوع است")
        return

    if message.document and locks.get("file", {}).get("enabled"):
        await _handle_lock_violation(update, context, "file", "📁 ارسال فایل ممنوع است")
        return

    if message.text:
        text = message.text

        if locks.get("link", {}).get("enabled") and re.search(r"https?://|t\.me/", text, re.IGNORECASE):
            await _handle_lock_violation(update, context, "link", "🔗 ارسال لینک ممنوع است")
            return

        if locks.get("username", {}).get("enabled") and USERNAME_PATTERN.search(text):
            await _handle_lock_violation(update, context, "username", "👤 ذکر یوزرنیم ممنوع است")
            return

        if locks.get("badwords", {}).get("enabled"):
            tl = text.lower()
            for w in db.get_bad_words(chat_id):
                if w in tl:
                    await _handle_lock_violation(update, context, "badwords", "🤬 کلمات نامناسب ممنوع است")
                    return

        tl = text.lower()
        for w in db.get_filter_words(chat_id):
            if w in tl:
                await safe_delete(message)
                import asyncio
                from utils.helpers import auto_delete
                m = await context.bot.send_message(
                    chat_id,
                    f"🚫 {user_mention(user)} — پیام حاوی کلمه فیلتر شده حذف شد.",
                    parse_mode="HTML",
                )
                settings = db.get_group_settings(chat_id)
                if settings.get("auto_delete_bot", 0):
                    asyncio.create_task(auto_delete(m))
                return


def get_command_handlers():
    return [
        CommandHandler("lock",    lock_cmd),
        CommandHandler("unlock",  unlock_cmd),
        CommandHandler("locks",   locks_status),
        CommandHandler("setwarn", set_warn_count),
    ]


def get_message_handler():
    return MessageHandler(filters.ALL & ~filters.COMMAND, check_locks)
