"""
Main entry point — clean handler registration with explicit group priorities.

Group 0 (default): Slash commands + CallbackQueryHandlers
Group 1:           Persian text triggers (priority over content checks)
Group 2:           Lock content check (runs on every non-command message)
Group 3:           Anti-spam / flood check
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters

from config import TELEGRAM_BOT_TOKEN, logger
from database import init_db

import handlers.menus           as menus
import handlers.admin           as admin
import handlers.warns           as warns
import handlers.locks           as locks
import handlers.filters_handler as filters_handler
import handlers.antispam        as antispam
import handlers.welcome         as welcome
import handlers.lists           as lists
import handlers.persian_commands as persian_commands
import handlers.report          as report
import handlers.help_center     as help_center


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
        .concurrent_updates(True)
        .build()
    )

    app.add_error_handler(global_error_handler)

    # ── Group 0: Commands & callbacks ────────────────────────────────────
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

    # ── Group 1: Persian text triggers (priority) ─────────────────────────
    for h in persian_commands.get_handlers():
        app.add_handler(h, group=1)

    # ── Group 2: Lock content check ───────────────────────────────────────
    app.add_handler(locks.get_message_handler(), group=2)

    # ── Group 3: Anti-spam / flood ────────────────────────────────────────
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
