import calendar
from datetime import date, datetime, timedelta

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

import models

bp = Blueprint("study", __name__)


@bp.app_template_filter("hm")
def hm(seconds):
    seconds = int(seconds)
    return f"{seconds // 3600}h {seconds % 3600 // 60:02d}m"


# --- Today + timer ---

@bp.route("/")
def today():
    day = date.today()
    month_str = request.args.get("month") or day.strftime("%Y-%m")
    year, month = (int(p) for p in month_str.split("-"))
    report = models.get_month_hours(year, month)
    chart = {
        "kind": "report",
        "labels": [l["name"] for l in report["lessons"]],
        "datasets": [
            {"label": "Actual", "data": [round(l["actual"], 2) for l in report["lessons"]]},
            {"label": "Planned", "data": [round(l["planned"], 2) for l in report["lessons"]]},
        ],
    }
    return render_template(
        "today.html",
        lessons=models.get_today(day),
        running=models.get_running_session(),
        today_str=day.isoformat(),
        month_name=f"{calendar.month_name[day.month]} {day.year}",
        weeks=models.get_month_weeks(day.year, day.month),
        checks=models.get_month_checks(day.year, day.month),
        report=report,
        chart=chart,
        sessions=models.list_recent_sessions(),
        all_lessons=models.list_lessons(include_archived=True),
        month_str=month_str,
        report_month_name=f"{calendar.month_name[month]} {year}",
    )


@bp.route("/checks/<int:lesson_id>/<date_str>", methods=["POST"])
def set_check(lesson_id, date_str):
    done = (request.get_json(silent=True) or {}).get("done", False)
    models.set_check(lesson_id, date_str, done)
    return jsonify({"ok": True})


@bp.route("/timer/start/<int:lesson_id>", methods=["POST"])
def start_timer(lesson_id):
    models.start_session(lesson_id)
    return redirect(url_for("study.today"))


@bp.route("/timer/stop", methods=["POST"])
def stop_timer():
    models.stop_running_session()
    return redirect(url_for("study.today"))


# --- Reports ---

@bp.route("/compare")
def compare():
    n = min(max(request.args.get("n", 3, type=int), 2), 6)
    today = date.today()
    data = models.get_comparison(n, today.year, today.month)
    chart = {
        "kind": "compare",
        "labels": [l["name"] for l in data["lessons"]],
        "datasets": [
            {"label": label, "data": [round(l["hours"][i], 2) for l in data["lessons"]]}
            for i, label in enumerate(data["months"])
        ],
    }
    return render_template("compare.html", **data, chart=chart, n=n)


# --- Manage lessons ---

@bp.route("/lessons", methods=["GET", "POST"])
def lessons():
    if request.method == "POST":
        name = request.form["name"].strip()
        if name and not models.add_lesson(name, float(request.form["target"])):
            flash(f'A lesson named "{name}" already exists.')
        return redirect(url_for("study.lessons"))
    return render_template("lessons.html", lessons=models.list_lessons(include_archived=True))


@bp.route("/lessons/<int:lesson_id>", methods=["POST"])
def update_lesson(lesson_id):
    name = request.form["name"].strip()
    if name and not models.update_lesson(lesson_id, name, float(request.form["target"])):
        flash(f'A lesson named "{name}" already exists.')
    return redirect(url_for("study.lessons"))


@bp.route("/lessons/<int:lesson_id>/archive", methods=["POST"])
def archive_lesson(lesson_id):
    models.set_archived(lesson_id, request.form["archived"] == "1")
    return redirect(url_for("study.lessons"))


# --- Edit sessions ---

def _session_times(form):
    """(start_at, end_at) strings from the date/start/end fields, or None if they are equal.
    An end time earlier than the start means the session ran past midnight."""
    start = datetime.fromisoformat(f"{form['date']}T{form['start']}")
    end = datetime.fromisoformat(f"{form['date']}T{form['end']}")
    if end == start:
        return None
    if end < start:
        end += timedelta(days=1)
    return start.strftime(models.TIME_FMT), end.strftime(models.TIME_FMT)


@bp.route("/sessions", methods=["POST"])
def add_session():
    times = _session_times(request.form)
    if times:
        models.add_session(int(request.form["lesson_id"]), *times)
    else:
        flash("Start and end time can't be the same.")
    return redirect(url_for("study.today", _anchor="sessions"))


@bp.route("/sessions/<int:session_id>", methods=["POST"])
def update_session(session_id):
    times = _session_times(request.form)
    if times:
        models.update_session(session_id, int(request.form["lesson_id"]), *times)
    else:
        flash("Start and end time can't be the same.")
    return redirect(url_for("study.today", _anchor="sessions"))


@bp.route("/sessions/<int:session_id>/delete", methods=["POST"])
def delete_session(session_id):
    models.delete_session(session_id)
    return redirect(url_for("study.today", _anchor="sessions"))
