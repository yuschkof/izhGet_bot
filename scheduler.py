"""Минутный планировщик подписок: расписание в заданное время и «напомни, когда выходить»."""
import asyncio
import html
import logging
from datetime import datetime, timedelta

import pytz
from aiogram import Bot
from aiogram.types import InputRichMessage

import db.db as db
import keyboards.keyboards as kb
import reminders
from request import parser, get_result

logger = logging.getLogger(__name__)

TZ = pytz.timezone('Europe/Samara')
# Сколько подписок обрабатываем одновременно (каждая — запрос к сайту ИжГЭТ)
CONCURRENCY = 5
# Если планировщик отстал (сон ноутбука, долгая пауза), догоняем не больше стольких минут
MAX_CATCH_UP = timedelta(minutes=10)


async def _run_limited(items, worker):
    """worker(item) для каждого элемента, не больше CONCURRENCY одновременно; ошибки — в лог."""
    semaphore = asyncio.Semaphore(CONCURRENCY)

    async def one(item):
        async with semaphore:
            try:
                await worker(item)
            except Exception:
                logger.exception("Ошибка обработки подписки: %s", item)

    await asyncio.gather(*(one(item) for item in items))


async def _send(bot: Bot, user_id: int, html_text: str, markup):
    await bot.send_rich_message(chat_id=user_id, rich_message=InputRichMessage(html=html_text), reply_markup=markup)


async def _send_schedule(bot: Bot, sub):
    _, user_id, fav_id, _ = sub
    fav = db.get_favorite(user_id, fav_id)
    if not fav:
        return
    _, route, snt, dsnt, timeint, custom_name = fav
    html_text = await get_result(timeint=timeint, snt=snt, dsnt=dsnt, route=route)
    name = html.escape(reminders.route_name(custom_name, route))
    await _send(bot, user_id, f"🔔 <b>{name}</b><br><br>{html_text}", kb.get_donate_kb())


async def _plan_reminder(bot: Bot, sub, now: str, today):
    sub_id, user_id, fav_id, notify_time, _, lead_min = sub
    fav = db.get_favorite(user_id, fav_id)
    if not fav:
        return
    _, route, snt, dsnt, _, custom_name = fav
    day = today.isoformat()

    departures = await parser.get_departures(route, snt, dsnt, today.strftime('%d.%m.%Y'),
                                             notify_time, reminders.PLAN_WINDOW_MIN)
    if departures is None:
        # Сайт не ответил — следующая минута попробует снова; к моменту «цель − N» сдаёмся и предупреждаем
        give_up_at = reminders.fire_time(notify_time, lead_min)
        if reminders.to_minutes(now) >= reminders.to_minutes(give_up_at):
            if db.add_run(sub_id, user_id, day, now, None, None, None, 'skipped'):
                name = reminders.route_name(custom_name, route)
                await _send(bot, user_id, reminders.site_error_text(name), kb.get_reminder_kb(fav_id))
        return

    first, following = reminders.pick_trips(departures, notify_time)
    if first:
        db.add_run(sub_id, user_id, day, reminders.fire_time(first.departure, lead_min),
                   first.departure, first.route, following.departure if following else None, 'planned')
    else:
        db.add_run(sub_id, user_id, day, reminders.fire_time(notify_time, lead_min), None, None, None, 'planned')


async def _send_reminder(bot: Bot, run, now: str):
    run_id, user_id, fire_at, dep_time, route, next_dep, fav_id, notify_time = run
    action = reminders.run_action(now, fire_at, dep_time)
    if action == 'wait':
        return
    # Захват до отправки: параллельный проход (догон минут) не отправит второй раз,
    # а ошибка Telegram не приведёт к повтору каждую минуту
    if not db.claim_run(run_id, 'sent' if action == 'send' else 'skipped') or action == 'skip':
        return
    fav = db.get_favorite(user_id, fav_id)
    name = reminders.route_name(fav[5], fav[1]) if fav else "Маршрут"
    if dep_time:
        text = reminders.reminder_text(name, route, dep_time, next_dep, now)
    else:
        text = reminders.no_trips_text(name, notify_time)
    await _send(bot, user_id, text, kb.get_reminder_kb(fav_id))


async def process_minute(bot: Bot, moment: datetime):
    """Всё, что нужно сделать в минуту moment (aware datetime в TZ)."""
    now = moment.strftime('%H:%M')
    today = moment.date()
    day = today.isoformat()

    schedule_subs = [s for s in db.get_due_schedule_subscriptions(now) if reminders.day_matches(s[3], today)]

    db.cleanup_runs((today - timedelta(days=2)).isoformat())
    remind_subs = [s for s in db.get_remind_subscriptions()
                   if reminders.day_matches(s[4], today)
                   and reminders.should_plan(now, s[3])
                   and db.get_run(s[0], day) is None]

    await asyncio.gather(
        _run_limited(schedule_subs, lambda s: _send_schedule(bot, s)),
        _run_limited(remind_subs, lambda s: _plan_reminder(bot, s, now, today)),
    )
    # После планирования: напоминание, чей момент уже наступил, уходит в ту же минуту
    await _run_limited(db.get_due_runs(day, now), lambda r: _send_reminder(bot, r, now))


async def run(bot: Bot):
    """Раз в минуту запускает process_minute.

    Обработка идёт в фоне, поэтому медленный сайт ИжГЭТ не задерживает следующую минуту.
    Минуты, пропущенные из-за задержек, догоняются (но не больше MAX_CATCH_UP).
    """
    running = set()  # держим ссылки на задачи, чтобы их не собрал GC
    last_minute = datetime.now(TZ).replace(second=0, microsecond=0) - timedelta(minutes=1)
    while True:
        try:
            now_minute = datetime.now(TZ).replace(second=0, microsecond=0)
            if now_minute - last_minute > MAX_CATCH_UP:
                logger.warning("Планировщик подписок отстал, пропускаю минуты до %s", now_minute - MAX_CATCH_UP)
                last_minute = now_minute - MAX_CATCH_UP
            while last_minute < now_minute:
                last_minute += timedelta(minutes=1)
                task = asyncio.create_task(process_minute(bot, last_minute))
                running.add(task)
                task.add_done_callback(running.discard)
        except Exception:
            logger.exception("Ошибка в планировщике подписок")
        await asyncio.sleep(10)
