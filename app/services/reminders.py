import asyncio
from datetime import datetime, timedelta, timezone

from app import db as dbm
from app.keyboards import post_deadline_kb
from app.services.formatting import format_datetime_line


def _utcnow():
    return datetime.utcnow()


def _to_naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def utc_iso(dt: datetime) -> str:
    return dt.replace(tzinfo=None).isoformat()


async def create_reminders_for_task(
    db,
    task_id: int,
    deadline_at_utc: datetime | None,
    remind_offsets: list[timedelta],
    include_deadline: bool,
):
    now = _utcnow()
    if deadline_at_utc:
        deadline_naive = _to_naive_utc(deadline_at_utc)
        if include_deadline and deadline_naive > now:
            await dbm.add_reminder(db, task_id, utc_iso(deadline_naive), "deadline")
        for offset in remind_offsets:
            remind_at = deadline_naive - offset
            if remind_at > now:
                minutes = int(offset.total_seconds() // 60)
                await dbm.add_reminder(db, task_id, utc_iso(remind_at), f"offset_{minutes}")
        await dbm.add_reminder(db, task_id, utc_iso(deadline_naive + timedelta(minutes=10)), "post_deadline")
    else:
        for offset in remind_offsets:
            remind_at = _utcnow() + offset
            await dbm.add_reminder(db, task_id, utc_iso(remind_at), f"preset_{int(offset.total_seconds())}")


async def reminder_loop(bot, db, poll_seconds: int, stop_event: asyncio.Event):
    while not stop_event.is_set():
        now_iso = utc_iso(_utcnow())
        due = await dbm.get_due_reminders(db, now_iso)
        for r_id, task_id, remind_at, kind, user_id, tz_offset, text, deadline_at in due:
            if kind == "post_deadline":
                msg = (
                    f"⚠️ Дедлайн прошел: {text}\n"
                    f"🕒 {format_datetime_line(remind_at, tz_offset)}\n\n"
                    "Задача выполнена?"
                )
                await bot.send_message(
                    user_id,
                    msg,
                    reply_markup=post_deadline_kb(task_id),
                )
                await dbm.mark_reminder_sent(db, r_id)
                continue

            if kind == "deadline":
                msg = f"🔔 Сейчас: {text}\n🕒 {format_datetime_line(remind_at, tz_offset)}"
            else:
                minutes = None
                if kind.startswith("offset_"):
                    try:
                        minutes = int(kind.split("_", 1)[1])
                    except ValueError:
                        minutes = None
                elif kind.startswith("preset_"):
                    try:
                        seconds = int(kind.split("_", 1)[1])
                        minutes = seconds // 60
                    except ValueError:
                        minutes = None
                if minutes == 1440:
                    prefix = "Через 1 день"
                elif minutes == 60:
                    prefix = "Через 1 час"
                elif minutes == 15:
                    prefix = "Через 15 минут"
                elif minutes is not None:
                    prefix = f"Через {minutes} минут"
                else:
                    prefix = "Напоминание"
                msg = f"⚠️ {prefix}: {text}\n🕒 {format_datetime_line(remind_at, tz_offset)}"

            await bot.send_message(user_id, msg)
            await dbm.mark_reminder_sent(db, r_id)

            # Auto-archive if no deadline and this was the last reminder
            if not deadline_at:
                has_more = await dbm.has_pending_reminders(db, task_id)
                if not has_more:
                    await dbm.archive_task(db, task_id)

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=poll_seconds)
        except asyncio.TimeoutError:
            pass
