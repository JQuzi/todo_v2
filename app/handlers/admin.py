from datetime import datetime, timedelta
import asyncio

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from app import db as dbm
from app.config import ADMIN_IDS
from app.keyboards import admin_menu_kb, admin_users_kb, admin_users_nav_kb, admin_cast_kb, admin_confirm_kb

router = Router()


class AdminStates(StatesGroup):
    cast_text = State()

PAGE_SIZE = 10


def _is_admin(user_id: int) -> bool:
    if not ADMIN_IDS:
        return False
    try:
        ids = {int(x.strip()) for x in ADMIN_IDS.split(",") if x.strip()}
    except ValueError:
        return False
    return user_id in ids


def _since_days(days: int) -> str:
    return (datetime.utcnow() - timedelta(days=days)).isoformat()


@router.message(Command("admin"))
async def admin_entry(message: Message):
    if not _is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return
    await message.answer("Админ-панель:", reply_markup=admin_menu_kb())


@router.callback_query(F.data == "admin:back")
async def admin_back(call: CallbackQuery):
    if not _is_admin(call.from_user.id):
        return
    await call.message.edit_text("Админ-панель:", reply_markup=admin_menu_kb())
    await call.answer()


@router.callback_query(F.data == "admin:stats")
async def admin_stats(call: CallbackQuery):
    if not _is_admin(call.from_user.id):
        return
    db = call.bot.db
    total = await dbm.count_users(db)
    active7 = await dbm.count_users(db, _since_days(7), active=True)
    inactive7 = await dbm.count_users(db, _since_days(7), active=False)
    msg = (
        "📊 Статистика\n\n"
        f"Всего пользователей: {total}\n"
        f"Активные за 7 дней: {active7}\n"
        f"Неактивные за 7 дней: {inactive7}"
    )
    await call.message.edit_text(msg, reply_markup=admin_menu_kb())
    await call.answer()


@router.callback_query(F.data == "admin:users")
async def admin_users(call: CallbackQuery):
    if not _is_admin(call.from_user.id):
        return
    await call.message.edit_text("👥 Пользователи:", reply_markup=admin_users_kb())
    await call.answer()


@router.callback_query(F.data.startswith("admin:users:"))
async def admin_users_list(call: CallbackQuery):
    if not _is_admin(call.from_user.id):
        return
    parts = call.data.split(":")
    kind = parts[2]
    page = int(parts[4]) if len(parts) > 4 else 1
    db = call.bot.db
    since = _since_days(7)
    if kind == "active":
        rows = await dbm.list_users(db, PAGE_SIZE, (page - 1) * PAGE_SIZE, since, True)
        total = await dbm.count_users(db, since, True)
    elif kind == "inactive":
        rows = await dbm.list_users(db, PAGE_SIZE, (page - 1) * PAGE_SIZE, since, False)
        total = await dbm.count_users(db, since, False)
    else:
        rows = await dbm.list_users(db, PAGE_SIZE, (page - 1) * PAGE_SIZE)
        total = await dbm.count_users(db)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(1, min(page, total_pages))
    lines = []
    for tg_id, username, full_name, last_seen in rows:
        uname = f"@{username}" if username else "-"
        name = full_name or "-"
        seen = last_seen.split("T")[0] if last_seen else "-"
        lines.append(f"{name} {uname} ({tg_id}) — {seen}")
    text = "👥 Пользователи:\n\n" + ("\n".join(lines) if lines else "Нет данных")
    await call.message.edit_text(text, reply_markup=admin_users_nav_kb(kind, page, total_pages))
    await call.answer()


@router.callback_query(F.data == "admin:cast")
async def admin_cast(call: CallbackQuery):
    if not _is_admin(call.from_user.id):
        return
    await call.message.edit_text("📣 Рассылка:\nВыбери аудиторию.", reply_markup=admin_cast_kb())
    await call.answer()


@router.callback_query(F.data.startswith("admin:cast:"))
async def admin_cast_select(call: CallbackQuery, state: FSMContext):
    if not _is_admin(call.from_user.id):
        return
    action = call.data.split(":")[2]
    if action in {"all", "active", "inactive", "select"}:
        await state.update_data(cast_target=action, cast_ids=None, cast_text=None, cast_entities=None)
        if action == "select":
            await call.message.edit_text(
                "✍️ Введите tg_id или @username через пробел.\n"
                "Пример: 12345678 @username",
            )
        else:
            await call.message.edit_text("✍️ Введите текст рассылки (HTML разрешён):")
        await state.set_state(AdminStates.cast_text)
        await call.answer()
        return
    if action == "send":
        data = await state.get_data()
        text = data.get("cast_text")
        entities = data.get("cast_entities")
        target = data.get("cast_target")
        ids = data.get("cast_ids")
        if not text or not target:
            await call.answer("Нет текста рассылки.", show_alert=True)
            return
        db = call.bot.db
        if target == "all":
            rows = await dbm.list_users(db, 100000, 0)
            user_ids = [r[0] for r in rows]
        elif target == "active":
            rows = await dbm.list_users(db, 100000, 0, _since_days(7), True)
            user_ids = [r[0] for r in rows]
        elif target == "inactive":
            rows = await dbm.list_users(db, 100000, 0, _since_days(7), False)
            user_ids = [r[0] for r in rows]
        else:
            user_ids = ids or []
        sent = 0
        for uid in user_ids:
            try:
                if entities:
                    await call.bot.send_message(uid, text, entities=entities, parse_mode=None)
                else:
                    await call.bot.send_message(uid, text, parse_mode="HTML")
                sent += 1
                await asyncio.sleep(0.05)
            except Exception:
                continue
        await state.clear()
        await call.message.edit_text(f"✅ Рассылка отправлена. Получателей: {sent}", reply_markup=admin_menu_kb())
        await call.answer()
        return
    if action == "cancel":
        await state.clear()
        await call.message.edit_text("Админ-панель:", reply_markup=admin_menu_kb())
        await call.answer()


@router.message(AdminStates.cast_text)
async def admin_cast_text(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    raw_text = message.text or ""
    if not raw_text.strip():
        await message.answer("Текст не может быть пустым.")
        return
    data = await state.get_data()
    target = data.get("cast_target")
    db = message.bot.db
    ids = None
    if target == "select":
        tokens = raw_text.split()
        ids_list = []
        usernames = [t[1:] for t in tokens if t.startswith("@")]
        raw_ids = [t for t in tokens if t.isdigit()]
        ids_list.extend([int(x) for x in raw_ids])
        if usernames:
            ids_list.extend(await dbm.find_users_by_usernames(db, usernames))
        ids = list(set(ids_list))
        await state.update_data(cast_ids=ids, cast_target="select_text")
        await message.answer("✍️ Введите текст рассылки (HTML разрешён):")
        await state.set_state(AdminStates.cast_text)
        return
    if target == "select_text":
        await state.update_data(cast_text=raw_text, cast_entities=message.entities, cast_target="select")
    else:
        await state.update_data(cast_text=raw_text, cast_entities=message.entities)
    await message.answer(
        "Отправить рассылку?",
        reply_markup=admin_confirm_kb(),
    )
