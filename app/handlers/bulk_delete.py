from math import ceil

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from app import db as dbm
from app.keyboards import bulk_delete_kb, cta_new_task_kb
from app.states import BulkDeleteStates
from app.handlers.matrix import _edit_tasks_list
from app.handlers.archive import _edit_archive_page

router = Router()

PAGE_SIZE = 10


async def _load_page(db, user_id: int, mode: str, page: int):
    if mode == "quick":
        total = await dbm.count_quick_tasks(db, user_id)
        rows = await dbm.list_quick_tasks_paged(db, user_id, PAGE_SIZE, (page - 1) * PAGE_SIZE)
    elif mode == "allq":
        total = await dbm.count_all_quadrant_tasks(db, user_id)
        rows = await dbm.list_all_quadrant_tasks_paged(db, user_id, PAGE_SIZE, (page - 1) * PAGE_SIZE)
    else:
        total = await dbm.count_archived_tasks(db, user_id)
        rows = await dbm.list_archived_tasks(db, user_id, PAGE_SIZE, (page - 1) * PAGE_SIZE)
    total_pages = max(1, ceil(total / PAGE_SIZE))
    page = max(1, min(page, total_pages))
    tasks = []
    for row in rows:
        task_id, text = row[0], row[1]
        if mode == "allq":
            important, urgent = bool(row[3]), bool(row[4])
            badge = "🟥" if important and urgent else "🟩" if important else "🟦" if urgent else "🟨"
            tasks.append((task_id, f"{badge} {text}"))
        else:
            tasks.append((task_id, text))
    return total, total_pages, page, tasks


@router.callback_query(F.data == "bulk:quick:start")
@router.callback_query(F.data == "bulk:archive:start")
@router.callback_query(F.data == "bulk:allq:start")
async def bulk_start(call: CallbackQuery, state: FSMContext):
    if call.data.startswith("bulk:quick"):
        mode = "quick"
    elif call.data.startswith("bulk:allq"):
        mode = "allq"
    else:
        mode = "archive"
    await state.set_state(BulkDeleteStates.select)
    await state.update_data(mode=mode, selected=[], page=1)
    db = call.bot.db
    user = await dbm.get_or_create_user(db, call.from_user.id)
    total, total_pages, page, tasks = await _load_page(db, user["id"], mode, 1)
    if total == 0:
        await state.clear()
        await call.message.edit_text("Пока пусто.", reply_markup=cta_new_task_kb())
        await call.answer()
        return
    await call.message.edit_text(
        "Выберите задачи для удаления:",
        reply_markup=bulk_delete_kb(mode, tasks, set(), page, total_pages),
    )
    await call.answer()


@router.callback_query(BulkDeleteStates.select, F.data.startswith("bulk:") & ~F.data.endswith(":confirm"))
async def bulk_actions(call: CallbackQuery, state: FSMContext):
    parts = call.data.split(":")
    if len(parts) < 3:
        await call.answer()
        return
    _, mode, action = parts[0], parts[1], parts[2]
    data = await state.get_data()
    selected = set(data.get("selected", []))
    page = int(data.get("page", 1))

    db = call.bot.db
    user = await dbm.get_or_create_user(db, call.from_user.id)

    if action == "toggle":
        task_id = int(parts[3])
        if task_id in selected:
            selected.remove(task_id)
        else:
            selected.add(task_id)
        await state.update_data(selected=list(selected))

    elif action == "page":
        page = int(parts[3])
        await state.update_data(page=page)

    elif action == "cancel":
        await state.clear()
        if mode == "quick":
            await _edit_tasks_list(call, user["id"], "quick", page=1)
        else:
            await _edit_archive_page(call, user["id"], page=1)
        await call.answer()
        return

    elif action == "delete":
        if not selected:
            await call.answer("Выберите хотя бы одну задачу.", show_alert=True)
            return
        await call.message.edit_text(
            f"Удалить {len(selected)} задач?",
            reply_markup=_confirm_kb(mode),
        )
        await call.answer()
        return

    total, total_pages, page, tasks = await _load_page(db, user["id"], mode, page)
    if total == 0:
        await call.message.edit_text("Пока пусто.", reply_markup=cta_new_task_kb())
        await call.answer()
        return
    await call.message.edit_text(
        "Выберите задачи для удаления:",
        reply_markup=bulk_delete_kb(mode, tasks, selected, page, total_pages),
    )
    await call.answer()


def _confirm_kb(mode: str):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    b = InlineKeyboardBuilder()
    b.button(text="✅ Да, удалить", callback_data=f"bulk:{mode}:confirm")
    b.button(text="❌ Отмена", callback_data=f"bulk:{mode}:cancel")
    b.adjust(1, 1)
    return b.as_markup()


@router.callback_query(BulkDeleteStates.select, F.data.endswith(":confirm"))
async def bulk_confirm(call: CallbackQuery, state: FSMContext):
    mode = call.data.split(":")[1]
    data = await state.get_data()
    selected = set(data.get("selected", []))
    if not selected:
        await call.answer("Выберите хотя бы одну задачу.", show_alert=True)
        return
    db = call.bot.db
    count = len(selected)
    for task_id in selected:
        await dbm.delete_task(db, task_id)
    await state.clear()
    user = await dbm.get_or_create_user(db, call.from_user.id)
    if mode == "quick":
        await _edit_tasks_list(call, user["id"], "quick", page=1)
    elif mode == "allq":
        await _edit_tasks_list(call, user["id"], "allq", page=1)
    else:
        await _edit_archive_page(call, user["id"], page=1)
    await call.message.answer(f"✅ Удалено задач: {count}")
    await call.answer()
