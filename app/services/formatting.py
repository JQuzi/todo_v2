from datetime import datetime, timezone, timedelta


def format_deadline(deadline_iso: str, tz_offset: str | None) -> str:
    dt = datetime.fromisoformat(deadline_iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    offset_hours = 0
    if tz_offset:
        try:
            offset_hours = int(tz_offset)
        except ValueError:
            offset_hours = 0
    tz = timezone(timedelta(hours=offset_hours))
    local = dt.astimezone(tz)
    date_s = local.strftime("%d.%m.%Y")
    time_s = local.strftime("%H:%M")
    return f"Дата: {date_s}\nВремя: {time_s}"


def format_datetime_line(iso_value: str, tz_offset: str | None) -> str:
    dt = datetime.fromisoformat(iso_value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    offset_hours = 0
    if tz_offset:
        try:
            offset_hours = int(tz_offset)
        except ValueError:
            offset_hours = 0
    tz = timezone(timedelta(hours=offset_hours))
    local = dt.astimezone(tz)
    return local.strftime("%d.%m %H:%M")


def format_task_details(task: dict, tz_offset: str | None) -> str:
    def quadrant_label(t: dict) -> str:
        if t.get("is_quick"):
            return "⚡ Быстрая задача"
        if t.get("important") and t.get("urgent"):
            return "🟥 Срочно/Важно"
        if t.get("important") and not t.get("urgent"):
            return "🟩 Несрочно/Важно"
        if not t.get("important") and t.get("urgent"):
            return "🟦 Срочно/Неважно"
        return "🟨 Несрочно/Неважно"

    text = f"Задача: {task['text']}\n"
    text += f"Квадрант: {quadrant_label(task)}\n"
    if task.get("deadline_at"):
        text += format_deadline(task["deadline_at"], tz_offset)
    else:
        text += "Дедлайн: не установлен"
    return text
