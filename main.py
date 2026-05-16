from flask import Flask, render_template, redirect, url_for, request
from datetime import datetime as dt
from calendar import monthrange
from pathlib import Path
import json
import os

app = Flask(__name__)


class FlaskApp:
    """Calendar web app with add, edit, delete, single and recurring events."""

    def __init__(self):
        self.todays_date = dt.today().date()

        self.base_dir = Path(__file__).resolve().parent

        # Use an environment variable if provided, otherwise use local data.json.
        self.calendar_file = Path(
            os.environ.get("CALENDAR_DATA_FILE", self.base_dir / "data.json")
        )

        self.ensure_calendar_file_exists()

        app.add_url_rule("/", view_func=self.home)
        app.add_url_rule("/previous-month", view_func=self.previous_month, methods=["POST"])
        app.add_url_rule("/next-month", view_func=self.next_month, methods=["POST"])
        app.add_url_rule("/change-date", view_func=self.change_date, methods=["POST"])
        app.add_url_rule("/select-day", view_func=self.select_day, methods=["POST"])
        app.add_url_rule("/add-event", view_func=self.add_event, methods=["POST"])
        app.add_url_rule("/edit-event", view_func=self.edit_event, methods=["POST"])
        app.add_url_rule("/delete-event", view_func=self.delete_event, methods=["POST"])

    def ensure_calendar_file_exists(self):
        """Create data.json if it does not exist."""
        if not self.calendar_file.exists():
            self.calendar_file.write_text(
                json.dumps({"events": {}}, indent=2),
                encoding="utf-8"
            )

    def load_calendar_data(self):
        """Load calendar events from JSON."""
        try:
            with open(file=self.calendar_file, mode="r", encoding="utf-8") as file:
                data = json.load(file)

            if "events" not in data:
                data["events"] = {}

            return data

        except FileNotFoundError:
            return {"events": {}}

        except json.JSONDecodeError:
            return {"events": {}}

    def save_calendar_data(self, data):
        """Save calendar data safely."""
        temp_file = self.calendar_file.with_suffix(".json.tmp")

        with open(file=temp_file, mode="w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)

        os.replace(temp_file, self.calendar_file)

    def parse_date(self, date_text):
        try:
            return dt.strptime(date_text, "%Y-%m-%d")
        except (TypeError, ValueError):
            return None

    def sort_events_by_time(self, events):
        def sort_by_time(event):
            event_time = event.get("time", "")

            if not event_time:
                return "99:99"

            return event_time

        return sorted(events, key=sort_by_time)

    def build_month_previews(self, year, month, calendar_data):
        """Build all event previews for the visible month in one pass."""
        days_in_month = monthrange(year, month)[1]

        month_previews = {}

        for day in range(1, days_in_month + 1):
            date_key = f"{year:04d}-{month:02d}-{day:02d}"
            month_previews[date_key] = []

        for saved_date, events in calendar_data.get("events", {}).items():
            saved_date_object = self.parse_date(saved_date)

            if not saved_date_object:
                continue

            for event_index, event in enumerate(events):
                event_type = event.get("type", "single")
                target_date = None

                if event_type == "single":
                    if saved_date_object.year == year and saved_date_object.month == month:
                        target_date = saved_date

                elif event_type == "recurring":
                    if saved_date_object.month == month:
                        target_date = f"{year:04d}-{saved_date_object.month:02d}-{saved_date_object.day:02d}"

                if target_date in month_previews:
                    preview_event = event.copy()
                    preview_event["event_date"] = saved_date
                    preview_event["event_index"] = event_index
                    preview_event["editable"] = True

                    month_previews[target_date].append(preview_event)

        for date_key, events in month_previews.items():
            month_previews[date_key] = self.sort_events_by_time(events)

        return month_previews

    def previous_month(self):
        current_month = request.form.get("current_month", type=int)
        current_year = request.form.get("current_year", type=int)

        if not current_month or not current_year:
            current_month = self.todays_date.month
            current_year = self.todays_date.year

        current_month -= 1

        if current_month < 1:
            current_month = 12
            current_year -= 1

        return redirect(url_for("home", month=current_month, year=current_year))

    def next_month(self):
        current_month = request.form.get("current_month", type=int)
        current_year = request.form.get("current_year", type=int)

        if not current_month or not current_year:
            current_month = self.todays_date.month
            current_year = self.todays_date.year

        current_month += 1

        if current_month > 12:
            current_month = 1
            current_year += 1

        return redirect(url_for("home", month=current_month, year=current_year))

    def change_date(self):
        month = request.form.get("month", type=int)
        year = request.form.get("year", type=int)

        if not month or not year:
            month = self.todays_date.month
            year = self.todays_date.year

        return redirect(url_for("home", month=month, year=year))

    def select_day(self):
        selected_date = request.form.get("selected_date")
        selected_date_object = self.parse_date(selected_date)

        if not selected_date_object:
            return redirect(url_for("home"))

        return redirect(url_for(
            "home",
            month=selected_date_object.month,
            year=selected_date_object.year,
            selected_date=selected_date
        ))

    def add_event(self):
        event_date = request.form.get("event_date")
        event_type = request.form.get("event_type", "single")
        title = request.form.get("title", "").strip()
        time = request.form.get("time", "").strip()
        description = request.form.get("description", "").strip()

        event_date_object = self.parse_date(event_date)

        if not event_date_object or not title:
            return redirect(url_for("home"))

        calendar_data = self.load_calendar_data()

        if "events" not in calendar_data:
            calendar_data["events"] = {}

        if event_date not in calendar_data["events"]:
            calendar_data["events"][event_date] = []

        calendar_data["events"][event_date].append({
            "type": event_type,
            "title": title,
            "time": time,
            "description": description,
            "completed": False,
        })

        self.save_calendar_data(calendar_data)

        return redirect(url_for(
            "home",
            month=event_date_object.month,
            year=event_date_object.year,
            selected_date=event_date
        ))

    def edit_event(self):
        old_event_date = request.form.get("event_date")
        new_event_date = request.form.get("new_event_date")
        event_index = request.form.get("event_index", type=int)
        event_type = request.form.get("event_type", "single")
        title = request.form.get("title", "").strip()
        time = request.form.get("time", "").strip()
        description = request.form.get("description", "").strip()

        new_event_date_object = self.parse_date(new_event_date)

        if not old_event_date or not new_event_date_object or event_index is None or not title:
            return redirect(url_for("home"))

        calendar_data = self.load_calendar_data()
        events = calendar_data.get("events", {}).get(old_event_date, [])

        if event_index < 0 or event_index >= len(events):
            return redirect(url_for("home"))

        updated_event = {
            "type": event_type,
            "title": title,
            "time": time,
            "description": description,
            "completed": events[event_index].get("completed", False),
        }

        events.pop(event_index)

        if len(events) == 0:
            del calendar_data["events"][old_event_date]

        if "events" not in calendar_data:
            calendar_data["events"] = {}

        if new_event_date not in calendar_data["events"]:
            calendar_data["events"][new_event_date] = []

        calendar_data["events"][new_event_date].append(updated_event)

        self.save_calendar_data(calendar_data)

        return redirect(url_for(
            "home",
            month=new_event_date_object.month,
            year=new_event_date_object.year,
            selected_date=new_event_date
        ))

    def delete_event(self):
        event_date = request.form.get("event_date")
        event_index = request.form.get("event_index", type=int)
        return_date = request.form.get("return_date") or event_date

        return_date_object = self.parse_date(return_date)

        if not event_date or event_index is None:
            return redirect(url_for("home"))

        calendar_data = self.load_calendar_data()
        events = calendar_data.get("events", {}).get(event_date, [])

        if event_index < 0 or event_index >= len(events):
            return redirect(url_for("home"))

        events.pop(event_index)

        if len(events) == 0:
            del calendar_data["events"][event_date]

        self.save_calendar_data(calendar_data)

        if return_date_object:
            return redirect(url_for(
                "home",
                month=return_date_object.month,
                year=return_date_object.year,
                selected_date=return_date
            ))

        return redirect(url_for("home"))

    def format_selected_date(self, date):
        if not date:
            return "Select a day"

        date_object = self.parse_date(date)

        if not date_object:
            return "Select a day"

        day = date_object.day

        if 10 <= day % 100 <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

        return f"{date_object.strftime('%a')} {day}{suffix} {date_object.strftime('%B %Y')}"

    def home(self):
        month = request.args.get("month", default=self.todays_date.month, type=int)
        year = request.args.get("year", default=self.todays_date.year, type=int)
        selected_date = request.args.get("selected_date", default=None, type=str)

        if not month or month < 1 or month > 12:
            month = self.todays_date.month

        if not year:
            year = self.todays_date.year

        selected_date_object = self.parse_date(selected_date)

        if selected_date and not selected_date_object:
            selected_date = None

        current_date_object = dt(year, month, 1)
        current_monthrange = monthrange(year, month)

        first_weekday = current_monthrange[0]
        days_in_month = current_monthrange[1]
        last_weekday = (first_weekday + days_in_month - 1) % 7
        remaining_days = 6 - last_weekday

        calendar_data = self.load_calendar_data()
        month_previews = self.build_month_previews(year, month, calendar_data)

        selected_events = []

        if selected_date:
            selected_events = month_previews.get(selected_date, [])

        return render_template(
            "index.html",
            current_month_name=current_date_object.strftime("%B").strip(),
            current_year=year,
            current_month=month,
            day_week_name_dict=range(1, days_in_month + 1),
            current_monthrange=range(first_weekday),
            remaining_days=range(remaining_days),
            current_day=self.todays_date.day,
            todays_month_name=dt(
                self.todays_date.year,
                self.todays_date.month,
                self.todays_date.day
            ).strftime("%B").strip(),
            todays_year=self.todays_date.year,
            month_previews=month_previews,
            selected_date=selected_date,
            selected_date_text=self.format_selected_date(selected_date),
            selected_events=selected_events,
        )


flask_app = FlaskApp()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)