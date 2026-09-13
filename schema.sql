CREATE TABLE IF NOT EXISTS months (
    id INTEGER PRIMARY KEY,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    locked_at TEXT,
    UNIQUE(year, month)
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS month_tasks (
    id INTEGER PRIMARY KEY,
    month_id INTEGER NOT NULL REFERENCES months(id),
    task_id INTEGER NOT NULL REFERENCES tasks(id),
    weekday INTEGER NOT NULL,
    UNIQUE(month_id, task_id, weekday)
);

CREATE TABLE IF NOT EXISTS daily_entries (
    id INTEGER PRIMARY KEY,
    month_id INTEGER NOT NULL REFERENCES months(id),
    task_id INTEGER NOT NULL REFERENCES tasks(id),
    date TEXT NOT NULL,
    done INTEGER NOT NULL DEFAULT 0,
    UNIQUE(month_id, task_id, date)
);

CREATE TABLE IF NOT EXISTS day_notes (
    id INTEGER PRIMARY KEY,
    month_id INTEGER NOT NULL REFERENCES months(id),
    date TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    UNIQUE(month_id, date)
);
