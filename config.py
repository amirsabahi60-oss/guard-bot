import os
import logging

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

DB_PATH = "bot.db"

MAX_WARNS_DEFAULT = 3

FLOOD_LIMIT = 5
FLOOD_WINDOW = 5
FLOOD_MUTE_DURATION = 300

DELETE_BOT_MESSAGES_AFTER = 30

LOCK_TYPES = [
    "link",
    "username",
    "forward",
    "sticker",
    "gif",
    "photo",
    "video",
    "voice",
    "file",
    "spam",
    "badwords",
]

LOCK_LABELS = {
    "link": "🔗 لینک",
    "username": "👤 یوزرنیم",
    "forward": "↪️ فوروارد",
    "sticker": "🎭 استیکر",
    "gif": "🎬 گیف",
    "photo": "🖼 عکس",
    "video": "📹 ویدیو",
    "voice": "🎤 ویس",
    "file": "📁 فایل",
    "spam": "🚫 اسپم",
    "badwords": "🤬 کلمات بد",
}

RANK_OWNER = "owner"
RANK_SUDO = "sudo"
RANK_ADMIN = "admin"
RANK_VIP = "vip"

RANK_LABELS = {
    RANK_OWNER: "👑 مالک",
    RANK_SUDO: "⚡ سودو",
    RANK_ADMIN: "🛡 ادمین",
    RANK_VIP: "💎 ویآیپی",
}

RANK_HIERARCHY = [RANK_OWNER, RANK_SUDO, RANK_ADMIN, RANK_VIP]

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)
