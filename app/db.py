import aiosqlite
from datetime import datetime

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER UNIQUE NOT NULL,
    timezone TEXT,
    default_reminder_enabled INTEGER NOT NULL DEFAULT 1,
    username TEXT,
    full_name TEXT,
    last_seen TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    important INTEGER NOT NULL DEFAULT 0,
    urgent INTEGER NOT NULL DEFAULT 0,
    is_quick INTEGER NOT NULL DEFAULT 0,
    deadline_at TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    remind_at TEXT NOT NULL,
    kind TEXT NOT NULL,
    sent_at TEXT,
    FOREIGN KEY(task_id) REFERENCES tasks(id)
);
"""


async def connect(db_path: str):
    return await aiosqlite.connect(db_path)


async def init_db(db):
    await db.executescript(SCHEMA_SQL)
    await _ensure_column(db, "users", "default_reminder_enabled", "INTEGER NOT NULL DEFAULT 1")
    await _ensure_column(db, "users", "username", "TEXT")
    await _ensure_column(db, "users", "full_name", "TEXT")
    await _ensure_column(db, "users", "last_seen", "TEXT")
    await db.commit()


async def _ensure_column(db, table: str, column: str, ddl: str):
    async with db.execute(f"PRAGMA table_info({table})") as cur:
        cols = [row[1] for row in await cur.fetchall()]
    if column not in cols:
        await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def _utcnow_str():
    return datetime.utcnow().isoformat()


async def get_or_create_user(db, tg_id: int):
    async with db.execute(
        "SELECT id, tg_id, timezone, default_reminder_enabled, username, full_name, last_seen FROM users WHERE tg_id = ?",
        (tg_id,),
    ) as cur:
        row = await cur.fetchone()
        if row:
            return {
                "id": row[0],
                "tg_id": row[1],
                "timezone": row[2],
                "default_reminder_enabled": bool(row[3]),
                "username": row[4],
                "full_name": row[5],
                "last_seen": row[6],
            }
    await db.execute(
        "INSERT INTO users (tg_id, timezone, default_reminder_enabled, created_at) VALUES (?, ?, ?, ?)",
        (tg_id, None, 1, _utcnow_str()),
    )
    await db.commit()
    return await get_or_create_user(db, tg_id)


async def upsert_user_meta(db, tg_id: int, username: str | None, full_name: str | None):
    now = _utcnow_str()
    await db.execute(
        """
        INSERT INTO users (tg_id, username, full_name, last_seen, created_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(tg_id) DO UPDATE SET
            username = excluded.username,
            full_name = excluded.full_name,
            last_seen = excluded.last_seen
        """,
        (tg_id, username, full_name, now, now),
    )
    await db.commit()


async def count_users(db, since_iso: str | None = None, active: bool | None = None):
    if since_iso is None or active is None:
        async with db.execute("SELECT COUNT(1) FROM users") as cur:
            row = await cur.fetchone()
            return row[0] if row else 0
    if active:
        query = "SELECT COUNT(1) FROM users WHERE last_seen IS NOT NULL AND last_seen >= ?"
    else:
        query = "SELECT COUNT(1) FROM users WHERE last_seen IS NULL OR last_seen < ?"
    async with db.execute(query, (since_iso,)) as cur:
        row = await cur.fetchone()
        return row[0] if row else 0


async def list_users(db, limit: int, offset: int, since_iso: str | None = None, active: bool | None = None):
    if since_iso is None or active is None:
        query = """
        SELECT tg_id, username, full_name, last_seen
        FROM users
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """
        params = (limit, offset)
    else:
        if active:
            query = """
            SELECT tg_id, username, full_name, last_seen
            FROM users
            WHERE last_seen IS NOT NULL AND last_seen >= ?
            ORDER BY last_seen DESC
            LIMIT ? OFFSET ?
            """
        else:
            query = """
            SELECT tg_id, username, full_name, last_seen
            FROM users
            WHERE last_seen IS NULL OR last_seen < ?
            ORDER BY last_seen DESC
            LIMIT ? OFFSET ?
            """
        params = (since_iso, limit, offset)
    async with db.execute(query, params) as cur:
        return await cur.fetchall()


async def find_users_by_usernames(db, usernames: list[str]):
    if not usernames:
        return []
    placeholders = ",".join("?" for _ in usernames)
    query = f"SELECT tg_id FROM users WHERE username IN ({placeholders})"
    async with db.execute(query, usernames) as cur:
        rows = await cur.fetchall()
        return [row[0] for row in rows]


async def set_timezone(db, tg_id: int, tz: str):
    await db.execute("UPDATE users SET timezone = ? WHERE tg_id = ?", (tz, tg_id))
    await db.commit()


async def set_default_reminder(db, tg_id: int, enabled: bool):
    await db.execute(
        "UPDATE users SET default_reminder_enabled = ? WHERE tg_id = ?",
        (1 if enabled else 0, tg_id),
    )
    await db.commit()


async def create_task(
    db,
    user_id: int,
    text: str,
    important: bool,
    urgent: bool,
    is_quick: bool,
    deadline_at: str | None,
):
    now = _utcnow_str()
    cur = await db.execute(
        """
        INSERT INTO tasks (user_id, text, important, urgent, is_quick, deadline_at, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 'open', ?, ?)
        """,
        (user_id, text, int(important), int(urgent), int(is_quick), deadline_at, now, now),
    )
    await db.commit()
    return cur.lastrowid


async def update_task_deadline(db, task_id: int, deadline_at: str | None):
    await db.execute(
        "UPDATE tasks SET deadline_at = ?, updated_at = ? WHERE id = ?",
        (deadline_at, _utcnow_str(), task_id),
    )
    await db.commit()


async def update_task_text(db, task_id: int, text: str):
    await db.execute(
        "UPDATE tasks SET text = ?, updated_at = ? WHERE id = ?",
        (text, _utcnow_str(), task_id),
    )
    await db.commit()


async def update_task_flags(db, task_id: int, important: bool, urgent: bool, is_quick: bool):
    await db.execute(
        "UPDATE tasks SET important = ?, urgent = ?, is_quick = ?, updated_at = ? WHERE id = ?",
        (int(important), int(urgent), int(is_quick), _utcnow_str(), task_id),
    )
    await db.commit()


async def archive_task(db, task_id: int):
    await db.execute(
        "UPDATE tasks SET status = 'archived', updated_at = ? WHERE id = ?",
        (_utcnow_str(), task_id),
    )
    await db.commit()


async def delete_task(db, task_id: int):
    await db.execute("DELETE FROM reminders WHERE task_id = ?", (task_id,))
    await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    await db.commit()


async def list_tasks_by_quadrant(db, user_id: int, important: int, urgent: int):
    async with db.execute(
        """
        SELECT id, text, deadline_at FROM tasks
        WHERE user_id = ? AND status = 'open' AND is_quick = 0 AND important = ? AND urgent = ?
        ORDER BY created_at DESC
        """,
        (user_id, important, urgent),
    ) as cur:
        return await cur.fetchall()


async def list_tasks_by_quadrant_paged(db, user_id: int, important: int, urgent: int, limit: int, offset: int):
    async with db.execute(
        """
        SELECT id, text, deadline_at FROM tasks
        WHERE user_id = ? AND status = 'open' AND is_quick = 0 AND important = ? AND urgent = ?
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        (user_id, important, urgent, limit, offset),
    ) as cur:
        return await cur.fetchall()


async def count_tasks_by_quadrant(db, user_id: int, important: int, urgent: int):
    async with db.execute(
        """
        SELECT COUNT(1) FROM tasks
        WHERE user_id = ? AND status = 'open' AND is_quick = 0 AND important = ? AND urgent = ?
        """,
        (user_id, important, urgent),
    ) as cur:
        row = await cur.fetchone()
        return row[0] if row else 0


async def list_all_quadrant_tasks_paged(db, user_id: int, limit: int, offset: int):
    async with db.execute(
        """
        SELECT id, text, deadline_at, important, urgent FROM tasks
        WHERE user_id = ? AND status = 'open' AND is_quick = 0
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        (user_id, limit, offset),
    ) as cur:
        return await cur.fetchall()


async def count_all_quadrant_tasks(db, user_id: int):
    async with db.execute(
        """
        SELECT COUNT(1) FROM tasks
        WHERE user_id = ? AND status = 'open' AND is_quick = 0
        """,
        (user_id,),
    ) as cur:
        row = await cur.fetchone()
        return row[0] if row else 0


async def list_quick_tasks(db, user_id: int):
    async with db.execute(
        """
        SELECT id, text, deadline_at FROM tasks
        WHERE user_id = ? AND status = 'open' AND is_quick = 1
        ORDER BY created_at DESC
        """,
        (user_id,),
    ) as cur:
        return await cur.fetchall()


async def list_quick_tasks_paged(db, user_id: int, limit: int, offset: int):
    async with db.execute(
        """
        SELECT id, text, deadline_at FROM tasks
        WHERE user_id = ? AND status = 'open' AND is_quick = 1
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        (user_id, limit, offset),
    ) as cur:
        return await cur.fetchall()


async def count_quick_tasks(db, user_id: int):
    async with db.execute(
        """
        SELECT COUNT(1) FROM tasks
        WHERE user_id = ? AND status = 'open' AND is_quick = 1
        """,
        (user_id,),
    ) as cur:
        row = await cur.fetchone()
        return row[0] if row else 0


async def list_quick_tasks_without_deadline(db, user_id: int):
    async with db.execute(
        """
        SELECT id, text, deadline_at FROM tasks
        WHERE user_id = ? AND status = 'open' AND is_quick = 1 AND deadline_at IS NULL
        ORDER BY created_at DESC
        """,
        (user_id,),
    ) as cur:
        return await cur.fetchall()


async def list_tasks_due_between(db, user_id: int, start_iso: str, end_iso: str):
    async with db.execute(
        """
        SELECT id, text, deadline_at, is_quick, important, urgent FROM tasks
        WHERE user_id = ? AND status = 'open' AND deadline_at IS NOT NULL
          AND deadline_at >= ? AND deadline_at < ?
        ORDER BY deadline_at ASC
        """,
        (user_id, start_iso, end_iso),
    ) as cur:
        return await cur.fetchall()


async def list_open_tasks(db, user_id: int):
    async with db.execute(
        """
        SELECT id, text, deadline_at, is_quick, important, urgent FROM tasks
        WHERE user_id = ? AND status = 'open'
        ORDER BY created_at DESC
        """,
        (user_id,),
    ) as cur:
        return await cur.fetchall()


async def list_archived_tasks(db, user_id: int, limit: int, offset: int):
    async with db.execute(
        """
        SELECT id, text, deadline_at FROM tasks
        WHERE user_id = ? AND status = 'archived'
        ORDER BY updated_at DESC
        LIMIT ? OFFSET ?
        """,
        (user_id, limit, offset),
    ) as cur:
        return await cur.fetchall()


async def count_archived_tasks(db, user_id: int):
    async with db.execute(
        "SELECT COUNT(1) FROM tasks WHERE user_id = ? AND status = 'archived'",
        (user_id,),
    ) as cur:
        row = await cur.fetchone()
        return row[0] if row else 0


async def get_quadrant_counts(db, user_id: int):
    counts = {"11": 0, "10": 0, "01": 0, "00": 0}
    async with db.execute(
        """
        SELECT important, urgent, COUNT(1)
        FROM tasks
        WHERE user_id = ? AND status = 'open' AND is_quick = 0
        GROUP BY important, urgent
        """,
        (user_id,),
    ) as cur:
        rows = await cur.fetchall()
        for imp, urg, cnt in rows:
            key = f"{int(imp)}{int(urg)}"
            if key in counts:
                counts[key] = cnt
    return counts


async def get_task(db, task_id: int):
    async with db.execute(
        "SELECT id, user_id, text, important, urgent, is_quick, deadline_at, status FROM tasks WHERE id = ?",
        (task_id,),
    ) as cur:
        row = await cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "user_id": row[1],
            "text": row[2],
            "important": bool(row[3]),
            "urgent": bool(row[4]),
            "is_quick": bool(row[5]),
            "deadline_at": row[6],
            "status": row[7],
        }


async def add_reminder(db, task_id: int, remind_at: str, kind: str):
    await db.execute(
        "INSERT INTO reminders (task_id, remind_at, kind, sent_at) VALUES (?, ?, ?, NULL)",
        (task_id, remind_at, kind),
    )
    await db.commit()


async def clear_pending_reminders(db, task_id: int):
    await db.execute("DELETE FROM reminders WHERE task_id = ? AND sent_at IS NULL", (task_id,))
    await db.commit()


async def get_due_reminders(db, now_iso: str):
    async with db.execute(
        """
        SELECT r.id, r.task_id, r.remind_at, r.kind, u.tg_id, u.timezone, t.text, t.deadline_at
        FROM reminders r
        JOIN tasks t ON t.id = r.task_id
        JOIN users u ON u.id = t.user_id
        WHERE r.sent_at IS NULL AND r.remind_at <= ? AND t.status = 'open'
        ORDER BY r.remind_at ASC
        """,
        (now_iso,),
    ) as cur:
        return await cur.fetchall()


async def mark_reminder_sent(db, reminder_id: int):
    await db.execute("UPDATE reminders SET sent_at = ? WHERE id = ?", (_utcnow_str(), reminder_id))
    await db.commit()


async def has_pending_reminders(db, task_id: int):
    async with db.execute(
        "SELECT 1 FROM reminders WHERE task_id = ? AND sent_at IS NULL LIMIT 1",
        (task_id,),
    ) as cur:
        return await cur.fetchone() is not None
