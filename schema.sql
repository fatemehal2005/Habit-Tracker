CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    daily_target_hours REAL NOT NULL,
    archived INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY,
    lesson_id INTEGER NOT NULL REFERENCES lessons(id),
    start_at TEXT NOT NULL,
    end_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_sessions_start ON sessions(start_at);

CREATE TABLE IF NOT EXISTS lesson_checks (
    lesson_id INTEGER NOT NULL REFERENCES lessons(id),
    date TEXT NOT NULL,
    PRIMARY KEY (lesson_id, date)
);
