"""Режим подписки «Напомни, когда выходить»: дни, выбор рейса, расчёт времени, тексты.

Без сети и БД — только чистые функции, чтобы их было легко тестировать.
Время везде — строки 'ЧЧ:ММ' по местному времени (Europe/Samara).
"""
import html
import re
from datetime import date
from typing import NamedTuple


class Departure(NamedTuple):
    route: str
    departure: str  # ЧЧ:ММ отправления с начальной остановки
    arrival: str    # ЧЧ:ММ прибытия на конечную


MODE_SCHEDULE = "schedule"
MODE_REMIND = "remind"

DAYS_LABELS = {"all": "Каждый день", "weekdays": "Будни", "weekends": "Выходные"}
_DAYS_PHRASE = {"all": "Каждый день", "weekdays": "По будням", "weekends": "По выходным"}

LEAD_CHOICES = (5, 10, 15, 20, 30)
# За сколько минут до цели планируем напоминание; на столько же вперёд запрашиваем рейсы
PLAN_WINDOW_MIN = 60


def to_minutes(hhmm: str) -> int:
    hours, minutes = hhmm.split(":")
    return int(hours) * 60 + int(minutes)


def from_minutes(total: int) -> str:
    total = max(total, 0)  # не уходим во вчерашний день
    return f"{total // 60:02d}:{total % 60:02d}"


def day_matches(days: str, d: date) -> bool:
    if days == "weekdays":
        return d.weekday() < 5
    if days == "weekends":
        return d.weekday() >= 5
    return True


def should_plan(now: str, target: str) -> bool:
    """Окно планирования: [цель − 60 мин, цель), но не раньше полуночи."""
    t = to_minutes(target)
    return max(t - PLAN_WINDOW_MIN, 0) <= to_minutes(now) < t


_TIME_RE = re.compile(r"^\d{1,2}:\d{2}$")


def _is_time(value) -> bool:
    return bool(value) and bool(_TIME_RE.match(value))


def pick_trips(departures, target: str):
    """Первый рейс с отправлением не раньше цели и следующий за ним (любой может быть None)."""
    later = sorted((d for d in departures
                   if _is_time(d.departure) and to_minutes(d.departure) >= to_minutes(target)),
                   key=lambda d: to_minutes(d.departure))
    first = later[0] if later else None
    following = later[1] if len(later) > 1 else None
    return first, following


def fire_time(at: str, lead_min: int) -> str:
    return from_minutes(to_minutes(at) - lead_min)


def run_action(now: str, fire_at: str, dep_time: str | None, target: str | None = None) -> str:
    """'wait' — ещё рано, 'send' — отправлять, 'skip' — рейс уже ушёл (бот лежал).

    Без рейсов (dep_time=None) «рейсов нет» теряет смысл, когда время цели уже прошло."""
    if to_minutes(now) < to_minutes(fire_at):
        return "wait"
    if dep_time and to_minutes(now) >= to_minutes(dep_time):
        return "skip"
    if not dep_time and target and to_minutes(now) >= to_minutes(target):
        return "skip"
    return "send"


def route_name(custom_name: str | None, route: str) -> str:
    return custom_name or f"Маршрут {route}"


def reminder_text(name: str, route: str, dep_time: str, next_dep: str | None, now: str) -> str:
    left = to_minutes(dep_time) - to_minutes(now)
    lines = [
        f"🚶 <b>Пора выходить! «{html.escape(name)}»</b>",
        f"🚋 <b>{html.escape(route)}</b> отправляется в <b>{dep_time}</b> — через {left} мин.",
    ]
    if next_dep:
        lines.append(f"Следующий — в {next_dep}.")
    return "<br>".join(lines)


def no_trips_text(name: str, target: str) -> str:
    return f"😕 «{html.escape(name)}»: сегодня после {target} в течение часа рейсов нет."


def site_error_text(name: str) -> str:
    return f"🚫 «{html.escape(name)}»: не удалось получить расписание с сайта ИжГЭТ."


def sub_button_text(mode: str | None, notify_time: str) -> str:
    if mode == MODE_REMIND:
        return f"🚶 Напоминание {notify_time}"
    return f"📋 Расписание {notify_time}"


def summary_text(mode: str | None, days: str, notify_time: str, lead_min: int | None, timeint: str) -> str:
    if mode == MODE_REMIND:
        return f"🚶 {DAYS_LABELS[days]}, {notify_time}, за {lead_min} мин"
    return f"📋 {DAYS_LABELS[days]}, {notify_time}, расписание на {timeint} мин"


def confirmation_text(mode: str, days: str, notify_time: str, lead_min: int | None, timeint: str) -> str:
    when = _DAYS_PHRASE[days]
    if mode == MODE_REMIND:
        return f"✅ {when} напомню за {lead_min} мин до первого рейса после {notify_time}."
    return f"✅ {when} в {notify_time} буду присылать расписание на ближайшие {timeint} мин."
