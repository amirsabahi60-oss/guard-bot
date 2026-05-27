from __future__ import annotations
import functools
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from config import logger, RANK_HIERARCHY, RANK_OWNER, RANK_SUDO, RANK_ADMIN


def admin_only(min_rank: str = RANK_ADMIN):
    """Decorator: only allow users who are TG admins or have a rank >= min_rank."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            if not update.effective_user or not update.effective_chat:
                return
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id

            try:
                member = await context.bot.get_chat_member(chat_id, user_id)
                is_tg_admin = member.status in ("administrator", "creator")
            except TelegramError:
                is_tg_admin = False

            if is_tg_admin:
                return await func(update, context, *args, **kwargs)

            from database import get_rank
            rank = get_rank(chat_id, user_id)
            if rank and RANK_HIERARCHY.index(rank) <= RANK_HIERARCHY.index(min_rank):
                return await func(update, context, *args, **kwargs)

            await update.message.reply_text("❌ این دستور فقط برای ادمین‌ها است.")
        return wrapper
    return decorator


def owner_only(func):
    """Decorator: only allow group creator or bot owner rank."""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if not update.effective_user or not update.effective_chat:
            return
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            is_creator = member.status == "creator"
        except TelegramError:
            is_creator = False

        if is_creator:
            return await func(update, context, *args, **kwargs)

        from database import get_rank
        rank = get_rank(chat_id, user_id)
        if rank == RANK_OWNER or rank == RANK_SUDO:
            return await func(update, context, *args, **kwargs)

        await update.message.reply_text("❌ این دستور فقط برای مالک گروه است.")
    return wrapper


def group_only(func):
    """Decorator: only allow in groups/supergroups."""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_chat and update.effective_chat.type in ("group", "supergroup"):
            return await func(update, context, *args, **kwargs)
        await update.message.reply_text("❌ این دستور فقط در گروه کار می‌کند.")
    return wrapper


def error_handler(func):
    """Decorator: catch and log exceptions."""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        try:
            return await func(update, context, *args, **kwargs)
        except TelegramError as e:
            logger.error(f"TelegramError in {func.__name__}: {e}")
            if update.effective_message:
                await update.effective_message.reply_text(f"⚠️ خطا: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error in {func.__name__}: {e}")
    return wrapper
