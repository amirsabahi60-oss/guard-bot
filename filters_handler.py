from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

import database as db
from utils.decorators import admin_only, group_only, error_handler
from utils.helpers import send_and_delete


@error_handler
@group_only
@admin_only()
async def add_bad_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await send_and_delete(update, context, "❗ مثال: /addbad فحش")
        return
    word = " ".join(context.args).lower().strip()
    chat_id = update.effective_chat.id
    db.add_bad_word(chat_id, word)
    await send_and_delete(update, context, f"✅ کلمه «{word}» به لیست کلمات بد اضافه شد.")


@error_handler
@group_only
@admin_only()
async def remove_bad_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await send_and_delete(update, context, "❗ مثال: /rmbad فحش")
        return
    word = " ".join(context.args).lower().strip()
    chat_id = update.effective_chat.id
    db.remove_bad_word(chat_id, word)
    await send_and_delete(update, context, f"✅ کلمه «{word}» از لیست کلمات بد حذف شد.")


@error_handler
@group_only
@admin_only()
async def list_bad_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    words = db.get_bad_words(chat_id)
    if not words:
        await send_and_delete(update, context, "📭 لیست کلمات بد خالی است.")
        return
    text = "🤬 <b>لیست کلمات بد:</b>\n\n" + "\n".join(f"• <code>{w}</code>" for w in sorted(words))
    await send_and_delete(update, context, text, parse_mode="HTML", delay=60)


@error_handler
@group_only
@admin_only()
async def add_filter_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await send_and_delete(update, context, "❗ مثال: /addfilter کلمه")
        return
    word = " ".join(context.args).lower().strip()
    chat_id = update.effective_chat.id
    db.add_filter_word(chat_id, word)
    await send_and_delete(update, context, f"✅ کلمه «{word}» به فیلتر اضافه شد.")


@error_handler
@group_only
@admin_only()
async def remove_filter_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await send_and_delete(update, context, "❗ مثال: /rmfilter کلمه")
        return
    word = " ".join(context.args).lower().strip()
    chat_id = update.effective_chat.id
    db.remove_filter_word(chat_id, word)
    await send_and_delete(update, context, f"✅ کلمه «{word}» از فیلتر حذف شد.")


@error_handler
@group_only
@admin_only()
async def list_filter_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    words = db.get_filter_words(chat_id)
    if not words:
        await send_and_delete(update, context, "📭 لیست فیلتر خالی است.")
        return
    text = "🚫 <b>لیست کلمات فیلتر:</b>\n\n" + "\n".join(f"• <code>{w}</code>" for w in sorted(words))
    await send_and_delete(update, context, text, parse_mode="HTML", delay=60)


def get_handlers():
    return [
        CommandHandler("addbad", add_bad_word),
        CommandHandler("rmbad", remove_bad_word),
        CommandHandler("badwords", list_bad_words),
        CommandHandler("addfilter", add_filter_word),
        CommandHandler("rmfilter", remove_filter_word),
        CommandHandler("filters", list_filter_words),
    ]
