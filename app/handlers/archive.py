from math import ceil

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from app import db as dbm
from app.keyboards import archive_page_kb, archive_task_kb, confirm_delete_kb, cta_new_task_kb
from app.services.formatting import format_task_details

router = Router()

PAGE_SIZE = 10


@router.message(F.text == "Архив")
async def archive_list(message: Message):
    db = message.bot.db
    user = await dbm.get_or_create_user(db, message.from_user.id)
    await _send_archive_page(message, user["id"], page=1)


@router.callback_query(F.data == "menu:archive")
async def archive_list_cb(call: CallbackQuery):
    db = call.bot.db
    user = await dbm.get_or_create_user(db, call.from_user.id)
    await _edit_archive_page(call, user["id"], page=1)
    await call.answer()


@router.callback_query(F.data.startswith("archive:page:"))
async def archive_page(call: CallbackQuery):
    page = int(call.data.split(":")[2])
    db = call.bot.db
    user = await dbm.get_or_create_user(db, call.from_user.id)
    await _edit_archive_page(call, user["id"], page)
    await call.answer()


@router.callback_query(F.data.startswith("archive:task:"))
async def archive_task_view(call: CallbackQuery):
    _, _, page_s, task_id_s = call.data.split(":")
    page = int(page_s)
    task_id = int(task_id_s)
    db = call.bot.db
    user = await dbm.get_or_create_user(db, call.from_user.id)
    task = await dbm.get_task(db, task_id)
    if not task:
        await call.answer("Задача не найдена.", show_alert=True)
        return
    msg = format_task_details(task, user["timezone"]) + "\n\nСтатус: архив"
    await call.message.edit_text(msg, reply_markup=archive_task_kb(task_id, page=page))
    await call.answer()


@router.callback_query(F.data.startswith("archive:delete:"))
async def archive_task_delete(call: CallbackQuery):
    task_id = int(call.data.split(":")[2])
    await call.message.edit_text("Удалить задачу?", reply_markup=confirm_delete_kb(task_id, scope="archive"))
    await call.answer()


@router.callback_query(F.data.startswith("confirm:archive:"))
async def archive_task_delete_confirm(call: CallbackQuery):
    task_id = int(call.data.split(":")[2])
    db = call.bot.db
    await dbm.delete_task(db, task_id)
    await call.message.edit_text("Задача удалена.")
    await call.answer()


@router.callback_query(F.data.startswith("cancel:archive:"))
async def archive_task_delete_cancel(call: CallbackQuery):
    task_id = int(call.data.split(":")[2])
    db = call.bot.db
    task = await dbm.get_task(db, task_id)
    if not task:
        await call.message.edit_text("Задача не найдена.")
        await call.answer()
        return
    await call.message.edit_text(f"Задача: {task['text']}\n\nСтатус: архив", reply_markup=archive_task_kb(task_id, page=1))
    await call.answer()


async def _send_archive_page(message: Message, user_id: int, page: int):
    db = message.bot.db
    total = await dbm.count_archived_tasks(db, user_id)
    if total == 0:
        await message.answer("Пока пусто.", reply_markup=cta_new_task_kb())
        return
    total_pages = max(1, ceil(total / PAGE_SIZE))
    page = max(1, min(page, total_pages))
    offset = (page - 1) * PAGE_SIZE
    rows = await dbm.list_archived_tasks(db, user_id, PAGE_SIZE, offset)
    tasks = [(task_id, text) for task_id, text, _ in rows]
    await message.answer(
        "🗂 Архив",
        reply_markup=archive_page_kb(tasks, page, total_pages, back_cb="menu:tasks", bulk_cb="bulk:archive:start"),
    )


async def _edit_archive_page(call: CallbackQuery, user_id: int, page: int):
    db = call.bot.db
    total = await dbm.count_archived_tasks(db, user_id)
    if total == 0:
        await call.message.edit_text("Пока пусто.", reply_markup=cta_new_task_kb())
        return
    total_pages = max(1, ceil(total / PAGE_SIZE))
    page = max(1, min(page, total_pages))
    offset = (page - 1) * PAGE_SIZE
    rows = await dbm.list_archived_tasks(db, user_id, PAGE_SIZE, offset)
    tasks = [(task_id, text) for task_id, text, _ in rows]
    await call.message.edit_text(
        "🗂 Архив",
        reply_markup=archive_page_kb(tasks, page, total_pages, back_cb="menu:tasks", bulk_cb="bulk:archive:start"),
    )
