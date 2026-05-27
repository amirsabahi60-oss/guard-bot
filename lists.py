from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from telegram.error import TelegramError

import database as db
from utils.decorators import admin_only, owner_only, group_only, error_handler
from utils.helpers import get_target_user, send_and_delete, user_mention, MUTE_PERMISSIONS


def _fmt_list(title: str, user_ids: list[int]) -> str:
    if not user_ids:
        return f"{title}\n\n📭 لیست خالی است."
    lines = [f"{title}\n"]
    for uid in user_ids:
        lines.append(f"• <code>{uid}</code>")
    return "\n".join(lines)


@error_handler
@group_only
@admin_only()
async def whitelist_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update, context)
    if not target:
        await send_and_delete(update, context, "❗ روی پیام کاربر ریپلای کنید.")
        return
    chat_id = update.effective_chat.id
    db.add_to_whitelist(chat_id, target.id)
    await send_and_delete(update, context, f"✅ {user_mention(target)} به وایت‌لیست اضافه شد.", parse_mode="HTML")


@error_handler
@group_only
@admin_only()
async def whitelist_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update, context)
    if not target:
        await send_and_delete(update, context, "❗ روی پیام کاربر ریپلای کنید.")
        return
    chat_id = update.effective_chat.id
    db.remove_from_whitelist(chat_id, target.id)
    await send_and_delete(update, context, f"✅ {user_mention(target)} از وایت‌لیست حذف شد.", parse_mode="HTML")


@error_handler
@group_only
@admin_only()
async def whitelist_show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    ids = db.get_whitelist(chat_id)
    await send_and_delete(update, context, _fmt_list("✅ <b>وایت‌لیست:</b>", ids), parse_mode="HTML", delay=60)


@error_handler
@group_only
@admin_only()
async def blacklist_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update, context)
    if not target:
        await send_and_delete(update, context, "❗ روی پیام کاربر ریپلای کنید.")
        return
    chat_id = update.effective_chat.id
    db.add_to_blacklist(chat_id, target.id)
    await send_and_delete(update, context, f"⛔ {user_mention(target)} به بلک‌لیست اضافه شد.", parse_mode="HTML")


@error_handler
@group_only
@admin_only()
async def blacklist_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update, context)
    if not target:
        await send_and_delete(update, context, "❗ روی پیام کاربر ریپلای کنید.")
        return
    chat_id = update.effective_chat.id
    db.remove_from_blacklist(chat_id, target.id)
    await send_and_delete(update, context, f"✅ {user_mention(target)} از بلک‌لیست حذف شد.", parse_mode="HTML")


@error_handler
@group_only
@admin_only()
async def blacklist_show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    ids = db.get_blacklist(chat_id)
    await send_and_delete(update, context, _fmt_list("⛔ <b>بلک‌لیست:</b>", ids), parse_mode="HTML", delay=60)


@error_handler
@group_only
@admin_only()
async def mutelist_show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    ids = db.get_mute_list(chat_id)
    await send_and_delete(update, context, _fmt_list("🔇 <b>لیست سکوت:</b>", ids), parse_mode="HTML", delay=60)


@error_handler
@group_only
@admin_only()
async def banlist_show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    ids = db.get_ban_list(chat_id)
    await send_and_delete(update, context, _fmt_list("🚫 <b>لیست بن:</b>", ids), parse_mode="HTML", delay=60)


@error_handler
@group_only
@owner_only
async def killist_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update, context)
    if not target:
        await send_and_delete(update, context, "❗ روی پیام کاربر ریپلای کنید.")
        return
    chat_id = update.effective_chat.id
    db.add_to_kill_list(chat_id, target.id)
    try:
        await context.bot.ban_chat_member(chat_id, target.id)
        db.add_to_ban_list(chat_id, target.id)
    except TelegramError:
        pass
    await send_and_delete(update, context, f"☠️ {user_mention(target)} به کیل‌لیست اضافه و بن شد.", parse_mode="HTML")


@error_handler
@group_only
@owner_only
async def killist_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update, context)
    if not target:
        await send_and_delete(update, context, "❗ روی پیام کاربر ریپلای کنید.")
        return
    chat_id = update.effective_chat.id
    db.remove_from_kill_list(chat_id, target.id)
    await send_and_delete(update, context, f"✅ {user_mention(target)} از کیل‌لیست حذف شد.", parse_mode="HTML")


@error_handler
@group_only
@admin_only()
async def killist_show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    ids = db.get_kill_list(chat_id)
    await send_and_delete(update, context, _fmt_list("☠️ <b>کیل‌لیست:</b>", ids), parse_mode="HTML", delay=60)


def get_handlers():
    return [
        CommandHandler("whitelist", whitelist_show),
        CommandHandler("addwhite", whitelist_add),
        CommandHandler("rmwhite", whitelist_remove),
        CommandHandler("blacklist", blacklist_show),
        CommandHandler("addblack", blacklist_add),
        CommandHandler("rmblack", blacklist_remove),
        CommandHandler("mutelist", mutelist_show),
        CommandHandler("banlist", banlist_show),
        CommandHandler("killist", killist_show),
        CommandHandler("addkill", killist_add),
        CommandHandler("rmkill", killist_remove),
    ]
