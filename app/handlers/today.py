from datetime import datetime, timedelta, timezone

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from app import db as dbm
from app.keyboards import tasks_page_kb, task_actions_kb, cta_new_task_kb
from app.services.formatting import format_task_details

router = Router()

PAGE_SIZE = 10


def _day_bounds_utc(tz_offset: str | None):
    offset_hours = 0
    if tz_offset:
        try:
            offset_hours = int(tz_offset)
        except ValueError:
            offset_hours = 0
    tz = timezone(timedelta(hours=offset_hours))
    now_local = datetime.now(tz)
    start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


async def _today_summary(message: Message, user_id: int):
    db = message.bot.db
    user = await dbm.get_or_create_user(db, user_id)
    start_utc, end_utc = _day_bounds_utc(user["timezone"])
    due = await dbm.list_tasks_due_between(db, user["id"], start_utc.isoformat(), end_utc.isoformat())
    quick_no_deadline = await dbm.list_quick_tasks_without_deadline(db, user["id"])
    items = [(task_id, text) for task_id, text, *_ in due] + [(task_id, text) for task_id, text, _ in quick_no_deadline]
    if not items:
        await message.answer("На сегодня задач нет.", reply_markup=cta_new_task_kb())
        return
    page = 1
    total_pages = (len(items) + PAGE_SIZE - 1) // PAGE_SIZE
    page_items = items[:PAGE_SIZE]
    await message.answer("📆 Сегодня", reply_markup=tasks_page_kb("today", page_items, page, total_pages, back_cb="menu:main"))


@router.callback_query(F.data == "menu:today")
async def today_summary_cb(call: CallbackQuery):
    await _today_summary(call.message, call.from_user.id)
    await call.answer()


@router.message(F.text == "Сегодня")
async def today_summary(message: Message):
    await _today_summary(message, message.from_user.id)


@router.callback_query(F.data.startswith("list:today:"))
async def today_page(call: CallbackQuery):
    _, _, page_s = call.data.split(":")
    page = int(page_s)
    db = call.bot.db
    user = await dbm.get_or_create_user(db, call.from_user.id)
    start_utc, end_utc = _day_bounds_utc(user["timezone"])
    due = await dbm.list_tasks_due_between(db, user["id"], start_utc.isoformat(), end_utc.isoformat())
    quick_no_deadline = await dbm.list_quick_tasks_without_deadline(db, user["id"])
    items = [(task_id, text) for task_id, text, *_ in due] + [(task_id, text) for task_id, text, _ in quick_no_deadline]
    if not items:
        await call.message.edit_text("На сегодня задач нет.", reply_markup=cta_new_task_kb())
        await call.answer()
        return
    total_pages = (len(items) + PAGE_SIZE - 1) // PAGE_SIZE
    page = max(1, min(page, total_pages))
    start = (page - 1) * PAGE_SIZE
    page_items = items[start:start + PAGE_SIZE]
    await call.message.edit_text("📆 Сегодня", reply_markup=tasks_page_kb("today", page_items, page, total_pages, back_cb="menu:main"))
    await call.answer()


@router.callback_query(F.data.startswith("taskview:today:"))
async def today_task_view(call: CallbackQuery):
    _, _, page_s, task_id_s = call.data.split(":")
    page = int(page_s)
    task_id = int(task_id_s)
    db = call.bot.db
    user = await dbm.get_or_create_user(db, call.from_user.id)
    task = await dbm.get_task(db, task_id)
    if not task:
        await call.answer("Задача не найдена.", show_alert=True)
        return
    msg = format_task_details(task, user["timezone"])
    await call.message.edit_text(msg, reply_markup=task_actions_kb(task_id, "today", page))
    await call.answer()


@router.callback_query(F.data.startswith("taskback:today:"))
async def today_task_back(call: CallbackQuery):
    _, _, page_s = call.data.split(":")
    page = int(page_s)
    db = call.bot.db
    user = await dbm.get_or_create_user(db, call.from_user.id)
    start_utc, end_utc = _day_bounds_utc(user["timezone"])
    due = await dbm.list_tasks_due_between(db, user["id"], start_utc.isoformat(), end_utc.isoformat())
    quick_no_deadline = await dbm.list_quick_tasks_without_deadline(db, user["id"])
    items = [(task_id, text) for task_id, text, *_ in due] + [(task_id, text) for task_id, text, _ in quick_no_deadline]
    if not items:
        await call.message.edit_text("На сегодня задач нет.", reply_markup=cta_new_task_kb())
        await call.answer()
        return
    total_pages = (len(items) + PAGE_SIZE - 1) // PAGE_SIZE
    page = max(1, min(page, total_pages))
    start = (page - 1) * PAGE_SIZE
    page_items = items[start:start + PAGE_SIZE]
    await call.message.edit_text("📆 Сегодня", reply_markup=tasks_page_kb("today", page_items, page, total_pages, back_cb="menu:main"))
    await call.answer()
