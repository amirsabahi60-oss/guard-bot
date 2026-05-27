from __future__ import annotations
import asyncio
from telegram import Update, ChatPermissions, Message
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from config import logger, DELETE_BOT_MESSAGES_AFTER


async def is_chat_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except TelegramError:
        return False


async def get_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return None
    if message.reply_to_message:
        return message.reply_to_message.from_user
    if context.args:
        try:
            user_id = int(context.args[0])
            member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
            return member.user
        except Exception:
            pass
    return None


async def safe_delete(message: Message):
    """Immediately delete a message (always — used for content violations)."""
    try:
        await message.delete()
    except TelegramError as e:
        logger.warning(f"Cannot delete message: {e}")


async def auto_delete(message: Message, delay: int = DELETE_BOT_MESSAGES_AFTER):
    """Sleep then delete. No-op if delay is 0 or negative."""
    if not delay or delay <= 0:
        return
    await asyncio.sleep(delay)
    await safe_delete(message)


def _check_autodel(chat_id: int) -> bool:
    """Return True if auto_delete_bot is enabled for this group."""
    try:
        from database import get_group_settings
        s = get_group_settings(chat_id)
        return bool(s.get("auto_delete_bot", 0))
    except Exception:
        return False


def schedule_delete(chat_id: int, message: Message, delay: int = DELETE_BOT_MESSAGES_AFTER):
    """
    Schedule deletion of `message` after `delay` seconds — but ONLY if
    auto_delete_bot is ON for this group.  Does nothing when it is OFF.
    Call this for:
      • user Persian command messages
      • bot reply/notification messages
    Do NOT call this for content-violation deletions (lock checks, spam) —
    those always use safe_delete() so they are removed immediately.
    """
    if _check_autodel(chat_id):
        asyncio.create_task(auto_delete(message, delay))


async def send_and_delete(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    parse_mode: str = "HTML",
    delay: int = DELETE_BOT_MESSAGES_AFTER,
    **kwargs,
):
    """
    Reply with text; schedule deletion of BOTH the bot reply AND the
    triggering command message if auto_delete_bot is ON.
    """
    chat_id = update.effective_chat.id
    msg = await update.effective_message.reply_text(text, parse_mode=parse_mode, **kwargs)
    if _check_autodel(chat_id):
        asyncio.create_task(auto_delete(msg, delay))
        if update.effective_message:
            asyncio.create_task(auto_delete(update.effective_message, delay))
    return msg


MUTE_PERMISSIONS = ChatPermissions(
    can_send_messages=False,
    can_send_audios=False,
    can_send_documents=False,
    can_send_photos=False,
    can_send_videos=False,
    can_send_video_notes=False,
    can_send_voice_notes=False,
    can_send_polls=False,
    can_send_other_messages=False,
    can_add_web_page_previews=False,
)

UNMUTE_PERMISSIONS = ChatPermissions(
    can_send_messages=True,
    can_send_audios=True,
    can_send_documents=True,
    can_send_photos=True,
    can_send_videos=True,
    can_send_video_notes=True,
    can_send_voice_notes=True,
    can_send_polls=True,
    can_send_other_messages=True,
    can_add_web_page_previews=True,
)


def user_mention(user) -> str:
    name = user.full_name or str(user.id)
    return f'<a href="tg://user?id={user.id}">{name}</a>'
