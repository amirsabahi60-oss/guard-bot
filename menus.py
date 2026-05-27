"""
Central panel handler.
- /start, /help, /panel → all open the inline Persian panel
- All callback_query routing lives here (except rpt_* which is in report.py)
- No text dumps, no duplicate commands
"""
from __future__ import annotations
import asyncio
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from telegram.error import TelegramError

import database as db
from config import LOCK_LABELS, logger
from utils.decorators import error_handler
from utils.helpers import safe_delete, auto_delete
from keyboards.inline import (
    persian_main_menu, moderation_menu, users_menu,
    locks_keyboard, settings_keyboard, filters_keyboard,
    back_to_panel, back_to_moderation,
)


async def _send_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    if not chat or not user:
        return

    if chat.type == "private":
        await update.effective_message.reply_text(
            "👋 سلام!\n\nمرا به گروهتان اضافه کنید، ادمین کنید، سپس در گروه بنویسید:\n\n<b>پنل</b>",
            parse_mode="HTML",
        )
        return

    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        is_admin = member.status in ("administrator", "creator")
    except TelegramError:
        is_admin = False

    if not is_admin:
        rank = db.get_rank(chat.id, user.id)
        if not rank:
            return

    await context.bot.send_message(
        chat.id,
        f"⚙️ <b>پنل مدیریت</b>\n<i>{chat.title}</i>",
        parse_mode="HTML",
        reply_markup=persian_main_menu(),
    )


@error_handler
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _send_panel(update, context)


@error_handler
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _send_panel(update, context)


@error_handler
async def panel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _send_panel(update, context)


async def _check_admin_for_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    query = update.callback_query
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.status in ("administrator", "creator"):
            return True
    except TelegramError:
        pass
    rank = db.get_rank(chat_id, user_id)
    if rank:
        return True
    await query.answer("❌ فقط ادمین‌ها می‌توانند از پنل استفاده کنند.", show_alert=True)
    return False


@error_handler
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return

    data = query.data or ""

    if not data.startswith(("panel_", "pmenu_", "lock_", "setting_", "filter_", "list_")):
        return

    await query.answer()

    if not await _check_admin_for_callback(update, context):
        return

    chat_id = update.effective_chat.id
    chat = update.effective_chat

    if data in ("panel_main", "pmenu_main"):
        await query.edit_message_text(
            f"⚙️ <b>پنل مدیریت</b>\n<i>{chat.title}</i>",
            parse_mode="HTML",
            reply_markup=persian_main_menu(),
        )

    elif data == "pmenu_moderation":
        await query.edit_message_text(
            "🛡 <b>مدیریت گروه</b>\n\nیک بخش را انتخاب کنید:",
            parse_mode="HTML",
            reply_markup=moderation_menu(),
        )

    elif data == "pmenu_users":
        await query.edit_message_text(
            "👮 <b>مدیریت کاربران</b>\n\nیک لیست را انتخاب کنید:",
            parse_mode="HTML",
            reply_markup=users_menu(),
        )

    elif data == "pmenu_rules":
        settings = db.get_group_settings(chat_id)
        rules = settings.get("rules_msg", "")
        text = (
            f"📜 <b>قوانین گروه:</b>\n\n{rules}"
            if rules
            else "📭 قوانینی تنظیم نشده.\n\nبرای تنظیم:\n<code>قوانین [متن]</code>"
        )
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=back_to_panel())

    elif data == "pmenu_warns_info":
        await query.edit_message_text(
            "⚠️ <b>سیستم اخطار</b>\n\n"
            "روی پیام کاربر ریپلای کنید و بنویسید:\n\n"
            "• <b>اخطار</b> — یک اخطار\n"
            "• <b>اخطار ریست</b> — پاک کردن اخطارها\n"
            "• <b>اخطارها</b> — مشاهده (ریپلای)\n\n"
            "━━━━━━━━━━━━━━\n"
            "بعد از رسیدن به حد اخطار، کاربر خودکار بن می‌شود.",
            parse_mode="HTML",
            reply_markup=back_to_moderation(),
        )

    elif data == "pmenu_purge_info":
        await query.edit_message_text(
            "🗑 <b>پاکسازی پیام‌ها</b>\n\n"
            "روی اولین پیامی که می‌خواهید پاک شود ریپلای کنید و بنویسید:\n\n"
            "<b>پاکسازی</b>\n\n"
            "همه پیام‌ها از آن نقطه تا پیام شما حذف می‌شوند.",
            parse_mode="HTML",
            reply_markup=back_to_moderation(),
        )

    elif data == "panel_locks":
        locks = db.get_locks(chat_id)
        await query.edit_message_text(
            "🔒 <b>قفل‌های گروه</b>\n\nروی هر قفل کلیک کنید تا وضعیت تغییر کند:",
            parse_mode="HTML",
            reply_markup=locks_keyboard(locks),
        )

    elif data.startswith("lock_toggle_"):
        lock_type = data[len("lock_toggle_"):]
        locks = db.get_locks(chat_id)
        current = locks.get(lock_type, {}).get("enabled", False)
        db.set_lock(chat_id, lock_type, not current)
        locks = db.get_locks(chat_id)
        label = LOCK_LABELS.get(lock_type, lock_type)
        status = "✅ فعال" if not current else "❌ غیرفعال"
        await query.answer(f"{label}: {status}")
        await query.edit_message_reply_markup(reply_markup=locks_keyboard(locks))

    elif data == "panel_settings":
        settings = db.get_group_settings(chat_id)
        await query.edit_message_text(
            "⚙️ <b>تنظیمات گروه</b>",
            parse_mode="HTML",
            reply_markup=settings_keyboard(settings),
        )

    elif data == "setting_toggle_welcome":
        settings = db.get_group_settings(chat_id)
        new_val = 0 if settings.get("welcome_enabled", 1) else 1
        db.set_group_setting(chat_id, "welcome_enabled", new_val)
        settings = db.get_group_settings(chat_id)
        await query.answer("✅ فعال" if new_val else "❌ غیرفعال")
        await query.edit_message_reply_markup(reply_markup=settings_keyboard(settings))

    elif data == "setting_toggle_autodel":
        settings = db.get_group_settings(chat_id)
        new_val = 0 if settings.get("auto_delete_bot", 1) else 1
        db.set_group_setting(chat_id, "auto_delete_bot", new_val)
        settings = db.get_group_settings(chat_id)
        await query.answer("✅ فعال" if new_val else "❌ غیرفعال")
        await query.edit_message_reply_markup(reply_markup=settings_keyboard(settings))

    elif data == "setting_edit_welcome":
        await query.edit_message_text(
            "✏️ <b>ویرایش پیام خوشامد</b>\n\n"
            "بنویسید:\n<code>خوشامد [متن پیام]</code>\n\n"
            "متغیرها:\n• <code>{name}</code> — نام کاربر\n• <code>{username}</code> — یوزرنیم",
            parse_mode="HTML",
            reply_markup=back_to_panel(),
        )

    elif data == "setting_edit_rules":
        await query.edit_message_text(
            "✏️ <b>ویرایش قوانین</b>\n\n"
            "بنویسید:\n<code>قوانین [متن قوانین گروه]</code>",
            parse_mode="HTML",
            reply_markup=back_to_panel(),
        )

    elif data == "panel_filters":
        await query.edit_message_text(
            "🚫 <b>مدیریت فیلترها</b>\n\nیک بخش را انتخاب کنید:",
            parse_mode="HTML",
            reply_markup=filters_keyboard(),
        )

    elif data == "filter_badwords":
        words = db.get_bad_words(chat_id)
        body = "\n".join(f"• <code>{w}</code>" for w in sorted(words)) if words else "📭 لیست خالی"
        await query.edit_message_text(
            f"🤬 <b>کلمات بد:</b>\n\n{body}\n\n"
            "افزودن: <code>کلمه بد [کلمه]</code>\n"
            "حذف: <code>حذف کلمه بد [کلمه]</code>",
            parse_mode="HTML",
            reply_markup=back_to_panel(),
        )

    elif data == "filter_words":
        words = db.get_filter_words(chat_id)
        body = "\n".join(f"• <code>{w}</code>" for w in sorted(words)) if words else "📭 لیست خالی"
        await query.edit_message_text(
            f"🚫 <b>کلمات فیلتر:</b>\n\n{body}\n\n"
            "افزودن: <code>فیلتر [کلمه]</code>\n"
            "حذف: <code>حذف فیلتر [کلمه]</code>",
            parse_mode="HTML",
            reply_markup=back_to_panel(),
        )

    elif data in ("list_mute", "list_ban", "list_white", "list_black", "list_kill"):
        mapping = {
            "list_mute":  ("🔇 لیست سکوت",  db.get_mute_list),
            "list_ban":   ("🚫 لیست بن",    db.get_ban_list),
            "list_white": ("✅ وایت‌لیست",  db.get_whitelist),
            "list_black": ("⛔ بلک‌لیست",   db.get_blacklist),
            "list_kill":  ("☠️ کیل‌لیست",  db.get_kill_list),
        }
        title, getter = mapping[data]
        ids = getter(chat_id)
        body = "\n".join(f"• <code>{uid}</code>" for uid in ids) if ids else "📭 لیست خالی"
        await query.edit_message_text(
            f"<b>{title}:</b>\n\n{body}",
            parse_mode="HTML",
            reply_markup=back_to_panel(),
        )

    elif data == "panel_stats":
        mutes  = len(db.get_mute_list(chat_id))
        bans   = len(db.get_ban_list(chat_id))
        whites = len(db.get_whitelist(chat_id))
        blacks = len(db.get_blacklist(chat_id))
        kills  = len(db.get_kill_list(chat_id))
        bad_ws = len(db.get_bad_words(chat_id))
        flt_ws = len(db.get_filter_words(chat_id))
        locks  = db.get_locks(chat_id)
        active_locks = sum(1 for v in locks.values() if v.get("enabled"))
        await query.edit_message_text(
            f"📊 <b>آمار گروه</b>\n\n"
            f"🔇 سکوت‌ها: <b>{mutes}</b>\n"
            f"🚫 بن‌ها: <b>{bans}</b>\n"
            f"✅ وایت‌لیست: <b>{whites}</b>\n"
            f"⛔ بلک‌لیست: <b>{blacks}</b>\n"
            f"☠️ کیل‌لیست: <b>{kills}</b>\n"
            f"🤬 کلمات بد: <b>{bad_ws}</b>\n"
            f"🚫 کلمات فیلتر: <b>{flt_ws}</b>\n"
            f"🔒 قفل‌های فعال: <b>{active_locks}</b>",
            parse_mode="HTML",
            reply_markup=back_to_panel(),
        )


def get_handlers():
    return [
        CommandHandler("start",    start_cmd),
        CommandHandler("panel",    panel_cmd),
        CallbackQueryHandler(
            handle_callback,
            pattern=r"^(panel_|pmenu_|lock_|setting_|filter_|list_)",
        ),
    ]
