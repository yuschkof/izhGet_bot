# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## About

Telegram bot for Izhevsk tram/trolleybus timetables. Data is scraped from [ижгэт.рф/rasp/](https://ижгэт.рф/rasp/). Live bot: [@izhGet_bot](https://t.me/izhGet_bot).

## Running

```bash
# Setup
python -m venv venv
source venv/bin/activate  # or .\venv\Scripts\activate on Windows
pip install -r requirements.txt

# Run directly
python main.py

# Run with Docker
docker-compose up -d
```

`.env` must contain `BOT_TOKEN`.

## Architecture

```
main.py              — Bot entry point: DB init, router registration
middlewares.py       — UserRegisterMiddleware: auto-registers every user on first interaction
request.py           — TimetableParser: HTTP scraper for ижгэт.рф (stations, destinations, timetable)
db/db.py             — SQLite wrapper (izhGet.db): users, favorite_route, statistics tables
handlers/
  common.py          — /start, /help
  new_route.py       — /new command: FSM flow (time → route → start stop → end stop → result)
  favorite_route.py  — /favorites: list, select, rename, delete saved routes
  inline.py          — Inline mode: search favorites, fetch timetable on chosen result
  admin.py           — Admin-only commands
keyboards/
  keyboards.py       — All InlineKeyboardBuilder factories + CallbackData classes
```

### Key data flow

1. User runs `/new` → FSM (`RouteOrder`) walks through 4 states collecting `timeint`, `route`, `snt`, `dsnt`
2. `TimetableParser.get_timetable()` POSTs to `ижгэт.рф/rasp/load_station.php` and parses HTML table with lxml
3. Result is displayed as HTML-formatted message; user can save it as a favorite
4. Favorites are stored in SQLite with a `custom_name` field; inline mode (`@bot`) searches them

### Callback data factories

- `TransportCallback(action, value)` — prefix `tr` — used for time/route/station selections
- `FavCallback(action, id)` — prefix `fav` — used for add/select/rename/delete/rename_ask favorites

### Timezone

The parser uses `Asia/Dubai` (UTC+4) as the local timezone for Izhevsk (Udmurtia does not observe DST).

### DB schema notes

`favorite_route` columns: `id, user_id, route, snt, dsnt, timeint, custom_name` (originally had `snt_name, dsnt_name` — see `migrate_all.py` for migration history).

`statistics.day` is stored as `DD.MM.YYYY`; sorting requires string manipulation (see `get_statistics()`).
