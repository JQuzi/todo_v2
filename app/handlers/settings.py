from datetime import timezone, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.states import SettingsStates
from app import db as dbm
from app.keyboards import main_menu_kb, settings_inline_kb, reminders_settings_kb, main_menu_inline_kb

router = Router()


@router.message(F.text == "Настройки")
async def settings_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("⚙️ Настройки", reply_markup=settings_inline_kb())


@router.callback_query(F.data == "menu:settings")
async def settings_menu_cb(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("⚙️ Настройки", reply_markup=settings_inline_kb())
    await call.answer()


@router.callback_query(F.data == "settings:tz")
async def settings_timezone_cb(call: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsStates.timezone)
    await call.message.edit_text("Укажи таймзону в формате смещения от UTC. Примеры: +3, +5, -5.")
    await call.answer()


@router.callback_query(F.data == "settings:back")
async def settings_back_cb(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("🏠 Главное меню", reply_markup=main_menu_inline_kb())
    await call.answer()


@router.callback_query(F.data == "settings:rem")
async def settings_reminder_toggle(call: CallbackQuery, state: FSMContext):
    db = call.bot.db
    user = await dbm.get_or_create_user(db, call.from_user.id)
    await call.message.edit_text(
        "🔔 Стандартное уведомление во время дедлайна.",
        reply_markup=reminders_settings_kb(user["default_reminder_enabled"]),
    )
    await call.answer()


@router.callback_query(F.data == "settings:features")
async def settings_features(call: CallbackQuery):
    text = (
        "<b>🧭 Матрица 4 квадрантов</b>\n"
        "• Срочно/Важно, Срочно/Неважно\n"
        "• Несрочно/Важно, Несрочно/Неважно\n\n"
        "<b>⚡ Быстрые задачи</b>\n"
        "• Для простых напоминаний без квадрантов\n\n"
        "<b>🔔 Напоминания</b>\n"
        "• За день / за час / за 15 минут\n"
        "• Свои минуты\n"
        "• Уведомление в момент дедлайна\n\n"
        "<b>📆 Сегодня</b>\n"
        "• Все задачи с дедлайном на сегодня\n\n"
        "<b>🔎 Поиск</b>\n"
        "• Находит по словам без учета регистра\n\n"
        "<b>🗂 Архив</b>\n"
        "• Выполненные задачи сохраняются отдельно"
    )
    await call.message.edit_text(text, reply_markup=settings_inline_kb())
    await call.answer()


@router.callback_query(F.data == "settings:support")
async def settings_support(call: CallbackQuery):
    await call.answer("Функция в разработке.", show_alert=True)
@router.callback_query(F.data == "settings:rem:on")
async def settings_reminder_on(call: CallbackQuery):
    db = call.bot.db
    await dbm.set_default_reminder(db, call.from_user.id, True)
    await call.message.edit_reply_markup(reply_markup=reminders_settings_kb(True))
    await call.answer()


@router.callback_query(F.data == "settings:rem:off")
async def settings_reminder_off(call: CallbackQuery):
    db = call.bot.db
    await dbm.set_default_reminder(db, call.from_user.id, False)
    await call.message.edit_reply_markup(reply_markup=reminders_settings_kb(False))
    await call.answer()


@router.message(SettingsStates.timezone)
async def set_timezone(message: Message, state: FSMContext):
    raw = (message.text or "").strip()
    if not raw:
        await message.answer("Таймзона не может быть пустой. Пример: +3")
        return
    try:
        offset_hours = int(raw)
    except ValueError:
        await message.answer("Неверный формат. Пример: +3 или -5")
        return
    if offset_hours < -12 or offset_hours > 14:
        await message.answer("Смещение должно быть от -12 до +14.")
        return
    tz = f"{offset_hours:+d}"

    db = message.bot.db
    await dbm.set_timezone(db, message.from_user.id, tz)
    await state.clear()
    await message.answer("Таймзона сохранена.", reply_markup=main_menu_kb())
