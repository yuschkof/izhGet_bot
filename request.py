import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re


def get_result(timeint, snt, dsnt, route):
    tz = pytz.timezone('Asia/Dubai')
    now = datetime.now(tz)
    current_hours = now.strftime("%H")
    current_minute = now.strftime("%M")
    current_date = now.strftime("%d.%m.%Y")

    stroke = '''<pre>
|Маршрут|   Время   | Время  |
|       |отправления|прибытия|
|:------|:---------:|-------:|'''

    with requests.Session() as session:
        data = {
            'route': route,
            'stn': snt,
            'dstn': dsnt,
            'dt': current_date,
            'th_rasp': current_hours,
            'tm_rasp': current_minute,
            'timeint': timeint,
        }
        response = session.post(
            'https://xn--c1aff6b0c.xn--p1ai/rasp/load_station.php', data=data)

        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table')
        if not table:
            font_tag = soup.find('font', {'color': 'RED', 'size': '3'})
            return font_tag.text
        text = re.search(r'^(.*)<table border=1>', response.text, re.DOTALL).group(1)
        parts = [text, stroke]
        rows = table.find_all('tr')[1:]
        for row in rows:
            cells = row.find_all('td')
            if len(cells) == 4:
                route = cells[0].text.strip()
                departure_time = cells[2].text.strip()
                arrival_time = cells[3].text.strip()
                if len(route) == 1:
                    parts.append(
                        f"|   {route}   |   {departure_time}   | {arrival_time}  |")
                    parts.append("|----------------------------|")
                else:
                    parts.append(
                        f"|   {route}  |   {departure_time}   | {arrival_time}  |")
                    parts.append("|----------------------------|")
        parts.append('</pre>')
        return '\n'.join(parts)
