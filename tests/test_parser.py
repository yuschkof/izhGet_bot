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
