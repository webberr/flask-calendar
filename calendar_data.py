import json
import os
import time

from gregorian_calendar import GregorianCalendar


class CalendarData:

    REPETITION_TYPE_WEEKLY = "w"
    REPETITION_TYPE_MONTHLY = "m"
    REPETITION_SUBTYPE_WEEK_DAY = "w"
    REPETITION_SUBTYPE_MONTH_DAY = "m"

    def __init__(self, data_folder):
        self.data_folder = data_folder

    def load_calendar(self, filename):
        with open(os.path.join(".", self.data_folder, "{}.json".format(filename))) as file:
            contents = json.load(file)
        return contents

    def tasks_from_calendar(self, year, month, view_past_tasks=True, data=None, calendar_id=None):
        if data is None and calendar_id is None:
            raise ValueError("Need to provide either calendar_id or loaded data")
        if data is None and calendar_id is not None:
            data = self.load_calendar(calendar_id)

        tasks = {}
        if str(year) in data["tasks"]["normal"]:
            if str(month) in data["tasks"]["normal"][str(year)]:
                tasks = data["tasks"]["normal"][str(year)][str(month)]

        if not view_past_tasks:
            current_day, current_month, current_year = GregorianCalendar.current_date()
            if year < current_year:
                tasks = {}
            elif year == current_year:
                if month < current_month:
                    tasks = {}
                else:
                    for day in tasks.keys():
                        if month == current_month and int(day) < current_day:
                            tasks[day] = []

        return tasks

    def add_repetitive_tasks_from_calendar(self, year, month, data, tasks, view_past_tasks=True):
        current_day, current_month, current_year = GregorianCalendar.current_date()

        repetitive_tasks = self._repetitive_tasks_from_calendar(
            year=year,
            month=month,
            month_days=GregorianCalendar.month_days_with_weekday(year=year, month=month),
            data=data)

        for day, day_tasks in repetitive_tasks.items():
            if not view_past_tasks:
                if year < current_year:
                    continue
                if year == current_year:
                    if month < current_month or (month == current_month and int(day) < current_day):
                        continue
            if day not in tasks:
                tasks[day] = []
            for task in day_tasks:
                tasks[day].append(task)

        return tasks

    def _repetitive_tasks_from_calendar(self, year, month, month_days, calendar_id=None, data=None):
        if data is None and calendar_id is None:
            raise ValueError("Need to provide either calendar_id or loaded data")
        if data is None and calendar_id is not None:
            data = self.load_calendar(calendar_id)

        repetitive_tasks = {}
        year_str = str(year)
        month_str = str(month)

        for task in data["tasks"]["repetition"]:
            id_str = str(task["id"])
            monthly_task_assigned = False
            for week in month_days:
                for weekday, day in enumerate(week):
                    if day == 0:
                        continue
                    if self._is_repetition_hidden(data, id_str, year_str, month_str, str(day)):
                        continue
                    if task["repetition_type"] == self.REPETITION_TYPE_WEEKLY:
                        if task["repetition_value"] == weekday:
                            self.add_task_to_list(repetitive_tasks, day, task)
                    elif task["repetition_type"] == self.REPETITION_TYPE_MONTHLY:
                        if task["repetition_subtype"] == self.REPETITION_SUBTYPE_WEEK_DAY:
                            if task["repetition_value"] == weekday and not monthly_task_assigned:
                                monthly_task_assigned = True
                                self.add_task_to_list(repetitive_tasks, day, task)
                        else:
                            if task["repetition_value"] == day:
                                self.add_task_to_list(repetitive_tasks, day, task)

        return repetitive_tasks

    @staticmethod
    def _is_repetition_hidden(data, id_str, year_str, month_str, day_str):
        if id_str in data["tasks"]["hidden_repetition"]:
            if (year_str in data["tasks"]["hidden_repetition"][id_str] and
                    month_str in data["tasks"]["hidden_repetition"][id_str][year_str] and
                    day_str in data["tasks"]["hidden_repetition"][id_str][year_str][month_str]):
                return True
        return False

    @staticmethod
    def add_task_to_list(tasks, day, new_task):
        day_str = str(day)
        if day_str not in tasks:
            tasks[day_str] = []
        tasks[day_str].append(new_task)

    def delete_task(self, calendar_id, year_str, month_str, day_str, task_id):
        data = self.load_calendar(calendar_id)

        if (year_str in data["tasks"]["normal"] and
                month_str in data["tasks"]["normal"][year_str] and
                day_str in data["tasks"]["normal"][year_str][month_str]):
            for index, task in enumerate(data["tasks"]["normal"][year_str][month_str][day_str]):
                if task["id"] == task_id:
                    data["tasks"]["normal"][year_str][month_str][day_str].pop(index)
        else:
            for index, task in enumerate(data["tasks"]["repetition"]):
                if task["id"] == task_id:
                    data["tasks"]["repetition"].pop(index)
                    if str(task_id) in data["tasks"]["hidden_repetition"]:
                        del(data["tasks"]["hidden_repetition"][str(task_id)])

        self._save_calendar(contents=data, filename=calendar_id)

    def update_task_day(self, calendar_id, year_str, month_str, day_str, task_id, new_day_str):
        data = self.load_calendar(calendar_id)

        task_to_update = None
        for index, task in enumerate(data["tasks"]["normal"][year_str][month_str][day_str]):
            if task["id"] == task_id:
                task_to_update = data["tasks"]["normal"][year_str][month_str][day_str].pop(index)

        if task_to_update is None:
            return

        if new_day_str not in data["tasks"]["normal"][year_str][month_str]:
            data["tasks"]["normal"][year_str][month_str][new_day_str] = []
        data["tasks"]["normal"][year_str][month_str][new_day_str].append(task_to_update)

        self._save_calendar(contents=data, filename=calendar_id)

    def create_task(self, calendar_id, year, month, day, title, is_all_day, due_time, details, color, has_repetition,
                    repetition_type, repetition_subtype, repetition_value):
        details = details if len(details) > 0 else "&nbsp;"
        data = self.load_calendar(calendar_id)

        new_task = {
            "id": int(time.time()),
            "color": color,
            "due_time": due_time,
            "is_all_day": is_all_day,
            "title": title,
            "details": details
        }
        if has_repetition:
            if repetition_type == self.REPETITION_SUBTYPE_MONTH_DAY and repetition_value == 0:
                return False
            new_task["repetition_type"] = repetition_type
            new_task["repetition_subtype"] = repetition_subtype
            new_task["repetition_value"] = repetition_value
            data["tasks"]["repetition"].append(new_task)
        else:
            if year is None or month is None or day is None:
                return False
            year_str = str(year)
            month_str = str(month)
            day_str = str(day)
            if year_str not in data["tasks"]["normal"]:
                data["tasks"]["normal"][year_str] = {}
            if month_str not in data["tasks"]["normal"][year_str]:
                data["tasks"]["normal"][year_str][month_str] = {}
            if day_str not in data["tasks"]["normal"][year_str][month_str]:
                data["tasks"]["normal"][year_str][month_str][day_str] = []
            data["tasks"]["normal"][year_str][month_str][day_str].append(new_task)

        self._save_calendar(contents=data, filename=calendar_id)
        return True

    def hide_repetition_task_instance(self, calendar_id, year_str, month_str, day_str, task_id_str):
        data = self.load_calendar(calendar_id)

        if task_id_str not in data["tasks"]["hidden_repetition"]:
            data["tasks"]["hidden_repetition"][task_id_str] = {}
        if year_str not in data["tasks"]["hidden_repetition"][task_id_str]:
            data["tasks"]["hidden_repetition"][task_id_str][year_str] = {}
        if month_str not in data["tasks"]["hidden_repetition"][task_id_str][year_str]:
            data["tasks"]["hidden_repetition"][task_id_str][year_str][month_str] = {}
        data["tasks"]["hidden_repetition"][task_id_str][year_str][month_str][day_str] = True

        self._save_calendar(contents=data, filename=calendar_id)

    def _save_calendar(self, contents, filename):
        self._clear_empty_entries(data=contents)
        with open(os.path.join(".", self.data_folder, "{}.json".format(filename)), "w+") as file:
            json.dump(contents, file)

    @staticmethod
    def _clear_empty_entries(data):
        for year in data["tasks"]["normal"]:
            months_to_delete = []
            for month in data["tasks"]["normal"][year]:
                days_to_delete = []
                for day in data["tasks"]["normal"][year][month]:
                    if len(data["tasks"]["normal"][year][month][day]) == 0:
                        days_to_delete.append(day)
                for day in days_to_delete:
                    del(data["tasks"]["normal"][year][month][day])
                if len(data["tasks"]["normal"][year][month]) == 0:
                    months_to_delete.append(month)
            for month in months_to_delete:
                del(data["tasks"]["normal"][year][month])
