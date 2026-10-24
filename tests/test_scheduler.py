import asyncio
import datetime

import pytest

import db.db as db
import scheduler
from reminders import Departure
from tests.helpers import make_bot

MONDAY = 26     # 26.10.2026 — понедельник
SATURDAY = 24   # 24.10.2026 — суббота
DEPS = [Departure("1", "08:07", "08:27"), Departure("1", "08:17", "08:37")]


def at(h, m, day=MONDAY):
    return scheduler.TZ.localize(datetime.datetime(2026, 10, day, h, m))


def today_iso(day=MONDAY):
    return f"2026-10-{day:02d}"


def sent(calls):
    return [c for c in calls if c.method == "SendRichMessage"]


@pytest.fixture
def site(monkeypatch):
    """Фиктивный сайт ИжГЭТ: state['result'] — что вернёт get_departures."""
    state = {"result": DEPS, "calls": 0}

    async def get_departures(route, stn, dstn, dt, start, timeint):
        state["calls"] += 1
        await asyncio.sleep(0)
        assert (dt, start, timeint) == ("26.10.2026", "08:00", 60)
        return state["result"]

    monkeypatch.setattr(scheduler.parser, "get_departures", get_departures)
    return state


@pytest.fixture
def remind(tmp_db):
    fav_id = db.add_favorite_route(5, "1", "1900", "900", "30", "Дом")
    sub_id = db.add_subscription(5, fav_id, "08:00", mode="remind", days="weekdays", lead_min=10)
    return fav_id, sub_id


async def test_plans_only_inside_window(remind, site):
    _, sub_id = remind
    bot, _ = make_bot()
    await scheduler.process_minute(bot, at(6, 59))
    assert site["calls"] == 0 and db.get_run(sub_id, today_iso()) is None

    await scheduler.process_minute(bot, at(7, 0))
    due = db.get_due_runs(today_iso(), "23:59")
    assert [(r[2], r[3], r[4], r[5]) for r in due] == [("07:57", "08:07", "1", "08:17")]


async def test_does_not_replan_after_restart(remind, site):
    bot, _ = make_bot()
    await scheduler.process_minute(bot, at(7, 0))
    await scheduler.process_minute(bot, at(7, 1))
    assert site["calls"] == 1


async def test_sends_once_at_fire_time(remind, site):
    _, sub_id = remind
    bot, calls = make_bot()
    await scheduler.process_minute(bot, at(7, 0))
    await scheduler.process_minute(bot, at(7, 56))
    assert sent(calls) == []

    await scheduler.process_minute(bot, at(7, 57))
    await scheduler.process_minute(bot, at(7, 58))
    msgs = sent(calls)
    assert len(msgs) == 1
    assert msgs[0].chat_id == 5
    assert "Пора выходить! «Дом»" in msgs[0].text
    assert "<b>08:07</b> — через 10 мин." in msgs[0].text
    assert "Следующий — в 08:17." in msgs[0].text
    assert db.get_run(sub_id, today_iso())[1] == "sent"


async def test_late_send_before_departure(remind, site):
    bot, calls = make_bot()
    await scheduler.process_minute(bot, at(7, 0))
    await scheduler.process_minute(bot, at(8, 5))  # бот лежал с 7:00 до 8:05
    assert "через 2 мин" in sent(calls)[0].text


async def test_skip_after_departure(remind, site):
    _, sub_id = remind
    bot, calls = make_bot()
    await scheduler.process_minute(bot, at(7, 0))
    await scheduler.process_minute(bot, at(8, 10))
    assert sent(calls) == []
    assert db.get_run(sub_id, today_iso())[1] == "skipped"


async def test_no_trips_message(remind, site):
    site["result"] = []
    bot, calls = make_bot()
    await scheduler.process_minute(bot, at(7, 0))
    await scheduler.process_minute(bot, at(7, 49))
    assert sent(calls) == []
    await scheduler.process_minute(bot, at(7, 50))
    assert sent(calls)[0].text == "😕 «Дом»: сегодня после 08:00 в течение часа рейсов нет."


async def test_site_down_retries_then_reports_once(remind, site):
    _, sub_id = remind
    site["result"] = None
    bot, calls = make_bot()
    await scheduler.process_minute(bot, at(7, 0))
    await scheduler.process_minute(bot, at(7, 49))
    assert db.get_run(sub_id, today_iso()) is None and sent(calls) == []

    await scheduler.process_minute(bot, at(7, 50))
    await scheduler.process_minute(bot, at(7, 51))
    assert [c.text for c in sent(calls)] == ["🚫 «Дом»: не удалось получить расписание с сайта ИжГЭТ."]
    assert db.get_run(sub_id, today_iso())[1] == "skipped"
    assert site["calls"] == 3  # 7:00, 7:49, 7:50; в 7:51 план уже есть


async def test_replans_after_subscription_change(remind, site):
    fav_id, sub_id = remind
    bot, _ = make_bot()
    await scheduler.process_minute(bot, at(7, 0))
    db.add_subscription(5, fav_id, "08:00", mode="remind", days="weekdays", lead_min=5)
    await scheduler.process_minute(bot, at(7, 1))
    assert [r[2] for r in db.get_due_runs(today_iso(), "23:59")] == ["08:02"]


async def test_weekday_reminder_not_planned_on_saturday(remind, site):
    bot, _ = make_bot()
    await scheduler.process_minute(bot, at(7, 0, day=SATURDAY))
    assert site["calls"] == 0


async def test_concurrent_minutes_send_once(remind, site):
    bot, calls = make_bot()
    await scheduler.process_minute(bot, at(7, 0))
    await asyncio.gather(scheduler.process_minute(bot, at(7, 57)), scheduler.process_minute(bot, at(7, 58)))
    assert len(sent(calls)) == 1


async def test_schedule_mode_respects_days(tmp_db, monkeypatch):
    async def get_result(**kwargs):
        return "<b>TT</b>"
    monkeypatch.setattr(scheduler, "get_result", get_result)
    fav_id = db.add_favorite_route(5, "1", "1900", "900", "30", "Дом")
    db.add_subscription(5, fav_id, "07:30", mode="schedule", days="weekends")
    bot, calls = make_bot()

    await scheduler.process_minute(bot, at(7, 30, day=MONDAY))
    assert sent(calls) == []
    await scheduler.process_minute(bot, at(7, 30, day=SATURDAY))
    assert sent(calls)[0].text == "🔔 <b>Дом</b><br><br><b>TT</b>"


async def test_catch_up_old_minute_does_not_send(remind, site):
    _, sub_id = remind
    bot, calls = make_bot()
    await scheduler.process_minute(bot, at(7, 0))
    await scheduler.process_minute(bot, at(8, 5), send_due=False)
    assert sent(calls) == []
    assert db.get_run(sub_id, today_iso())[1] == "planned"

    await scheduler.process_minute(bot, at(8, 12))
    assert sent(calls) == []
    assert db.get_run(sub_id, today_iso())[1] == "skipped"


async def test_overlapping_minutes_fetch_site_once(remind, site):
    bot, _ = make_bot()
    await asyncio.gather(scheduler.process_minute(bot, at(7, 0)), scheduler.process_minute(bot, at(7, 1)))
    assert site["calls"] == 1


async def test_plan_and_send_in_same_minute(remind, site):
    _, sub_id = remind
    bot, calls = make_bot()
    await scheduler.process_minute(bot, at(7, 58))
    msgs = sent(calls)
    assert len(msgs) == 1
    assert "<b>08:07</b> — через 9 мин." in msgs[0].text
    assert db.get_run(sub_id, today_iso())[1] == "sent"


async def test_send_failure_is_not_retried(remind, site, monkeypatch):
    _, sub_id = remind
    bot, calls = make_bot()
    await scheduler.process_minute(bot, at(7, 0))

    async def failing_send(*args, **kwargs):
        raise RuntimeError("telegram down")

    with monkeypatch.context() as patch:
        patch.setattr(scheduler, "_send", failing_send)
        await scheduler.process_minute(bot, at(7, 57))
    assert db.get_run(sub_id, today_iso())[1] == "sent"

    await scheduler.process_minute(bot, at(7, 58))
    assert sent(calls) == []
