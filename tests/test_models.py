import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db
import models


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()


def lesson_id(name):
    return next(l["id"] for l in models.list_lessons(include_archived=True) if l["name"] == name)


def test_starting_a_second_lesson_stops_the_first():
    models.add_lesson("Math", 2)
    models.add_lesson("Physics", 1)
    models.start_session(lesson_id("Math"))
    models.start_session(lesson_id("Physics"))

    running = [s for s in models.list_recent_sessions() if s["end_at"] is None]
    assert len(running) == 1
    assert running[0]["name"] == "Physics"
    assert models.get_running_session()["name"] == "Physics"

    models.stop_running_session()
    assert models.get_running_session() is None


def test_duplicate_lesson_name_is_rejected():
    assert models.add_lesson("Math", 2)
    assert not models.add_lesson("Math", 3)


def test_month_hours_planned_and_progress():
    models.add_lesson("Math", 2)
    math = lesson_id("Math")
    models.add_session(math, "2026-10-01T09:00:00", "2026-10-01T10:30:00")
    models.add_session(math, "2026-10-02T09:00:00", "2026-10-02T11:00:00")

    report = models.get_month_hours(2026, 10)
    row = report["lessons"][0]
    assert row["actual"] == 3.5
    assert row["planned"] == 62  # 2 h/day x 31 days
    assert row["pct"] == 6  # 3.5 / 62
    assert report["total"] == 3.5


def test_session_belongs_to_the_month_it_started_in():
    models.add_lesson("Math", 2)
    math = lesson_id("Math")
    models.add_session(math, "2026-09-30T23:00:00", "2026-10-01T01:00:00")

    assert models.get_month_hours(2026, 9)["lessons"][0]["actual"] == 2
    assert models.get_month_hours(2026, 10)["lessons"][0]["actual"] == 0


def test_archived_lesson_shows_only_in_months_it_was_studied():
    models.add_lesson("Math", 2)
    math = lesson_id("Math")
    models.add_session(math, "2026-09-10T09:00:00", "2026-09-10T10:00:00")
    models.set_archived(math, True)

    assert len(models.get_month_hours(2026, 9)["lessons"]) == 1
    assert models.get_month_hours(2026, 10)["lessons"] == []


def test_today_counts_only_sessions_started_that_day():
    models.add_lesson("Math", 2)
    math = lesson_id("Math")
    models.add_session(math, "2026-10-02T09:00:00", "2026-10-02T10:00:00")
    models.add_session(math, "2026-10-03T09:00:00", "2026-10-03T09:30:00")

    row = models.get_today(date(2026, 10, 3))[0]
    assert row["seconds"] == 1800
    assert row["ticking"] == 0


def test_comparison_percent_change():
    models.add_lesson("Math", 2)
    models.add_lesson("Physics", 1)
    math, physics = lesson_id("Math"), lesson_id("Physics")
    models.add_session(math, "2026-07-05T09:00:00", "2026-07-05T11:00:00")  # Jul: 2 h
    models.add_session(math, "2026-08-05T09:00:00", "2026-08-05T13:00:00")  # Aug: 4 h
    models.add_session(math, "2026-09-05T09:00:00", "2026-09-05T12:00:00")  # Sep: 3 h
    models.add_session(physics, "2026-10-05T09:00:00", "2026-10-05T10:00:00")  # Oct: 1 h

    cmp = models.get_comparison(3, 2026, 10)
    assert cmp["months"] == ["Aug 2026", "Sep 2026", "Oct 2026"]

    by_name = {l["name"]: l for l in cmp["lessons"]}
    assert by_name["Math"]["hours"] == [4, 3, 0]
    assert by_name["Math"]["changes"] == [100, -25, -100]
    assert by_name["Physics"]["hours"] == [0, 0, 1]
    assert by_name["Physics"]["changes"] == [None, None, None]  # previous month was 0


def test_comparison_wraps_across_years():
    assert models.get_comparison(3, 2026, 1)["months"] == ["Nov 2025", "Dec 2025", "Jan 2026"]


def test_month_weeks_cover_every_day_once():
    weeks = models.get_month_weeks(2026, 10)  # 1 Oct 2026 is a Thursday
    assert [len(w) for w in weeks] == [4, 7, 7, 7, 6]
    assert weeks[0][0] == date(2026, 10, 1) and weeks[-1][-1] == date(2026, 10, 31)


def test_checks_can_be_set_and_cleared():
    models.add_lesson("Math", 2)
    math = lesson_id("Math")
    models.set_check(math, "2026-10-03", True)
    models.set_check(math, "2026-10-03", True)
    models.set_check(math, "2026-09-30", True)
    assert models.get_month_checks(2026, 10) == {(math, "2026-10-03")}

    models.set_check(math, "2026-10-03", False)
    assert models.get_month_checks(2026, 10) == set()
