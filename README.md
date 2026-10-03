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
