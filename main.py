import sys
import os
import types
import importlib

sys.path.insert(0, os.path.dirname(__file__))


def make_package(name, modules):
    package = types.ModuleType(name)
    package.__path__ = []
    sys.modules[name] = package

    for mod in modules:
        module = importlib.import_module(mod)
        sys.modules[f"{name}.{mod}"] = module
        setattr(package, mod, module)


make_package("utils", ["decorators", "helpers"])
make_package("keyboards", ["inline"])
make_package("handlers", [
    "menus",
    "admin",
    "warns",
    "locks",
    "filters_handler",
    "antispam",
    "welcome",
    "lists",
    "persian_commands",
    "report",
    "help_center",
])

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


def main():
    init_db()

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).concurrent_updates(False).build()
    app.add_error_handler(global_error_handler)

    for module in [menus, admin, warns, filters_handler, lists, welcome, report, help_center]:
        for h in module.get_handlers():
            app.add_handler(h, group=0)

    for h in locks.get_command_handlers():
        app.add_handler(h, group=0)

    for h in persian_commands.get_handlers():
        app.add_handler(h, group=1)

    app.add_handler(locks.get_message_handler(), group=2)

    for h in antispam.get_handlers():
        app.add_handler(h, group=3)

    print("Bot Started")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
