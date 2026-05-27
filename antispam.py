from __future__ import annotations
import asyncio
import time
from collections import defaultdict, deque
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from telegram.error import TelegramError

import database as db
from config import FLOOD_LIMIT, FLOOD_WINDOW, FLOOD_MUTE_DURATION, logger
from utils.helpers import safe_delete, user_mention, MUTE_PERMISSIONS, auto_delete

_flood_tracker: dict[tuple, deque] = defaultdict(lambda: deque())
_last_messages: dict[tuple, str] = {}
_repeat_count: dict[tuple, int] = defaultdict(int)
_muted_flood: set[tuple] = set()


async def check_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message or not update.effective_chat or not update.effective_user:
        return

    chat_id = update.effective_chat.id
    user = update.effective_user
    user_id = user.id

    if db.is_in_whitelist(chat_id, user_id):
        return

    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.status in ("administrator", "creator"):
            return
    except TelegramError:
        return

    locks = db.get_locks(chat_id)
    if not locks.get("spam", {}).get("enabled"):
        return

    key = (chat_id, user_id)
    now = time.time()

    timestamps = _flood_tracker[key]
    timestamps.append(now)
    while timestamps and now - timestamps[0] > FLOOD_WINDOW:
        timestamps.popleft()

    if key in _muted_flood:
        await safe_delete(message)
        return

    if len(timestamps) >= FLOOD_LIMIT:
        _muted_flood.add(key)
        try:
            await safe_delete(message)
            await context.bot.restrict_chat_member(
                chat_id, user_id, MUTE_PERMISSIONS
            )
            db.add_to_mute_list(chat_id, user_id)
            msg = await context.bot.send_message(
                chat_id,
                f"🚫 {user_mention(user)} به دلیل فلود برای {FLOOD_MUTE_DURATION // 60} دقیقه ساکت شد.",
                parse_mode="HTML"
            )
            asyncio.create_task(auto_delete(msg))
            asyncio.create_task(_unmute_after(context, chat_id, user_id, FLOOD_MUTE_DURATION, key))
        except TelegramError as e:
            logger.error(f"Flood mute error: {e}")
            _muted_flood.discard(key)
        return

    if message.text:
        last = _last_messages.get(key, "")
        if message.text == last:
            _repeat_count[key] += 1
            if _repeat_count[key] >= 3:
                await safe_delete(message)
                msg = await context.bot.send_message(
                    chat_id,
                    f"⚠️ {user_mention(user)} — پیام تکراری ممنوع است.",
                    parse_mode="HTML"
                )
                asyncio.create_task(auto_delete(msg))
                return
        else:
            _repeat_count[key] = 0
        _last_messages[key] = message.text


async def _unmute_after(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int, delay: int, key: tuple):
    await asyncio.sleep(delay)
    from utils.helpers import UNMUTE_PERMISSIONS
    try:
        await context.bot.restrict_chat_member(chat_id, user_id, UNMUTE_PERMISSIONS)
        db.remove_from_mute_list(chat_id, user_id)
    except TelegramError as e:
        logger.error(f"Auto-unmute error: {e}")
    finally:
        _muted_flood.discard(key)


def get_handlers():
    return [
        MessageHandler(filters.ALL & ~filters.COMMAND, check_spam),
    ]
