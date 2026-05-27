from __future__ import annotations
import asyncio
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from telegram.error import TelegramError

import database as db
from config import logger, RANK_HIERARCHY, RANK_LABELS, RANK_OWNER, RANK_SUDO, RANK_ADMIN, RANK_VIP
from utils.decorators import admin_only, owner_only, group_only, error_handler
from utils.helpers import get_target_user, send_and_delete, user_mention, MUTE_PERMISSIONS, UNMUTE_PERMISSIONS


@error_handler
@group_only
@admin_only()
async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update, context)
    if not target:
        await send_and_delete(update, context, "❗ روی پیام کاربر ریپلای کنید یا آیدی بدهید.")
        return
    if target.is_bot:
        await send_and_delete(update, context, "❌ نمی‌توان ربات را ساکت کرد.")
        return

    chat_id = update.effective_chat.id
    duration_min = None
    args = context.args or []
    reason_args = args

    if args and args[0].isdigit():
        duration_min = int(args[0])
        reason_args = args[1:]

    reason = " ".join(reason_args) if reason_args else "بدون دلیل"
    until = datetime.now() + timedelta(minutes=duration_min) if duration_min else None

    try:
        await context.bot.restrict_chat_member(
            chat_id, target.id, MUTE_PERMISSIONS, until_date=until
        )
        db.add_to_mute_list(chat_id, target.id)
        dur_text = f"برای {duration_min} دقیقه" if duration_min else "تا اطلاع ثانوی"
        await update.message.reply_text(
            f"🔇 {user_mention(target)} ساکت شد {dur_text}.\n📌 دلیل: {reason}",
            parse_mode="HTML"
        )
    except TelegramError as e:
        await send_and_delete(update, context, f"⚠️ خطا: {e}")


@error_handler
@group_only
@admin_only()
async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update, context)
    if not target:
        await send_and_delete(update, context, "❗ روی پیام کاربر ریپلای کنید.")
        return

    chat_id = update.effective_chat.id
    try:
        await context.bot.restrict_chat_member(chat_id, target.id, UNMUTE_PERMISSIONS)
        db.remove_from_mute_list(chat_id, target.id)
        await send_and_delete(update, context,
            f"🔊 سکوت {user_mention(target)} رفع شد.", parse_mode="HTML"
        )
    except TelegramError as e:
        await send_and_delete(update, context, f"⚠️ خطا: {e}")


@error_handler
@group_only
@admin_only()
async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update, context)
    if not target:
        await send_and_delete(update, context, "❗ روی پیام کاربر ریپلای کنید یا آیدی بدهید.")
        return
    if target.is_bot:
        await send_and_delete(update, context, "❌ نمی‌توان ربات را بن کرد.")
        return

    chat_id = update.effective_chat.id
    args = context.args or []
    reason_start = 1 if not update.message.reply_to_message else 0
    reason = " ".join(args[reason_start:]) if len(args) > reason_start else "بدون دلیل"

    try:
        await context.bot.ban_chat_member(chat_id, target.id)
        db.add_to_ban_list(chat_id, target.id)
        db.reset_warns(chat_id, target.id)
        await update.message.reply_text(
            f"🚫 {user_mention(target)} بن شد.\n📌 دلیل: {reason}",
            parse_mode="HTML"
        )
    except TelegramError as e:
        await send_and_delete(update, context, f"⚠️ خطا: {e}")


@error_handler
@group_only
@admin_only()
async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update, context)
    if not target:
        await send_and_delete(update, context, "❗ روی پیام کاربر ریپلای کنید یا آیدی بدهید.")
        return

    chat_id = update.effective_chat.id
    try:
        await context.bot.unban_chat_member(chat_id, target.id, only_if_banned=True)
        db.remove_from_ban_list(chat_id, target.id)
        await send_and_delete(update, context,
            f"✅ بن {user_mention(target)} رفع شد.", parse_mode="HTML"
        )
    except TelegramError as e:
        await send_and_delete(update, context, f"⚠️ خطا: {e}")


@error_handler
@group_only
@admin_only()
async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update, context)
    if not target:
        await send_and_delete(update, context, "❗ روی پیام کاربر ریپلای کنید.")
        return

    chat_id = update.effective_chat.id
    args = context.args or []
    reason = " ".join(args) if args else "بدون دلیل"
    try:
        await context.bot.ban_chat_member(chat_id, target.id)
        await context.bot.unban_chat_member(chat_id, target.id)
        await update.message.reply_text(
            f"👢 {user_mention(target)} اخراج شد.\n📌 دلیل: {reason}",
            parse_mode="HTML"
        )
    except TelegramError as e:
        await send_and_delete(update, context, f"⚠️ خطا: {e}")


@error_handler
@group_only
@owner_only
async def promote_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update, context)
    if not target:
        await send_and_delete(update, context, "❗ روی پیام کاربر ریپلای کنید.")
        return
    if target.is_bot:
        await send_and_delete(update, context, "❌ نمی‌توان به ربات رتبه داد.")
        return

    chat_id = update.effective_chat.id
    args = context.args or []
    rank_arg_idx = 1 if not update.message.reply_to_message else 0
    rank_str = args[rank_arg_idx].lower() if len(args) > rank_arg_idx else RANK_ADMIN

    valid_ranks = {
        "owner": RANK_OWNER, "sudo": RANK_SUDO,
        "admin": RANK_ADMIN, "vip": RANK_VIP,
        "مالک": RANK_OWNER, "سودو": RANK_SUDO,
        "ادمین": RANK_ADMIN, "ویآیپی": RANK_VIP,
    }
    rank = valid_ranks.get(rank_str, RANK_ADMIN)
    db.set_rank(chat_id, target.id, rank)
    label = RANK_LABELS.get(rank, rank)
    await send_and_delete(update, context,
        f"✅ {user_mention(target)} به رتبه {label} ارتقا یافت.", parse_mode="HTML"
    )


@error_handler
@group_only
@owner_only
async def demote_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update, context)
    if not target:
        await send_and_delete(update, context, "❗ روی پیام کاربر ریپلای کنید.")
        return

    chat_id = update.effective_chat.id
    db.set_rank(chat_id, target.id, None)
    await send_and_delete(update, context,
        f"✅ رتبه {user_mention(target)} حذف شد.", parse_mode="HTML"
    )


@error_handler
@group_only
@admin_only()
async def purge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await send_and_delete(update, context, "❗ برای پاک کردن پیام‌ها، روی اولین پیام ریپلای کنید.")
        return

    chat_id = update.effective_chat.id
    from_msg_id = update.message.reply_to_message.message_id
    to_msg_id = update.message.message_id

    deleted = 0
    ids_to_delete = list(range(from_msg_id, to_msg_id + 1))
    for i in range(0, len(ids_to_delete), 100):
        chunk = ids_to_delete[i:i+100]
        try:
            result = await context.bot.delete_messages(chat_id, chunk)
            deleted += len(chunk)
        except TelegramError:
            for mid in chunk:
                try:
                    await context.bot.delete_message(chat_id, mid)
                    deleted += 1
                except Exception:
                    pass

    msg = await context.bot.send_message(chat_id, f"🗑 {deleted} پیام پاک شد.")
    await asyncio.sleep(5)
    try:
        await msg.delete()
    except Exception:
        pass


def get_handlers():
    return [
        CommandHandler("mute", mute_user),
        CommandHandler("unmute", unmute_user),
        CommandHandler("ban", ban_user),
        CommandHandler("unban", unban_user),
        CommandHandler("kick", kick_user),
        CommandHandler("promote", promote_user),
        CommandHandler("demote", demote_user),
        CommandHandler("purge", purge),
    ]
