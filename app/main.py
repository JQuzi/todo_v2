import asyncio
import logging
import os
import sys

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

if __package__ is None or __package__ == "":
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

load_dotenv()

from app.config import DB_PATH, REMINDER_POLL_SECONDS  # noqa: E402
from app import db as dbm  # noqa: E402
from app.handlers import routers  # noqa: E402
from app.middlewares import UserActivityMiddleware  # noqa: E402
from app.services.reminders import reminder_loop  # noqa: E402


async def main():
    token = os.getenv("BOT_TOKEN") or os.getenv("API_TOKEN", "")
    if not token:
        raise RuntimeError("BOT_TOKEN or API_TOKEN is not set")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    logging.info("Starting bot...")

    bot = Bot(token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.message.middleware(UserActivityMiddleware())
    dp.callback_query.middleware(UserActivityMiddleware())

    for r in routers:
        dp.include_router(r)

    db = await dbm.connect(DB_PATH)
    await dbm.init_db(db)
    bot.db = db
    logging.info("Database initialized.")

    stop_event = asyncio.Event()
    reminder_task = asyncio.create_task(reminder_loop(bot, db, REMINDER_POLL_SECONDS, stop_event))

    try:
        await dp.start_polling(bot, drop_pending_updates=True)
    finally:
        stop_event.set()
        await reminder_task
        await db.close()
        logging.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
