from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from app import db as dbm
from app.handlers.matrix import _send_tasks_list, _edit_tasks_list

router = Router()


@router.message(F.text == "Быстрые задачи")
async def quick_tasks(message: Message):
    db = message.bot.db
    user = await dbm.get_or_create_user(db, message.from_user.id)
    await _send_tasks_list(message, user["id"], "quick", page=1)


@router.callback_query(F.data == "menu:quick")
async def quick_tasks_cb(call: CallbackQuery):
    db = call.bot.db
    user = await dbm.get_or_create_user(db, call.from_user.id)
    await _edit_tasks_list(call, user["id"], "quick", page=1)
    await call.answer()
