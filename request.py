import re
from typing import List, Dict, Optional
from datetime import datetime
import pytz
import requests
from lxml import etree

import db.db as db

class TimetableParser:

    def __init__(self, timezone: str = 'Asia/Dubai'):
        self._timezone = pytz.timezone(timezone)
        self._session = requests.Session()

    def _get_current_datetime(self) -> Dict[str, str]:
        now = datetime.now(self._timezone)
        return {
            'date': now.strftime("%d.%m.%Y"),
            'hours': now.strftime("%H"),
            'minutes': now.strftime("%M")
        }

    def _prepare_request_data(self, route: str, stn: str, dstn: str, timeint: str) -> Dict[str, str]:
        current_datetime = self._get_current_datetime()
        return {
            'route': route,
            'stn': stn,
            'dstn': dstn,
            'dt': current_datetime['date'],
            'th_rasp': current_datetime['hours'],
            'tm_rasp': current_datetime['minutes'],
            'timeint': timeint,
        }

    def _parse_response_table(self, response_text: str) -> List[str]:
        html_parser = etree.HTMLParser()
        root = etree.fromstring(response_text, html_parser)
        table = root.find(".//table")

        if table is None or len(table) == 0:
            font_tag = root.find(".//font[@color='RED'][@size='3']")
            return [font_tag.text] if font_tag is not None else []
        
        template ='''<pre>
|Маршрут|   Время   | Время  |
|       |отправления|прибытия|
|:------|:---------:|-------:|'''
                  
        text = re.search(r'^(.*)<table border=1>', response_text, re.DOTALL).group(1)
        parts = [text, template]

        rows = table.findall(".//tr")[1:]
        for row in rows:
            cells = row.findall(".//td")
            if len(cells) == 4:
                route = cells[0].text.strip()
                departure_time = cells[2].text.strip()
                arrival_time = cells[3].text.strip()
                
                route_format = f"   {route}   " if len(route) == 1 else f"   {route}  "
                parts.append(f"|{route_format}|   {departure_time}   | {arrival_time}  |")
                parts.append("|----------------------------|")

        parts.append('</pre>')
        return parts

    def get_timetable(self, route: str, stn: str, dstn: str, timeint: str) -> Optional[str]:
        db.create_tabel_statistics()
        current_date = self._get_current_datetime()['date']
        db.update_uses_statistics(current_date)

        request_data = self._prepare_request_data(route, stn, dstn, timeint)
        response = self._session.post(
            'https://xn--c1aff6b0c.xn--p1ai/rasp/load_station.php', 
            data=request_data
        )

        parsed_table = self._parse_response_table(response.text)
        return '\n'.join(parsed_table) if parsed_table else None

def get_result(timeint, snt, dsnt, route):
    parser = TimetableParser()
    return parser.get_timetable(route, snt, dsnt, timeint) or "Расписание не найдено"