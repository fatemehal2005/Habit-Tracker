# Habit Tracker

A small local web app for planning a month of daily habits and watching your progress build up as the month goes on. Set up your habits once, lock the month in, and check things off every day from a single colorful grid.

## Features

- **Monthly habit grid** — habits as rows, the whole month's days (grouped into calendar weeks) as columns. Check things off with one click, no page reloads.
- **Locked months** — once you start a month, its habit list is locked in so it can't drift mid-month. Past months stay saved for history.
- **Progress everywhere** — a daily ring for today, an overall ring for the month so far, a per-habit progress column, a weekly bar chart, and a full report page (completion %, streaks, calendar heatmap).
- **Streak badges** — 🔥 next to any habit you're currently on a roll with.
- **Copy last month's habits** — don't retype your list every month.
- **Day notes** — jot a quick note on any day (e.g. "traveled", "sick").
- **CSV export** — download a month's data for backup or your own analysis.
- **History with trend chart** — see completion % across all your past months at a glance.
- **Installable (PWA)** — add it to your phone's home screen or install it as a standalone app.

## Tech stack

- **Backend:** Python + [Flask](https://flask.palletsprojects.com/), server-rendered with Jinja2 templates
- **Database:** SQLite (stdlib `sqlite3`, no ORM) — a single file at `data/plan.db`
- **Frontend:** vanilla HTML/CSS/JS, no build step, no framework

This is intentionally a small, dependency-light app — it's meant to run locally for one person, not to scale to many users.

## Getting started

**Requirements:** Python 3.9+

```bash
git clone <this-repo-url>
cd "My Plan"
pip install -r requirements.txt
python3 app.py
```

Then open **http://127.0.0.1:5050** in your browser.

> Port 5000 is used by macOS's AirPlay Receiver on many Macs, which is why this app runs on 5050 instead.

## Usage

1. **New Month** — enter a year/month and list your habits. Every habit applies every day of the month.
2. **Start This Month** — locks the habit list in and generates a checklist entry for every day.
3. **Check things off** on the grid as you go. Progress rings, the weekly chart, and the per-habit progress column update live.
4. **View report** for a full breakdown once the month's underway (or over): completion %, per-habit streaks, and a calendar heatmap.
5. **History** lists every month you've tracked, with a trend chart comparing them.

## Project structure

```
My Plan/
├── app.py               # Flask app factory / entry point
├── db.py                # SQLite connection + schema init
├── schema.sql            # Database schema
├── models.py             # All data-access logic (SQL lives here)
├── routes/
│   └── months.py         # All routes (setup, grid, report, history, notes, export...)
├── templates/             # Jinja2 HTML templates
├── static/                # CSS, JS, PWA manifest/service worker/icon
└── data/
    └── plan.db            # SQLite database (gitignored)
```

## Data & privacy

All data stays local in `data/plan.db` — nothing is sent anywhere. That file (along with your Python virtual environment, if you create one) is excluded via `.gitignore`, so your personal habit data won't accidentally get committed.
