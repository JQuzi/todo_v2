from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from app import db as dbm


class UserActivityMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        bot = data.get("bot")
        if bot and hasattr(bot, "db"):
            if isinstance(event, Message):
                user = event.from_user
            elif isinstance(event, CallbackQuery):
                user = event.from_user
            else:
                user = None
            if user:
                username = user.username
                full_name = " ".join([p for p in [user.first_name, user.last_name] if p])
                await dbm.upsert_user_meta(bot.db, user.id, username, full_name)
        return await handler(event, data)
