import pytest
from aiogram import Dispatcher

import db.db as db
from handlers import subscription
from keyboards.keyboards import SubCallback
from reminders import Departure
from tests.helpers import make_bot, callback_update, text_update, button_texts


@pytest.fixture(scope="module")
def dp():
    # Роутер можно подключить только к одному диспетчеру — один на весь модуль
    dispatcher = Dispatcher()
    dispatcher.include_router(subscription.router)
    return dispatcher


@pytest.fixture
def site(monkeypatch):
    state = {"result": [Departure("1", "08:07", "08:27")], "calls": 0}

    async def get_departures(route, stn, dstn, dt, start, timeint):
        state["calls"] += 1
        return state["result"]

    async def get_result(**kwargs):
        return "<b>TT</b>"

    monkeypatch.setattr(subscription.parser, "get_departures", get_departures)
    monkeypatch.setattr(subscription, "get_result", get_result)
    return state


def cb(action, value):
    return SubCallback(action=action, id=str(value)).pack()


def last_edit(calls):
    return [c for c in calls if c.method == "EditMessageText"][-1]


async def test_remind_flow(dp, tmp_db, site):
    user = 101
    fav_id = db.add_favorite_route(user, "1", "1900", "900", "30", "Дом")
    bot, calls = make_bot()

    await dp.feed_update(bot, callback_update(user, cb("ask", fav_id)))
    screen = last_edit(calls)
    assert "Как присылать?" in screen.text and "Напомнить, когда выходить" in screen.text
    assert button_texts(screen.markup) == ["📋 Расписание", "🚶 Напоминание", "Отмена"]

    await dp.feed_update(bot, callback_update(user, cb("mode", "remind")))
    assert "В какие дни" in last_edit(calls).text
    await dp.feed_update(bot, callback_update(user, cb("days", "weekdays")))
    assert "За сколько минут" in last_edit(calls).text
    await dp.feed_update(bot, callback_update(user, cb("lead", 10)))
    assert "Во сколько ты готов выйти" in last_edit(calls).text

    await dp.feed_update(bot, text_update(user, "8:00"))
    answer = calls[-1]
    assert answer.method == "SendMessage"
    assert answer.text == "✅ По будням напомню за 10 мин до первого рейса после 08:00."
    assert db.get_subscription(user, fav_id)[3:] == ("08:00", 1, "remind", "weekdays", 10)


async def test_remind_flow_warns_when_no_trips(dp, tmp_db, site):
    user = 102
    site["result"] = []
    fav_id = db.add_favorite_route(user, "1", "1900", "900", "30", "Дом")
    bot, calls = make_bot()
    for data in (cb("ask", fav_id), cb("mode", "remind"), cb("days", "all"), cb("lead", 5)):
        await dp.feed_update(bot, callback_update(user, data))
    await dp.feed_update(bot, text_update(user, "3:00"))
    assert "⚠️ После 03:00 в течение часа рейсов не нашлось — проверь время." in calls[-1].text


async def test_schedule_flow_skips_lead_and_site(dp, tmp_db, site):
    user = 103
    fav_id = db.add_favorite_route(user, "1", "1900", "900", "30", "Дом")
    bot, calls = make_bot()
    for data in (cb("ask", fav_id), cb("mode", "schedule"), cb("days", "weekends")):
        await dp.feed_update(bot, callback_update(user, data))
    assert "Во сколько присылать расписание" in last_edit(calls).text

    await dp.feed_update(bot, text_update(user, "9:15"))
    assert calls[-1].text == "✅ По выходным в 09:15 буду присылать расписание на ближайшие 30 мин."
    assert db.get_subscription(user, fav_id)[3:] == ("09:15", 1, "schedule", "weekends", None)
    assert site["calls"] == 0


async def test_existing_subscription_shows_summary(dp, tmp_db, site):
    user = 104
    fav_id = db.add_favorite_route(user, "1", "1900", "900", "30", "Дом")
    db.add_subscription(user, fav_id, "08:00", mode="remind", days="weekdays", lead_min=10)
    bot, calls = make_bot()
    await dp.feed_update(bot, callback_update(user, cb("ask", fav_id)))
    screen = last_edit(calls)
    assert "🚶 Будни, 08:00, за 10 мин" in screen.text
    assert button_texts(screen.markup) == ["🔕 Отписаться", "✏️ Изменить", "🔙 Назад"]


async def test_edit_restarts_setup(dp, tmp_db, site):
    user = 105
    fav_id = db.add_favorite_route(user, "1", "1900", "900", "30", "Дом")
    db.add_subscription(user, fav_id, "08:00", mode="remind", days="weekdays", lead_min=10)
    bot, calls = make_bot()
    for data in (cb("edit", fav_id), cb("mode", "schedule"), cb("days", "all")):
        await dp.feed_update(bot, callback_update(user, data))
    await dp.feed_update(bot, text_update(user, "07:30"))
    assert db.get_subscription(user, fav_id)[3:] == ("07:30", 1, "schedule", "all", None)


async def test_stale_setup_after_restart(dp, tmp_db, site):
    bot, calls = make_bot()
    await dp.feed_update(bot, callback_update(106, cb("days", "all")))
    assert "Настройка устарела" in last_edit(calls).text


async def test_cancel_returns_to_route_and_clears_state(dp, tmp_db, site):
    user = 107
    fav_id = db.add_favorite_route(user, "1", "1900", "900", "30", "Дом")
    bot, calls = make_bot()
    await dp.feed_update(bot, callback_update(user, cb("ask", fav_id)))
    await dp.feed_update(bot, callback_update(user, cb("mode", "remind")))
    await dp.feed_update(bot, callback_update(user, f"sub_back_{fav_id}"))
    assert "<b>TT</b>" in last_edit(calls).text
    assert "🔔 Подписаться" in button_texts(last_edit(calls).markup)

    await dp.feed_update(bot, text_update(user, "8:00"))
    assert db.get_subscription(user, fav_id) is None


async def test_bad_time_keeps_waiting(dp, tmp_db, site):
    user = 108
    fav_id = db.add_favorite_route(user, "1", "1900", "900", "30", "Дом")
    bot, calls = make_bot()
    for data in (cb("ask", fav_id), cb("mode", "schedule"), cb("days", "all")):
        await dp.feed_update(bot, callback_update(user, data))
    await dp.feed_update(bot, text_update(user, "25:00"))
    assert "Неверный формат" in calls[-1].text
    await dp.feed_update(bot, text_update(user, "7:05"))
    assert db.get_subscription(user, fav_id)[3] == "07:05"


async def test_forged_values_are_ignored(dp, tmp_db, site):
    user = 109
    fav_id = db.add_favorite_route(user, "1", "1900", "900", "30", "Дом")
    bot, calls = make_bot()
    for data in (cb("ask", fav_id), cb("mode", "x"), cb("mode", "remind"), cb("days", "foo"),
                 cb("days", "all"), cb("lead", 999), cb("lead", "abc"), cb("lead", 10)):
        await dp.feed_update(bot, callback_update(user, data))
    await dp.feed_update(bot, text_update(user, "8:00"))
    assert calls[-1].method == "SendMessage"
    assert calls[-1].text.startswith("✅")
    assert db.get_subscription(user, fav_id)[3:] == ("08:00", 1, "remind", "all", 10)


async def test_delete_someone_elses_subscription(dp, tmp_db, site):
    fav_id = db.add_favorite_route(110, "1", "1900", "900", "30", "Дом")
    db.add_subscription(110, fav_id, "08:00", mode="schedule", days="all", lead_min=None)
    sub_id = db.get_subscription(110, fav_id)[0]
    bot, calls = make_bot()
    await dp.feed_update(bot, callback_update(111, cb("del", f"{sub_id}_{fav_id}")))
    assert db.get_subscription(110, fav_id) is not None
    assert any(c.method == "AnswerCallbackQuery" for c in calls)


async def test_bad_ids_in_delete_and_back_are_ignored(dp, tmp_db, site):
    bot, calls = make_bot()
    await dp.feed_update(bot, callback_update(112, cb("del", "abc")))
    await dp.feed_update(bot, callback_update(112, "sub_back_abc"))
    assert [c.method for c in calls] == ["AnswerCallbackQuery", "AnswerCallbackQuery"]


async def test_site_down_no_warning(dp, tmp_db, site):
    user = 113
    site["result"] = None
    fav_id = db.add_favorite_route(user, "1", "1900", "900", "30", "Дом")
    bot, calls = make_bot()
    for data in (cb("ask", fav_id), cb("mode", "remind"), cb("days", "all"), cb("lead", 5)):
        await dp.feed_update(bot, callback_update(user, data))
    await dp.feed_update(bot, text_update(user, "8:00"))
    assert "⚠️" not in calls[-1].text
