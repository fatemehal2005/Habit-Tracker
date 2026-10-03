# Study Tracker

A small personal web app for tracking study time. Define your lessons with a daily target in hours, run a timer while you study, and see how each month went compared with the plan and with earlier months.

## Features

- **Today** — one compact card per lesson with today's studied time against the daily target, a progress bar, and a Start/Stop button. A banner shows the running session and its elapsed time.
- **Monthly check table** — on the Today page: lessons as rows, every day of the current month as columns (grouped by week), a checkbox per day, and a result per lesson (days ticked out of the days in the month).
- **Timer on the server** — the running session is stored in the database, so it keeps counting when the phone locks and shows up on every device. Only one timer runs at a time: starting a lesson stops the one that was running.
- **Monthly report** — at the bottom of the Today page: actual vs planned hours per lesson as side-by-side bars (planned = daily target × days in the month) and the month's total.
- **Compare Months** — hours per lesson for the last 2–6 months, with the percent change versus the month before.
- **Manage Lessons** — add, rename, change the daily target, archive.
- **Sessions** — at the bottom right of the Today page: add a forgotten session, fix times, or delete.
- **Installable (PWA)** — add it to your phone's home screen.

## Tech stack

- **Backend:** Python + [Flask](https://flask.palletsprojects.com/), server-rendered with Jinja2 templates
- **Database:** SQLite (stdlib `sqlite3`, no ORM) — a single file at `data/plan.db`
- **Frontend:** vanilla HTML/CSS/JS, no build step; [Chart.js](https://www.chartjs.org/) is vendored in `static/vendor/`

This is intentionally a small, dependency-light app for one person.

## Getting started

**Requirements:** Python 3.9+

```bash
pip install -r requirements.txt
python3 app.py
```

Then open **http://127.0.0.1:5050** in your browser.

> Port 5000 is used by macOS's AirPlay Receiver on many Macs, which is why this app runs on 5050 instead.

## Using it from your phone and other devices

The app and its database stay on the Mac. [Tailscale](https://tailscale.com/) makes it reachable from your other devices without exposing it to the internet.

1. Install Tailscale on the Mac and on each device, and sign in with the same account.
2. With the app running, publish it to your tailnet:
   ```bash
   tailscale serve --bg 5050
   ```
3. Open the `https://<mac-name>.<tailnet>.ts.net` address it prints on your phone, then use "Add to Home Screen".

The Mac has to be awake and the app running for other devices to reach it. There is no login: anyone on your tailnet can open the app.

## How time is counted

- A session counts toward the day and month it **started** in, even if it runs past midnight.
- Planned hours always use the lesson's **current** daily target, including for past months.
- Archived lessons are hidden from Today, but still appear in the report of any month they were studied in.
- When adding or editing a session, an end time earlier than the start time means the session ended the next day.

## Seeding lessons

To start a fresh database with a set of lessons, fill in `SEED_LESSONS` in `db.py` (name, daily target in hours). They are inserted once, when the lessons table is empty.

## Tests

```bash
pip install pytest
python3 -m pytest tests
```

## Project structure

```
My Plan/
├── app.py               # Flask app factory / entry point
├── db.py                # SQLite connection, schema init, seed lessons
├── schema.sql           # Database schema
├── models.py            # All data-access logic (SQL lives here)
├── routes/
│   └── study.py         # All routes (today, timer, checks, compare, lessons, sessions)
├── templates/           # Jinja2 HTML templates
├── static/              # CSS, JS, Chart.js, PWA manifest/service worker/icon
├── tests/               # Model tests
└── data/
    └── plan.db          # SQLite database (gitignored)
```

## Data & privacy

All data stays in `data/plan.db` on your Mac. That file is excluded via `.gitignore`, so your study data won't accidentally get committed.
