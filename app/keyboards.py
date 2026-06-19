from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏠 Главное меню")],
        ],
        resize_keyboard=True,
    )


def main_menu_inline_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="➕ Новая задача", callback_data="menu:new")
    b.button(text="📆 Сегодня", callback_data="menu:today")
    b.button(text="🔎 Поиск", callback_data="menu:search")
    b.button(text="📋 Задачи", callback_data="menu:tasks")
    b.button(text="⚙️ Настройки", callback_data="menu:settings")
    b.adjust(2, 2, 1)
    return b.as_markup()


def tasks_menu_inline_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🧭 Квадранты", callback_data="menu:quadrants")
    b.button(text="⚡ Быстрые задачи", callback_data="menu:quick")
    b.button(text="🗂 Архив", callback_data="menu:archive")
    b.button(text="⬅️ Назад", callback_data="menu:main")
    b.adjust(2, 1, 1)
    return b.as_markup()


def settings_inline_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🕒 Таймзона", callback_data="settings:tz")
    b.button(text="🔔 Уведомления", callback_data="settings:rem")
    b.button(text="✨ Возможности бота", callback_data="settings:features")
    b.button(text="🛟 Поддержка", callback_data="settings:support")
    b.button(text="⬅️ Назад", callback_data="settings:back")
    b.adjust(2, 1, 1, 1)
    return b.as_markup()


def cancel_new_task_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="Отменить", callback_data="new:cancel")
    return b.as_markup()


def cta_new_task_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="➕ Новая задача", callback_data="menu:new")
    return b.as_markup()


def archive_page_kb(
    tasks: list[tuple[int, str]],
    page: int,
    total_pages: int,
    back_cb: str | None = None,
    bulk_cb: str | None = None,
) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for task_id, text in tasks:
        label = text if len(text) <= 40 else text[:37] + "..."
        b.row(InlineKeyboardButton(text=label, callback_data=f"archive:task:{page}:{task_id}"))
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"archive:page:{page-1}"))
    nav_row.append(InlineKeyboardButton(text=f"Стр. {page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"archive:page:{page+1}"))
    b.row(*nav_row)
    if bulk_cb or back_cb:
        row = []
        if bulk_cb:
            row.append(InlineKeyboardButton(text="🗑 Удалить", callback_data=bulk_cb))
        if back_cb:
            row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cb))
        b.row(*row)
    return b.as_markup()


def tasks_page_kb(
    kind: str,
    tasks: list[tuple[int, str]],
    page: int,
    total_pages: int,
    back_cb: str | None = None,
    bulk_cb: str | None = None,
) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for task_id, text in tasks:
        label = text if len(text) <= 40 else text[:37] + "..."
        b.row(InlineKeyboardButton(text=label, callback_data=f"taskview:{kind}:{page}:{task_id}"))
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"list:{kind}:{page-1}"))
    nav_row.append(InlineKeyboardButton(text=f"Стр. {page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"list:{kind}:{page+1}"))
    b.row(*nav_row)
    if bulk_cb or back_cb:
        row = []
        if bulk_cb:
            row.append(InlineKeyboardButton(text="🗑 Удалить", callback_data=bulk_cb))
        if back_cb:
            row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cb))
        b.row(*row)
    return b.as_markup()


def bulk_delete_kb(
    mode: str,
    tasks: list[tuple[int, str]],
    selected: set[int],
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for task_id, text in tasks:
        label = text if len(text) <= 40 else text[:37] + "..."
        prefix = "✅ " if task_id in selected else ""
        b.row(InlineKeyboardButton(text=prefix + label, callback_data=f"bulk:{mode}:toggle:{task_id}"))
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"bulk:{mode}:page:{page-1}"))
    nav_row.append(InlineKeyboardButton(text=f"Стр. {page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"bulk:{mode}:page:{page+1}"))
    b.row(*nav_row)
    b.row(
        InlineKeyboardButton(text=f"🗑 Удалить ({len(selected)})", callback_data=f"bulk:{mode}:delete"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"bulk:{mode}:cancel"),
    )
    return b.as_markup()


def archive_task_kb(task_id: int, page: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🗑 Удалить", callback_data=f"archive:delete:{task_id}")
    b.button(text="Назад", callback_data=f"archive:page:{page}")
    b.adjust(1, 1)
    return b.as_markup()


def confirm_delete_kb(task_id: int, scope: str, extra: str | None = None) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    suffix = f":{extra}" if extra else ""
    b.button(text="✅ Да", callback_data=f"confirm:{scope}:{task_id}{suffix}")
    b.button(text="❌ Нет", callback_data=f"cancel:{scope}:{task_id}{suffix}")
    b.adjust(2)
    return b.as_markup()


def reminders_settings_kb(enabled: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    on_text = "Вкл ✅" if enabled else "Вкл"
    off_text = "Выкл ✅" if not enabled else "Выкл"
    b.button(text=on_text, callback_data="settings:rem:on")
    b.button(text=off_text, callback_data="settings:rem:off")
    b.button(text="⬅️ Назад", callback_data="settings:back")
    b.adjust(2, 1)
    return b.as_markup()


def admin_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📊 Статистика", callback_data="admin:stats")
    b.button(text="👥 Пользователи", callback_data="admin:users")
    b.button(text="📣 Рассылка", callback_data="admin:cast")
    b.button(text="⬅️ Назад", callback_data="admin:back")
    b.adjust(2, 1, 1)
    return b.as_markup()


def admin_users_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="Все", callback_data="admin:users:all")
    b.button(text="Активные", callback_data="admin:users:active")
    b.button(text="Неактивные", callback_data="admin:users:inactive")
    b.button(text="⬅️ Назад", callback_data="admin:back")
    b.adjust(2, 1, 1)
    return b.as_markup()


def admin_users_nav_kb(kind: str, page: int, total_pages: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if page > 1:
        b.button(text="⬅️", callback_data=f"admin:users:{kind}:page:{page-1}")
    b.button(text=f"Стр. {page}/{total_pages}", callback_data="noop")
    if page < total_pages:
        b.button(text="➡️", callback_data=f"admin:users:{kind}:page:{page+1}")
    b.button(text="⬅️ Назад", callback_data="admin:users")
    b.adjust(3, 1)
    return b.as_markup()


def admin_cast_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="Всем", callback_data="admin:cast:all")
    b.button(text="Активным", callback_data="admin:cast:active")
    b.button(text="Неактивным", callback_data="admin:cast:inactive")
    b.button(text="Выборочно", callback_data="admin:cast:select")
    b.button(text="⬅️ Назад", callback_data="admin:back")
    b.adjust(2, 2, 1)
    return b.as_markup()


def admin_confirm_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Отправить", callback_data="admin:cast:send")
    b.button(text="❌ Отмена", callback_data="admin:cast:cancel")
    b.adjust(2)
    return b.as_markup()


def flags_kb(important: bool, urgent: bool, is_quick: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=("✅ " if important else "") + "Важно", callback_data="flag:important")
    b.button(text=("✅ " if urgent else "") + "Срочно", callback_data="flag:urgent")
    b.button(text=("✅ " if is_quick else "") + "Быстрая задача", callback_data="flag:quick")
    b.button(text="Дальше", callback_data="flag:next")
    b.adjust(2, 1, 1)
    return b.as_markup()


def deadline_choice_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="Без дедлайна", callback_data="deadline:none")
    b.button(text="Указать дедлайн", callback_data="deadline:set")
    b.adjust(2)
    return b.as_markup()


def reminder_choice_kb(selected: set[str]) -> InlineKeyboardMarkup:
    def _label(key: str, text: str) -> str:
        return ("✅ " if key in selected else "") + text

    b = InlineKeyboardBuilder()
    b.button(text=_label("24h", "За день"), callback_data="rem:24h")
    b.button(text=_label("1h", "За час"), callback_data="rem:1h")
    b.button(text=_label("15m", "За 15 минут"), callback_data="rem:15m")
    b.button(text=_label("custom", "⏱️ Свои минуты"), callback_data="rem:custom")
    b.button(text="✅ Готово", callback_data="rem:done")
    b.adjust(2, 2, 1)
    return b.as_markup()


def task_actions_kb(task_id: int, kind: str, page: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Готово", callback_data=f"task:done:{task_id}")
    b.button(text="⏰ Напоминания", callback_data=f"task:reminders:{task_id}")
    b.button(text="✏️ Изменить", callback_data=f"task:edit:{task_id}:{kind}:{page}")
    b.button(text="🗑 Удалить", callback_data=f"task:delete:{task_id}:{kind}:{page}")
    b.button(text="Назад", callback_data=f"taskback:{kind}:{page}")
    b.adjust(2, 2, 1)
    return b.as_markup()


def edit_menu_kb(task_id: int, kind: str, page: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✏️ Текст", callback_data=f"edit:text:{task_id}:{kind}:{page}")
    b.button(text="🕒 Дедлайн", callback_data=f"edit:deadline:{task_id}:{kind}:{page}")
    b.button(text="🧭 Квадрант", callback_data=f"edit:quadrant:{task_id}:{kind}:{page}")
    b.button(text="⬅️ Назад", callback_data=f"edit:back:{task_id}:{kind}:{page}")
    b.adjust(2, 2)
    return b.as_markup()


def quadrant_select_kb(selected: str, task_id: int, kind: str, page: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()

    def _label(key: str, text: str) -> str:
        return ("✅ " if selected == key else "") + text

    b.button(text=_label("11", "🟥 Срочно/Важно"), callback_data="editquad:11")
    b.button(text=_label("10", "🟩 Несрочно/Важно"), callback_data="editquad:10")
    b.button(text=_label("01", "🟦 Срочно/Неважно"), callback_data="editquad:01")
    b.button(text=_label("00", "🟨 Несрочно/Неважно"), callback_data="editquad:00")
    b.button(text="🔁 Переместить", callback_data=f"editquad:done:{task_id}:{kind}:{page}")
    b.button(text="⬅️ Назад", callback_data=f"edit:back:{task_id}:{kind}:{page}")
    b.adjust(2, 2, 1, 1)
    return b.as_markup()


def post_deadline_kb(task_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="В архив", callback_data=f"post:done:{task_id}")
    b.button(text="Перенести", callback_data=f"post:reschedule:{task_id}")
    b.button(text="Удалить", callback_data=f"post:delete:{task_id}")
    b.adjust(2, 1)
    return b.as_markup()


def quadrants_kb(counts: dict[str, int]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=f"🟥 ({counts['11']}) Срочно/Важно", callback_data="quad:11")
    b.button(text=f"🟩 ({counts['10']}) Несрочно/Важно", callback_data="quad:10")
    b.button(text=f"🟦 ({counts['01']}) Срочно/Неважно", callback_data="quad:01")
    b.button(text=f"🟨 ({counts['00']}) Несрочно/Неважно", callback_data="quad:00")
    b.button(text="📋 Все задачи квадрантов", callback_data="quad:allq")
    b.button(text="⬅️ Назад", callback_data="menu:tasks")
    b.adjust(2, 2, 1, 1)
    return b.as_markup()
