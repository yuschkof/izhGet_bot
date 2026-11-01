"""Закрепление избранного маршрута внизу чата (постоянная reply-клавиатура)."""
import pytest
from aiogram import Dispatcher
from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove

import db.db as db
from handlers import common, favorite_route, new_route, subscription
from keyboards.keyboards import FavCallback
from tests.helpers import make_bot, callback_update, text_update, button_texts


@pytest.fixture(scope="module")
def dp():
    # Порядок как в main.py (subscription уже подключён в test_subscription_flow,
    # а роутер можно подключить только к одному диспетчеру)
    dispatcher = Dispatcher()
    dispatcher.include_router(favorite_route.pinned_router)
    dispatcher.include_router(common.router)
    dispatcher.include_router(new_route.router)
    dispatcher.include_router(favorite_route.router)
    return dispatcher


@pytest.fixture(autouse=True)
def fake_site(monkeypatch):
    async def get_result(**kwargs):
        return f"<b>TT {kwargs['route']}</b>"
    monkeypatch.setattr(favorite_route, "get_result", get_result)
    monkeypatch.setattr(subscription, "get_result", get_result)
    monkeypatch.setattr(common.db, "update_unknown_messages_statistics", lambda user_id: None)


def pin(fav_id):
    return FavCallback(action="pin", id=str(fav_id)).pack()


def unpin(fav_id):
    return FavCallback(action="unpin", id=str(fav_id)).pack()


def reply_rows(markup):
    return [[b.text for b in row] for row in markup.keyboard]


def answers(calls):
    return [c for c in calls if c.method == "AnswerCallbackQuery"]


async def test_pin_shows_bottom_keyboard_and_toggles_button(dp, tmp_db):
    user = 201
    fav = db.add_favorite_route(user, "1", "1900", "900", "30", "Дом")
    bot, calls = make_bot()

    await dp.feed_update(bot, callback_update(user, pin(fav)))

    assert db.is_pinned(user, fav)
    edit = [c for c in calls if c.method == "EditMessageReplyMarkup"][-1]
    assert "📍 Открепить" in button_texts(edit.markup)
    sent = [c for c in calls if c.method == "SendMessage"][-1]
    assert "«Дом» закреплён внизу" in sent.text
    assert isinstance(sent.markup, ReplyKeyboardMarkup)
    assert reply_rows(sent.markup) == [["Дом"]]


async def test_pressing_bottom_button_opens_timetable(dp, tmp_db):
    user = 202
    fav = db.add_favorite_route(user, "3", "1900", "900", "30", "Работа")
    db.set_pinned(user, fav, True)
    bot, calls = make_bot()

    await dp.feed_update(bot, text_update(user, "Работа"))

    assert calls[0].method == "SendMessage" and "Загружаю" in calls[0].text
    edit = [c for c in calls if c.method == "EditMessageText"][-1]
    assert edit.text == "<b>TT 3</b>"
    assert "📍 Открепить" in button_texts(edit.markup)
    assert not any("не понимаю" in (c.text or "") for c in calls)


async def test_other_text_still_gets_stub(dp, tmp_db):
    user = 203
    fav = db.add_favorite_route(user, "3", "1900", "900", "30", "Работа")
    db.set_pinned(user, fav, True)
    bot, calls = make_bot()

    await dp.feed_update(bot, text_update(user, "Привет"))

    assert "не понимаю" in calls[-1].text


async def test_someone_elses_pinned_name_is_not_opened(dp, tmp_db):
    fav = db.add_favorite_route(204, "3", "1900", "900", "30", "Работа")
    db.set_pinned(204, fav, True)
    bot, calls = make_bot()

    await dp.feed_update(bot, text_update(205, "Работа"))

    assert "не понимаю" in calls[-1].text


async def test_pin_limit(dp, tmp_db):
    user = 206
    favs = [db.add_favorite_route(user, str(i), "1900", "900", "30", f"М{i}") for i in range(5)]
    for f in favs[:4]:
        db.set_pinned(user, f, True)
    bot, calls = make_bot()

    await dp.feed_update(bot, callback_update(user, pin(favs[4])))

    assert not db.is_pinned(user, favs[4])
    assert not [c for c in calls if c.method == "SendMessage"]
    assert answers(calls)


async def test_pin_duplicate_name_rejected(dp, tmp_db):
    user = 207
    a = db.add_favorite_route(user, "1", "1900", "900", "30", "Дом")
    b = db.add_favorite_route(user, "1", "1900", "900", "60", "Дом")
    db.set_pinned(user, a, True)
    bot, calls = make_bot()

    await dp.feed_update(bot, callback_update(user, pin(b)))

    assert not db.is_pinned(user, b)


async def test_unpin_last_removes_keyboard(dp, tmp_db):
    user = 208
    fav = db.add_favorite_route(user, "1", "1900", "900", "30", "Дом")
    db.set_pinned(user, fav, True)
    bot, calls = make_bot()

    await dp.feed_update(bot, callback_update(user, unpin(fav)))

    assert not db.is_pinned(user, fav)
    edit = [c for c in calls if c.method == "EditMessageReplyMarkup"][-1]
    assert "📌 Закрепить внизу" in button_texts(edit.markup)
    sent = [c for c in calls if c.method == "SendMessage"][-1]
    assert isinstance(sent.markup, ReplyKeyboardRemove)


async def test_pin_someone_elses_favorite(dp, tmp_db):
    fav = db.add_favorite_route(209, "1", "1900", "900", "30", "Дом")
    bot, calls = make_bot()

    await dp.feed_update(bot, callback_update(210, pin(fav)))

    assert not db.is_pinned(209, fav)
    assert not [c for c in calls if c.method == "SendMessage"]


async def test_rename_pinned_updates_keyboard(dp, tmp_db):
    user = 211
    fav = db.add_favorite_route(user, "1", "1900", "900", "30", "Дом")
    db.set_pinned(user, fav, True)
    bot, calls = make_bot()

    await dp.feed_update(bot, callback_update(user, FavCallback(action="rename_ask", id=str(fav)).pack()))
    await dp.feed_update(bot, text_update(user, "Домой"))

    confirm = [c for c in calls if c.method == "SendMessage" and "переименован" in (c.text or "")][-1]
    assert reply_rows(confirm.markup) == [["Домой"]]


async def test_rename_pinned_to_other_pinned_name_rejected(dp, tmp_db):
    user = 212
    a = db.add_favorite_route(user, "1", "1900", "900", "30", "Дом")
    b = db.add_favorite_route(user, "2", "1900", "900", "30", "Работа")
    db.set_pinned(user, a, True)
    db.set_pinned(user, b, True)
    bot, calls = make_bot()

    await dp.feed_update(bot, callback_update(user, FavCallback(action="rename_ask", id=str(b)).pack()))
    await dp.feed_update(bot, text_update(user, "Дом"))

    assert db.get_favorite(user, b)[5] == "Работа"
    assert "уже есть" in calls[-1].text


async def test_delete_pinned_updates_keyboard(dp, tmp_db):
    user = 213
    a = db.add_favorite_route(user, "1", "1900", "900", "30", "Дом")
    b = db.add_favorite_route(user, "2", "1900", "900", "30", "Работа")
    db.set_pinned(user, a, True)
    db.set_pinned(user, b, True)
    bot, calls = make_bot()

    await dp.feed_update(bot, callback_update(user, FavCallback(action="del", id=str(a)).pack()))

    sent = [c for c in calls if c.method == "SendMessage"][-1]
    assert reply_rows(sent.markup) == [["Работа"]]


async def test_start_restores_keyboard(dp, tmp_db):
    user = 214
    fav = db.add_favorite_route(user, "1", "1900", "900", "30", "Дом")
    bot, calls = make_bot()

    await dp.feed_update(bot, text_update(user, "/start"))
    assert calls[-1].markup is None

    db.set_pinned(user, fav, True)
    await dp.feed_update(bot, text_update(user, "/start"))
    assert reply_rows(calls[-1].markup) == [["Дом"]]


def rename_ask(fav_id):
    return FavCallback(action="rename_ask", id=str(fav_id)).pack()


@pytest.mark.parametrize("command", ["/help", "/new", "/favorites"])
async def test_commands_during_rename_are_not_saved_as_name(dp, tmp_db, command):
    user = 215
    fav = db.add_favorite_route(user, "1", "1900", "900", "30", "Дом")
    bot, calls = make_bot()

    await dp.feed_update(bot, callback_update(user, rename_ask(fav)))
    await dp.feed_update(bot, text_update(user, command))

    assert db.get_favorite(user, fav)[5] == "Дом"


async def test_name_with_slash_rejected(dp, tmp_db):
    user = 216
    fav = db.add_favorite_route(user, "1", "1900", "900", "30", "Дом")
    bot, calls = make_bot()

    await dp.feed_update(bot, callback_update(user, rename_ask(fav)))
    await dp.feed_update(bot, text_update(user, "/дом"))

    assert db.get_favorite(user, fav)[5] == "Дом"


async def test_pin_twice_and_unpin_twice_are_noops(dp, tmp_db):
    user = 217
    fav = db.add_favorite_route(user, "1", "1900", "900", "30", "Дом")
    db.set_pinned(user, fav, True)
    bot, calls = make_bot()

    await dp.feed_update(bot, callback_update(user, pin(fav)))
    assert [c.method for c in calls] == ["AnswerCallbackQuery"]

    db.set_pinned(user, fav, False)
    calls.clear()
    await dp.feed_update(bot, callback_update(user, unpin(fav)))
    assert [c.method for c in calls] == ["AnswerCallbackQuery"]


async def test_pinned_button_ends_support_flow(dp, tmp_db):
    user = 218
    fav = db.add_favorite_route(user, "3", "1900", "900", "30", "Работа")
    db.set_pinned(user, fav, True)
    bot, calls = make_bot()

    await dp.feed_update(bot, text_update(user, "/support"))
    calls.clear()
    await dp.feed_update(bot, text_update(user, "Работа"))

    assert [c for c in calls if c.method == "EditMessageText"][-1].text == "<b>TT 3</b>"
    assert not [c for c in calls if c.method == "CopyMessage"]
