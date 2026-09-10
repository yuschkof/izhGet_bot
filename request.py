import re
import aiohttp
import pytz
from datetime import datetime
from lxml import etree
import db.db as db

class TimetableParser:
    def __init__(self, timezone: str = 'Europe/Samara'):
        self._timezone = pytz.timezone(timezone)
        self._url = 'https://xn--c1aff6b0c.xn--p1ai/rasp/load_station.php'
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
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
            html_parser = etree.HTMLParser()
            root = etree.fromstring(response_text, html_parser)
            
            # 1. Проверка на сообщение "Нет рейсов"
            font_tag = root.find(".//font[@color='RED'][@size='3']")
            if font_tag is not None:
                 return f"😕 <b>Нет рейсов:</b> {font_tag.text}"

            table = root.find(".//table")
            if table is None or len(table) == 0:
                return "⚠️ Нет данных или ошибка парсинга."
            
            lines = []
            
            # --- ШАПКА (Обычный текст) ---
            match = re.search(r'^(.*)<table border=1>', response_text, re.DOTALL)
            if match:
                station_name = match.group(1).strip()
                lines.append(f"🚏 <b>{station_name}</b>")
            else:
                lines.append("🚏 <b>Расписание</b>")

            lines.append("<blockquote>⚠️ <i>Внимание: на сайте ИжГЭТ ведутся тех. работы, расписание может быть неточным.</i></blockquote>")
            
            # --- СПИСОК (Таблица Bot API 10.3) ---
            lines.append("<table compact bordered striped>")
            lines.append("<tr><th>Маршрут</th><th>Отправление</th><th>Прибытие</th></tr>")

            rows = table.findall(".//tr")[1:] 
            
            if not rows:
                lines.append("<tr><td colspan=\"3\" align=\"center\">Рейсов не найдено</td></tr>")

            for row in rows:
                cells = row.findall(".//td")
                if len(cells) == 4:
                    route = cells[0].text.strip()
                    departure_time = cells[2].text.strip()
                    arrival_time = cells[3].text.strip()
                    
                    line = f"<tr><td align=\"center\">🚋 {route}</td><td align=\"center\">{departure_time}</td><td align=\"center\">🏁 {arrival_time}</td></tr>"
                    lines.append(line)

            lines.append("</table>")
            # --- ПОДВАЛ (Обычный текст) ---
            
            lines.append("<i>Время местное</i>")
            
            return '\n'.join(lines)

        except Exception as e:
            return f"🚫 Ошибка обработки данных: {e}"

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
                return "🚫 Сайт ИжГЭТ недоступен."
        except Exception as e:
            return f"🚫 Ошибка сети: {e}"

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
