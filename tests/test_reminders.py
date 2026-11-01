from datetime import date

import pytest

import reminders
from reminders import Departure

MONDAY = date(2026, 10, 26)
SATURDAY = date(2026, 10, 24)
SUNDAY = date(2026, 10, 25)


@pytest.mark.parametrize("days, d, expected", [
    ("all", MONDAY, True), ("all", SATURDAY, True),
    ("weekdays", MONDAY, True), ("weekdays", SATURDAY, False), ("weekdays", SUNDAY, False),
    ("weekends", MONDAY, False), ("weekends", SATURDAY, True), ("weekends", SUNDAY, True),
])
def test_day_matches(days, d, expected):
    assert reminders.day_matches(days, d) is expected


def test_minutes_roundtrip():
    assert reminders.to_minutes("08:07") == 487
    assert reminders.from_minutes(487) == "08:07"
    assert reminders.from_minutes(-20) == "00:00"


@pytest.mark.parametrize("now, expected", [
    ("06:59", False), ("07:00", True), ("07:59", True), ("08:00", False), ("09:00", False),
])
def test_should_plan_window(now, expected):
    assert reminders.should_plan(now, "08:00") is expected


def test_should_plan_after_midnight_starts_at_midnight():
    assert reminders.should_plan("00:00", "00:30") is True
    assert reminders.should_plan("23:50", "00:30") is False


DEPS = [Departure("1", "07:58", "08:20"), Departure("1", "08:07", "08:27"),
        Departure("1", "08:17", "08:37"), Departure("1", "08:27", "08:47")]


def test_pick_trips_first_not_earlier_than_target():
    first, following = reminders.pick_trips(DEPS, "08:00")
    assert first == Departure("1", "08:07", "08:27")
    assert following == Departure("1", "08:17", "08:37")


def test_pick_trips_exact_target_counts():
    first, _ = reminders.pick_trips(DEPS, "08:07")
    assert first.departure == "08:07"


def test_pick_trips_single_and_none():
    assert reminders.pick_trips(DEPS[-1:], "08:00") == (DEPS[-1], None)
    assert reminders.pick_trips([], "08:00") == (None, None)
    assert reminders.pick_trips(DEPS[:1], "08:00") == (None, None)


def test_fire_time():
    assert reminders.fire_time("08:07", 10) == "07:57"
    assert reminders.fire_time("00:10", 30) == "00:00"


@pytest.mark.parametrize("now, dep, expected", [
    ("07:56", "08:07", "wait"),
    ("07:57", "08:07", "send"),
    ("08:06", "08:07", "send"),
    ("08:07", "08:07", "skip"),
    ("07:57", None, "send"),
])
def test_run_action(now, dep, expected):
    assert reminders.run_action(now, "07:57", dep) == expected


def test_run_action_no_trips_skipped_once_target_passed():
    assert reminders.run_action("07:30", "07:20", None, target="07:30") == "skip"
    assert reminders.run_action("07:25", "07:20", None, target="07:30") == "send"


def test_route_name():
    assert reminders.route_name("Дом", "1") == "Дом"
    assert reminders.route_name(None, "1") == "Маршрут 1"


def test_reminder_text():
    assert reminders.reminder_text("Дом <1>", "1", "08:07", "08:17", "07:57") == (
        "🚶 <b>Пора выходить! «Дом &lt;1&gt;»</b><br>"
        "🚋 <b>1</b> отправляется в <b>08:07</b> — через 10 мин.<br>"
        "Следующий — в 08:17."
    )


def test_reminder_text_without_next():
    assert "Следующий" not in reminders.reminder_text("Дом", "1", "08:07", None, "08:05")
    assert "через 2 мин" in reminders.reminder_text("Дом", "1", "08:07", None, "08:05")


def test_no_trips_and_error_texts():
    assert reminders.no_trips_text("Дом", "08:00") == "😕 «Дом»: сегодня после 08:00 в течение часа рейсов нет."
    assert reminders.site_error_text("Дом") == "🚫 «Дом»: не удалось получить расписание с сайта ИжГЭТ."


def test_sub_button_text():
    assert reminders.sub_button_text("remind", "08:00") == "🚶 Напоминание 08:00"
    assert reminders.sub_button_text("schedule", "07:30") == "📋 Расписание 07:30"
    assert reminders.sub_button_text(None, "07:30") == "📋 Расписание 07:30"


def test_summary_text():
    assert reminders.summary_text("remind", "weekdays", "08:00", 10, "30") == "🚶 Будни, 08:00, за 10 мин"
    assert reminders.summary_text("schedule", "all", "07:30", None, "30") == \
        "📋 Каждый день, 07:30, расписание на 30 мин"


def test_confirmation_text():
    assert reminders.confirmation_text("remind", "weekdays", "08:00", 10, "30") == \
        "✅ По будням напомню за 10 мин до первого рейса после 08:00."
    assert reminders.confirmation_text("schedule", "weekends", "09:15", None, "60") == \
        "✅ По выходным в 09:15 буду присылать расписание на ближайшие 60 мин."
    assert reminders.confirmation_text("schedule", "all", "07:30", None, "30") == \
        "✅ Каждый день в 07:30 буду присылать расписание на ближайшие 30 мин."


def test_pick_trips_skips_malformed_times():
    deps = [Departure("1", "", ""), Departure("1", "??", "08:30"), Departure("1", "08:07", "08:27")]
    first, following = reminders.pick_trips(deps, "08:00")
    assert first == Departure("1", "08:07", "08:27")
    assert following is None


def test_pick_trips_unsorted_input():
    first, following = reminders.pick_trips([DEPS[3], DEPS[1], DEPS[2]], "08:00")
    assert first == DEPS[1]
    assert following == DEPS[2]


def test_fire_time_exactly_target():
    assert reminders.fire_time("08:10", 10) == "08:00"
