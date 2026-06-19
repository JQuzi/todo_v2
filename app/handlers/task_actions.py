from datetime import datetime, timedelta, timezone

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from app import db as dbm
from app.states import RescheduleStates
from app.keyboards import (
    reminder_choice_kb,
    main_menu_kb,
    confirm_delete_kb,
    task_actions_kb,
    edit_menu_kb,
    quadrant_select_kb,
)
from app.handlers.matrix import _edit_tasks_list
from app.services.formatting import format_deadline, format_task_details
from app.states import EditTaskStates
from app.services import nlp
from app.services.reminders import create_reminders_for_task

router = Router()


@router.callback_query(F.data.startswith("task:done:"))
async def task_done(call: CallbackQuery):
    task_id = int(call.data.split(":")[2])
    db = call.bot.db
    await dbm.archive_task(db, task_id)
    await call.message.edit_text("Задача перемещена в архив.")
    await call.answer()


@router.callback_query(F.data.startswith("task:delete:"))
async def task_delete(call: CallbackQuery):
    parts = call.data.split(":")
    task_id = int(parts[2])
    kind = parts[3] if len(parts) > 3 else "search"
    page = parts[4] if len(parts) > 4 else "1"
    extra = f"{kind}:{page}"
    await call.message.edit_text("Удалить задачу?", reply_markup=confirm_delete_kb(task_id, scope="task", extra=extra))
    await call.answer()


@router.callback_query(F.data.startswith("confirm:task:"))
async def task_delete_confirm(call: CallbackQuery):
    parts = call.data.split(":")
    task_id = int(parts[2])
    kind = parts[3] if len(parts) > 3 else None
    page = int(parts[4]) if len(parts) > 4 else 1
    db = call.bot.db
    await dbm.delete_task(db, task_id)
    if kind in {"quick", "00", "01", "10", "11", "allq"}:
        user = await dbm.get_or_create_user(db, call.from_user.id)
        await _edit_tasks_list(call, user["id"], kind, page)
    else:
        await call.message.edit_text("Задача удалена.")
    await call.answer()


@router.callback_query(F.data.startswith("cancel:task:"))
async def task_delete_cancel(call: CallbackQuery):
    parts = call.data.split(":")
    task_id = int(parts[2])
    kind = parts[3] if len(parts) > 3 else "search"
    page = int(parts[4]) if len(parts) > 4 else 1
    db = call.bot.db
    task = await dbm.get_task(db, task_id)
    if not task:
        await call.message.edit_text("Задача не найдена.")
        await call.answer()
        return
    await _render_task_card(call, task_id, kind, page)
    await call.answer()


@router.callback_query(F.data.startswith("task:edit:"))
async def task_edit(call: CallbackQuery, state: FSMContext):
    parts = call.data.split(":")
    task_id = int(parts[2])
    kind = parts[3] if len(parts) > 3 else "search"
    page = int(parts[4]) if len(parts) > 4 else 1
    db = call.bot.db
    user = await dbm.get_or_create_user(db, call.from_user.id)
    task = await dbm.get_task(db, task_id)
    if not task:
        await call.message.edit_text("Задача не найдена.")
        await call.answer()
        return
    await state.set_state(EditTaskStates.menu)
    await state.update_data(task_id=task_id, kind=kind, page=page)
    await call.message.edit_text(
        _edit_header(task, user["timezone"]),
        reply_markup=edit_menu_kb(task_id, kind, page),
    )
    await call.answer()


@router.callback_query(EditTaskStates.menu, F.data.startswith("edit:back:"))
async def edit_back(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    task_id = data.get("task_id")
    kind = data.get("kind", "search")
    page = int(data.get("page", 1))
    await state.clear()
    await _render_task_card(call, task_id, kind, page)
    await call.answer()


@router.callback_query(EditTaskStates.menu, F.data.startswith("edit:text:"))
async def edit_text_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(EditTaskStates.text)
    await call.message.edit_text("✏️ Введите новое описание:")
    await call.answer()


@router.message(EditTaskStates.text)
async def edit_text_save(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text:
        await message.answer("Текст не может быть пустым.")
        return
    data = await state.get_data()
    task_id = data.get("task_id")
    kind = data.get("kind", "search")
    page = int(data.get("page", 1))
    db = message.bot.db
    await dbm.update_task_text(db, task_id, text)
    await state.clear()
    await message.answer("✅ Обновлено.")


@router.callback_query(EditTaskStates.menu, F.data.startswith("edit:deadline:"))
async def edit_deadline_start(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    task_id = data.get("task_id")
    await state.clear()
    await state.set_state(RescheduleStates.deadline_input)
    await state.update_data(task_id=task_id, reminders_selected=[], custom_offset_minutes=None)
    await call.message.edit_text("🕒 Укажи новый дедлайн (например 26.02 13:00):")
    await call.answer()


@router.callback_query(EditTaskStates.menu, F.data.startswith("edit:quadrant:"))
async def edit_quadrant_start(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    task_id = data.get("task_id")
    kind = data.get("kind", "search")
    page = int(data.get("page", 1))
    db = call.bot.db
    task = await dbm.get_task(db, task_id)
    if not task:
        await call.message.edit_text("Задача не найдена.")
        await call.answer()
        return
    await state.set_state(EditTaskStates.quadrant)
    sel = "11" if task["important"] and task["urgent"] else "10" if task["important"] else "01" if task["urgent"] else "00"
    await state.update_data(selected=sel, task_id=task_id, kind=kind, page=page)
    await call.message.edit_text(
        "🧭 Выбери квадрант:",
        reply_markup=quadrant_select_kb(sel, task_id, kind, page),
    )
    await call.answer()


@router.callback_query(EditTaskStates.quadrant, F.data.startswith("editquad:"))
async def edit_quadrant_select(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    task_id = data.get("task_id")
    kind = data.get("kind", "search")
    page = int(data.get("page", 1))
    action = call.data.split(":")[1]

    if action == "done":
        sel = data.get("selected", "00")
        important = sel in {"11", "10"}
        urgent = sel in {"11", "01"}
        db = call.bot.db
        await dbm.update_task_flags(db, task_id, important, urgent, is_quick=False)
        await state.clear()
        await _render_task_card(call, task_id, kind, page)
        await call.answer()
        return

    selected = action
    await state.update_data(selected=selected)
    await call.message.edit_reply_markup(reply_markup=quadrant_select_kb(selected, task_id, kind, page))
    await call.answer()


@router.callback_query(F.data.startswith("task:reminders:"))
async def task_reschedule(call: CallbackQuery, state: FSMContext):
    task_id = int(call.data.split(":")[2])
    await state.set_state(RescheduleStates.deadline_input)
    await state.update_data(task_id=task_id, reminders_selected=[], custom_offset_minutes=None)
    await call.message.edit_text("🕒 Укажи новый дедлайн (например 26.02 13:00):")
    await call.answer()


@router.callback_query(F.data.startswith("post:done:"))
async def post_deadline_done(call: CallbackQuery):
    task_id = int(call.data.split(":")[2])
    db = call.bot.db
    await dbm.archive_task(db, task_id)
    await call.message.edit_text("Отлично. Задача закрыта и перенесена в архив.")
    await call.answer()


@router.callback_query(F.data.startswith("post:delete:"))
async def post_deadline_delete(call: CallbackQuery):
    task_id = int(call.data.split(":")[2])
    db = call.bot.db
    await dbm.delete_task(db, task_id)
    await call.message.edit_text("Задача удалена.")
    await call.answer()


@router.callback_query(F.data.startswith("post:reschedule:"))
async def post_deadline_reschedule(call: CallbackQuery, state: FSMContext):
    task_id = int(call.data.split(":")[2])
    await state.set_state(RescheduleStates.deadline_input)
    await state.update_data(task_id=task_id, reminders_selected=[], custom_offset_minutes=None)
    await call.message.edit_text("🕒 Укажи новый дедлайн (например 26.02 13:00):")
    await call.answer()


@router.message(RescheduleStates.deadline_input)
async def reschedule_deadline_input(message: Message, state: FSMContext):
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
    await state.set_state(RescheduleStates.reminders)
    await message.answer("✅ Готово. Выбери напоминания:", reply_markup=reminder_choice_kb(set()))


@router.callback_query(RescheduleStates.reminders, F.data.startswith("rem:"))
async def reschedule_reminders(call: CallbackQuery, state: FSMContext):
    action = call.data.split(":", 1)[1]
    data = await state.get_data()
    selected = set(data.get("reminders_selected", []))

    if action == "custom":
        if "custom" in selected:
            selected.remove("custom")
            await state.update_data(reminders_selected=list(selected), custom_offset_minutes=None)
            await call.message.edit_reply_markup(reply_markup=reminder_choice_kb(selected))
            await call.answer()
            return
        selected.add("custom")
        await state.update_data(reminders_selected=list(selected))
        await state.set_state(RescheduleStates.custom_reminder)
        await call.message.edit_text(
            "⏱️ Введи число минут, за сколько напомнить до события.\n"
            "Например: 30\n\n"
            "Чтобы отключить кастомное напоминание — введи 0."
        )
        await call.answer()
        return

    if action == "done":
        await _finalize_reschedule(call, state)
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


@router.message(RescheduleStates.custom_reminder)
async def reschedule_custom_reminder(message: Message, state: FSMContext):
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
        await state.set_state(RescheduleStates.reminders)
        await message.answer("✅ Готово. Выбери напоминания:", reply_markup=reminder_choice_kb(selected))
        return
    await state.update_data(custom_offset_minutes=minutes)
    await state.set_state(RescheduleStates.reminders)
    data = await state.get_data()
    selected = set(data.get("reminders_selected", []))
    await message.answer("✅ Готово. Выбери напоминания:", reply_markup=reminder_choice_kb(selected))


async def _finalize_reschedule(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    db = call.bot.db

    task_id = data.get("task_id")
    deadline_iso = data.get("deadline_at")

    await dbm.update_task_deadline(db, task_id, deadline_iso)
    await dbm.clear_pending_reminders(db, task_id)

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

    user = await dbm.get_or_create_user(db, call.from_user.id)
    await create_reminders_for_task(
        db,
        task_id,
        deadline_dt_utc,
        offsets,
        include_deadline=bool(user["default_reminder_enabled"]),
    )

    await state.clear()
    await call.message.edit_text("✅ Дедлайн обновлен, напоминания пересозданы.")
    await call.answer()


async def _render_task_card(call: CallbackQuery, task_id: int, kind: str, page: int):
    db = call.bot.db
    user = await dbm.get_or_create_user(db, call.from_user.id)
    task = await dbm.get_task(db, task_id)
    if not task:
        await call.message.edit_text("Задача не найдена.")
        return
    msg = format_task_details(task, user["timezone"])
    await call.message.edit_text(msg, reply_markup=task_actions_kb(task_id, kind, page))


def _edit_header(task: dict, tz_offset: str | None) -> str:
    return format_task_details(task, tz_offset)
