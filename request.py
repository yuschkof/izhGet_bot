import os
import re
import logging
import aiohttp
import pytz
from datetime import datetime
from lxml import etree
import db.db as db
from reminders import Departure

logger = logging.getLogger(__name__)

# Предупреждение над каждым расписанием. Задаётся в .env; пустое значение — не показывать.
TIMETABLE_NOTICE = os.getenv(
    "TIMETABLE_NOTICE",
    "Внимание: на сайте ИжГЭТ ведутся тех. работы, расписание может быть неточным."
).strip()

# Сайт ИжГЭТ иногда подвисает — не держим пользователя дольше этого
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)


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


class TimetableParser:
    def __init__(self, timezone: str = 'Europe/Samara'):
        self._timezone = pytz.timezone(timezone)
        self._url = 'https://xn--c1aff6b0c.xn--p1ai/rasp/load_station.php'
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=REQUEST_TIMEOUT)
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    def _get_current_datetime(self):
        now = datetime.now(self._timezone)
        return {
            'date': now.strftime("%d.%m.%Y"),
            'hours': now.strftime("%H"),
            'minutes': now.strftime("%M")
        }

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

        session = await self._get_session()
        try:
            async with session.post(self._url, data=data, ssl=False) as response:
                if response.status == 200:
                    html = await response.text()
                    return self._parse_response_table(html)
                logger.warning("ИжГЭТ ответил статусом %s на запрос расписания", response.status)
                return "🚫 Сайт ИжГЭТ недоступен."
        except Exception as e:
            logger.warning("Ошибка сети при запросе расписания: %r", e)
            return "🚫 Сайт ИжГЭТ не отвечает. Попробуйте позже."

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
                text = await response.text()
        except Exception as e:
            logger.warning("Ошибка сети при запросе рейсов: %r", e)
            return None
        return parse_departures(text)

    async def get_stations(self, route: str, dt: str) -> dict:
        """
        Получает список остановок для заданного маршрута и даты.
        Возвращает словарь: {'id_остановки': 'Название остановки'}
        """
        url = 'https://xn--c1aff6b0c.xn--p1ai/rasp/list_station.php'
        data = {
            'route': str(route),
            'dt': dt
        }

        session = await self._get_session()
        try:
            async with session.post(url, data=data, ssl=False) as response:
                if response.status == 200:
                    html = await response.text()
                    return self._parse_stations_html(html)
                return {}
        except Exception as e:
            print(f"🚫 Ошибка сети при получении остановок: {e}")
            return {}

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
        url = 'https://xn--c1aff6b0c.xn--p1ai/rasp/list_destinations.php'
        data = {
            'route': str(route),
            'dt': dt,
            'stn': str(stn)
        }

        session = await self._get_session()
        try:
            async with session.post(url, data=data, ssl=False) as response:
                if response.status == 200:
                    html = await response.text()
                    return self._parse_stations_html(html)
                return {}
        except Exception as e:
            print(f"🚫 Ошибка сети при получении пунктов назначения: {e}")
            return {}


# Глобальный экземпляр — используется во всех хэндлерах
parser = TimetableParser()


async def get_result(timeint, snt, dsnt, route):
    return await parser.get_timetable(route, snt, dsnt, timeint)
