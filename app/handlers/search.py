from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app import db as dbm
from app.keyboards import tasks_page_kb, task_actions_kb
from app.states import SearchStates
from app.services.formatting import format_task_details

router = Router()

PAGE_SIZE = 10


async def _search_items(db, user_id: int, query: str):
    rows = await dbm.list_open_tasks(db, user_id)
    q = query.casefold()
    items = []
    for task_id, text, _, *_ in rows:
        if q in text.casefold():
            items.append((task_id, text))
    return items


@router.message(F.text == "Поиск")
async def search_start(message: Message, state: FSMContext):
    await state.set_state(SearchStates.query)
    await message.answer("🔎 Введите текст для поиска.")


@router.callback_query(F.data == "menu:search")
async def search_start_cb(call: CallbackQuery, state: FSMContext):
    await state.set_state(SearchStates.query)
    await call.message.edit_text("🔎 Введите текст для поиска.")
    await call.answer()


@router.message(SearchStates.query)
async def search_query(message: Message, state: FSMContext):
    query = (message.text or "").strip()
    if not query:
        await message.answer("Текст поиска не может быть пустым.")
        return
    db = message.bot.db
    user = await dbm.get_or_create_user(db, message.from_user.id)
    items = await _search_items(db, user["id"], query)
    await state.update_data(query=query)
    await state.set_state(SearchStates.results)
    if not items:
        await message.answer("Ничего не найдено.")
        return
    total_pages = (len(items) + PAGE_SIZE - 1) // PAGE_SIZE
    page_items = items[:PAGE_SIZE]
    await message.answer("🔎 Поиск", reply_markup=tasks_page_kb("search", page_items, 1, total_pages, back_cb="menu:main"))


@router.callback_query(F.data.startswith("list:search:"))
async def search_page(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    query = data.get("query")
    if not query:
        await call.answer("Повтори поиск.", show_alert=True)
        return
    _, _, page_s = call.data.split(":")
    page = int(page_s)
    db = call.bot.db
    user = await dbm.get_or_create_user(db, call.from_user.id)
    items = await _search_items(db, user["id"], query)
    if not items:
        await call.message.edit_text("Ничего не найдено.")
        await call.answer()
        return
    total_pages = (len(items) + PAGE_SIZE - 1) // PAGE_SIZE
    page = max(1, min(page, total_pages))
    start = (page - 1) * PAGE_SIZE
    page_items = items[start:start + PAGE_SIZE]
    await call.message.edit_text("🔎 Поиск", reply_markup=tasks_page_kb("search", page_items, page, total_pages, back_cb="menu:main"))
    await call.answer()


@router.callback_query(F.data.startswith("taskview:search:"))
async def search_task_view(call: CallbackQuery):
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
    await call.message.edit_text(msg, reply_markup=task_actions_kb(task_id, "search", page))
    await call.answer()


@router.callback_query(F.data.startswith("taskback:search:"))
async def search_task_back(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    query = data.get("query")
    if not query:
        await call.answer("Повтори поиск.", show_alert=True)
        return
    _, _, page_s = call.data.split(":")
    page = int(page_s)
    db = call.bot.db
    user = await dbm.get_or_create_user(db, call.from_user.id)
    items = await _search_items(db, user["id"], query)
    if not items:
        await call.message.edit_text("Ничего не найдено.")
        await call.answer()
        return
    total_pages = (len(items) + PAGE_SIZE - 1) // PAGE_SIZE
    page = max(1, min(page, total_pages))
    start = (page - 1) * PAGE_SIZE
    page_items = items[start:start + PAGE_SIZE]
    await call.message.edit_text("🔎 Поиск", reply_markup=tasks_page_kb("search", page_items, page, total_pages, back_cb="menu:main"))
    await call.answer()
