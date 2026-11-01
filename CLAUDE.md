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

```bash
# Tests
pip install -r requirements-dev.txt
python -m pytest
```

`.env` must contain `BOT_TOKEN`. Optional: `ADMIN_ID`, `TIMETABLE_NOTICE` (warning shown above every timetable; set to empty to hide it).

## Architecture

```
main.py              — Bot entry point: DB init, router registration
middlewares.py       — UserRegisterMiddleware: auto-registers every user on first interaction
request.py           — TimetableParser: HTTP scraper for ижгэт.рф (stations, destinations, timetable)
reminders.py         — Pure logic for subscription modes: days filter, trip choice, reminder texts
scheduler.py         — Minute loop: schedule-mode sends, leave-reminder planning (reminder_runs) and sending
db/db.py             — SQLite wrapper (izhGet.db): users, favorite_route, statistics, subscriptions, reminder_runs tables
tests/               — pytest suite; fixtures/ holds saved ижгэт.рф responses
handlers/
  common.py          — /start, /help
  new_route.py       — /new command: FSM flow (time → route → start stop → end stop → result)
  favorite_route.py  — /favorites: list, select, rename, delete saved routes
  subscription.py    — Subscription setup flow: mode → days → lead minutes → time; manage/unsubscribe
  inline.py          — Inline mode: search favorites, fetch timetable on chosen result
  admin.py           — Admin-only commands
keyboards/
  keyboards.py       — All InlineKeyboardBuilder factories + CallbackData classes
```

### Key data flow

1. User runs `/new` → FSM (`RouteOrder`) walks through 4 states collecting `timeint`, `route`, `snt`, `dsnt`
2. `TimetableParser.get_timetable()` POSTs to `ижгэт.рф/rasp/load_station.php` and parses HTML table with lxml
3. Result is displayed as HTML-formatted message; user can save it as a favorite
4. Favorites are stored in SQLite with a `custom_name` field; inline mode (`@bot`) searches them. Up to 4 favorites can be pinned (`favorite_route.pin_order`) to a persistent reply keyboard; a press sends the button text (= route name, unique among pinned, never starting with `/`), caught by `favorite_route.pinned_router`, which `main.py` registers before `common` so the unknown-text stub doesn't swallow it
5. Subscriptions have `mode` (`schedule` — timetable at HH:MM; `remind` — message N minutes before the first trip not earlier than HH:MM) and `days` (`all`/`weekdays`/`weekends`). `remind` subs are planned 60 min before the target into `reminder_runs` (one row per sub per day), then sent by `scheduler.process_minute`. The scheduler sends only on the current minute (catch-up minutes only plan), processes missed minutes newest first, and uses `db.claim_run` so a reminder is sent at most once. Changing a subscription deletes all its `reminder_runs`, so it is re-planned (even the same day).

### Callback data factories

- `TransportCallback(action, value)` — prefix `tr` — used for time/route/station selections
- `FavCallback(action, id)` — prefix `fav` — used for add/select/rename/delete/rename_ask favorites
- `SubCallback(action, id)` — prefix `sub` — subscription ask/edit/del and setup steps mode/days/lead (`id` carries the chosen value; `fav_id` lives in FSM data)

### Timezone

All local time (parser requests, subscription scheduler, statistics dates) uses `Europe/Samara` (UTC+4, same as Izhevsk; no DST).

### DB schema notes

`favorite_route` columns: `id, user_id, route, snt, dsnt, timeint, custom_name, pin_order` (`pin_order` NULL = not pinned; originally had `snt_name, dsnt_name` — see `migrate_all.py` for migration history).

`statistics.day` is stored as `DD.MM.YYYY`; sorting requires string manipulation (see `get_statistics()`).

`subscriptions` extra columns: `mode`, `days`, `lead_min` (added via `ALTER TABLE`; old rows default to `schedule`/`all`). `reminder_runs`: `sub_id, user_id, day (YYYY-MM-DD), fire_at, dep_time, route, next_dep, status (planned/sent/skipped)`, `UNIQUE(sub_id, day)`.
