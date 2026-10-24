import keyboards.keyboards as kb
from keyboards.keyboards import SubCallback, FavCallback
from tests.helpers import button_texts


def _callbacks(markup):
    return [b.callback_data for row in markup.inline_keyboard for b in row]


def test_delete_kb_subscription_label():
    assert "🔔 Подписаться" in button_texts(kb.get_delete_kb(7))
    sub = (1, 5, 7, "08:00", 1, "remind", "weekdays", 10)
    assert "🚶 Напоминание 08:00" in button_texts(kb.get_delete_kb(7, sub))


def test_mode_kb():
    markup = kb.get_sub_mode_kb(7)
    assert button_texts(markup) == ["📋 Расписание", "🚶 Напоминание", "Отмена"]
    assert _callbacks(markup) == [SubCallback(action="mode", id="schedule").pack(),
                                  SubCallback(action="mode", id="remind").pack(), "sub_back_7"]


def test_days_kb():
    markup = kb.get_sub_days_kb(7)
    assert button_texts(markup) == ["Каждый день", "Будни", "Выходные", "Отмена"]
    assert _callbacks(markup)[1] == SubCallback(action="days", id="weekdays").pack()


def test_lead_kb():
    markup = kb.get_sub_lead_kb(7)
    assert button_texts(markup) == ["5", "10", "15", "20", "30", "Отмена"]
    assert _callbacks(markup)[1] == SubCallback(action="lead", id="10").pack()


def test_manage_kb_edit_label():
    assert button_texts(kb.get_sub_manage_kb(1, 7)) == ["🔕 Отписаться", "✏️ Изменить", "🔙 Назад"]


def test_reminder_kb():
    markup = kb.get_reminder_kb(7)
    assert button_texts(markup) == ["📋 Полное расписание", "💖 Поддержать автора"]
    assert _callbacks(markup)[0] == FavCallback(action="select", id="7").pack()
