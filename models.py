import calendar
import sqlite3
from datetime import datetime

from db import get_db

TIME_FMT = "%Y-%m-%dT%H:%M:%S"

# Length of a session in seconds; a running session (end_at NULL) counts up to now.
SECONDS_SQL = (
    "strftime('%s', COALESCE(s.end_at, datetime('now', 'localtime')))"
    " - strftime('%s', s.start_at)"
)


def _now():
    return datetime.now().strftime(TIME_FMT)


# --- Lessons ---

def list_lessons(include_archived=False):
    conn = get_db()
    sql = "SELECT * FROM lessons"
    if not include_archived:
        sql += " WHERE archived = 0"
    rows = conn.execute(sql + " ORDER BY archived, name").fetchall()
    conn.close()
    return rows


def add_lesson(name, daily_target_hours):
    """Returns False if a lesson with that name already exists."""
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO lessons (name, daily_target_hours) VALUES (?, ?)",
            (name, daily_target_hours),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def update_lesson(lesson_id, name, daily_target_hours):
    """Returns False if another lesson already has that name."""
    conn = get_db()
    try:
        conn.execute(
            "UPDATE lessons SET name = ?, daily_target_hours = ? WHERE id = ?",
            (name, daily_target_hours, lesson_id),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def set_archived(lesson_id, archived):
    conn = get_db()
    conn.execute("UPDATE lessons SET archived = ? WHERE id = ?", (int(archived), lesson_id))
    conn.commit()
    conn.close()


# --- Timer ---

def get_running_session():
    conn = get_db()
    row = conn.execute(
        f"""SELECT s.id, s.lesson_id, l.name, s.start_at, {SECONDS_SQL} AS seconds
            FROM sessions s JOIN lessons l ON l.id = s.lesson_id
            WHERE s.end_at IS NULL"""
    ).fetchone()
    conn.close()
    return row


def start_session(lesson_id):
    """Starts a timer for the lesson, stopping any timer that is already running."""
    now = _now()
    conn = get_db()
    conn.execute("UPDATE sessions SET end_at = ? WHERE end_at IS NULL", (now,))
    conn.execute("INSERT INTO sessions (lesson_id, start_at) VALUES (?, ?)", (lesson_id, now))
    conn.commit()
    conn.close()


def stop_running_session():
    conn = get_db()
    conn.execute("UPDATE sessions SET end_at = ? WHERE end_at IS NULL", (_now(),))
    conn.commit()
    conn.close()


# --- Sessions ---

def list_recent_sessions(limit=50):
    conn = get_db()
    rows = conn.execute(
        f"""SELECT s.id, s.lesson_id, l.name, s.start_at, s.end_at, {SECONDS_SQL} AS seconds
            FROM sessions s JOIN lessons l ON l.id = s.lesson_id
            ORDER BY s.start_at DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return rows


def add_session(lesson_id, start_at, end_at):
    conn = get_db()
    conn.execute(
        "INSERT INTO sessions (lesson_id, start_at, end_at) VALUES (?, ?, ?)",
        (lesson_id, start_at, end_at),
    )
    conn.commit()
    conn.close()


def update_session(session_id, lesson_id, start_at, end_at):
    conn = get_db()
    conn.execute(
        "UPDATE sessions SET lesson_id = ?, start_at = ?, end_at = ? WHERE id = ?",
        (lesson_id, start_at, end_at, session_id),
    )
    conn.commit()
    conn.close()


def delete_session(session_id):
    conn = get_db()
    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()


# --- Reports ---

def get_today(day):
    """Active lessons with the seconds studied in sessions that started on `day`."""
    conn = get_db()
    rows = conn.execute(
        f"""SELECT l.id, l.name, l.daily_target_hours,
                   COALESCE(SUM({SECONDS_SQL}), 0) AS seconds,
                   COALESCE(SUM(s.id IS NOT NULL AND s.end_at IS NULL), 0) AS ticking
            FROM lessons l
            LEFT JOIN sessions s ON s.lesson_id = l.id AND s.start_at LIKE ?
            WHERE l.archived = 0
            GROUP BY l.id
            ORDER BY l.name""",
        (f"{day.isoformat()}%",),
    ).fetchall()
    conn.close()
    return rows


def _month_hours(conn, year, month):
    """{lesson_id: hours} for sessions that started in the given month."""
    rows = conn.execute(
        f"""SELECT s.lesson_id, SUM({SECONDS_SQL}) / 3600.0 AS hours
            FROM sessions s WHERE s.start_at LIKE ? GROUP BY s.lesson_id""",
        (f"{year}-{month:02d}-%",),
    ).fetchall()
    return {r["lesson_id"]: r["hours"] for r in rows}


def get_month_hours(year, month):
    """Actual vs planned hours per lesson. Archived lessons appear only if studied that month."""
    conn = get_db()
    hours = _month_hours(conn, year, month)
    all_lessons = conn.execute("SELECT * FROM lessons ORDER BY name").fetchall()
    conn.close()

    _, days_in_month = calendar.monthrange(year, month)
    lessons = []
    for l in all_lessons:
        actual = hours.get(l["id"], 0)
        if l["archived"] and not actual:
            continue
        planned = l["daily_target_hours"] * days_in_month
        lessons.append(
            {
                "name": l["name"],
                "actual": actual,
                "planned": planned,
                "pct": round(100 * actual / planned) if planned else 0,
            }
        )
    return {"lessons": lessons, "total": sum(l["actual"] for l in lessons)}


def get_comparison(n, year, month):
    """Hours per lesson for the last n months ending at (year, month), oldest first,
    with the percent change versus the month before (None when that month had 0 hours)."""
    months = []
    y, m = year, month
    for _ in range(n + 1):  # one extra so the oldest shown month has a previous month
        months.append((y, m))
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    months.reverse()

    conn = get_db()
    by_month = [_month_hours(conn, y, m) for y, m in months]
    all_lessons = conn.execute("SELECT * FROM lessons ORDER BY name").fetchall()
    conn.close()

    lessons = []
    for l in all_lessons:
        hours = [h.get(l["id"], 0) for h in by_month]
        if l["archived"] and not any(hours[1:]):
            continue
        changes = [
            round(100 * (cur - prev) / prev) if prev else None
            for prev, cur in zip(hours, hours[1:])
        ]
        lessons.append({"name": l["name"], "hours": hours[1:], "changes": changes})

    labels = [f"{calendar.month_abbr[m]} {y}" for y, m in months[1:]]
    return {"months": labels, "lessons": lessons}


# --- Monthly check table ---

def get_month_weeks(year, month):
    """The month's days grouped into calendar weeks (Mon-Sun): a list of lists of dates."""
    return [
        [d for d in week if d.month == month]
        for week in calendar.Calendar().monthdatescalendar(year, month)
    ]


def get_month_checks(year, month):
    """Set of (lesson_id, 'YYYY-MM-DD') that are checked in the given month."""
    conn = get_db()
    rows = conn.execute(
        "SELECT lesson_id, date FROM lesson_checks WHERE date LIKE ?",
        (f"{year}-{month:02d}-%",),
    ).fetchall()
    conn.close()
    return {(r["lesson_id"], r["date"]) for r in rows}


def set_check(lesson_id, date_str, done):
    conn = get_db()
    if done:
        conn.execute(
            "INSERT OR IGNORE INTO lesson_checks (lesson_id, date) VALUES (?, ?)",
            (lesson_id, date_str),
        )
    else:
        conn.execute(
            "DELETE FROM lesson_checks WHERE lesson_id = ? AND date = ?", (lesson_id, date_str)
        )
    conn.commit()
    conn.close()
