from math import ceil

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from app import db as dbm
from app.keyboards import quadrants_kb, task_actions_kb, tasks_page_kb, cta_new_task_kb
from app.services.formatting import format_task_details

router = Router()

PAGE_SIZE = 10


@router.message(F.text == "Квадранты")
async def show_quadrants(message: Message):
    db = message.bot.db
    user = await dbm.get_or_create_user(db, message.from_user.id)
    counts = await dbm.get_quadrant_counts(db, user["id"])
    await message.answer("📌 Квадранты", reply_markup=quadrants_kb(counts))


@router.callback_query(F.data == "menu:quadrants")
async def show_quadrants_cb(call: CallbackQuery):
    db = call.bot.db
    user = await dbm.get_or_create_user(db, call.from_user.id)
    counts = await dbm.get_quadrant_counts(db, user["id"])
    await call.message.edit_text("📌 Квадранты", reply_markup=quadrants_kb(counts))
    await call.answer()


@router.callback_query(F.data.startswith("quad:"))
async def show_quadrant_tasks(call: CallbackQuery):
    key = call.data.split(":", 1)[1]
    db = call.bot.db
    user = await dbm.get_or_create_user(db, call.from_user.id)

    await _edit_tasks_list(call, user["id"], key, page=1)
    await call.answer()


@router.callback_query(F.data.startswith("list:"))
async def list_page(call: CallbackQuery):
    _, kind, page_s = call.data.split(":")
    page = int(page_s)
    db = call.bot.db
    user = await dbm.get_or_create_user(db, call.from_user.id)
    await _edit_tasks_list(call, user["id"], kind, page)
    await call.answer()


@router.callback_query(F.data.startswith("taskview:"))
async def task_view(call: CallbackQuery):
    _, kind, page_s, task_id_s = call.data.split(":")
    task_id = int(task_id_s)
    page = int(page_s)
    db = call.bot.db
    user = await dbm.get_or_create_user(db, call.from_user.id)
    task = await dbm.get_task(db, task_id)
    if not task:
        await call.answer("Задача не найдена.", show_alert=True)
        return
    msg = format_task_details(task, user["timezone"])
    await call.message.edit_text(msg, reply_markup=task_actions_kb(task_id, kind, page))
    await call.answer()


@router.callback_query(F.data.regexp(r"^taskback:(quick|allq|00|01|10|11):"))
async def task_back_to_list(call: CallbackQuery):
    _, kind, page_s = call.data.split(":")
    page = int(page_s)
    db = call.bot.db
    user = await dbm.get_or_create_user(db, call.from_user.id)
    await _edit_tasks_list(call, user["id"], kind, page)
    await call.answer()


async def _send_tasks_list(message: Message, user_id: int, kind: str, page: int):
    db = message.bot.db
    if kind == "quick":
        total = await dbm.count_quick_tasks(db, user_id)
        if total == 0:
            await message.answer("Пока пусто.", reply_markup=cta_new_task_kb())
            return
        total_pages = max(1, ceil(total / PAGE_SIZE))
        page = max(1, min(page, total_pages))
        rows = await dbm.list_quick_tasks_paged(db, user_id, PAGE_SIZE, (page - 1) * PAGE_SIZE)
        tasks = [(task_id, text) for task_id, text, _ in rows]
        await message.answer(
            "📎 Быстрые задачи",
            reply_markup=tasks_page_kb(kind, tasks, page, total_pages, back_cb="menu:tasks", bulk_cb="bulk:quick:start"),
        )
        return

    if kind == "allq":
        total = await dbm.count_all_quadrant_tasks(db, user_id)
        if total == 0:
            await message.answer("Пока пусто.", reply_markup=cta_new_task_kb())
            return
        total_pages = max(1, ceil(total / PAGE_SIZE))
        page = max(1, min(page, total_pages))
        rows = await dbm.list_all_quadrant_tasks_paged(db, user_id, PAGE_SIZE, (page - 1) * PAGE_SIZE)
        tasks = []
        for task_id, text, _, important, urgent in rows:
            label = _quadrant_badge(bool(important), bool(urgent)) + " " + text
            tasks.append((task_id, label))
        await message.answer(
            "📋 Все задачи квадрантов",
            reply_markup=tasks_page_kb(kind, tasks, page, total_pages, back_cb="menu:quadrants", bulk_cb="bulk:allq:start"),
        )
        return

    important = int(kind[0])
    urgent = int(kind[1])
    total = await dbm.count_tasks_by_quadrant(db, user_id, important, urgent)
    if total == 0:
        await message.answer("Пока пусто.", reply_markup=cta_new_task_kb())
        return
    total_pages = max(1, ceil(total / PAGE_SIZE))
    page = max(1, min(page, total_pages))
    rows = await dbm.list_tasks_by_quadrant_paged(db, user_id, important, urgent, PAGE_SIZE, (page - 1) * PAGE_SIZE)
    tasks = [(task_id, text) for task_id, text, _ in rows]
    name = {
        "11": "🟥 Срочно/Важно",
        "10": "🟩 Несрочно/Важно",
        "01": "🟦 Срочно/Неважно",
        "00": "🟨 Несрочно/Неважно",
    }.get(kind, "Квадрант")
    await message.answer(
        name,
        reply_markup=tasks_page_kb(kind, tasks, page, total_pages, back_cb="menu:quadrants"),
    )


async def _edit_tasks_list(call: CallbackQuery, user_id: int, kind: str, page: int):
    db = call.bot.db
    if kind == "quick":
        total = await dbm.count_quick_tasks(db, user_id)
        if total == 0:
            await call.message.edit_text("Пока пусто.", reply_markup=cta_new_task_kb())
            return
        total_pages = max(1, ceil(total / PAGE_SIZE))
        page = max(1, min(page, total_pages))
        rows = await dbm.list_quick_tasks_paged(db, user_id, PAGE_SIZE, (page - 1) * PAGE_SIZE)
        tasks = [(task_id, text) for task_id, text, _ in rows]
        await call.message.edit_text(
            "📎 Быстрые задачи",
            reply_markup=tasks_page_kb(kind, tasks, page, total_pages, back_cb="menu:tasks", bulk_cb="bulk:quick:start"),
        )
        return

    if kind == "allq":
        total = await dbm.count_all_quadrant_tasks(db, user_id)
        if total == 0:
            await call.message.edit_text("Пока пусто.", reply_markup=cta_new_task_kb())
            return
        total_pages = max(1, ceil(total / PAGE_SIZE))
        page = max(1, min(page, total_pages))
        rows = await dbm.list_all_quadrant_tasks_paged(db, user_id, PAGE_SIZE, (page - 1) * PAGE_SIZE)
        tasks = []
        for task_id, text, _, important, urgent in rows:
            label = _quadrant_badge(bool(important), bool(urgent)) + " " + text
            tasks.append((task_id, label))
        await call.message.edit_text(
            "📋 Все задачи квадрантов",
            reply_markup=tasks_page_kb(kind, tasks, page, total_pages, back_cb="menu:quadrants", bulk_cb="bulk:allq:start"),
        )
        return

    important = int(kind[0])
    urgent = int(kind[1])
    total = await dbm.count_tasks_by_quadrant(db, user_id, important, urgent)
    if total == 0:
        await call.message.edit_text("Пока пусто.", reply_markup=cta_new_task_kb())
        return
    total_pages = max(1, ceil(total / PAGE_SIZE))
    page = max(1, min(page, total_pages))
    rows = await dbm.list_tasks_by_quadrant_paged(db, user_id, important, urgent, PAGE_SIZE, (page - 1) * PAGE_SIZE)
    tasks = [(task_id, text) for task_id, text, _ in rows]
    name = {
        "11": "🟥 Срочно/Важно",
        "10": "🟩 Несрочно/Важно",
        "01": "🟦 Срочно/Неважно",
        "00": "🟨 Несрочно/Неважно",
    }.get(kind, "Квадрант")
    await call.message.edit_text(
        name,
        reply_markup=tasks_page_kb(kind, tasks, page, total_pages, back_cb="menu:quadrants"),
    )


def _quadrant_badge(important: bool, urgent: bool) -> str:
    if important and urgent:
        return "🟥"
    if important and not urgent:
        return "🟩"
    if not important and urgent:
        return "🟦"
    return "🟨"
