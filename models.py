import calendar
import csv
import io
from datetime import date

from db import get_db

WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def list_months():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM months ORDER BY year DESC, month DESC"
    ).fetchall()
    conn.close()
    return rows


def get_month(month_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM months WHERE id = ?", (month_id,)).fetchone()
    conn.close()
    return row


def get_month_by_year_month(year, month):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM months WHERE year = ? AND month = ?", (year, month)
    ).fetchone()
    conn.close()
    return row


def create_month(year, month):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO months (year, month, status) VALUES (?, ?, 'draft')",
        (year, month),
    )
    conn.commit()
    month_id = cur.lastrowid
    conn.close()
    return month_id


def get_or_create_task(conn, name):
    row = conn.execute("SELECT id FROM tasks WHERE name = ?", (name,)).fetchone()
    if row:
        return row["id"]
    cur = conn.execute("INSERT INTO tasks (name) VALUES (?)", (name,))
    return cur.lastrowid


ALL_WEEKDAYS = [0, 1, 2, 3, 4, 5, 6]


def set_month_habits(month_id, habit_names):
    """habit_names: list of habit name strings. Each applies every day of the week."""
    conn = get_db()
    conn.execute("DELETE FROM month_tasks WHERE month_id = ?", (month_id,))
    for name in habit_names:
        name = name.strip()
        if not name:
            continue
        task_id = get_or_create_task(conn, name)
        for wd in ALL_WEEKDAYS:
            conn.execute(
                "INSERT OR IGNORE INTO month_tasks (month_id, task_id, weekday) VALUES (?, ?, ?)",
                (month_id, task_id, wd),
            )
    conn.commit()
    conn.close()


def get_month_habit_names(month_id):
    conn = get_db()
    rows = conn.execute(
        """SELECT DISTINCT t.name
           FROM month_tasks mt JOIN tasks t ON t.id = mt.task_id
           WHERE mt.month_id = ?
           ORDER BY t.name""",
        (month_id,),
    ).fetchall()
    conn.close()
    return [r["name"] for r in rows]


def get_previous_month_habits(year, month):
    """Habit names from the most recent month before (year, month) that has any habits set."""
    conn = get_db()
    row = conn.execute(
        """SELECT id FROM months
           WHERE (year < ?) OR (year = ? AND month < ?)
           ORDER BY year DESC, month DESC
           LIMIT 1""",
        (year, year, month),
    ).fetchone()
    conn.close()
    if row is None:
        return []
    return get_month_habit_names(row["id"])


def delete_month(month_id):
    conn = get_db()
    conn.execute("DELETE FROM daily_entries WHERE month_id = ?", (month_id,))
    conn.execute("DELETE FROM month_tasks WHERE month_id = ?", (month_id,))
    conn.execute("DELETE FROM day_notes WHERE month_id = ?", (month_id,))
    conn.execute("DELETE FROM months WHERE id = ?", (month_id,))
    conn.commit()
    conn.close()


def get_month_schedule(month_id):
    """Returns list of rows: task_id, task name, weekday."""
    conn = get_db()
    rows = conn.execute(
        """SELECT mt.task_id, t.name, mt.weekday
           FROM month_tasks mt JOIN tasks t ON t.id = mt.task_id
           WHERE mt.month_id = ?
           ORDER BY t.name, mt.weekday""",
        (month_id,),
    ).fetchall()
    conn.close()
    return rows


def lock_month(month_id):
    conn = get_db()
    month = conn.execute("SELECT * FROM months WHERE id = ?", (month_id,)).fetchone()
    if month is None or month["status"] != "draft":
        conn.close()
        return False

    schedule = conn.execute(
        "SELECT task_id, weekday FROM month_tasks WHERE month_id = ?", (month_id,)
    ).fetchall()

    by_weekday = {}
    for row in schedule:
        by_weekday.setdefault(row["weekday"], []).append(row["task_id"])

    _, days_in_month = calendar.monthrange(month["year"], month["month"])
    for day in range(1, days_in_month + 1):
        d = date(month["year"], month["month"], day)
        weekday = d.weekday()
        for task_id in by_weekday.get(weekday, []):
            conn.execute(
                "INSERT OR IGNORE INTO daily_entries (month_id, task_id, date, done) VALUES (?, ?, ?, 0)",
                (month_id, task_id, d.isoformat()),
            )

    conn.execute(
        "UPDATE months SET status = 'locked', locked_at = ? WHERE id = ?",
        (date.today().isoformat(), month_id),
    )
    conn.commit()
    conn.close()
    return True


def get_daily_entries(date_str):
    conn = get_db()
    rows = conn.execute(
        """SELECT de.id, de.task_id, t.name, de.done
           FROM daily_entries de JOIN tasks t ON t.id = de.task_id
           WHERE de.date = ?
           ORDER BY t.name""",
        (date_str,),
    ).fetchall()
    conn.close()
    return rows


def get_month_grid(month_id):
    """Returns habits (rows) x calendar weeks (Mon-Sun columns) for checking off the whole month."""
    conn = get_db()
    month = conn.execute("SELECT * FROM months WHERE id = ?", (month_id,)).fetchone()

    habits = conn.execute(
        """SELECT DISTINCT t.id AS task_id, t.name
           FROM daily_entries de JOIN tasks t ON t.id = de.task_id
           WHERE de.month_id = ?
           ORDER BY t.name""",
        (month_id,),
    ).fetchall()

    entries = conn.execute(
        "SELECT id, task_id, date, done FROM daily_entries WHERE month_id = ?",
        (month_id,),
    ).fetchall()
    conn.close()

    entry_map = {(e["task_id"], e["date"]): e for e in entries}

    _, days_in_month = calendar.monthrange(month["year"], month["month"])
    weeks = _build_date_weeks(month["year"], month["month"], days_in_month)

    by_date = {}
    for e in entries:
        by_date.setdefault(e["date"], []).append(e["done"])

    weekly_progress = []
    for i, week in enumerate(weeks, start=1):
        total = 0
        done = 0
        for cell in week:
            if cell is None:
                continue
            for d in by_date.get(cell["date"], []):
                total += 1
                done += d
        pct = round(100 * done / total) if total else 0
        weekly_progress.append({"label": f"Week {i}", "done": done, "total": total, "pct": pct})

    today_str = date.today().isoformat()
    today_vals = by_date.get(today_str)
    today_progress = None
    if today_vals is not None:
        total = len(today_vals)
        done = sum(today_vals)
        pct = round(100 * done / total) if total else 0
        today_progress = {"date": today_str, "done": done, "total": total, "pct": pct}

    by_task = {}
    for e in entries:
        by_task.setdefault(e["task_id"], []).append(e["done"])

    entries_by_task = {}
    for e in entries:
        entries_by_task.setdefault(e["task_id"], []).append(e)

    habit_progress = {}
    for h in habits:
        vals = by_task.get(h["task_id"], [])
        total = len(vals)
        done = sum(vals)
        pct = round(100 * done / total) if total else 0

        dated = sorted(entries_by_task.get(h["task_id"], []), key=lambda e: e["date"])
        current_streak = 0
        for e in reversed(dated):
            if e["done"]:
                current_streak += 1
            else:
                break

        habit_progress[h["task_id"]] = {
            "done": done,
            "total": total,
            "pct": pct,
            "current_streak": current_streak,
        }

    overall_total = len(entries)
    overall_done = sum(e["done"] for e in entries)
    overall_pct = round(100 * overall_done / overall_total) if overall_total else 0
    overall_progress = {"done": overall_done, "total": overall_total, "pct": overall_pct}

    day_notes = get_day_notes(month_id)

    return {
        "month": month,
        "habits": habits,
        "weeks": weeks,
        "entry_map": entry_map,
        "weekly_progress": weekly_progress,
        "today_progress": today_progress,
        "habit_progress": habit_progress,
        "overall_progress": overall_progress,
        "day_notes": day_notes,
    }


def get_day_notes(month_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT date, note FROM day_notes WHERE month_id = ?", (month_id,)
    ).fetchall()
    conn.close()
    return {r["date"]: r["note"] for r in rows}


def set_day_note(month_id, date_str, note):
    conn = get_db()
    note = note.strip()
    if note:
        conn.execute(
            """INSERT INTO day_notes (month_id, date, note) VALUES (?, ?, ?)
               ON CONFLICT(month_id, date) DO UPDATE SET note = excluded.note""",
            (month_id, date_str, note),
        )
    else:
        conn.execute(
            "DELETE FROM day_notes WHERE month_id = ? AND date = ?", (month_id, date_str)
        )
    conn.commit()
    conn.close()


def mark_all_done(month_id, date_str):
    conn = get_db()
    conn.execute(
        "UPDATE daily_entries SET done = 1 WHERE month_id = ? AND date = ?",
        (month_id, date_str),
    )
    conn.commit()
    conn.close()


def get_months_trend():
    """Overall completion % for every locked month, oldest first, for a history trend chart."""
    conn = get_db()
    months = conn.execute(
        "SELECT id, year, month FROM months WHERE status = 'locked' ORDER BY year, month"
    ).fetchall()
    trend = []
    for m in months:
        row = conn.execute(
            "SELECT COUNT(*) AS total, SUM(done) AS done FROM daily_entries WHERE month_id = ?",
            (m["id"],),
        ).fetchone()
        total = row["total"] or 0
        done = row["done"] or 0
        pct = round(100 * done / total) if total else 0
        trend.append(
            {
                "label": f"{calendar.month_abbr[m['month']]} {m['year']}",
                "pct": pct,
            }
        )
    conn.close()
    return trend


def export_month_csv(month_id):
    conn = get_db()
    month = conn.execute("SELECT * FROM months WHERE id = ?", (month_id,)).fetchone()
    habits = conn.execute(
        """SELECT DISTINCT t.id AS task_id, t.name
           FROM daily_entries de JOIN tasks t ON t.id = de.task_id
           WHERE de.month_id = ?
           ORDER BY t.name""",
        (month_id,),
    ).fetchall()
    entries = conn.execute(
        "SELECT task_id, date, done FROM daily_entries WHERE month_id = ?", (month_id,)
    ).fetchall()
    notes = conn.execute(
        "SELECT date, note FROM day_notes WHERE month_id = ?", (month_id,)
    ).fetchall()
    conn.close()

    note_map = {r["date"]: r["note"] for r in notes}
    value_map = {(e["task_id"], e["date"]): e["done"] for e in entries}

    _, days_in_month = calendar.monthrange(month["year"], month["month"])
    dates = [date(month["year"], month["month"], d).isoformat() for d in range(1, days_in_month + 1)]

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Date"] + [h["name"] for h in habits] + ["Note"])
    for d in dates:
        row = [d]
        for h in habits:
            val = value_map.get((h["task_id"], d))
            row.append("" if val is None else val)
        row.append(note_map.get(d, ""))
        writer.writerow(row)
    return buf.getvalue()


def get_month_overall_progress(month_id):
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) AS total, SUM(done) AS done FROM daily_entries WHERE month_id = ?",
        (month_id,),
    ).fetchone()
    conn.close()
    total = row["total"] or 0
    done = row["done"] or 0
    pct = round(100 * done / total) if total else None
    return {"done": done, "total": total, "pct": pct}


def toggle_entry(entry_id):
    conn = get_db()
    row = conn.execute(
        "SELECT done FROM daily_entries WHERE id = ?", (entry_id,)
    ).fetchone()
    if row is None:
        conn.close()
        return
    new_val = 0 if row["done"] else 1
    conn.execute("UPDATE daily_entries SET done = ? WHERE id = ?", (new_val, entry_id))
    conn.commit()
    conn.close()


def get_month_report(month_id):
    conn = get_db()
    month = conn.execute("SELECT * FROM months WHERE id = ?", (month_id,)).fetchone()

    overall = conn.execute(
        "SELECT COUNT(*) AS total, SUM(done) AS done FROM daily_entries WHERE month_id = ?",
        (month_id,),
    ).fetchone()
    total = overall["total"] or 0
    done = overall["done"] or 0
    overall_pct = round(100 * done / total) if total else 0

    per_task_rows = conn.execute(
        """SELECT t.id AS task_id, t.name,
                  COUNT(*) AS scheduled,
                  SUM(de.done) AS completed
           FROM daily_entries de JOIN tasks t ON t.id = de.task_id
           WHERE de.month_id = ?
           GROUP BY t.id, t.name
           ORDER BY t.name""",
        (month_id,),
    ).fetchall()

    per_task = []
    for r in per_task_rows:
        scheduled = r["scheduled"] or 0
        completed = r["completed"] or 0
        pct = round(100 * completed / scheduled) if scheduled else 0

        dated_rows = conn.execute(
            """SELECT date, done FROM daily_entries
               WHERE month_id = ? AND task_id = ? ORDER BY date""",
            (month_id, r["task_id"]),
        ).fetchall()
        best_streak = 0
        current_streak = 0
        running = 0
        for dr in dated_rows:
            if dr["done"]:
                running += 1
                best_streak = max(best_streak, running)
            else:
                running = 0
        # current streak = trailing run of done days up to the last entry
        for dr in reversed(dated_rows):
            if dr["done"]:
                current_streak += 1
            else:
                break

        per_task.append(
            {
                "name": r["name"],
                "scheduled": scheduled,
                "completed": completed,
                "pct": pct,
                "best_streak": best_streak,
                "current_streak": current_streak,
            }
        )

    daily_rows = conn.execute(
        """SELECT date, COUNT(*) AS scheduled, SUM(done) AS completed
           FROM daily_entries WHERE month_id = ? GROUP BY date""",
        (month_id,),
    ).fetchall()
    daily_ratio = {
        r["date"]: (r["completed"] or 0) / r["scheduled"] if r["scheduled"] else None
        for r in daily_rows
    }

    conn.close()

    _, days_in_month = calendar.monthrange(month["year"], month["month"])
    weeks = _build_calendar_weeks(month["year"], month["month"], days_in_month, daily_ratio)

    return {
        "month": month,
        "overall_pct": overall_pct,
        "total": total,
        "done": done,
        "per_task": per_task,
        "weeks": weeks,
    }


def _build_date_weeks(year, month, days_in_month):
    """List of week-rows (Mon-Sun), each a list of 7 items: {day, date} or None for out-of-month cells."""
    first_weekday = date(year, month, 1).weekday()
    weeks = []
    week = [None] * first_weekday
    for day in range(1, days_in_month + 1):
        d = date(year, month, day)
        week.append({"day": day, "date": d.isoformat()})
        if len(week) == 7:
            weeks.append(week)
            week = []
    if week:
        while len(week) < 7:
            week.append(None)
        weeks.append(week)
    return weeks


def _build_calendar_weeks(year, month, days_in_month, daily_ratio):
    weeks = _build_date_weeks(year, month, days_in_month)
    for week in weeks:
        for cell in week:
            if cell is not None:
                cell["ratio"] = daily_ratio.get(cell["date"])
    return weeks
