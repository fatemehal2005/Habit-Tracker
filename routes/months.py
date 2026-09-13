import calendar
from datetime import date

from flask import Blueprint, Response, flash, jsonify, redirect, render_template, request, url_for

import models
from models import WEEKDAY_NAMES

bp = Blueprint("months", __name__)


@bp.route("/")
def index():
    today = date.today()
    existing = models.get_month_by_year_month(today.year, today.month)
    if existing is None:
        flash("Set up this month's habits to get started.")
        return redirect(url_for("months.new_month"))
    if existing["status"] == "locked":
        return redirect(url_for("months.grid", month_id=existing["id"]))
    return redirect(url_for("months.view_month", month_id=existing["id"]))


@bp.route("/months")
def list_months():
    months = models.list_months()
    progress_by_id = {
        m["id"]: models.get_month_overall_progress(m["id"])
        for m in months
        if m["status"] == "locked"
    }
    trend = models.get_months_trend()
    return render_template(
        "month_list.html", months=months, progress_by_id=progress_by_id, trend=trend
    )


@bp.route("/months/new", methods=["GET", "POST"])
def new_month():
    today = date.today()
    if request.method == "POST":
        year = int(request.form["year"])
        month = int(request.form["month"])

        existing = models.get_month_by_year_month(year, month)
        if existing:
            month_id = existing["id"]
            if existing["status"] == "locked":
                flash("That month is already locked and cannot be edited.")
                return redirect(url_for("months.view_month", month_id=month_id))
        else:
            month_id = models.create_month(year, month)

        habit_names = request.form.getlist("habit_name")
        models.set_month_habits(month_id, habit_names)
        return redirect(url_for("months.view_month", month_id=month_id))

    existing = models.get_month_by_year_month(today.year, today.month)
    prefill_habits = models.get_month_habit_names(existing["id"]) if existing else []

    if request.args.get("copy") == "1":
        prev_habits = models.get_previous_month_habits(today.year, today.month)
        if prev_habits:
            prefill_habits = prev_habits
            flash("Copied habits from last month — review and save.")
        else:
            flash("No previous month with habits to copy from.")

    prev_habits_available = bool(models.get_previous_month_habits(today.year, today.month))

    return render_template(
        "month_new.html",
        default_year=today.year,
        default_month=today.month,
        prefill_habits=prefill_habits,
        prev_habits_available=prev_habits_available,
    )


@bp.route("/months/<int:month_id>")
def view_month(month_id):
    month = models.get_month(month_id)
    if month is None:
        flash("Month not found.")
        return redirect(url_for("months.list_months"))
    habit_names = models.get_month_habit_names(month_id)
    month_name = calendar.month_name[month["month"]]

    return render_template(
        "month_view.html", month=month, habit_names=habit_names, month_name=month_name
    )


@bp.route("/months/<int:month_id>/lock", methods=["POST"])
def lock_month(month_id):
    ok = models.lock_month(month_id)
    if ok:
        flash("Month started! Your habits are now locked in.")
        return redirect(url_for("months.grid", month_id=month_id))
    flash("Could not lock this month (already locked or not found).")
    return redirect(url_for("months.view_month", month_id=month_id))


@bp.route("/months/<int:month_id>/delete", methods=["POST"])
def delete_month(month_id):
    month = models.get_month(month_id)
    if month is None:
        flash("Month not found.")
        return redirect(url_for("months.list_months"))
    models.delete_month(month_id)
    flash(f"Deleted {calendar.month_name[month['month']]} {month['year']}.")
    return redirect(url_for("months.list_months"))


@bp.route("/months/<int:month_id>/grid")
def grid(month_id):
    month = models.get_month(month_id)
    if month is None:
        flash("Month not found.")
        return redirect(url_for("months.list_months"))
    if month["status"] != "locked":
        flash("Start this month first to begin checking off habits.")
        return redirect(url_for("months.view_month", month_id=month_id))
    data = models.get_month_grid(month_id)
    month_name = calendar.month_name[month["month"]]
    return render_template(
        "grid.html",
        **data,
        weekday_names=WEEKDAY_NAMES,
        today_str=date.today().isoformat(),
        month_name=month_name,
    )


@bp.route("/months/<int:month_id>/grid/entries/<int:entry_id>/toggle", methods=["POST"])
def toggle(month_id, entry_id):
    models.toggle_entry(entry_id)
    return jsonify({"ok": True})


@bp.route("/months/<int:month_id>/grid/mark-today", methods=["POST"])
def mark_today(month_id):
    models.mark_all_done(month_id, date.today().isoformat())
    flash("Marked today's habits as done.")
    return redirect(url_for("months.grid", month_id=month_id))


@bp.route("/months/<int:month_id>/notes/<date_str>", methods=["POST"])
def save_note(month_id, date_str):
    note = (request.get_json(silent=True) or {}).get("note", "")
    models.set_day_note(month_id, date_str, note)
    return jsonify({"ok": True})


@bp.route("/months/<int:month_id>/export.csv")
def export_csv(month_id):
    month = models.get_month(month_id)
    if month is None:
        flash("Month not found.")
        return redirect(url_for("months.list_months"))
    csv_data = models.export_month_csv(month_id)
    filename = f"habit-tracker-{month['year']}-{month['month']:02d}.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@bp.route("/months/<int:month_id>/report")
def report(month_id):
    month = models.get_month(month_id)
    if month is None:
        flash("Month not found.")
        return redirect(url_for("months.list_months"))
    data = models.get_month_report(month_id)
    month_name = calendar.month_name[month["month"]]
    return render_template("report.html", **data, month_name=month_name)
