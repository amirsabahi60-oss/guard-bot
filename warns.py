from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from telegram.error import TelegramError

import database as db
from config import MAX_WARNS_DEFAULT, logger
from utils.decorators import admin_only, group_only, error_handler
from utils.helpers import get_target_user, send_and_delete, user_mention, MUTE_PERMISSIONS


async def _check_warn_limit(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int, user) -> bool:
    """Returns True if user was banned (reached limit)."""
    count = db.get_warns(chat_id, user_id)
    settings = db.get_group_settings(chat_id)
    max_warns = settings.get("max_warns", MAX_WARNS_DEFAULT)

    if count >= max_warns:
        try:
            await context.bot.ban_chat_member(chat_id, user_id)
            db.add_to_ban_list(chat_id, user_id)
            db.reset_warns(chat_id, user_id)
            msg = await update.effective_message.reply_text(
                f"🚫 {user_mention(user)} به دلیل رسیدن به حداکثر اخطار ({max_warns}) بن شد.",
                parse_mode="HTML"
            )
            return True
        except TelegramError as e:
            logger.error(f"Cannot ban user {user_id}: {e}")
    return False


@error_handler
@group_only
@admin_only()
async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update, context)
    if not target:
        await send_and_delete(update, context, "❗ روی پیام کاربر ریپلای کنید یا آیدی را بدهید.")
        return
    if target.is_bot:
        await send_and_delete(update, context, "❌ نمی‌توان به ربات اخطار داد.")
        return

    chat_id = update.effective_chat.id
    user_id = target.id

    if db.is_in_whitelist(chat_id, user_id):
        await send_and_delete(update, context, f"⚠️ {user_mention(target)} در وایت‌لیست است و نمی‌توان اخطار داد.", parse_mode="HTML")
        return

    args = context.args or []
    reason_start = 1 if not update.message.reply_to_message else 0
    reason = " ".join(args[reason_start:]) if len(args) > reason_start else "بدون دلیل"

    count = db.add_warn(chat_id, user_id)
    settings = db.get_group_settings(chat_id)
    max_warns = settings.get("max_warns", MAX_WARNS_DEFAULT)

    banned = await _check_warn_limit(update, context, chat_id, user_id, target)
    if not banned:
        await update.message.reply_text(
            f"⚠️ اخطار {count}/{max_warns} به {user_mention(target)}\n"
            f"📌 دلیل: {reason}",
            parse_mode="HTML"
        )


@error_handler
@group_only
@admin_only()
async def unwarn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update, context)
    if not target:
        await send_and_delete(update, context, "❗ روی پیام کاربر ریپلای کنید.")
        return

    chat_id = update.effective_chat.id
    current = db.get_warns(chat_id, target.id)
    if current <= 0:
        await send_and_delete(update, context, f"✅ {user_mention(target)} هیچ اخطاری ندارد.", parse_mode="HTML")
        return

    db.add_warn(chat_id, target.id, -1)
    new_count = db.get_warns(chat_id, target.id)
    settings = db.get_group_settings(chat_id)
    max_warns = settings.get("max_warns", MAX_WARNS_DEFAULT)
    await send_and_delete(update, context,
        f"✅ یک اخطار از {user_mention(target)} کم شد. ({new_count}/{max_warns})",
        parse_mode="HTML"
    )


@error_handler
@group_only
@admin_only()
async def reset_warns_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update, context)
    if not target:
        await send_and_delete(update, context, "❗ روی پیام کاربر ریپلای کنید.")
        return

    chat_id = update.effective_chat.id
    db.reset_warns(chat_id, target.id)
    await send_and_delete(update, context,
        f"✅ تمام اخطارهای {user_mention(target)} پاک شد.",
        parse_mode="HTML"
    )


@error_handler
@group_only
async def get_warns_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update, context)
    if not target:
        target = update.effective_user

    chat_id = update.effective_chat.id
    count = db.get_warns(chat_id, target.id)
    settings = db.get_group_settings(chat_id)
    max_warns = settings.get("max_warns", MAX_WARNS_DEFAULT)

    bar = "🟥" * count + "⬜️" * max(0, max_warns - count)
    await send_and_delete(update, context,
        f"📊 اخطارهای {user_mention(target)}:\n"
        f"{bar}\n"
        f"تعداد: {count} از {max_warns}",
        parse_mode="HTML"
    )


async def apply_lock_warn(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    lock_type: str,
    reason: str,
):
    """Called by lock/filter system to issue a lock-specific warn."""
    user = update.effective_user
    chat_id = update.effective_chat.id
    user_id = user.id

    if db.is_in_whitelist(chat_id, user_id):
        return

    locks = db.get_locks(chat_id)
    lock_info = locks.get(lock_type, {})
    warn_per_violation = lock_info.get("warn_count", 1)

    count = db.add_warn(chat_id, user_id, warn_per_violation)
    settings = db.get_group_settings(chat_id)
    max_warns = settings.get("max_warns", MAX_WARNS_DEFAULT)

    banned = await _check_warn_limit(update, context, chat_id, user_id, user)
    if not banned:
        from utils.helpers import schedule_delete
        msg = await context.bot.send_message(
            chat_id,
            f"⚠️ {user_mention(user)} — {reason}\n"
            f"اخطار: {count}/{max_warns}",
            parse_mode="HTML"
        )
        schedule_delete(chat_id, msg)


def get_handlers():
    return [
        CommandHandler("warn", warn_user),
        CommandHandler("unwarn", unwarn_user),
        CommandHandler("resetwarns", reset_warns_cmd),
        CommandHandler("warns", get_warns_cmd),
    ]
