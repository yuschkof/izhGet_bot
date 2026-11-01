"""Устойчивость к сайту ИжГЭТ: минутный кэш, кэш списков остановок, запасное расписание."""
import datetime

import aiohttp
import pytest

import request
from tests.test_parser import FakeHttp, FakeResponse

STATIONS_HTML = '<select><option value="0">выберите</option><option value="1900">Аграрный</option></select>'
NETWORK_ERROR = aiohttp.ClientError("boom")


@pytest.fixture
def clock():
    """Управляемое время: state['now'] — местное «сейчас», state['mono'] — секунды для TTL."""
    return {"now": datetime.datetime(2026, 10, 26, 8, 0), "mono": 1000.0}


@pytest.fixture
def make_parser(monkeypatch, clock):
    def make(http):
        p = request.TimetableParser()

        async def get_session():
            return http
        monkeypatch.setattr(p, "_get_session", get_session)
        monkeypatch.setattr(p, "_now", lambda: p._timezone.localize(clock["now"]))
        monkeypatch.setattr(p, "_clock", lambda: clock["mono"])
        return p
    return make


@pytest.fixture(autouse=True)
def no_stats(monkeypatch):
    monkeypatch.setattr(request.db, "update_uses_statistics", lambda date: None)


def set_time(clock, hh, mm, day=26, plus_seconds=0):
    clock["now"] = datetime.datetime(2026, 10, day, hh, mm)
    clock["mono"] += plus_seconds


def rows(html_text):
    return [line for line in html_text.splitlines() if line.startswith("<tr><td")]


# --- Минутный кэш расписания ---

async def test_same_timetable_within_a_minute_hits_site_once(make_parser, clock, fixture_html):
    http = FakeHttp(FakeResponse(200, fixture_html("timetable_trips.html")))
    p = make_parser(http)

    first = await p.get_timetable("1", "1900", "900", "60")
    set_time(clock, 8, 0, plus_seconds=30)
    second = await p.get_timetable("1", "1900", "900", "60")

    assert first == second
    assert len(http.sent) == 1


async def test_timetable_cache_expires_after_a_minute(make_parser, clock, fixture_html):
    http = FakeHttp(FakeResponse(200, fixture_html("timetable_trips.html")))
    p = make_parser(http)

    await p.get_timetable("1", "1900", "900", "60")
    set_time(clock, 8, 0, plus_seconds=61)
    await p.get_timetable("1", "1900", "900", "60")

    assert len(http.sent) == 2


async def test_different_routes_are_cached_separately(make_parser, fixture_html):
    http = FakeHttp(FakeResponse(200, fixture_html("timetable_trips.html")))
    p = make_parser(http)

    await p.get_timetable("1", "1900", "900", "60")
    await p.get_timetable("1", "1900", "900", "30")

    assert len(http.sent) == 2


async def test_failures_are_not_cached(make_parser, clock, fixture_html):
    http = FakeHttp(error=NETWORK_ERROR)
    p = make_parser(http)

    await p.get_timetable("1", "1900", "900", "60")
    http.error, http.response = None, FakeResponse(200, fixture_html("timetable_trips.html"))
    out = await p.get_timetable("1", "1900", "900", "60")

    assert len(rows(out)) == 6


# --- Запасное расписание ---

async def test_site_down_shows_last_timetable_without_departed_trips(make_parser, clock, fixture_html):
    http = FakeHttp(FakeResponse(200, fixture_html("timetable_trips.html")))
    p = make_parser(http)
    await p.get_timetable("1", "1900", "900", "60")

    http.error = NETWORK_ERROR
    set_time(clock, 8, 20, plus_seconds=1200)
    out = await p.get_timetable("1", "1900", "900", "60")

    assert "не отвечает" in out and "08:00" in out
    departures = [r.split("</td>")[1].split(">")[-1] for r in rows(out)]
    assert departures == ["08:27", "08:35", "08:46", "08:57"]


async def test_unparsable_answer_also_falls_back(make_parser, clock, fixture_html):
    http = FakeHttp(FakeResponse(200, fixture_html("timetable_trips.html")))
    p = make_parser(http)
    await p.get_timetable("1", "1900", "900", "60")

    http.response = FakeResponse(200, "<html><body>технические работы</body></html>")
    set_time(clock, 8, 10, plus_seconds=600)
    out = await p.get_timetable("1", "1900", "900", "60")

    assert "не отвечает" in out
    assert len(rows(out)) == 5


async def test_no_fallback_when_all_trips_departed(make_parser, clock, fixture_html):
    http = FakeHttp(FakeResponse(200, fixture_html("timetable_trips.html")))
    p = make_parser(http)
    await p.get_timetable("1", "1900", "900", "60")

    http.error = NETWORK_ERROR
    set_time(clock, 9, 0, plus_seconds=3600)
    out = await p.get_timetable("1", "1900", "900", "60")

    assert out.startswith("🚫")


async def test_no_fallback_from_yesterday(make_parser, clock, fixture_html):
    http = FakeHttp(FakeResponse(200, fixture_html("timetable_trips.html")))
    p = make_parser(http)
    await p.get_timetable("1", "1900", "900", "60")

    http.error = NETWORK_ERROR
    set_time(clock, 7, 0, day=27, plus_seconds=86400)
    out = await p.get_timetable("1", "1900", "900", "60")

    assert out.startswith("🚫")


async def test_no_fallback_for_other_route(make_parser, clock, fixture_html):
    http = FakeHttp(FakeResponse(200, fixture_html("timetable_trips.html")))
    p = make_parser(http)
    await p.get_timetable("1", "1900", "900", "60")

    http.error = NETWORK_ERROR
    set_time(clock, 8, 1, plus_seconds=60)
    out = await p.get_timetable("2", "1900", "900", "60")

    assert out.startswith("🚫")


# --- Рейсы для напоминаний: кэш есть, запасного нет ---

async def test_get_departures_cached_but_never_stale(make_parser, clock, fixture_html):
    http = FakeHttp(FakeResponse(200, fixture_html("timetable_trips.html")))
    p = make_parser(http)

    first = await p.get_departures("1", "1900", "900", "26.10.2026", "08:00", 60)
    again = await p.get_departures("1", "1900", "900", "26.10.2026", "08:00", 60)
    assert first == again and len(http.sent) == 1

    http.error = NETWORK_ERROR
    set_time(clock, 8, 0, plus_seconds=61)
    assert await p.get_departures("1", "1900", "900", "26.10.2026", "08:00", 60) is None


# --- Списки остановок ---

async def test_stations_cached(make_parser):
    http = FakeHttp(FakeResponse(200, STATIONS_HTML))
    p = make_parser(http)

    assert await p.get_stations("1", "26.10.2026") == {"1900": "Аграрный"}
    assert await p.get_stations("1", "26.10.2026") == {"1900": "Аграрный"}
    assert len(http.sent) == 1


async def test_stations_fallback_to_last_known_even_from_other_day(make_parser, clock):
    http = FakeHttp(FakeResponse(200, STATIONS_HTML))
    p = make_parser(http)
    await p.get_stations("1", "26.10.2026")
    await p.get_destinations("1", "26.10.2026", "1900")

    http.error = NETWORK_ERROR
    assert await p.get_stations("1", "27.10.2026") == {"1900": "Аграрный"}
    assert await p.get_destinations("1", "27.10.2026", "1900") == {"1900": "Аграрный"}
    assert await p.get_stations("2", "27.10.2026") == {}


async def test_old_fallbacks_are_swept(make_parser, clock, fixture_html, monkeypatch):
    monkeypatch.setattr(request, "CACHE_SWEEP_SIZE", 2)
    http = FakeHttp(FakeResponse(200, fixture_html("timetable_trips.html")))
    p = make_parser(http)
    await p.get_timetable("1", "1900", "900", "60")
    await p.get_timetable("2", "1900", "900", "60")

    set_time(clock, 8, 0, day=27, plus_seconds=86400)
    await p.get_timetable("3", "1900", "900", "60")

    assert [k[0] for k in p._last_timetable] == ["3"]
