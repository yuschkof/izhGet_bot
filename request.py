import re
import aiohttp
import pytz
from datetime import datetime
from lxml import etree
import db.db as db

class TimetableParser:
    def __init__(self, timezone: str = 'Asia/Dubai'):
        self._timezone = pytz.timezone(timezone)
        self._url = 'https://xn--c1aff6b0c.xn--p1ai/rasp/load_station.php'

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

            lines.append("➖➖➖➖➖➖➖➖")
            
            # --- СПИСОК (Моноширинный текст для выравнивания) ---
            # Открываем тег <pre>, чтобы цифры встали ровно друг под другом
            lines.append("<pre>") 

            rows = table.findall(".//tr")[1:] 
            
            if not rows:
                lines.append(" Рейсов не найдено")

            for row in rows:
                cells = row.findall(".//td")
                if len(cells) == 4:
                    route = cells[0].text.strip()
                    departure_time = cells[2].text.strip()
                    arrival_time = cells[3].text.strip()
                    
                    # МАГИЯ ВЫРАВНИВАНИЯ:
                    # {route:<3} — означает "занять под номер маршрута ровно 3 символа".
                    # Если номер "9", бот добавит 2 пробела. Если "12" — 1 пробел.
                    # Это выровняет часы 🕒 идеально по вертикали.
                    
                    line = f"🚌 {route:<3} 🕒 {departure_time} ➝ 🏁 {arrival_time}"
                    lines.append(line)

            lines.append("</pre>")
            # --- ПОДВАЛ (Обычный текст) ---
            
            lines.append("➖➖➖➖➖➖➖➖")
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

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self._url, data=data) as response:
                    if response.status == 200:
                        html = await response.text()
                        return self._parse_response_table(html)
                    return "🚫 Сайт ИжГЭТ недоступен."
            except Exception as e:
                return f"🚫 Ошибка сети: {e}"

async def get_result(timeint, snt, dsnt, route):
    parser = TimetableParser()
    return await parser.get_timetable(route, snt, dsnt, timeint)