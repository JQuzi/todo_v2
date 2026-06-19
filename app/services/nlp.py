from datetime import datetime, timezone, timedelta
import dateparser


def parse_datetime(text: str, tz: str) -> datetime | None:
    try:
        offset_hours = int(tz)
    except ValueError:
        offset_hours = 0
    sign = "+" if offset_hours >= 0 else "-"
    abs_h = abs(offset_hours)
    tz_offset = f"{sign}{abs_h:02d}:00"
    local_tz = timezone(timedelta(hours=offset_hours))
    now_local = datetime.now(local_tz)
    settings = {
        "TIMEZONE": tz_offset,
        "TO_TIMEZONE": "UTC",
        "RETURN_AS_TIMEZONE_AWARE": True,
        "PREFER_DATES_FROM": "future",
        "DATE_ORDER": "DMY",
        "RELATIVE_BASE": now_local,
    }
    dt = dateparser.parse(text, settings=settings, languages=["ru"])
    if not dt:
        return None
    return dt


def parse_duration_minutes(text: str) -> int | None:
    if not text:
        return None
    t = text.strip()
    if t.isdigit():
        return int(t)
    return None
