# «Напомни, когда выходить» — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить второй режим подписки: бот каждый подходящий день находит первый рейс не раньше целевого времени и пишет за N минут до его отправления. Плюс выбор дней (каждый день / будни / выходные) для обоих режимов.

**Architecture:** Чистая доменная логика (дни, выбор рейса, тексты) — в новом `reminders.py`. Парсер отдаёт рейсы списком через `get_departures`. Минутный цикл переезжает из `main.py` в новый `scheduler.py`: каждая минута рассылает `schedule`-подписки, планирует `remind`-подписки за 60 мин до цели (план хранится в таблице `reminder_runs`) и отправляет наступившие напоминания. Двойная отправка исключена атомарным «захватом» записи в БД.

**Tech Stack:** Python 3.12, aiogram 3.31 (Bot API 10.3 rich messages), aiohttp, lxml, SQLite, pytest + pytest-asyncio.

**Спека:** `docs/superpowers/specs/2026-10-24-leave-reminder-design.md`

---

## Карта файлов

| Файл | Ответственность |
|---|---|
| `reminders.py` (новый) | `Departure`, константы режимов/дней/минут, чистые функции расчёта и тексты сообщений. Без импортов проекта. |
| `request.py` | `parse_departures()` (модульная функция), `TimetableParser.get_departures()`; HTML-расписание строится из того же разбора |
| `db/db.py` | Миграция `subscriptions`, таблица `reminder_runs`, функции для неё; `add_subscription` / `get_subscription` с новыми полями |
| `keyboards/keyboards.py` | Клавиатуры режима, дней, минут, напоминания; подпись кнопки подписки по режиму |
| `scheduler.py` (новый) | Минутный цикл с догоном, `process_minute()` — рассылка, планирование, отправка |
| `main.py` | Только запуск `scheduler.run(bot)` |
| `handlers/subscription.py` | Сценарий настройки (режим → дни → минуты → время), экран управления |
| `handlers/favorite_route.py` | Передать подписку в `get_delete_kb` |
| `tests/` (новый) | `helpers.py` (заглушка Telegram, билдеры апдейтов), `conftest.py`, тесты, `fixtures/*.html` |
| `pytest.ini`, `requirements-dev.txt` (новые) | Настройка тестов |

Фикстуры `tests/fixtures/timetable_trips.html` и `tests/fixtures/timetable_no_trips.html` уже сохранены с живого сайта (маршрут 1, «Аграрный университет» → «Воткинская линия», 26.10.2026: от 08:00 на 60 мин — 6 рейсов 08:07…08:57; от 02:00 на 30 мин — «рейсов нет»).

Все команды запускаются из корня репозитория. Python — `venv/Scripts/python.exe` (Windows) или `venv/bin/python`.

---

### Task 1: Тестовая инфраструктура

**Files:**
- Create: `requirements-dev.txt`, `pytest.ini`, `tests/__init__.py`, `tests/helpers.py`, `tests/conftest.py`, `tests/test_parser.py`

- [ ] **Step 1: Зависимости и настройка pytest**

`requirements-dev.txt`:
```
-r requirements.txt
pytest==9.1.1
pytest-asyncio==1.4.0
```

`pytest.ini`:
```ini
[pytest]
testpaths = tests
pythonpath = .
asyncio_mode = auto
```

`tests/__init__.py` — пустой файл.

Run: `venv/Scripts/python.exe -m pip install -r requirements-dev.txt`

- [ ] **Step 2: Заглушка Telegram и билдеры апдейтов**

`tests/helpers.py`:
```python
"""Общие помощники тестов: заглушка Telegram API и сборка апдейтов."""
import datetime
from typing import NamedTuple

from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.types import Update, Message, Chat, User, CallbackQuery


class Call(NamedTuple):
    method: str
    chat_id: int | None
    text: str | None
    markup: object


class FakeSession(BaseSession):
    """Вместо Telegram API: запоминает вызовы и возвращает правдоподобный ответ."""

    def __init__(self):
        super().__init__()
        self.calls: list[Call] = []

    async def make_request(self, bot, method, timeout=None):
        rich = getattr(method, "rich_message", None)
        self.calls.append(Call(
            type(method).__name__,
            getattr(method, "chat_id", None),
            getattr(method, "text", None) or (rich.html if rich else None),
            getattr(method, "reply_markup", None),
        ))
        returning = method.__returning__
        if hasattr(returning, "model_validate"):
            return returning.model_validate({
                "message_id": 1,
                "date": datetime.datetime.now(),
                "chat": {"id": 1, "type": "private"},
            })
        return True

    async def close(self):
        pass

    async def stream_content(self, *args, **kwargs):
        yield b""


def make_bot() -> tuple[Bot, list[Call]]:
    session = FakeSession()
    return Bot("42:TEST", session=session), session.calls


def button_texts(markup) -> list[str]:
    return [b.text for row in markup.inline_keyboard for b in row]


def _user(user_id: int) -> User:
    return User(id=user_id, is_bot=False, first_name="T")


def callback_update(user_id: int, data: str) -> Update:
    message = Message(message_id=10, date=datetime.datetime.now(),
                      chat=Chat(id=user_id, type="private"), text="screen")
    return Update(update_id=1, callback_query=CallbackQuery(
        id="1", from_user=_user(user_id), chat_instance="c", data=data, message=message))


def text_update(user_id: int, text: str) -> Update:
    return Update(update_id=2, message=Message(
        message_id=11, date=datetime.datetime.now(), chat=Chat(id=user_id, type="private"),
        from_user=_user(user_id), text=text))
```

`tests/conftest.py`:
```python
import pathlib

import pytest

import db.db as db

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Чистая izhGet.db во временной папке (db.py открывает файл по относительному пути)."""
    monkeypatch.chdir(tmp_path)
    db.create_tables()
    return tmp_path


@pytest.fixture
def fixture_html():
    def read(name: str) -> str:
        return (FIXTURES / name).read_text(encoding="utf-8")
    return read
```

- [ ] **Step 3: Характеризационный тест текущего HTML-расписания**

Фиксирует нынешний вывод, чтобы рефакторинг парсера в Task 3 его не изменил.

`tests/test_parser.py`:
```python
import request


def test_timetable_html_from_fixture(fixture_html):
    out = request.parser._parse_response_table(fixture_html("timetable_trips.html"))
    lines = out.splitlines()
    assert lines[0] == ('🚏 <b>Рейсы от <b>"Аграрный университет"</b> до <b>"Воткинская линия"</b> '
                        'по состоянию на 26.10.2026г., <b>будний день</b>, 08:00</b>')
    rows = [line for line in lines if line.startswith("<tr><td")]
    assert len(rows) == 6
    assert rows[0] == ('<tr><td align="center">🚋 1</td><td align="center">08:07</td>'
                       '<td align="center">🏁 08:27</td></tr>')
    assert lines[-1] == "<i>Время местное</i>"


def test_timetable_html_no_trips(fixture_html):
    out = request.parser._parse_response_table(fixture_html("timetable_no_trips.html"))
    assert out.startswith("😕 <b>Нет рейсов:</b>")
    assert "рейсов нет" in out


def test_timetable_html_garbage():
    assert request.parser._parse_response_table("").startswith("🚫")
```

- [ ] **Step 4: Запустить**

Run: `venv/Scripts/python.exe -m pytest -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add requirements-dev.txt pytest.ini tests/
git commit -m "test: pytest setup, Telegram fake session, parser characterization tests"
```

---

### Task 2: Доменная логика `reminders.py`

**Files:**
- Create: `reminders.py`, `tests/test_reminders.py`

- [ ] **Step 1: Тесты**

`tests/test_reminders.py`:
```python
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
```

- [ ] **Step 2: Убедиться, что падают**

Run: `venv/Scripts/python.exe -m pytest tests/test_reminders.py -q`
Expected: ошибка сбора — `ModuleNotFoundError: No module named 'reminders'`.

- [ ] **Step 3: Реализация**

`reminders.py`:
```python
"""Режим подписки «Напомни, когда выходить»: дни, выбор рейса, расчёт времени, тексты.

Без сети и БД — только чистые функции, чтобы их было легко тестировать.
Время везде — строки 'ЧЧ:ММ' по местному времени (Europe/Samara).
"""
import html
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


def pick_trips(departures, target: str):
    """Первый рейс с отправлением не раньше цели и следующий за ним (любой может быть None)."""
    later = sorted((d for d in departures if to_minutes(d.departure) >= to_minutes(target)),
                   key=lambda d: to_minutes(d.departure))
    first = later[0] if later else None
    following = later[1] if len(later) > 1 else None
    return first, following


def fire_time(at: str, lead_min: int) -> str:
    return from_minutes(to_minutes(at) - lead_min)


def run_action(now: str, fire_at: str, dep_time: str | None) -> str:
    """'wait' — ещё рано, 'send' — отправлять, 'skip' — рейс уже ушёл (бот лежал)."""
    if to_minutes(now) < to_minutes(fire_at):
        return "wait"
    if dep_time and to_minutes(now) >= to_minutes(dep_time):
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
```

- [ ] **Step 4: Тесты проходят**

Run: `venv/Scripts/python.exe -m pytest tests/test_reminders.py -q`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add reminders.py tests/test_reminders.py
git commit -m "feat: reminders domain logic (days, trip choice, fire time, texts)"
```

---

### Task 3: Рейсы списком — `parse_departures` и `get_departures`

**Files:**
- Modify: `request.py` (импорты, `_parse_response_table` строки 50–105, новый метод после `get_timetable`)
- Modify: `tests/test_parser.py`

- [ ] **Step 1: Тесты**

Добавить в `tests/test_parser.py`:
```python
import aiohttp
import pytest

from reminders import Departure


def test_parse_departures_trips(fixture_html):
    deps = request.parse_departures(fixture_html("timetable_trips.html"))
    assert len(deps) == 6
    assert deps[0] == Departure("1", "08:07", "08:27")
    assert deps[-1] == Departure("1", "08:57", "09:19")


def test_parse_departures_no_trips(fixture_html):
    assert request.parse_departures(fixture_html("timetable_no_trips.html")) == []


@pytest.mark.parametrize("text", ["", "<html><body>что-то другое</body></html>"])
def test_parse_departures_unknown(text):
    assert request.parse_departures(text) is None


def test_parse_departures_empty_cell():
    html_text = ("X<table border=1><tr><td>h</td><td>h</td><td>h</td><td>h</td></tr>"
                 "<tr><td></td><td>x</td><td><b>08:15</b></td><td>08:40</td></tr></table>")
    assert request.parse_departures(html_text) == [Departure("", "08:15", "08:40")]


class FakeResponse:
    def __init__(self, status, text):
        self.status = status
        self._text = text

    async def text(self):
        return self._text

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakeHttp:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.sent = []

    def post(self, url, data=None, ssl=None):
        self.sent.append(data)
        if self.error:
            raise self.error
        return self.response


def _parser_with(monkeypatch, http):
    p = request.TimetableParser()

    async def get_session():
        return http
    monkeypatch.setattr(p, "_get_session", get_session)
    return p


async def test_get_departures_request_and_result(monkeypatch, fixture_html):
    http = FakeHttp(FakeResponse(200, fixture_html("timetable_trips.html")))
    p = _parser_with(monkeypatch, http)
    deps = await p.get_departures("1", "1900", "900", "26.10.2026", "08:00", 60)
    assert deps[0].departure == "08:07"
    assert http.sent == [{"route": "1", "stn": "1900", "dstn": "900", "dt": "26.10.2026",
                          "th_rasp": "08", "tm_rasp": "00", "timeint": "60"}]


async def test_get_departures_http_error(monkeypatch):
    p = _parser_with(monkeypatch, FakeHttp(FakeResponse(500, "")))
    assert await p.get_departures("1", "1900", "900", "26.10.2026", "08:00", 60) is None


async def test_get_departures_network_error(monkeypatch):
    p = _parser_with(monkeypatch, FakeHttp(error=aiohttp.ClientError("boom")))
    assert await p.get_departures("1", "1900", "900", "26.10.2026", "08:00", 60) is None
```

- [ ] **Step 2: Убедиться, что падают**

Run: `venv/Scripts/python.exe -m pytest tests/test_parser.py -q`
Expected: новые тесты FAIL (`AttributeError: module 'request' has no attribute 'parse_departures'` / `'TimetableParser' object has no attribute 'get_departures'`), три старых — PASS.

- [ ] **Step 3: Реализация**

В `request.py` после `import db.db as db` добавить:
```python
from reminders import Departure
```

После функции `_cell_text` добавить:
```python
NO_TRIPS_XPATH = ".//font[@color='RED'][@size='3']"


def _departures_from_root(root):
    """Рейсы из таблицы ответа. None — таблицы нет (неизвестный формат)."""
    table = root.find(".//table")
    if table is None or len(table) == 0:
        return None
    departures = []
    for row in table.findall(".//tr")[1:]:
        cells = row.findall(".//td")
        if len(cells) == 4:
            departures.append(Departure(_cell_text(cells[0]), _cell_text(cells[2]), _cell_text(cells[3])))
    return departures


def parse_departures(response_text: str):
    """Рейсы из ответа load_station.php: [] — «рейсов нет», None — ответ не разобран."""
    try:
        root = etree.fromstring(response_text, etree.HTMLParser())
    except Exception:
        return None
    if root is None:
        return None
    if root.find(NO_TRIPS_XPATH) is not None:
        return []
    return _departures_from_root(root)
```

Заменить метод `_parse_response_table` целиком на:
```python
    def _parse_response_table(self, response_text: str):
        try:
            root = etree.fromstring(response_text, etree.HTMLParser())

            # 1. Проверка на сообщение "Нет рейсов"
            font_tag = root.find(NO_TRIPS_XPATH)
            if font_tag is not None:
                 return f"😕 <b>Нет рейсов:</b> {font_tag.text}"

            departures = _departures_from_root(root)
            if departures is None:
                return "⚠️ Нет данных или ошибка парсинга."

            lines = []

            # --- ШАПКА (Обычный текст) ---
            match = re.search(r'^(.*)<table border=1>', response_text, re.DOTALL)
            if match:
                station_name = match.group(1).strip()
                lines.append(f"🚏 <b>{station_name}</b>")
            else:
                lines.append("🚏 <b>Расписание</b>")

            if TIMETABLE_NOTICE:
                lines.append(f"<blockquote>⚠️ <i>{TIMETABLE_NOTICE}</i></blockquote>")

            # --- СПИСОК (Таблица Bot API 10.3) ---
            lines.append("<table compact bordered striped>")
            lines.append("<tr><th>Маршрут</th><th>Отправление</th><th>Прибытие</th></tr>")

            if not departures:
                lines.append("<tr><td colspan=\"3\" align=\"center\">Рейсов не найдено</td></tr>")

            for d in departures:
                lines.append(f"<tr><td align=\"center\">🚋 {d.route}</td><td align=\"center\">{d.departure}</td>"
                             f"<td align=\"center\">🏁 {d.arrival}</td></tr>")

            lines.append("</table>")
            # --- ПОДВАЛ (Обычный текст) ---

            lines.append("<i>Время местное</i>")

            return '\n'.join(lines)

        except Exception:
            logger.exception("Ошибка парсинга расписания")
            return "🚫 Не удалось разобрать ответ сайта ИжГЭТ. Попробуйте позже."
```

После метода `get_timetable` добавить:
```python
    async def get_departures(self, route: str, stn: str, dstn: str, dt: str, start: str, timeint: int):
        """Рейсы на дату dt (ДД.ММ.ГГГГ) от времени start (ЧЧ:ММ) на timeint минут вперёд.

        [] — рейсов нет, None — сайт недоступен или ответ не разобран.
        """
        hours, minutes = start.split(":")
        data = {
            'route': route,
            'stn': stn,
            'dstn': dstn,
            'dt': dt,
            'th_rasp': hours,
            'tm_rasp': minutes,
            'timeint': str(timeint),
        }
        session = await self._get_session()
        try:
            async with session.post(self._url, data=data, ssl=False) as response:
                if response.status != 200:
                    logger.warning("ИжГЭТ ответил статусом %s на запрос рейсов", response.status)
                    return None
                return parse_departures(await response.text())
        except Exception as e:
            logger.warning("Ошибка сети при запросе рейсов: %r", e)
            return None
```

- [ ] **Step 4: Все тесты парсера проходят, включая характеризационные**

Run: `venv/Scripts/python.exe -m pytest tests/test_parser.py -q`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add request.py tests/test_parser.py
git commit -m "feat: parse departures as a list, add get_departures for arbitrary start time"
```

---

### Task 4: БД — режимы подписки и `reminder_runs`

**Files:**
- Modify: `db/db.py` (`create_tables`, `delete_favorite_route`, блок «Подписки»)
- Create: `tests/test_db.py`

- [ ] **Step 1: Тесты**

`tests/test_db.py`:
```python
import sqlite3

import db.db as db


def test_migration_keeps_old_subscriptions(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    conn = sqlite3.connect("izhGet.db")
    conn.execute("""CREATE TABLE subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, fav_id INTEGER,
        notify_time TEXT, is_active INTEGER DEFAULT 1)""")
    conn.execute("INSERT INTO subscriptions (user_id, fav_id, notify_time) VALUES (5, 7, '07:30')")
    conn.commit()
    conn.close()

    db.create_tables()
    db.create_tables()  # повторный запуск не падает

    assert db.get_due_schedule_subscriptions("07:30") == [(1, 5, 7, "all")]
    assert db.get_subscription(5, 7) == (1, 5, 7, "07:30", 1, "schedule", "all", None)
    assert db.get_remind_subscriptions() == []


def test_add_and_update_subscription(tmp_db):
    sub_id = db.add_subscription(5, 7, "08:00", mode="remind", days="weekdays", lead_min=10)
    assert db.get_subscription(5, 7) == (sub_id, 5, 7, "08:00", 1, "remind", "weekdays", 10)
    assert db.get_remind_subscriptions() == [(sub_id, 5, 7, "08:00", "weekdays", 10)]
    assert db.get_due_schedule_subscriptions("08:00") == []

    assert db.add_subscription(5, 7, "07:30") == sub_id
    assert db.get_subscription(5, 7) == (sub_id, 5, 7, "07:30", 1, "schedule", "all", None)


def test_add_run_is_unique_per_day(tmp_db):
    assert db.add_run(1, 5, "2026-10-26", "07:57", "08:07", "1", "08:17", "planned") is True
    assert db.add_run(1, 5, "2026-10-26", "07:50", None, None, None, "planned") is False
    assert db.get_run(1, "2026-10-26")[1] == "planned"
    assert db.get_run(1, "2026-10-27") is None


def test_get_due_runs_and_claim(tmp_db):
    sub_id = db.add_subscription(5, 7, "08:00", mode="remind", days="all", lead_min=10)
    db.add_run(sub_id, 5, "2026-10-26", "07:57", "08:07", "1", "08:17", "planned")

    assert db.get_due_runs("2026-10-26", "07:56") == []
    due = db.get_due_runs("2026-10-26", "07:57")
    assert len(due) == 1
    run_id, user_id, fire_at, dep_time, route, next_dep, fav_id, notify_time = due[0]
    assert (user_id, fire_at, dep_time, route, next_dep, fav_id, notify_time) == \
        (5, "07:57", "08:07", "1", "08:17", 7, "08:00")
    assert db.get_due_runs("2026-10-27", "07:57") == []

    assert db.claim_run(run_id, "sent") is True
    assert db.claim_run(run_id, "sent") is False
    assert db.get_due_runs("2026-10-26", "08:30") == []


def test_changing_subscription_resets_planned_run_only(tmp_db):
    sub_id = db.add_subscription(5, 7, "08:00", mode="remind", days="all", lead_min=10)
    db.add_run(sub_id, 5, "2026-10-25", "07:57", "08:07", "1", None, "sent")
    db.add_run(sub_id, 5, "2026-10-26", "07:57", "08:07", "1", None, "planned")

    db.add_subscription(5, 7, "08:00", mode="remind", days="all", lead_min=5)

    assert db.get_run(sub_id, "2026-10-26") is None
    assert db.get_run(sub_id, "2026-10-25")[1] == "sent"


def test_delete_subscription_removes_runs(tmp_db):
    sub_id = db.add_subscription(5, 7, "08:00", mode="remind", days="all", lead_min=10)
    db.add_run(sub_id, 5, "2026-10-26", "07:57", "08:07", "1", None, "planned")
    assert db.delete_subscription(sub_id, 6) is False
    assert db.get_run(sub_id, "2026-10-26") is not None
    assert db.delete_subscription(sub_id, 5) is True
    assert db.get_run(sub_id, "2026-10-26") is None


def test_delete_favorite_removes_subscription_and_runs(tmp_db):
    fav_id = db.add_favorite_route(5, "1", "1900", "900", "30", "Дом")
    sub_id = db.add_subscription(5, fav_id, "08:00", mode="remind", days="all", lead_min=10)
    db.add_run(sub_id, 5, "2026-10-26", "07:57", "08:07", "1", None, "planned")
    assert db.delete_favorite_route(fav_id, 5) is True
    assert db.get_subscription(5, fav_id) is None
    assert db.get_run(sub_id, "2026-10-26") is None


def test_cleanup_runs(tmp_db):
    db.add_run(1, 5, "2026-10-23", "07:57", None, None, None, "sent")
    db.add_run(1, 5, "2026-10-24", "07:57", None, None, None, "sent")
    db.cleanup_runs("2026-10-24")
    assert db.get_run(1, "2026-10-23") is None
    assert db.get_run(1, "2026-10-24") is not None
```

- [ ] **Step 2: Убедиться, что падают**

Run: `venv/Scripts/python.exe -m pytest tests/test_db.py -q`
Expected: FAIL (`AttributeError: module 'db.db' has no attribute 'get_due_schedule_subscriptions'` и т.п.).

- [ ] **Step 3: Реализация**

В `create_tables()` сразу после `CREATE TABLE IF NOT EXISTS subscriptions (...)` добавить:
```python
        # Режимы подписки (для существующих БД; у старых записей — прежнее поведение)
        for ddl in ("mode TEXT DEFAULT 'schedule'", "days TEXT DEFAULT 'all'", "lead_min INTEGER"):
            try:
                cursor.execute(f'ALTER TABLE subscriptions ADD COLUMN {ddl}')
            except Exception:
                pass

        # Запланированные напоминания «когда выходить» — по одному на подписку в день
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminder_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sub_id INTEGER,
            user_id INTEGER,
            day TEXT,
            fire_at TEXT,
            dep_time TEXT,
            route TEXT,
            next_dep TEXT,
            status TEXT,
            UNIQUE (sub_id, day)
        )''')
```

В `delete_favorite_route` заменить блок `if deleted:` на:
```python
        if deleted:
            cursor.execute(
                'DELETE FROM reminder_runs WHERE sub_id IN (SELECT id FROM subscriptions WHERE fav_id = ? AND user_id = ?)',
                (fav_id, user_id)
            )
            cursor.execute('DELETE FROM subscriptions WHERE fav_id = ? AND user_id = ?', (fav_id, user_id))
```

Заменить функции `add_subscription`, `get_subscription`, `delete_subscription`, `get_due_subscriptions` (весь блок от `def add_subscription` до конца `get_due_subscriptions`) на:
```python
SUBSCRIPTION_COLUMNS = 'id, user_id, fav_id, notify_time, is_active, mode, days, lead_min'


def add_subscription(user_id, fav_id, notify_time, mode='schedule', days='all', lead_min=None):
    """Добавляет или обновляет подписку. Возвращает ID записи.

    При изменении сбрасывает ещё не отправленное напоминание — планировщик пересчитает его.
    """
    with connection_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id FROM subscriptions WHERE user_id = ? AND fav_id = ?',
            (user_id, fav_id)
        )
        existing = cursor.fetchone()
        if existing:
            cursor.execute(
                'UPDATE subscriptions SET notify_time = ?, mode = ?, days = ?, lead_min = ?, is_active = 1 WHERE id = ?',
                (notify_time, mode, days, lead_min, existing[0])
            )
            cursor.execute("DELETE FROM reminder_runs WHERE sub_id = ? AND status = 'planned'", (existing[0],))
            conn.commit()
            return existing[0]
        cursor.execute(
            'INSERT INTO subscriptions (user_id, fav_id, notify_time, mode, days, lead_min) VALUES (?, ?, ?, ?, ?, ?)',
            (user_id, fav_id, notify_time, mode, days, lead_min)
        )
        conn.commit()
        return cursor.lastrowid

def get_subscription(user_id, fav_id):
    """Возвращает (id, user_id, fav_id, notify_time, is_active, mode, days, lead_min) или None."""
    with connection_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f'SELECT {SUBSCRIPTION_COLUMNS} FROM subscriptions WHERE user_id = ? AND fav_id = ?',
            (user_id, fav_id)
        )
        return cursor.fetchone()

def delete_subscription(sub_id, user_id):
    """Удаляет подписку по ID вместе с её напоминаниями, только если принадлежит user_id."""
    with connection_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM subscriptions WHERE id = ? AND user_id = ?', (sub_id, user_id))
        deleted = cursor.rowcount > 0
        if deleted:
            cursor.execute('DELETE FROM reminder_runs WHERE sub_id = ?', (sub_id,))
        conn.commit()
        return deleted

def get_due_schedule_subscriptions(notify_time: str):
    """Подписки «расписание в заданное время» на эту минуту: [(id, user_id, fav_id, days), ...]"""
    with connection_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, user_id, fav_id, days FROM subscriptions "
            "WHERE notify_time = ? AND is_active = 1 AND mode = 'schedule'",
            (notify_time,)
        )
        return cursor.fetchall()

def get_remind_subscriptions():
    """Активные подписки «напомнить, когда выходить»: [(id, user_id, fav_id, notify_time, days, lead_min), ...]"""
    with connection_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, user_id, fav_id, notify_time, days, lead_min FROM subscriptions "
            "WHERE is_active = 1 AND mode = 'remind'"
        )
        return cursor.fetchall()

# --- Напоминания «когда выходить» ---

def add_run(sub_id, user_id, day, fire_at, dep_time, route, next_dep, status) -> bool:
    """Записывает план на день. False — на этот день план уже есть."""
    with connection_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT OR IGNORE INTO reminder_runs (sub_id, user_id, day, fire_at, dep_time, route, next_dep, status) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (sub_id, user_id, day, fire_at, dep_time, route, next_dep, status)
        )
        conn.commit()
        return cursor.rowcount == 1

def get_run(sub_id, day):
    """(id, status) плана подписки на день или None."""
    with connection_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, status FROM reminder_runs WHERE sub_id = ? AND day = ?', (sub_id, day))
        return cursor.fetchone()

def get_due_runs(day, now):
    """Наступившие неотправленные напоминания:
    [(run_id, user_id, fire_at, dep_time, route, next_dep, fav_id, notify_time), ...]"""
    with connection_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT r.id, r.user_id, r.fire_at, r.dep_time, r.route, r.next_dep, s.fav_id, s.notify_time "
            "FROM reminder_runs r JOIN subscriptions s ON s.id = r.sub_id "
            "WHERE r.day = ? AND r.status = 'planned' AND r.fire_at <= ?",
            (day, now)
        )
        return cursor.fetchall()

def claim_run(run_id, status) -> bool:
    """Атомарно переводит план из planned в status. False — его уже обработал другой проход."""
    with connection_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE reminder_runs SET status = ? WHERE id = ? AND status = 'planned'",
            (status, run_id)
        )
        conn.commit()
        return cursor.rowcount == 1

def cleanup_runs(before_day):
    """Удаляет планы старше before_day (YYYY-MM-DD)."""
    with connection_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM reminder_runs WHERE day < ?', (before_day,))
        conn.commit()
```

Примечание: `get_due_subscriptions` удалена — её единственный пользователь (`main.py`) переезжает в `scheduler.py` в Task 6. `get_subscription` теперь возвращает 8 полей, а старый `on_sub_ask` распаковывает 5 — его переписывает Task 7. Между Task 4 и Task 7 бот целиком не работает, это ожидаемо; не деплоить до конца плана.

- [ ] **Step 4: Тесты проходят**

Run: `venv/Scripts/python.exe -m pytest tests/test_db.py -q`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add db/db.py tests/test_db.py
git commit -m "feat: subscription modes/days columns and reminder_runs table"
```

---

### Task 5: Клавиатуры

**Files:**
- Modify: `keyboards/keyboards.py` (импорты, `SubCallback`, `get_delete_kb`, `get_sub_manage_kb`, новые функции)
- Modify: вызовы `get_delete_kb` в `handlers/favorite_route.py:59-60` и `handlers/subscription.py:28-29`
- Create: `tests/test_keyboards.py`

- [ ] **Step 1: Тесты**

`tests/test_keyboards.py`:
```python
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
```

- [ ] **Step 2: Убедиться, что падают**

Run: `venv/Scripts/python.exe -m pytest tests/test_keyboards.py -q`
Expected: FAIL (`AttributeError: module 'keyboards.keyboards' has no attribute 'get_sub_mode_kb'`, неверные подписи).

- [ ] **Step 3: Реализация**

В начале `keyboards/keyboards.py` после импортов aiogram добавить:
```python
import reminders
```

Заменить класс `SubCallback`:
```python
class SubCallback(CallbackData, prefix="sub"):
    action: str  # 'ask', 'edit', 'del', 'mode', 'days', 'lead'
    id: str      # fav_id; для 'del' — "sub_id_fav_id"; для 'mode'/'days'/'lead' — выбранное значение
```

Заменить `get_delete_kb`:
```python
def get_delete_kb(fav_id, sub=None):
    """sub — строка из db.get_subscription (или None, если подписки нет)."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Переименовать", callback_data=FavCallback(action='rename_ask', id=str(fav_id)))
    builder.button(text="❌ Удалить", callback_data=FavCallback(action='del', id=str(fav_id)))
    sub_text = reminders.sub_button_text(sub[5], sub[3]) if sub else "🔔 Подписаться"
    builder.button(text=sub_text, callback_data=SubCallback(action='ask', id=str(fav_id)))
    builder.button(text="💖 Поддержать автора", url=DONATE_URL)
    builder.button(text="🔙 Назад к списку", callback_data="back_to_favorites")
    builder.adjust(2, 1, 1, 1)
    return builder.as_markup()
```

В `get_sub_manage_kb` заменить подпись `"✏️ Изменить время"` на `"✏️ Изменить"`.

После `get_cancel_sub_kb` добавить:
```python
def get_sub_mode_kb(fav_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Расписание", callback_data=SubCallback(action='mode', id=reminders.MODE_SCHEDULE))
    builder.button(text="🚶 Напоминание", callback_data=SubCallback(action='mode', id=reminders.MODE_REMIND))
    builder.button(text="Отмена", callback_data=f"sub_back_{fav_id}")
    builder.adjust(2, 1)
    return builder.as_markup()


def get_sub_days_kb(fav_id):
    builder = InlineKeyboardBuilder()
    for key, label in reminders.DAYS_LABELS.items():
        builder.button(text=label, callback_data=SubCallback(action='days', id=key))
    builder.button(text="Отмена", callback_data=f"sub_back_{fav_id}")
    builder.adjust(3, 1)
    return builder.as_markup()


def get_sub_lead_kb(fav_id):
    builder = InlineKeyboardBuilder()
    for minutes in reminders.LEAD_CHOICES:
        builder.button(text=str(minutes), callback_data=SubCallback(action='lead', id=str(minutes)))
    builder.button(text="Отмена", callback_data=f"sub_back_{fav_id}")
    builder.adjust(len(reminders.LEAD_CHOICES), 1)
    return builder.as_markup()


def get_reminder_kb(fav_id):
    """Под напоминанием «пора выходить»: открыть маршрут и донат."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Полное расписание", callback_data=FavCallback(action='select', id=str(fav_id)))
    builder.button(text="💖 Поддержать автора", url=DONATE_URL)
    builder.adjust(2)
    return builder.as_markup()
```

Обновить вызовы `get_delete_kb` (параметра `has_subscription` больше нет). В `handlers/favorite_route.py` (`on_favorite_click`) и в `handlers/subscription.py` (`_show_favorite`) заменить:
```python
    sub = db.get_subscription(user_id, fav_id)
    markup = kb.get_delete_kb(fav_id, has_subscription=bool(sub))
```
на:
```python
    markup = kb.get_delete_kb(fav_id, db.get_subscription(user_id, fav_id))
```

- [ ] **Step 4: Тесты проходят, старый параметр нигде не используется**

Run: `venv/Scripts/python.exe -m pytest tests/test_keyboards.py -q`
Expected: all passed.

Run: `grep -rn "has_subscription" --include=*.py . | grep -v venv`
Expected: пусто.

- [ ] **Step 5: Commit**

```bash
git add keyboards/keyboards.py handlers/favorite_route.py handlers/subscription.py tests/test_keyboards.py
git commit -m "feat: keyboards for subscription mode, days, lead time and reminder"
```

---

### Task 6: Планировщик `scheduler.py`

**Files:**
- Create: `scheduler.py`, `tests/test_scheduler.py`
- Modify: `main.py` (целиком)

- [ ] **Step 1: Тесты**

`tests/test_scheduler.py`:
```python
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
```

Фикстура `site` проверяет `dt == "26.10.2026"`: в субботнем тесте `get_departures` не вызывается, поэтому это верно для всех вызовов.

- [ ] **Step 2: Убедиться, что падают**

Run: `venv/Scripts/python.exe -m pytest tests/test_scheduler.py -q`
Expected: ошибка сбора — `ModuleNotFoundError: No module named 'scheduler'`.

- [ ] **Step 3: Реализация `scheduler.py`**

```python
"""Минутный планировщик подписок: расписание в заданное время и «напомни, когда выходить»."""
import asyncio
import html
import logging
from datetime import datetime, timedelta

import pytz
from aiogram import Bot
from aiogram.types import InputRichMessage

import db.db as db
import keyboards.keyboards as kb
import reminders
from request import parser, get_result

logger = logging.getLogger(__name__)

TZ = pytz.timezone('Europe/Samara')
# Сколько подписок обрабатываем одновременно (каждая — запрос к сайту ИжГЭТ)
CONCURRENCY = 5
# Если планировщик отстал (сон ноутбука, долгая пауза), догоняем не больше стольких минут
MAX_CATCH_UP = timedelta(minutes=10)


async def _run_limited(items, worker):
    """worker(item) для каждого элемента, не больше CONCURRENCY одновременно; ошибки — в лог."""
    semaphore = asyncio.Semaphore(CONCURRENCY)

    async def one(item):
        async with semaphore:
            try:
                await worker(item)
            except Exception:
                logger.exception("Ошибка обработки подписки: %s", item)

    await asyncio.gather(*(one(item) for item in items))


async def _send(bot: Bot, user_id: int, html_text: str, markup):
    await bot.send_rich_message(chat_id=user_id, rich_message=InputRichMessage(html=html_text), reply_markup=markup)


async def _send_schedule(bot: Bot, sub):
    _, user_id, fav_id, _ = sub
    fav = db.get_favorite(user_id, fav_id)
    if not fav:
        return
    _, route, snt, dsnt, timeint, custom_name = fav
    html_text = await get_result(timeint=timeint, snt=snt, dsnt=dsnt, route=route)
    name = html.escape(reminders.route_name(custom_name, route))
    await _send(bot, user_id, f"🔔 <b>{name}</b><br><br>{html_text}", kb.get_donate_kb())


async def _plan_reminder(bot: Bot, sub, now: str, today):
    sub_id, user_id, fav_id, notify_time, _, lead_min = sub
    fav = db.get_favorite(user_id, fav_id)
    if not fav:
        return
    _, route, snt, dsnt, _, custom_name = fav
    day = today.isoformat()

    departures = await parser.get_departures(route, snt, dsnt, today.strftime('%d.%m.%Y'),
                                             notify_time, reminders.PLAN_WINDOW_MIN)
    if departures is None:
        # Сайт не ответил — следующая минута попробует снова; к моменту «цель − N» сдаёмся и предупреждаем
        give_up_at = reminders.fire_time(notify_time, lead_min)
        if reminders.to_minutes(now) >= reminders.to_minutes(give_up_at):
            if db.add_run(sub_id, user_id, day, now, None, None, None, 'skipped'):
                name = reminders.route_name(custom_name, route)
                await _send(bot, user_id, reminders.site_error_text(name), kb.get_reminder_kb(fav_id))
        return

    first, following = reminders.pick_trips(departures, notify_time)
    if first:
        db.add_run(sub_id, user_id, day, reminders.fire_time(first.departure, lead_min),
                   first.departure, first.route, following.departure if following else None, 'planned')
    else:
        db.add_run(sub_id, user_id, day, reminders.fire_time(notify_time, lead_min), None, None, None, 'planned')


async def _send_reminder(bot: Bot, run, now: str):
    run_id, user_id, fire_at, dep_time, route, next_dep, fav_id, notify_time = run
    action = reminders.run_action(now, fire_at, dep_time)
    if action == 'wait':
        return
    # Захват до отправки: параллельный проход (догон минут) не отправит второй раз,
    # а ошибка Telegram не приведёт к повтору каждую минуту
    if not db.claim_run(run_id, 'sent' if action == 'send' else 'skipped') or action == 'skip':
        return
    fav = db.get_favorite(user_id, fav_id)
    name = reminders.route_name(fav[5], fav[1]) if fav else "Маршрут"
    if dep_time:
        text = reminders.reminder_text(name, route, dep_time, next_dep, now)
    else:
        text = reminders.no_trips_text(name, notify_time)
    await _send(bot, user_id, text, kb.get_reminder_kb(fav_id))


async def process_minute(bot: Bot, moment: datetime):
    """Всё, что нужно сделать в минуту moment (aware datetime в TZ)."""
    now = moment.strftime('%H:%M')
    today = moment.date()
    day = today.isoformat()

    schedule_subs = [s for s in db.get_due_schedule_subscriptions(now) if reminders.day_matches(s[3], today)]

    db.cleanup_runs((today - timedelta(days=2)).isoformat())
    remind_subs = [s for s in db.get_remind_subscriptions()
                   if reminders.day_matches(s[4], today)
                   and reminders.should_plan(now, s[3])
                   and db.get_run(s[0], day) is None]

    await asyncio.gather(
        _run_limited(schedule_subs, lambda s: _send_schedule(bot, s)),
        _run_limited(remind_subs, lambda s: _plan_reminder(bot, s, now, today)),
    )
    # После планирования: напоминание, чей момент уже наступил, уходит в ту же минуту
    await _run_limited(db.get_due_runs(day, now), lambda r: _send_reminder(bot, r, now))


async def run(bot: Bot):
    """Раз в минуту запускает process_minute.

    Обработка идёт в фоне, поэтому медленный сайт ИжГЭТ не задерживает следующую минуту.
    Минуты, пропущенные из-за задержек, догоняются (но не больше MAX_CATCH_UP).
    """
    running = set()  # держим ссылки на задачи, чтобы их не собрал GC
    last_minute = datetime.now(TZ).replace(second=0, microsecond=0) - timedelta(minutes=1)
    while True:
        try:
            now_minute = datetime.now(TZ).replace(second=0, microsecond=0)
            if now_minute - last_minute > MAX_CATCH_UP:
                logger.warning("Планировщик подписок отстал, пропускаю минуты до %s", now_minute - MAX_CATCH_UP)
                last_minute = now_minute - MAX_CATCH_UP
            while last_minute < now_minute:
                last_minute += timedelta(minutes=1)
                task = asyncio.create_task(process_minute(bot, last_minute))
                running.add(task)
                task.add_done_callback(running.discard)
        except Exception:
            logger.exception("Ошибка в планировщике подписок")
        await asyncio.sleep(10)
```

- [ ] **Step 4: `main.py` — только запуск планировщика**

Заменить `main.py` целиком:
```python
import asyncio
import logging
import os
from dotenv import load_dotenv

load_dotenv()

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault

# Импорт роутеров
from handlers import common, new_route, favorite_route, admin, inline
from handlers import subscription
from middlewares import UserRegisterMiddleware
from request import parser
import db.db as db
import scheduler


async def main():
    # 1. Инициализация БД
    db.create_tables()
    print("Database initialized.")

    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        print("Error: BOT_TOKEN is missing in .env")
        return

    bot = Bot(
        token=bot_token, 
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher()

    # 3. Регистрация Middleware
    dp.update.outer_middleware(UserRegisterMiddleware())

    # 4. Подключение роутеров
    # admin — первым: иначе текстовый реплай админа перехватит заглушка из common
    dp.include_router(admin.router)
    dp.include_router(common.router)
    dp.include_router(new_route.router)
    dp.include_router(favorite_route.router)
    dp.include_router(subscription.router)
    dp.include_router(inline.router)

    # 5. Меню команд
    commands = [
        BotCommand(command="start", description="Начало работы"),
        BotCommand(command="new", description="Найти транспорт"),
        BotCommand(command="favorites", description="Мои маршруты"),
        BotCommand(command="support", description="Вопрос разработчику"),
        BotCommand(command="donate", description="Поддержать проект"),
    ]
    
    try:
        await bot.delete_my_commands()
        await bot.set_my_commands(commands, scope=BotCommandScopeDefault(), language_code="ru")
        await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
        
        print("Bot started!")
        await bot.delete_webhook(drop_pending_updates=True)
        scheduler_task = asyncio.create_task(scheduler.run(bot))  # noqa: F841 — ссылка не даёт GC собрать задачу
        await dp.start_polling(bot)
    finally:
        await parser.close()
        await bot.session.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")
```

- [ ] **Step 5: Тесты проходят, бот импортируется**

Run: `venv/Scripts/python.exe -m pytest -q`
Expected: all passed.

Run: `venv/Scripts/python.exe -c "import main; print('ok')"`
Expected: `ok`

- [ ] **Step 6: Commit**

```bash
git add scheduler.py main.py tests/test_scheduler.py
git commit -m "feat: scheduler module with leave reminders planning and sending"
```

---

### Task 7: Сценарий настройки подписки

**Files:**
- Modify: `handlers/subscription.py` (целиком)
- Create: `tests/test_subscription_flow.py`

- [ ] **Step 1: Тесты**

`tests/test_subscription_flow.py`:
```python
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
```

- [ ] **Step 2: Убедиться, что падают**

Run: `venv/Scripts/python.exe -m pytest tests/test_subscription_flow.py -q`
Expected: FAIL (на экране старый текст «Подписка на расписание», нет обработчиков `mode`/`days`/`lead`).

- [ ] **Step 3: Реализация — `handlers/subscription.py` целиком**

```python
import re
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InputRichMessage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import db.db as db
import keyboards.keyboards as kb
import reminders
from keyboards.keyboards import SubCallback
from request import get_result, parser

router = Router()

MODE_TEXT = (
    "<b>🔔 Как присылать?</b>\n\n"
    "<b>📋 Расписание в заданное время</b> — каждый день в выбранное время бот пришлёт расписание "
    "этого маршрута. Удобно, если хочешь сам посмотреть ближайшие рейсы.\n\n"
    "<b>🚶 Напомнить, когда выходить</b> — укажи, к какому времени ты готов выйти и сколько идти "
    "до остановки. Бот сам найдёт первый рейс после этого времени и напишет ровно тогда, когда пора "
    "выходить, плюс подскажет следующий рейс на случай, если не успеешь."
)
DAYS_TEXT = "📅 В какие дни присылать?"
LEAD_TEXT = "⏱ За сколько минут предупредить? (сколько тебе идти до остановки)"
TIME_TEXT = {
    reminders.MODE_SCHEDULE: "🕗 Во сколько присылать расписание?",
    reminders.MODE_REMIND: "🕗 Во сколько ты готов выйти? Я найду первый рейс не раньше этого времени.",
}
TIME_HINT = "\n\nВведите время в формате <b>ЧЧ:ММ</b>, например: <code>07:30</code> или <code>8:00</code>"
STALE_TEXT = "⌛ Настройка устарела (бот перезапускался). Начни заново: /favorites"


class SubEdit(StatesGroup):
    waiting_for_time = State()


async def _show_favorite(call: CallbackQuery, user_id: int, fav_id: int):
    """Загружает и показывает расписание избранного маршрута."""
    target = db.get_favorite(user_id, fav_id)
    if not target:
        await call.message.edit_text("❌ Маршрут не найден.", reply_markup=None)
        return
    _, route, snt, dsnt, timeint, _ = target
    await call.message.edit_text("⏳ Загружаю расписание...", reply_markup=None)
    text_result = await get_result(timeint=timeint, snt=snt, dsnt=dsnt, route=route)
    markup = kb.get_delete_kb(fav_id, db.get_subscription(user_id, fav_id))
    # Расписание содержит <table> — его понимает только rich_message
    await call.bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        rich_message=InputRichMessage(html=text_result),
        reply_markup=markup
    )


def _parse_time(text: str):
    """Парсит строку ЧЧ:ММ. Возвращает 'HH:MM' или None при ошибке."""
    match = re.match(r'^(\d{1,2}):(\d{2})$', text.strip())
    if not match:
        return None
    h, m = int(match.group(1)), int(match.group(2))
    if not (0 <= h <= 23 and 0 <= m <= 59):
        return None
    return f"{h:02d}:{m:02d}"


async def _get_setup(call: CallbackQuery, state: FSMContext, *keys):
    """Данные настройки подписки. FSM живёт в памяти и теряется при перезапуске бота —
    тогда кнопки старого сообщения сообщают об этом, а не падают с KeyError."""
    data = await state.get_data()
    if all(data.get(k) for k in keys):
        return data
    await state.clear()
    await call.answer()
    await call.message.edit_text(STALE_TEXT, reply_markup=None)
    return None


async def _start_setup(call: CallbackQuery, state: FSMContext, fav_id: int):
    await state.clear()
    await state.update_data(sub_fav_id=fav_id)
    await call.message.edit_text(MODE_TEXT, parse_mode="HTML", reply_markup=kb.get_sub_mode_kb(fav_id))


async def _ask_time(call: CallbackQuery, state: FSMContext, mode: str, fav_id: int):
    await call.message.edit_text(TIME_TEXT[mode] + TIME_HINT, parse_mode="HTML",
                                 reply_markup=kb.get_cancel_sub_kb(fav_id))
    await state.set_state(SubEdit.waiting_for_time)


@router.callback_query(SubCallback.filter(F.action == "ask"))
async def on_sub_ask(call: CallbackQuery, callback_data: SubCallback, state: FSMContext):
    fav_id = int(callback_data.id)
    user_id = call.from_user.id

    fav = db.get_favorite(user_id, fav_id)
    if not fav:
        await call.answer("Маршрут не найден", show_alert=True)
        return

    existing = db.get_subscription(user_id, fav_id)
    if existing:
        sub_id, _, _, notify_time, _, mode, days, lead_min = existing
        await call.message.edit_text(
            f"🔔 <b>Подписка активна</b>\n\n{reminders.summary_text(mode, days, notify_time, lead_min, fav[4])}",
            parse_mode="HTML",
            reply_markup=kb.get_sub_manage_kb(sub_id, fav_id)
        )
        return

    await _start_setup(call, state, fav_id)


@router.callback_query(SubCallback.filter(F.action == "edit"))
async def on_sub_edit(call: CallbackQuery, callback_data: SubCallback, state: FSMContext):
    await _start_setup(call, state, int(callback_data.id))


@router.callback_query(SubCallback.filter(F.action == "mode"))
async def on_sub_mode(call: CallbackQuery, callback_data: SubCallback, state: FSMContext):
    data = await _get_setup(call, state, 'sub_fav_id')
    if data is None:
        return
    await state.update_data(sub_mode=callback_data.id)
    await call.message.edit_text(DAYS_TEXT, reply_markup=kb.get_sub_days_kb(data['sub_fav_id']))


@router.callback_query(SubCallback.filter(F.action == "days"))
async def on_sub_days(call: CallbackQuery, callback_data: SubCallback, state: FSMContext):
    data = await _get_setup(call, state, 'sub_fav_id', 'sub_mode')
    if data is None:
        return
    await state.update_data(sub_days=callback_data.id)
    if data['sub_mode'] == reminders.MODE_REMIND:
        await call.message.edit_text(LEAD_TEXT, reply_markup=kb.get_sub_lead_kb(data['sub_fav_id']))
    else:
        await _ask_time(call, state, data['sub_mode'], data['sub_fav_id'])


@router.callback_query(SubCallback.filter(F.action == "lead"))
async def on_sub_lead(call: CallbackQuery, callback_data: SubCallback, state: FSMContext):
    data = await _get_setup(call, state, 'sub_fav_id', 'sub_mode', 'sub_days')
    if data is None:
        return
    await state.update_data(sub_lead=int(callback_data.id))
    await _ask_time(call, state, data['sub_mode'], data['sub_fav_id'])


@router.message(SubEdit.waiting_for_time)
async def on_sub_time_input(message: Message, state: FSMContext):
    notify_time = _parse_time(message.text or "")
    if not notify_time:
        await message.answer(
            "⚠️ Неверный формат. Введите время как <b>ЧЧ:ММ</b>, например: <code>07:30</code>",
            parse_mode="HTML"
        )
        return

    data = await state.get_data()
    await state.clear()
    fav_id, mode, days = data.get('sub_fav_id'), data.get('sub_mode'), data.get('sub_days')
    lead_min = data.get('sub_lead') if mode == reminders.MODE_REMIND else None
    if not (fav_id and mode and days) or (mode == reminders.MODE_REMIND and not lead_min):
        await message.answer(STALE_TEXT)
        return

    user_id = message.from_user.id
    fav = db.get_favorite(user_id, fav_id)
    if not fav:
        await message.answer("❌ Маршрут не найден.")
        return
    _, route, snt, dsnt, timeint, _ = fav

    db.add_subscription(user_id, fav_id, notify_time, mode=mode, days=days, lead_min=lead_min)
    text = reminders.confirmation_text(mode, days, notify_time, lead_min, timeint)

    if mode == reminders.MODE_REMIND:
        # Ловим опечатки вроде 3:00 вместо 8:00, пока пользователь ещё здесь
        today = parser._get_current_datetime()['date']
        departures = await parser.get_departures(route, snt, dsnt, today, notify_time, reminders.PLAN_WINDOW_MIN)
        if departures == []:
            text += f"\n\n⚠️ После {notify_time} в течение часа рейсов не нашлось — проверь время."

    await message.answer(text)


@router.callback_query(SubCallback.filter(F.action == "del"))
async def on_sub_delete(call: CallbackQuery, callback_data: SubCallback):
    sub_id, fav_id = map(int, callback_data.id.split("_"))
    user_id = call.from_user.id
    db.delete_subscription(sub_id, user_id)
    await call.answer("🔕 Подписка отменена")
    await _show_favorite(call, user_id, fav_id)


@router.callback_query(F.data.startswith("sub_back_"))
async def on_sub_back(call: CallbackQuery, state: FSMContext):
    await state.clear()
    fav_id = int(call.data.split("_")[-1])
    user_id = call.from_user.id
    await _show_favorite(call, user_id, fav_id)
```

- [ ] **Step 4: Все тесты проходят**

Run: `venv/Scripts/python.exe -m pytest -q`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add handlers/subscription.py tests/test_subscription_flow.py
git commit -m "feat: subscription setup flow with schedule/remind modes and days"
```

---

### Task 8: Документация и финальная проверка

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: CLAUDE.md**

В разделе `## Running` после блока Docker добавить:
````markdown
```bash
# Tests
pip install -r requirements-dev.txt
python -m pytest
```
````

В разделе `## Architecture` в дерево файлов добавить строки (после `request.py`):
```
reminders.py         — Pure logic for subscription modes: days filter, trip choice, reminder texts
scheduler.py         — Minute loop: schedule-mode sends, leave-reminder planning (reminder_runs) and sending
tests/               — pytest suite; fixtures/ holds saved ижгэт.рф responses
```

В `### Key data flow` добавить пункт:
```markdown
5. Subscriptions have `mode` (`schedule` — timetable at HH:MM; `remind` — message N minutes before the first trip not earlier than HH:MM) and `days` (`all`/`weekdays`/`weekends`). `remind` subs are planned 60 min before the target into `reminder_runs` (one row per sub per day), then sent by `scheduler.process_minute`.
```

В `### DB schema notes` добавить:
```markdown
`subscriptions` extra columns: `mode`, `days`, `lead_min` (added via `ALTER TABLE`; old rows default to `schedule`/`all`). `reminder_runs`: `sub_id, user_id, day (YYYY-MM-DD), fire_at, dep_time, route, next_dep, status (planned/sent/skipped)`, `UNIQUE(sub_id, day)`.
```

- [ ] **Step 2: Полный прогон и импорт бота**

Run: `venv/Scripts/python.exe -m pytest -q`
Expected: all passed.

Run: `venv/Scripts/python.exe -c "import main; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: describe subscription modes, scheduler and tests"
```

- [ ] **Step 4: Ручная проверка в Telegram** — по разделу «Ручная проверка в Telegram» спеки (тестовый бот, напоминание на «сейчас + 70 минут»).
