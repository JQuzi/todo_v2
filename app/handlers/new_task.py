from datetime import datetime, timedelta, timezone

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.states import NewTaskStates
from app.keyboards import (
    flags_kb,
    deadline_choice_kb,
    reminder_choice_kb,
    main_menu_kb,
    cancel_new_task_kb,
    main_menu_inline_kb,
)
from app import db as dbm
from app.services import nlp
from app.services.reminders import create_reminders_for_task

router = Router()


async def _ensure_timezone(user_id: int, message: Message, state: FSMContext) -> str | None:
    db = message.bot.db
    user = await dbm.get_or_create_user(db, user_id)
    if not user["timezone"]:
        await state.clear()
        await message.answer("Сначала установи таймзону в настройках: Настройки → Таймзона.", reply_markup=main_menu_kb())
        return None
    return user["timezone"]


@router.message(F.text == "Новая задача")
async def new_task(message: Message, state: FSMContext):
    tz = await _ensure_timezone(message.from_user.id, message, state)
    if not tz:
        return
    await state.set_state(NewTaskStates.text)
    await message.answer("📝 Введите текст задачи.", reply_markup=cancel_new_task_kb())


@router.callback_query(F.data == "menu:new")
async def new_task_cb(call: CallbackQuery, state: FSMContext):
    tz = await _ensure_timezone(call.from_user.id, call.message, state)
    if not tz:
        await call.answer()
        return
    await state.set_state(NewTaskStates.text)
    await call.message.edit_text("📝 Введите текст задачи.", reply_markup=cancel_new_task_kb())
    await call.answer()


@router.message(NewTaskStates.text)
async def new_task_text(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text:
        await message.answer("Текст не может быть пустым.")
        return
    await state.update_data(text=text, important=False, urgent=False, is_quick=False)
    await state.set_state(NewTaskStates.flags)
    await message.answer("Отметь важность/срочность:", reply_markup=flags_kb(False, False, False))


@router.callback_query(NewTaskStates.flags, F.data.startswith("flag:"))
async def flags_toggle(call: CallbackQuery, state: FSMContext):
    action = call.data.split(":", 1)[1]
    data = await state.get_data()
    important = bool(data.get("important"))
    urgent = bool(data.get("urgent"))
    is_quick = bool(data.get("is_quick"))

    if action == "important":
        important = not important
        if important and is_quick:
            is_quick = False
    elif action == "urgent":
        urgent = not urgent
        if urgent and is_quick:
            is_quick = False
    elif action == "quick":
        is_quick = not is_quick
        if is_quick:
            important = False
            urgent = False
    elif action == "next":
        await state.update_data(important=important, urgent=urgent, is_quick=is_quick)
        if is_quick:
            await state.set_state(NewTaskStates.deadline_input)
            await call.message.edit_text("Укажи дедлайн (например 26.02 13:00):")
            await call.answer()
            return
        await state.set_state(NewTaskStates.deadline_choice)
        await call.message.edit_text("Нужен дедлайн?", reply_markup=deadline_choice_kb())
        await call.answer()
        return

    await state.update_data(important=important, urgent=urgent, is_quick=is_quick)
    await call.message.edit_reply_markup(reply_markup=flags_kb(important, urgent, is_quick))
    await call.answer()


@router.callback_query(NewTaskStates.deadline_choice, F.data.startswith("deadline:"))
async def deadline_choice(call: CallbackQuery, state: FSMContext):
    choice = call.data.split(":", 1)[1]
    if choice == "none":
        await state.update_data(deadline_at=None, reminders_selected=[], custom_offset_minutes=None)
        await _finalize_task(call, state)
        return

    await state.set_state(NewTaskStates.deadline_input)
    await call.message.edit_text("Укажи дедлайн (например 26.02 13:00):")
    await call.answer()


@router.message(NewTaskStates.deadline_input)
async def deadline_input(message: Message, state: FSMContext):
    db = message.bot.db
    user = await dbm.get_or_create_user(db, message.from_user.id)
    tz = user["timezone"]
    if not tz:
        await state.clear()
        await message.answer("Сначала установи таймзону в настройках.", reply_markup=main_menu_kb())
        return

    text = (message.text or "").strip()
    dt = nlp.parse_datetime(text, tz)
    if not dt:
        await message.answer("Не смог распознать дату. Пример: 26.02 13:00 или завтра 18:00")
        return
    dt_utc = dt.astimezone(timezone.utc)
    await state.update_data(deadline_at=dt_utc.isoformat())
    await state.set_state(NewTaskStates.reminders)
    await message.answer("✅ Готово. Выбери напоминания:", reply_markup=reminder_choice_kb(set()))


@router.callback_query(NewTaskStates.reminders, F.data.startswith("rem:"))
async def reminders_select(call: CallbackQuery, state: FSMContext):
    action = call.data.split(":", 1)[1]
    data = await state.get_data()
    selected = set(data.get("reminders_selected", []))
    custom_offset = data.get("custom_offset_minutes")

    if action == "custom":
        if "custom" in selected:
            selected.remove("custom")
            custom_offset = None
            await state.update_data(reminders_selected=list(selected), custom_offset_minutes=custom_offset)
            await call.message.edit_reply_markup(reply_markup=reminder_choice_kb(selected))
            await call.answer()
            return
        selected.add("custom")
        await state.update_data(reminders_selected=list(selected))
        await state.set_state(NewTaskStates.custom_reminder)
        await call.message.edit_text(
            "⏱️ Введи число минут, за сколько напомнить до события.\n"
            "Например: 30\n\n"
            "Чтобы отключить кастомное напоминание — введи 0."
        )
        await call.answer()
        return

    if action == "done":
        await _finalize_task(call, state)
        return

    if action in {"24h", "1h", "15m"}:
        if action in selected:
            selected.remove(action)
        else:
            selected.add(action)
        await state.update_data(reminders_selected=list(selected))
        await call.message.edit_reply_markup(reply_markup=reminder_choice_kb(selected))
        await call.answer()
        return


@router.callback_query(
    NewTaskStates.text,
    F.data == "new:cancel",
)
@router.callback_query(
    NewTaskStates.flags,
    F.data == "new:cancel",
)
@router.callback_query(
    NewTaskStates.deadline_choice,
    F.data == "new:cancel",
)
@router.callback_query(
    NewTaskStates.deadline_input,
    F.data == "new:cancel",
)
@router.callback_query(
    NewTaskStates.reminders,
    F.data == "new:cancel",
)
@router.callback_query(
    NewTaskStates.custom_reminder,
    F.data == "new:cancel",
)
async def new_task_cancel_any(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("Создание задачи отменено.")
    await call.message.answer("🏠 Главное меню", reply_markup=main_menu_inline_kb())
    await call.answer()


@router.message(NewTaskStates.custom_reminder)
async def custom_reminder_input(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    minutes = nlp.parse_duration_minutes(text)
    if minutes is None:
        await message.answer("Не смог распознать длительность. Пример: 30")
        return
    if minutes == 0:
        data = await state.get_data()
        selected = set(data.get("reminders_selected", []))
        if "custom" in selected:
            selected.remove("custom")
        await state.update_data(custom_offset_minutes=None, reminders_selected=list(selected))
        await state.set_state(NewTaskStates.reminders)
        await message.answer("✅ Готово. Выбери напоминания:", reply_markup=reminder_choice_kb(selected))
        return
    await state.update_data(custom_offset_minutes=minutes)
    await state.set_state(NewTaskStates.reminders)
    data = await state.get_data()
    selected = set(data.get("reminders_selected", []))
    await message.answer("✅ Готово. Выбери напоминания:", reply_markup=reminder_choice_kb(selected))


async def _finalize_task(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    db = call.bot.db
    user = await dbm.get_or_create_user(db, call.from_user.id)

    text = data.get("text")
    important = bool(data.get("important"))
    urgent = bool(data.get("urgent"))
    is_quick = bool(data.get("is_quick"))
    if is_quick:
        important = False
        urgent = False
    deadline_iso = data.get("deadline_at")

    task_id = await dbm.create_task(
        db,
        user["id"],
        text,
        important,
        urgent,
        is_quick,
        deadline_iso,
    )

    selected = set(data.get("reminders_selected", []))
    offsets = []
    if "24h" in selected:
        offsets.append(timedelta(hours=24))
    if "1h" in selected:
        offsets.append(timedelta(hours=1))
    if "15m" in selected:
        offsets.append(timedelta(minutes=15))

    if data.get("custom_offset_minutes"):
        offsets.append(timedelta(minutes=int(data["custom_offset_minutes"])))

    deadline_dt_utc = None
    if deadline_iso:
        dt = datetime.fromisoformat(deadline_iso)
        if dt.tzinfo:
            dt = dt.astimezone(timezone.utc)
        else:
            dt = dt.replace(tzinfo=timezone.utc)
        deadline_dt_utc = dt

    await create_reminders_for_task(
        db,
        task_id,
        deadline_dt_utc,
        offsets,
        include_deadline=bool(user["default_reminder_enabled"]),
    )

    await state.clear()
    await call.message.edit_text("✅ Задача сохранена!")
    await call.message.answer("🏠 Главное меню", reply_markup=main_menu_inline_kb())
    await call.answer()
