"""
Main entry point — clean handler registration with explicit group priorities.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from telegram import Update
from telegram.ext import ApplicationBuilder

from config import TELEGRAM_BOT_TOKEN, logger
from database import init_db

import menus
import admin
import warns
import locks
import filters_handler
import antispam
import welcome
import lists
import persian_commands
import report
import help_center


async def global_error_handler(update: object, context) -> None:
    logger.error(f"Unhandled exception: {context.error}", exc_info=context.error)


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        logger.critical("TELEGRAM_BOT_TOKEN تنظیم نشده است!")
        sys.exit(1)

    init_db()
    logger.info("دیتابیس آماده شد.")

    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .concurrent_updates(False)
        .build()
    )

    app.add_error_handler(global_error_handler)

    for h in menus.get_handlers():
        app.add_handler(h, group=0)

    for h in admin.get_handlers():
        app.add_handler(h, group=0)

    for h in warns.get_handlers():
        app.add_handler(h, group=0)

    for h in filters_handler.get_handlers():
        app.add_handler(h, group=0)

    for h in lists.get_handlers():
        app.add_handler(h, group=0)

    for h in welcome.get_handlers():
        app.add_handler(h, group=0)

    for h in report.get_handlers():
        app.add_handler(h, group=0)

    for h in help_center.get_handlers():
        app.add_handler(h, group=0)

    for h in locks.get_command_handlers():
        app.add_handler(h, group=0)

    for h in persian_commands.get_handlers():
        app.add_handler(h, group=1)

    app.add_handler(locks.get_message_handler(), group=2)

    for h in antispam.get_handlers():
        app.add_handler(h, group=3)

    logger.info("✅ ربات گارد پیشرفته آماده است.")
    print("✅ ربات گارد پیشرفته در حال اجرا...")

    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
