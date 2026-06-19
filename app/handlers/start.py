from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery

from app.keyboards import main_menu_kb, main_menu_inline_kb, tasks_menu_inline_kb
from app import db as dbm

router = Router()


@router.message(CommandStart())
async def start_cmd(message: Message):
    db = message.bot.db
    await dbm.get_or_create_user(db, message.from_user.id)
    await message.answer(
        "Хелов! 🌿\n"
        "Я аккуратно убираю стикеры с монитора 🗒️\n"
        "И превращаю их в понятный список задач 📋✨",
        reply_markup=main_menu_kb(),
    )


@router.callback_query(F.data == "noop")
async def noop(call: CallbackQuery):
    await call.answer()


@router.message(F.text == "🏠 Главное меню")
async def main_menu(message: Message):
    await message.answer("🏠 Главное меню", reply_markup=main_menu_inline_kb())


@router.callback_query(F.data == "menu:main")
async def menu_main(call: CallbackQuery):
    await call.message.edit_text("🏠 Главное меню", reply_markup=main_menu_inline_kb())
    await call.answer()


@router.callback_query(F.data == "menu:tasks")
async def menu_tasks(call: CallbackQuery):
    await call.message.edit_text("📋 Задачи", reply_markup=tasks_menu_inline_kb())
    await call.answer()


@router.message(Command("id"))
async def show_id(message: Message):
    await message.answer(f"Ваш ID: {message.from_user.id}")
