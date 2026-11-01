import os
import re
import time
import logging
import aiohttp
import pytz
from datetime import datetime
from lxml import etree
import db.db as db
import reminders
from reminders import Departure

logger = logging.getLogger(__name__)

# Предупреждение над каждым расписанием. Задаётся в .env; пустое значение — не показывать.
TIMETABLE_NOTICE = os.getenv(
    "TIMETABLE_NOTICE",
    "Внимание: на сайте ИжГЭТ ведутся тех. работы, расписание может быть неточным."
).strip()

# Сайт ИжГЭТ иногда подвисает — не держим пользователя дольше этого
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)

SITE = 'https://xn--c1aff6b0c.xn--p1ai/rasp/'
# Сколько секунд переиспользуем ответ сайта на тот же запрос
TIMETABLE_TTL = 60
STATIONS_TTL = 6 * 3600  # списки остановок меняются редко
# Чистим просроченные ответы, когда кэш разрастается больше этого
CACHE_SWEEP_SIZE = 500


def _cell_text(cell) -> str:
    """Текст ячейки таблицы, включая вложенные теги; пустая ячейка -> ''."""
    return ''.join(cell.itertext()).strip()


NO_TRIPS_XPATH = ".//font[@color='RED'][@size='3']"


def _departures_from_root(root) -> list[Departure] | None:
    """Рейсы из таблицы ответа. None — таблицы нет (неизвестный формат)."""
    table = root.find(".//table")
    if table is None or len(table) == 0:
        return None
    rows = table.findall(".//tr")[1:]
    departures = []
    for row in rows:
        cells = row.findall(".//td")
        if len(cells) == 4:
            departures.append(Departure(_cell_text(cells[0]), _cell_text(cells[2]), _cell_text(cells[3])))
    if rows and not departures:
        return None  # строки есть, но формат не распознан — сайт изменил таблицу
    return departures


def parse_departures(response_text: str) -> list[Departure] | None:
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


def _render_timetable(response_text: str, departures: list[Departure], banner: str | None = None) -> str:
    """HTML-расписание для Telegram: шапка с сайта, предупреждения, таблица рейсов."""
    lines = []

    # --- ШАПКА (Обычный текст) ---
    match = re.search(r'^(.*)<table border=1>', response_text, re.DOTALL)
    if match:
        station_name = match.group(1).strip()
        lines.append(f"🚏 <b>{station_name}</b>")
    else:
        lines.append("🚏 <b>Расписание</b>")

    if banner:
        lines.append(f"<blockquote>⚠️ <b>{banner}</b></blockquote>")
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


class TimetableParser:
    def __init__(self, timezone: str = 'Europe/Samara'):
        self._timezone = pytz.timezone(timezone)
        self._url = SITE + 'load_station.php'
        self._session: aiohttp.ClientSession | None = None
        # (url, параметры) -> (истекает_в, текст ответа): один запрос к сайту на всех в пределах TTL
        self._responses: dict[tuple, tuple[float, str]] = {}
        # (route, stn, dstn, timeint) -> (когда получено, текст): запасное расписание на случай падения сайта
        self._last_timetable: dict[tuple, tuple[datetime, str]] = {}
        # (url, параметры без даты) -> последний непустой список остановок
        self._last_stations: dict[tuple, dict] = {}

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=REQUEST_TIMEOUT)
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    def _now(self) -> datetime:
        return datetime.now(self._timezone)

    def _clock(self) -> float:
        return time.monotonic()

    def _get_current_datetime(self):
        now = self._now()
        return {
            'date': now.strftime("%d.%m.%Y"),
            'hours': now.strftime("%H"),
            'minutes': now.strftime("%M")
        }

    async def _post(self, url: str, data: dict, ttl: float) -> str | None:
        """Ответ сайта (с кэшем на ttl секунд). None — сайт недоступен или ответил ошибкой."""
        key = (url, tuple(sorted(data.items())))
        cached = self._responses.get(key)
        if cached and cached[0] > self._clock():
            return cached[1]

        session = await self._get_session()
        try:
            async with session.post(url, data=data, ssl=False) as response:
                if response.status != 200:
                    logger.warning("ИжГЭТ ответил статусом %s на %s", response.status, url)
                    return None
                text = await response.text()
        except Exception as e:
            logger.warning("Ошибка сети при запросе %s: %r", url, e)
            return None

        now = self._clock()
        if len(self._responses) >= CACHE_SWEEP_SIZE:
            self._responses = {k: v for k, v in self._responses.items() if v[0] > now}
        self._responses[key] = (now + ttl, text)
        return text

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

            return _render_timetable(response_text, departures)

        except Exception:
            logger.exception("Ошибка парсинга расписания")
            return "🚫 Не удалось разобрать ответ сайта ИжГЭТ. Попробуйте позже."

    def _fallback_timetable(self, key: tuple) -> str | None:
        """Последнее удачное расписание за сегодня без ушедших рейсов. None — показать нечего."""
        saved = self._last_timetable.get(key)
        if not saved:
            return None
        fetched_at, response_text = saved
        now = self._now()
        if fetched_at.date() != now.date():
            return None
        now_min = now.hour * 60 + now.minute
        upcoming = [d for d in parse_departures(response_text) or []
                    if reminders.is_time(d.departure) and reminders.to_minutes(d.departure) >= now_min]
        if not upcoming:
            return None
        banner = (f"Сайт ИжГЭТ не отвечает — показываю расписание, полученное в "
                  f"{fetched_at.strftime('%H:%M')}. Ушедшие рейсы убраны.")
        return _render_timetable(response_text, upcoming, banner)

    async def get_timetable(self, route: str, stn: str, dstn: str, timeint: str):
        current_dt = self._get_current_datetime()

        try:
            db.update_uses_statistics(current_dt['date'])
        except Exception:
            pass

        data = {
            'route': route,
            'stn': stn,
            'dstn': dstn,
            'dt': current_dt['date'],
            'th_rasp': current_dt['hours'],
            'tm_rasp': current_dt['minutes'],
            'timeint': timeint,
        }
        key = (str(route), str(stn), str(dstn), str(timeint))

        html = await self._post(self._url, data, TIMETABLE_TTL)
        if html is not None and parse_departures(html) is not None:
            now = self._now()
            if len(self._last_timetable) >= CACHE_SWEEP_SIZE:
                # Запасное расписание годится только на сегодня — вчерашнее выбрасываем
                self._last_timetable = {k: v for k, v in self._last_timetable.items()
                                        if v[0].date() == now.date()}
            self._last_timetable[key] = (now, html)
            return self._parse_response_table(html)

        fallback = self._fallback_timetable(key)
        if fallback:
            return fallback
        if html is not None:
            return self._parse_response_table(html)  # ответ есть, но не разобран
        return "🚫 Сайт ИжГЭТ не отвечает. Попробуйте позже."

    async def get_departures(self, route: str, stn: str, dstn: str, dt: str, start: str, timeint: int):
        """Рейсы на дату dt (ДД.ММ.ГГГГ) от времени start (ЧЧ:ММ) на timeint минут вперёд.

        [] — рейсов нет, None — сайт недоступен или ответ не разобран.
        Запасное расписание здесь не используется: напоминание по устаревшим данным хуже повтора.
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
        text = await self._post(self._url, data, TIMETABLE_TTL)
        if text is None:
            return None
        return parse_departures(text)

    async def _get_station_list(self, page: str, data: dict) -> dict:
        """Список остановок {'id': 'Название'}; при недоступном сайте — последний известный."""
        url = SITE + page
        key = (url, tuple(sorted((k, v) for k, v in data.items() if k != 'dt')))
        html = await self._post(url, data, STATIONS_TTL)
        stations = self._parse_stations_html(html) if html is not None else {}
        if stations:
            self._last_stations[key] = stations
            return stations
        return self._last_stations.get(key, {})

    async def get_stations(self, route: str, dt: str) -> dict:
        """
        Получает список остановок для заданного маршрута и даты.
        Возвращает словарь: {'id_остановки': 'Название остановки'}
        """
        return await self._get_station_list('list_station.php', {'route': str(route), 'dt': dt})

    def _parse_stations_html(self, html_text: str) -> dict:
        """Внутренний метод для парсинга HTML списка остановок."""
        stations = {}
        try:
            html_parser = etree.HTMLParser()
            root = etree.fromstring(html_text, html_parser)

            # Находим все теги <option>
            options = root.findall(".//option")

            for opt in options:
                val = opt.get("value")
                name = opt.text

                # Отсеиваем пустые значения и пункт "выберите остановку..." (value="0")
                if val and val != "0" and name:
                    stations[val] = name.strip()

            return stations
        except Exception as e:
            print(f"🚫 Ошибка парсинга остановок: {e}")
            return {}

    async def get_destinations(self, route: str, dt: str, stn: str) -> dict:
        """
        Получает список конечных остановок (пунктов назначения)
        для заданного маршрута, даты и начальной остановки.
        Возвращает словарь: {'id_остановки': 'Название остановки'}
        """
        return await self._get_station_list(
            'list_destinations.php', {'route': str(route), 'dt': dt, 'stn': str(stn)})


# Глобальный экземпляр — используется во всех хэндлерах
parser = TimetableParser()


async def get_result(timeint, snt, dsnt, route):
    return await parser.get_timetable(route, snt, dsnt, timeint)
