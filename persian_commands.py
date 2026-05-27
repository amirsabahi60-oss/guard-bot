"""
Persian text command handler — group 1 (priority over lock/antispam).

Deletion policy (per auto_delete_bot setting):
  OFF (default) → nothing is deleted — commands stay, bot replies stay.
  ON            → both the user command message AND the bot reply are
                  scheduled for deletion 30 s after being sent.
                  No immediate deletion of command messages.

گزارش is excluded from TRIGGER_RE — handled exclusively by report.py (group 0).
"""
from __future__ import annotations
import asyncio
import re
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from telegram.error import TelegramError

import database as db
from config import (
    LOCK_LABELS, MAX_WARNS_DEFAULT,
    RANK_OWNER, RANK_SUDO, RANK_ADMIN, RANK_VIP, RANK_LABELS,
)
from utils.decorators import error_handler
from utils.helpers import (
    auto_delete, schedule_delete, user_mention,
    MUTE_PERMISSIONS, UNMUTE_PERMISSIONS,
)
from keyboards.inline import persian_main_menu

PERSIAN_LOCK_MAP: dict[str, str] = {
    "لینک":     "link",
    "یوزرنیم":  "username",
    "فوروارد":  "forward",
    "استیکر":   "sticker",
    "گیف":      "gif",
    "عکس":      "photo",
    "ویدیو":    "video",
    "ویس":      "voice",
    "فایل":     "file",
    "اسپم":     "spam",
    "کلمات بد": "badwords",
    "کلمه بد":  "badwords",
}

RANK_FA_MAP: dict[str, str] = {
    "مالک":  RANK_OWNER,
    "سودو":  RANK_SUDO,
    "ادمین": RANK_ADMIN,
    "ویژه":  RANK_VIP,
}

TRIGGER_RE = re.compile(
    r"^(پنل"
    r"|بن|بن کردن|رفع بن"
    r"|سکوت|میوت|ساکت|رفع سکوت|آنمیوت"
    r"|اخطار|وارن|اخطار ریست|اخطارها"
    r"|پاکسازی|اخراج"
    r"|ارتقا مالک|ارتقا سودو|ارتقا ادمین|ارتقا ویژه|تنزل"
    r"|افزودن وایت|حذف وایت"
    r"|افزودن بلک|حذف بلک"
    r"|افزودن کیل|حذف کیل"
    r"|قوانین(?:\s+.+)?"
    r"|خوشامد\s+.+"
    r"|قفل\s+\S+|باز کردن\s+\S+|آنلاک\s+\S+"
    r"|کلمه بد\s+.+|حذف کلمه بد\s+.+"
    r"|فیلتر\s+.+|حذف فیلتر\s+.+"
    r"|راهنما|کمک|help"
    r"|حذف خودکار روشن|حذف خودکار خاموش)$",
    re.IGNORECASE,
)

_DEFAULT_DELAY = 30


async def _is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(
            update.effective_chat.id, update.effective_user.id
        )
        if member.status in ("administrator", "creator"):
            return True
    except TelegramError:
        pass
    return db.get_rank(update.effective_chat.id, update.effective_user.id) is not None


async def _notify(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    text: str,
    delay: int = _DEFAULT_DELAY,
) -> None:
    """
    Send a bot notification and schedule its deletion if auto_delete_bot is ON.
    Returns without deleting anything when the setting is OFF.
    """
    try:
        msg = await context.bot.send_message(chat_id, text, parse_mode="HTML")
        schedule_delete(chat_id, msg, delay)
    except TelegramError:
        pass


async def _need_reply(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    await _notify(context, chat_id, "❗ روی پیام کاربر ریپلای کنید.")


def _reply_target(msg):
    return msg.reply_to_message.from_user if msg.reply_to_message else None


@error_handler
async def handle_persian(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg  = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    if not msg or not user or not chat:
        return
    if chat.type not in ("group", "supergroup"):
        return

    text     = (msg.text or "").strip()
    chat_id  = chat.id
    is_admin = await _is_admin(update, context)

    # ── پنل ──────────────────────────────────────────────────────────────
    if text == "پنل":
        if not is_admin:
            return
        panel = await context.bot.send_message(
            chat_id,
            f"⚙️ <b>پنل مدیریت</b>\n<i>{chat.title}</i>",
            parse_mode="HTML",
            reply_markup=persian_main_menu(),
        )
        # Panel itself is never auto-deleted (important UI)
        return

    # ── راهنما / کمک / help ───────────────────────────────────────────────
    if text.lower() in ("راهنما", "کمک", "help"):
        from handlers.help_center import send_help
        await send_help(update, context)
        # Help panel is never auto-deleted
        return

    # ── قوانین ───────────────────────────────────────────────────────────
    if text == "قوانین" or text.startswith("قوانین "):
        parts = text.split(" ", 1)
        if len(parts) > 1 and is_admin:
            db.set_group_setting(chat_id, "rules_msg", parts[1].strip())
            schedule_delete(chat_id, msg)
            await _notify(context, chat_id, "✅ قوانین گروه ذخیره شد.")
        else:
            settings = db.get_group_settings(chat_id)
            rules    = settings.get("rules_msg", "")
            if rules:
                await context.bot.send_message(
                    chat_id,
                    f"📜 <b>قوانین گروه:</b>\n\n{rules}",
                    parse_mode="HTML",
                )
            else:
                await _notify(context, chat_id, "📭 قوانینی تنظیم نشده است.")
        return

    # ── حذف خودکار روشن ──────────────────────────────────────────────────
    if text == "حذف خودکار روشن":
        if not is_admin:
            return
        db.set_group_setting(chat_id, "auto_delete_bot", 1)
        # Setting is NOW on — so schedule both the command and the reply
        schedule_delete(chat_id, msg)
        await _notify(
            context, chat_id,
            "✅ <b>حذف خودکار روشن شد</b>\n"
            "پیام‌های دستوری و پاسخ‌های ربات ۳۰ ثانیه بعد از ارسال پاک می‌شوند.",
        )
        return

    # ── حذف خودکار خاموش ─────────────────────────────────────────────────
    if text == "حذف خودکار خاموش":
        if not is_admin:
            return
        db.set_group_setting(chat_id, "auto_delete_bot", 0)
        # Setting is NOW off — nothing gets deleted from this point
        await _notify(
            context, chat_id,
            "🔕 <b>حذف خودکار خاموش شد</b>\n"
            "از این لحظه هیچ پیامی حذف نمی‌شود.",
        )
        return

    # ── admin-only from here ──────────────────────────────────────────────
    if not is_admin:
        return

    # ── بن ───────────────────────────────────────────────────────────────
    if text in ("بن", "بن کردن"):
        target = _reply_target(msg)
        if not target:
            await _need_reply(context, chat_id)
            return
        if target.is_bot:
            return
        try:
            await context.bot.ban_chat_member(chat_id, target.id)
            db.add_to_ban_list(chat_id, target.id)
            db.reset_warns(chat_id, target.id)
        except TelegramError as e:
            await _notify(context, chat_id, f"⚠️ خطا: {e}")
            return
        schedule_delete(chat_id, msg)
        await _notify(context, chat_id, f"🚫 {user_mention(target)} بن شد.")
        return

    # ── رفع بن ───────────────────────────────────────────────────────────
    if text == "رفع بن":
        target = _reply_target(msg)
        if not target:
            await _need_reply(context, chat_id)
            return
        try:
            await context.bot.unban_chat_member(chat_id, target.id, only_if_banned=True)
            db.remove_from_ban_list(chat_id, target.id)
        except TelegramError as e:
            await _notify(context, chat_id, f"⚠️ خطا: {e}")
            return
        schedule_delete(chat_id, msg)
        await _notify(context, chat_id, f"✅ بن {user_mention(target)} رفع شد.")
        return

    # ── سکوت ─────────────────────────────────────────────────────────────
    if text in ("سکوت", "میوت", "ساکت"):
        target = _reply_target(msg)
        if not target:
            await _need_reply(context, chat_id)
            return
        if target.is_bot:
            return
        try:
            await context.bot.restrict_chat_member(chat_id, target.id, MUTE_PERMISSIONS)
            db.add_to_mute_list(chat_id, target.id)
        except TelegramError as e:
            await _notify(context, chat_id, f"⚠️ خطا: {e}")
            return
        schedule_delete(chat_id, msg)
        await _notify(context, chat_id, f"🔇 {user_mention(target)} ساکت شد.")
        return

    # ── رفع سکوت ─────────────────────────────────────────────────────────
    if text in ("رفع سکوت", "آنمیوت"):
        target = _reply_target(msg)
        if not target:
            await _need_reply(context, chat_id)
            return
        try:
            await context.bot.restrict_chat_member(chat_id, target.id, UNMUTE_PERMISSIONS)
            db.remove_from_mute_list(chat_id, target.id)
        except TelegramError as e:
            await _notify(context, chat_id, f"⚠️ خطا: {e}")
            return
        schedule_delete(chat_id, msg)
        await _notify(context, chat_id, f"🔊 سکوت {user_mention(target)} رفع شد.")
        return

    # ── اخراج ────────────────────────────────────────────────────────────
    if text == "اخراج":
        target = _reply_target(msg)
        if not target:
            await _need_reply(context, chat_id)
            return
        if target.is_bot:
            return
        try:
            await context.bot.ban_chat_member(chat_id, target.id)
            await context.bot.unban_chat_member(chat_id, target.id)
        except TelegramError as e:
            await _notify(context, chat_id, f"⚠️ خطا: {e}")
            return
        schedule_delete(chat_id, msg)
        await _notify(context, chat_id, f"👢 {user_mention(target)} اخراج شد.")
        return

    # ── اخطار ────────────────────────────────────────────────────────────
    if text in ("اخطار", "وارن"):
        target = _reply_target(msg)
        if not target:
            await _need_reply(context, chat_id)
            return
        if target.is_bot:
            return
        if db.is_in_whitelist(chat_id, target.id):
            await _notify(context, chat_id, f"ℹ️ {user_mention(target)} در وایت‌لیست است.")
            return
        from handlers.warns import _check_warn_limit
        count    = db.add_warn(chat_id, target.id)
        settings = db.get_group_settings(chat_id)
        max_warns = settings.get("max_warns", MAX_WARNS_DEFAULT)
        schedule_delete(chat_id, msg)
        banned = await _check_warn_limit(update, context, chat_id, target.id, target)
        if not banned:
            await _notify(context, chat_id, f"⚠️ اخطار {count}/{max_warns} به {user_mention(target)}")
        return

    # ── اخطار ریست ───────────────────────────────────────────────────────
    if text == "اخطار ریست":
        target = _reply_target(msg)
        if not target:
            await _need_reply(context, chat_id)
            return
        db.reset_warns(chat_id, target.id)
        schedule_delete(chat_id, msg)
        await _notify(context, chat_id, f"✅ اخطارهای {user_mention(target)} پاک شد.")
        return

    # ── اخطارها ──────────────────────────────────────────────────────────
    if text == "اخطارها":
        target    = _reply_target(msg) or user
        count     = db.get_warns(chat_id, target.id)
        settings  = db.get_group_settings(chat_id)
        max_warns = settings.get("max_warns", MAX_WARNS_DEFAULT)
        bar       = "🟥" * count + "⬜️" * max(0, max_warns - count)
        schedule_delete(chat_id, msg)
        await _notify(context, chat_id,
            f"📊 اخطارهای {user_mention(target)}:\n{bar}\n{count}/{max_warns}")
        return

    # ── پاکسازی ──────────────────────────────────────────────────────────
    if text == "پاکسازی":
        if not msg.reply_to_message:
            await _notify(context, chat_id, "❗ روی اولین پیامی که می‌خواهید پاک شود ریپلای کنید.")
            return
        from_id = msg.reply_to_message.message_id
        to_id   = msg.message_id
        deleted = 0
        for i in range(0, to_id - from_id + 1, 100):
            chunk = list(range(from_id + i, min(from_id + i + 100, to_id + 1)))
            try:
                await context.bot.delete_messages(chat_id, chunk)
                deleted += len(chunk)
            except TelegramError:
                for mid in chunk:
                    try:
                        await context.bot.delete_message(chat_id, mid)
                        deleted += 1
                    except Exception:
                        pass
        notice = await context.bot.send_message(chat_id, f"🗑 {deleted} پیام پاک شد.")
        await asyncio.sleep(5)
        try:
            await notice.delete()
        except Exception:
            pass
        return

    # ── ارتقا / تنزل ─────────────────────────────────────────────────────
    for fa_cmd, rank_key in (
        ("ارتقا مالک", "مالک"), ("ارتقا سودو", "سودو"),
        ("ارتقا ادمین", "ادمین"), ("ارتقا ویژه", "ویژه"),
    ):
        if text == fa_cmd:
            target = _reply_target(msg)
            if not target:
                await _need_reply(context, chat_id)
                return
            if target.is_bot:
                await _notify(context, chat_id, "❌ نمی‌توان به ربات رتبه داد.")
                return
            rank  = RANK_FA_MAP[rank_key]
            label = RANK_LABELS.get(rank, rank)
            db.set_rank(chat_id, target.id, rank)
            schedule_delete(chat_id, msg)
            await _notify(context, chat_id, f"✅ {user_mention(target)} به رتبه {label} ارتقا یافت.")
            return

    if text == "تنزل":
        target = _reply_target(msg)
        if not target:
            await _need_reply(context, chat_id)
            return
        db.set_rank(chat_id, target.id, None)
        schedule_delete(chat_id, msg)
        await _notify(context, chat_id, f"✅ رتبه {user_mention(target)} حذف شد.")
        return

    # ── لیست‌ها ───────────────────────────────────────────────────────────
    if text == "افزودن وایت":
        target = _reply_target(msg)
        if not target:
            await _need_reply(context, chat_id)
            return
        db.add_to_whitelist(chat_id, target.id)
        schedule_delete(chat_id, msg)
        await _notify(context, chat_id, f"✅ {user_mention(target)} به وایت‌لیست اضافه شد.")
        return

    if text == "حذف وایت":
        target = _reply_target(msg)
        if not target:
            await _need_reply(context, chat_id)
            return
        db.remove_from_whitelist(chat_id, target.id)
        schedule_delete(chat_id, msg)
        await _notify(context, chat_id, f"✅ {user_mention(target)} از وایت‌لیست حذف شد.")
        return

    if text == "افزودن بلک":
        target = _reply_target(msg)
        if not target:
            await _need_reply(context, chat_id)
            return
        db.add_to_blacklist(chat_id, target.id)
        schedule_delete(chat_id, msg)
        await _notify(context, chat_id, f"⛔ {user_mention(target)} به بلک‌لیست اضافه شد.")
        return

    if text == "حذف بلک":
        target = _reply_target(msg)
        if not target:
            await _need_reply(context, chat_id)
            return
        db.remove_from_blacklist(chat_id, target.id)
        schedule_delete(chat_id, msg)
        await _notify(context, chat_id, f"✅ {user_mention(target)} از بلک‌لیست حذف شد.")
        return

    if text == "افزودن کیل":
        target = _reply_target(msg)
        if not target:
            await _need_reply(context, chat_id)
            return
        db.add_to_kill_list(chat_id, target.id)
        try:
            await context.bot.ban_chat_member(chat_id, target.id)
            db.add_to_ban_list(chat_id, target.id)
        except TelegramError:
            pass
        schedule_delete(chat_id, msg)
        await _notify(context, chat_id, f"☠️ {user_mention(target)} به کیل‌لیست اضافه و بن شد.")
        return

    if text == "حذف کیل":
        target = _reply_target(msg)
        if not target:
            await _need_reply(context, chat_id)
            return
        db.remove_from_kill_list(chat_id, target.id)
        schedule_delete(chat_id, msg)
        await _notify(context, chat_id, f"✅ {user_mention(target)} از کیل‌لیست حذف شد.")
        return

    # ── خوشامد ───────────────────────────────────────────────────────────
    if text.startswith("خوشامد "):
        welcome_text = text[len("خوشامد "):].strip()
        db.set_group_setting(chat_id, "welcome_msg", welcome_text)
        schedule_delete(chat_id, msg)
        await _notify(context, chat_id, "✅ پیام خوشامد ذخیره شد.\n<code>{name}</code> = نام کاربر")
        return

    # ── قفل / باز کردن ───────────────────────────────────────────────────
    for prefix, enabling in (("قفل ", True), ("باز کردن ", False), ("آنلاک ", False)):
        if text.startswith(prefix):
            lock_fa   = text[len(prefix):].strip()
            lock_type = PERSIAN_LOCK_MAP.get(lock_fa)
            if not lock_type:
                keys = "، ".join(k for k in PERSIAN_LOCK_MAP if k != "کلمات بد")
                await _notify(context, chat_id, f"❌ نوع نامعتبر.\nانواع: {keys}")
                return
            db.set_lock(chat_id, lock_type, enabling)
            label  = LOCK_LABELS.get(lock_type, lock_type)
            status = "قفل شد 🔒" if enabling else "باز شد 🔓"
            schedule_delete(chat_id, msg)
            await _notify(context, chat_id, f"{label} {status}")
            return

    # ── کلمه بد ──────────────────────────────────────────────────────────
    if text.startswith("کلمه بد "):
        word = text[len("کلمه بد "):].strip().lower()
        db.add_bad_word(chat_id, word)
        schedule_delete(chat_id, msg)
        await _notify(context, chat_id, f"✅ «{word}» به کلمات ممنوع اضافه شد.")
        return

    if text.startswith("حذف کلمه بد "):
        word = text[len("حذف کلمه بد "):].strip().lower()
        db.remove_bad_word(chat_id, word)
        schedule_delete(chat_id, msg)
        await _notify(context, chat_id, f"✅ «{word}» از کلمات ممنوع حذف شد.")
        return

    # ── فیلتر ────────────────────────────────────────────────────────────
    if text.startswith("فیلتر "):
        word = text[len("فیلتر "):].strip().lower()
        db.add_filter_word(chat_id, word)
        schedule_delete(chat_id, msg)
        await _notify(context, chat_id, f"✅ «{word}» به فیلتر اضافه شد.")
        return

    if text.startswith("حذف فیلتر "):
        word = text[len("حذف فیلتر "):].strip().lower()
        db.remove_filter_word(chat_id, word)
        schedule_delete(chat_id, msg)
        await _notify(context, chat_id, f"✅ «{word}» از فیلتر حذف شد.")
        return


def get_handlers():
    return [
        MessageHandler(
            filters.TEXT & filters.Regex(TRIGGER_RE) & ~filters.COMMAND,
            handle_persian,
        )
    ]
