import aiohttp
import pytest

import request
from reminders import Departure


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


def test_parse_departures_header_only_table():
    html_text = "X<table border=1><tr><td>h</td><td>h</td><td>h</td><td>h</td></tr></table>"
    assert request.parse_departures(html_text) == []


def test_parse_departures_unknown_row_format():
    html_text = ("X<table border=1><tr><td>h</td><td>h</td><td>h</td><td>h</td></tr>"
                 "<tr><td>1</td><td>x</td><td>08:15</td><td>08:40</td><td>extra</td></tr></table>")
    assert request.parse_departures(html_text) is None


async def test_get_departures_no_trips_end_to_end(monkeypatch, fixture_html):
    http = FakeHttp(FakeResponse(200, fixture_html("timetable_no_trips.html")))
    p = _parser_with(monkeypatch, http)
    assert await p.get_departures("1", "1900", "900", "26.10.2026", "08:00", 60) == []
