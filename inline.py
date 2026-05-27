from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import LOCK_TYPES, LOCK_LABELS


def persian_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🛡 مدیریت",    callback_data="pmenu_moderation"),
            InlineKeyboardButton("⚙️ تنظیمات",  callback_data="panel_settings"),
        ],
        [
            InlineKeyboardButton("👮 کاربران",   callback_data="pmenu_users"),
            InlineKeyboardButton("📜 قوانین",    callback_data="pmenu_rules"),
        ],
        [
            InlineKeyboardButton("📊 آمار",      callback_data="panel_stats"),
            InlineKeyboardButton("❓ راهنما",    callback_data="hlp_main"),
        ],
    ])


def moderation_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔒 قفل‌ها", callback_data="panel_locks"),
            InlineKeyboardButton("🚫 فیلترها", callback_data="panel_filters"),
        ],
        [
            InlineKeyboardButton("⚠️ اخطارها", callback_data="pmenu_warns_info"),
            InlineKeyboardButton("🗑 پاکسازی", callback_data="pmenu_purge_info"),
        ],
        [InlineKeyboardButton("🔙 برگشت", callback_data="pmenu_main")],
    ])


def users_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔇 لیست سکوت", callback_data="list_mute"),
            InlineKeyboardButton("🚫 لیست بن", callback_data="list_ban"),
        ],
        [
            InlineKeyboardButton("✅ وایت‌لیست", callback_data="list_white"),
            InlineKeyboardButton("⛔ بلک‌لیست", callback_data="list_black"),
        ],
        [InlineKeyboardButton("☠️ کیل‌لیست", callback_data="list_kill")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="pmenu_main")],
    ])


def main_panel_keyboard() -> InlineKeyboardMarkup:
    return persian_main_menu()


def locks_keyboard(locks: dict) -> InlineKeyboardMarkup:
    rows = []
    items = list(LOCK_TYPES)
    for i in range(0, len(items), 2):
        row = []
        for lt in items[i:i+2]:
            label = LOCK_LABELS.get(lt, lt)
            status = "✅" if locks.get(lt, {}).get("enabled") else "❌"
            row.append(InlineKeyboardButton(
                f"{status} {label}",
                callback_data=f"lock_toggle_{lt}"
            ))
        rows.append(row)
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="pmenu_moderation")])
    return InlineKeyboardMarkup(rows)


def settings_keyboard(settings: dict) -> InlineKeyboardMarkup:
    welcome   = "✅" if settings.get("welcome_enabled") else "❌"
    auto_del  = "🟢 روشن" if settings.get("auto_delete_bot") else "🔴 خاموش"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{welcome} خوشامدگویی", callback_data="setting_toggle_welcome")],
        [InlineKeyboardButton(f"🗑 حذف خودکار اعلان‌ها: {auto_del}", callback_data="setting_toggle_autodel")],
        [InlineKeyboardButton("✏️ ویرایش پیام خوشامد", callback_data="setting_edit_welcome")],
        [InlineKeyboardButton("📜 ویرایش قوانین", callback_data="setting_edit_rules")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="pmenu_main")],
    ])


def filters_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤬 کلمات بد", callback_data="filter_badwords")],
        [InlineKeyboardButton("🚫 کلمات فیلتر", callback_data="filter_words")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="pmenu_moderation")],
    ])


def lists_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔇 لیست سکوت", callback_data="list_mute"),
            InlineKeyboardButton("🚫 لیست بن", callback_data="list_ban"),
        ],
        [
            InlineKeyboardButton("✅ وایت‌لیست", callback_data="list_white"),
            InlineKeyboardButton("⛔ بلک‌لیست", callback_data="list_black"),
        ],
        [InlineKeyboardButton("💀 کیل‌لیست", callback_data="list_kill")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="pmenu_main")],
    ])


def back_to_panel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 برگشت به منو", callback_data="pmenu_main")]
    ])


def back_to_moderation() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 برگشت", callback_data="pmenu_moderation")]
    ])


def confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ بله", callback_data=f"confirm_{action}"),
            InlineKeyboardButton("❌ خیر", callback_data="pmenu_main"),
        ]
    ])
