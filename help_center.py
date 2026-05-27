"""
Persian inline help center.
Triggered by: راهنما | کمک | help | /help
All callbacks use hlp_ prefix.
"""
from __future__ import annotations
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from telegram.error import TelegramError

from config import logger
from utils.decorators import error_handler
from utils.helpers import safe_delete, auto_delete


# ══════════════════════════════════════════════════════════════════════════
#  Keyboards
# ══════════════════════════════════════════════════════════════════════════

def _help_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🛡 مدیریت گروه",    callback_data="hlp_moderation"),
            InlineKeyboardButton("🔒 آموزش قفل‌ها",   callback_data="hlp_locks"),
        ],
        [
            InlineKeyboardButton("⚠️ سیستم اخطار",   callback_data="hlp_warns"),
            InlineKeyboardButton("👮 مدیریت کاربران", callback_data="hlp_users"),
        ],
        [
            InlineKeyboardButton("📜 قوانین",          callback_data="hlp_rules"),
            InlineKeyboardButton("⚙️ تنظیمات",        callback_data="hlp_settings"),
        ],
        [
            InlineKeyboardButton("📊 آمار و گزارشات", callback_data="hlp_stats"),
            InlineKeyboardButton("🤖 درباره ربات",    callback_data="hlp_about"),
        ],
        [InlineKeyboardButton("❌ بستن",              callback_data="hlp_close")],
    ])


def _back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 بازگشت به راهنما",  callback_data="hlp_main")],
        [InlineKeyboardButton("❌ بستن",               callback_data="hlp_close")],
    ])


# ══════════════════════════════════════════════════════════════════════════
#  Content pages
# ══════════════════════════════════════════════════════════════════════════

SEP = "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"


def _main_text() -> str:
    return (
        "🤖 <b>مرکز راهنمای ربات گارد</b>\n\n"
        "یک بخش را انتخاب کنید:\n\n"
        "🛡 <b>مدیریت گروه</b>\n"
        "   بن، سکوت، اخراج و پاکسازی\n\n"
        "🔒 <b>آموزش قفل‌ها</b>\n"
        "   محدودسازی محتوای گروه\n\n"
        "⚠️ <b>سیستم اخطار</b>\n"
        "   اخطار و بن خودکار\n\n"
        "👮 <b>مدیریت کاربران</b>\n"
        "   رتبه‌بندی و لیست‌های کاربری\n\n"
        "📜 <b>قوانین</b>\n"
        "   تنظیم و نمایش قوانین گروه\n\n"
        "⚙️ <b>تنظیمات</b>\n"
        "   خوشامد، فیلترها و سایر موارد\n\n"
        "📊 <b>آمار و گزارشات</b>\n"
        "   وضعیت گروه و سیستم گزارش\n\n"
        "🤖 <b>درباره ربات</b>\n"
        "   اطلاعات و راهنمای شروع"
    )


def _moderation_text() -> str:
    return (
        "🛡 <b>مدیریت گروه</b>\n\n"
        "برای استفاده از این دستورات، روی پیام کاربر <b>ریپلای</b> کنید:\n\n"

        f"{SEP}\n"
        "🚫 <b>بن کردن کاربر</b>\n"
        "کاربر از گروه حذف و دسترسی او مسدود می‌شود.\n\n"
        "<code>بن</code>  یا  <code>بن کردن</code>\n\n"

        f"{SEP}\n"
        "✅ <b>رفع بن</b>\n"
        "کاربر دوباره اجازه ورود به گروه دارد.\n\n"
        "<code>رفع بن</code>\n\n"

        f"{SEP}\n"
        "🔇 <b>سکوت کردن</b>\n"
        "کاربر در گروه می‌ماند ولی نمی‌تواند پیام بفرستد.\n\n"
        "<code>سکوت</code>  یا  <code>میوت</code>  یا  <code>ساکت</code>\n\n"

        f"{SEP}\n"
        "🔊 <b>رفع سکوت</b>\n"
        "دسترسی ارسال پیام به کاربر برگردانده می‌شود.\n\n"
        "<code>رفع سکوت</code>\n\n"

        f"{SEP}\n"
        "🗑 <b>پاکسازی پیام‌ها</b>\n"
        "روی اولین پیامی که می‌خواهید پاک شود ریپلای کنید،\n"
        "سپس بنویسید:\n\n"
        "<code>پاکسازی</code>\n\n"
        "تمام پیام‌ها از آن نقطه تا آخر حذف می‌شوند.\n\n"

        f"{SEP}\n"
        "💡 <b>نکته:</b>\n"
        "ادمین‌ها و کاربران وایت‌لیست از این محدودیت‌ها مستثنی هستند."
    )


def _locks_text() -> str:
    return (
        "🔒 <b>آموزش قفل‌ها</b>\n\n"
        "با قفل‌ها می‌توانید انواع خاصی از محتوا را در گروه ممنوع کنید.\n"
        "مدیریت بصری قفل‌ها: <b>پنل ← مدیریت ← قفل‌ها</b>\n\n"

        f"{SEP}\n"
        "🔗 <b>قفل لینک</b>\n"
        "ارسال هر نوع لینک اینترنتی ممنوع می‌شود.\n"
        "روشن: <code>قفل لینک</code>  •  خاموش: <code>باز کردن لینک</code>\n\n"

        "👤 <b>قفل یوزرنیم</b>\n"
        "ذکر آیدی کاربران و کانال‌ها ممنوع می‌شود.\n"
        "روشن: <code>قفل یوزرنیم</code>  •  خاموش: <code>باز کردن یوزرنیم</code>\n\n"

        "↩️ <b>قفل فوروارد</b>\n"
        "پیام‌های فوروارد‌شده از هر جایی حذف می‌شوند.\n"
        "روشن: <code>قفل فوروارد</code>  •  خاموش: <code>باز کردن فوروارد</code>\n\n"

        "🎭 <b>قفل استیکر</b>\n"
        "ارسال استیکر ممنوع می‌شود.\n"
        "روشن: <code>قفل استیکر</code>  •  خاموش: <code>باز کردن استیکر</code>\n\n"

        "🎬 <b>قفل گیف</b>\n"
        "ارسال انیمیشن و گیف ممنوع می‌شود.\n"
        "روشن: <code>قفل گیف</code>  •  خاموش: <code>باز کردن گیف</code>\n\n"

        "🖼 <b>قفل عکس</b>\n"
        "ارسال تصویر ممنوع می‌شود.\n"
        "روشن: <code>قفل عکس</code>  •  خاموش: <code>باز کردن عکس</code>\n\n"

        "📹 <b>قفل ویدیو</b>\n"
        "ارسال ویدیو ممنوع می‌شود.\n"
        "روشن: <code>قفل ویدیو</code>  •  خاموش: <code>باز کردن ویدیو</code>\n\n"

        "🎤 <b>قفل ویس</b>\n"
        "ارسال پیام صوتی ممنوع می‌شود.\n"
        "روشن: <code>قفل ویس</code>  •  خاموش: <code>باز کردن ویس</code>\n\n"

        "📁 <b>قفل فایل</b>\n"
        "ارسال هر نوع فایل ممنوع می‌شود.\n"
        "روشن: <code>قفل فایل</code>  •  خاموش: <code>باز کردن فایل</code>\n\n"

        "🤬 <b>قفل کلمات بد</b>\n"
        "پیام‌های حاوی کلمات نامناسب خودکار حذف می‌شوند.\n"
        "روشن: <code>قفل کلمه بد</code>  •  خاموش: <code>باز کردن کلمه بد</code>\n\n"

        f"{SEP}\n"
        "💡 کاربران وایت‌لیست از همه قفل‌ها معاف هستند."
    )


def _warns_text() -> str:
    return (
        "⚠️ <b>سیستم اخطار</b>\n\n"
        "سیستم اخطار ابزار اصلی کنترل رفتار ناشایست در گروه است.\n\n"

        f"{SEP}\n"
        "📌 <b>دادن اخطار به کاربر</b>\n"
        "روی پیام کاربر ریپلای کنید و بنویسید:\n\n"
        "<code>اخطار</code>  یا  <code>وارن</code>\n\n"

        f"{SEP}\n"
        "📊 <b>مشاهده اخطارهای کاربر</b>\n"
        "روی پیام کاربر ریپلای کنید:\n\n"
        "<code>اخطارها</code>\n\n"

        f"{SEP}\n"
        "🔄 <b>پاک کردن اخطارها</b>\n"
        "روی پیام کاربر ریپلای کنید:\n\n"
        "<code>اخطار ریست</code>\n\n"

        f"{SEP}\n"
        "🤖 <b>بن خودکار</b>\n"
        "وقتی کاربر به سقف اخطار برسد، ربات به‌طور خودکار او را بن می‌کند.\n"
        "سقف پیش‌فرض: ۳ اخطار\n\n"

        f"{SEP}\n"
        "🔒 <b>اخطار بر اساس قفل</b>\n"
        "می‌توانید تعداد دفعاتی که کاربر باید قفل را نقض کند تا اخطار بگیرد تنظیم کنید:\n\n"
        "مثال — اخطار بعد از ۲ بار ارسال لینک:\n"
        "<code>تنظیم اخطار لینک ۲</code>\n\n"

        f"{SEP}\n"
        "✅ <b>معافیت از اخطار</b>\n"
        "کاربرانی که در وایت‌لیست هستند هرگز اخطار نمی‌گیرند.\n"
        "برای افزودن به وایت‌لیست: روی پیام کاربر ریپلای کنید و بنویسید:\n"
        "<code>افزودن وایت</code>"
    )


def _users_text() -> str:
    return (
        "👮 <b>مدیریت کاربران</b>\n\n"

        f"{SEP}\n"
        "🎖 <b>رتبه‌بندی ادمین‌ها</b>\n\n"
        "روی پیام کاربر ریپلای کنید و یکی از این دستورات را بنویسید:\n\n"
        "👑 <code>ارتقا مالک</code> — بالاترین سطح دسترسی\n"
        "⚡ <code>ارتقا سودو</code> — سوپرادمین\n"
        "🛡 <code>ارتقا ادمین</code> — ادمین معمولی\n"
        "⭐ <code>ارتقا ویژه</code> — کاربر ویژه\n"
        "🗑 <code>تنزل</code> — حذف رتبه\n\n"

        f"{SEP}\n"
        "📋 <b>لیست‌های کاربری</b>\n\n"
        "✅ <b>وایت‌لیست</b> — کاربران مورد اعتماد\n"
        "این کاربران از قفل‌ها و اخطارها معاف هستند.\n"
        "افزودن: <code>افزودن وایت</code>  (ریپلای)\n"
        "حذف: <code>حذف وایت</code>  (ریپلای)\n\n"

        "⛔ <b>بلک‌لیست</b> — کاربران ممنوع\n"
        "این کاربران با ورود به گروه بن می‌شوند.\n"
        "افزودن: <code>افزودن بلک</code>  (ریپلای)\n"
        "حذف: <code>حذف بلک</code>  (ریپلای)\n\n"

        "☠️ <b>کیل‌لیست</b> — بن فوری دائمی\n"
        "این کاربران در هر گروهی که ربات باشد فوری بن می‌شوند.\n"
        "افزودن: <code>افزودن کیل</code>  (ریپلای)\n\n"

        "🔇 <b>لیست سکوت</b> — مشاهده سکوت‌های فعال\n"
        "🚫 <b>لیست بن</b> — مشاهده بن‌های فعال\n\n"

        f"{SEP}\n"
        "💡 مشاهده همه لیست‌ها: <b>پنل ← کاربران</b>"
    )


def _rules_text() -> str:
    return (
        "📜 <b>قوانین گروه</b>\n\n"

        f"{SEP}\n"
        "⚙️ <b>تنظیم قوانین (ادمین)</b>\n\n"
        "بنویسید:\n"
        "<code>قوانین [متن قوانین]</code>\n\n"
        "نمونه:\n"
        "<code>قوانین\n"
        "۱. احترام را رعایت کنید\n"
        "۲. تبلیغ ممنوع است\n"
        "۳. با فارسی صحبت کنید\n"
        "۴. موضوع گروه را رعایت کنید</code>\n\n"

        f"{SEP}\n"
        "👁 <b>مشاهده قوانین</b>\n\n"
        "همه اعضای گروه می‌توانند بنویسند:\n"
        "<code>قوانین</code>\n\n"
        "یا از منو:\n"
        "<b>پنل ← قوانین</b>\n\n"

        f"{SEP}\n"
        "💡 <b>نکته:</b>\n"
        "قوانین به‌صورت دائمی ذخیره می‌شوند و تا زمانی که تغییرشان ندهید، پابرجا می‌مانند."
    )


def _settings_text() -> str:
    return (
        "⚙️ <b>تنظیمات ربات</b>\n\n"

        f"{SEP}\n"
        "💬 <b>پیام خوشامدگویی</b>\n\n"
        "بنویسید:\n"
        "<code>خوشامد [متن دلخواه]</code>\n\n"
        "می‌توانید از این متغیرها استفاده کنید:\n"
        "• <code>{name}</code> — نام کاربر جدید\n"
        "• <code>{username}</code> — آیدی کاربر\n\n"
        "نمونه:\n"
        "<code>خوشامد سلام {name} عزیز! 👋\n"
        "به گروه ما خوش آمدی. حتماً قوانین را بخوان.</code>\n\n"

        f"{SEP}\n"
        "🤬 <b>کلمات ممنوع</b>\n\n"
        "پیام‌های حاوی این کلمات خودکار حذف می‌شوند:\n\n"
        "افزودن: <code>کلمه بد [کلمه]</code>\n"
        "حذف: <code>حذف کلمه بد [کلمه]</code>\n\n"

        f"{SEP}\n"
        "🚫 <b>کلمات فیلتر</b>\n\n"
        "مشابه کلمات ممنوع — برای فیلتر دقیق‌تر:\n\n"
        "افزودن: <code>فیلتر [کلمه]</code>\n"
        "حذف: <code>حذف فیلتر [کلمه]</code>\n\n"

        f"{SEP}\n"
        "🔧 <b>سایر تنظیمات</b>\n\n"
        "از طریق پنل قابل تغییر هستند:\n"
        "<b>پنل ← تنظیمات</b>\n\n"
        "• روشن یا خاموش کردن خوشامدگویی\n"
        "• روشن یا خاموش کردن حذف خودکار پیام‌های ربات"
    )


def _stats_text() -> str:
    return (
        "📊 <b>آمار و گزارشات</b>\n\n"

        f"{SEP}\n"
        "📈 <b>آمار گروه</b>\n\n"
        "برای مشاهده آمار کامل و لحظه‌ای گروه:\n"
        "<b>پنل ← آمار</b>\n\n"
        "اطلاعاتی که نمایش داده می‌شود:\n\n"
        "🔇 تعداد کاربران ساکت‌شده\n"
        "🚫 تعداد کاربران بن‌شده\n"
        "✅ تعداد کاربران وایت‌لیست\n"
        "⛔ تعداد کاربران بلک‌لیست\n"
        "☠️ تعداد کاربران کیل‌لیست\n"
        "🤬 تعداد کلمات ممنوع\n"
        "🚫 تعداد کلمات فیلتر\n"
        "🔒 تعداد قفل‌های فعال\n\n"

        f"{SEP}\n"
        "🚨 <b>سیستم گزارش</b>\n\n"
        "هر عضو گروه می‌تواند روی یک پیام ریپلای کند و بنویسد:\n"
        "<code>گزارش</code>\n\n"
        "ربات به‌صورت محرمانه به همه ادمین‌ها اطلاع می‌دهد.\n"
        "ادمین‌ها می‌توانند مستقیماً از پیام اطلاع‌رسانی اقدام کنند.\n\n"
        "⏱ هر کاربر هر ۲ دقیقه یک‌بار می‌تواند گزارش بدهد."
    )


def _about_text() -> str:
    return (
        "🤖 <b>درباره ربات گارد</b>\n\n"
        "ربات گارد یک دستیار مدیریت حرفه‌ای برای گروه‌های تلگرام است.\n\n"

        f"{SEP}\n"
        "✨ <b>امکانات ربات</b>\n\n"
        "🛡 مدیریت کامل گروه — بن، سکوت، اخراج\n"
        "🔒 جلوگیری از انتشار محتوای ناخواسته\n"
        "⚠️ سیستم اخطار با بن خودکار\n"
        "👮 سطح‌بندی ادمین‌ها و کاربران ویژه\n"
        "📋 مدیریت لیست سیاه و سفید\n"
        "🚨 گزارش‌گیری ناشناس توسط اعضا\n"
        "💬 پیام خوشامد قابل شخصی‌سازی\n"
        "📜 قوانین گروه قابل تنظیم\n"
        "🚫 فیلتر هوشمند کلمات\n"
        "📱 پنل مدیریت با منوی فارسی\n\n"

        f"{SEP}\n"
        "📖 <b>نحوه شروع</b>\n\n"
        "۱. ربات را به گروه اضافه کنید\n"
        "۲. ربات را ادمین کنید و همه دسترسی‌ها را فعال کنید\n"
        "۳. در گروه بنویسید: <b>پنل</b>\n"
        "۴. از منوی مدیریت همه چیز را تنظیم کنید\n\n"

        f"{SEP}\n"
        "💡 برای مشاهده راهنمای هر بخش از منوی بالا استفاده کنید."
    )


# ══════════════════════════════════════════════════════════════════════════
#  Entry point
# ══════════════════════════════════════════════════════════════════════════

async def send_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    if not msg or not chat:
        return

    await context.bot.send_message(
        chat.id,
        _main_text(),
        parse_mode="HTML",
        reply_markup=_help_main_kb(),
    )


@error_handler
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_help(update, context)


# ══════════════════════════════════════════════════════════════════════════
#  Callback router
# ══════════════════════════════════════════════════════════════════════════

_PAGE_MAP: dict[str, tuple[str, bool]] = {
    "hlp_main":       (_main_text(),       True),
    "hlp_moderation": (_moderation_text(), False),
    "hlp_locks":      (_locks_text(),      False),
    "hlp_warns":      (_warns_text(),      False),
    "hlp_users":      (_users_text(),      False),
    "hlp_rules":      (_rules_text(),      False),
    "hlp_settings":   (_settings_text(),   False),
    "hlp_stats":      (_stats_text(),      False),
    "hlp_about":      (_about_text(),      False),
}


@error_handler
async def handle_help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return

    data = query.data or ""
    await query.answer()

    if data == "hlp_close":
        try:
            await query.message.delete()
        except TelegramError:
            pass
        return

    page = _PAGE_MAP.get(data)
    if page is None:
        return

    text, use_main_kb = page
    kb = _help_main_kb() if use_main_kb else _back_kb()

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)


def get_handlers():
    return [
        CommandHandler("help", help_cmd),
        CallbackQueryHandler(handle_help_callback, pattern=r"^hlp_"),
    ]
