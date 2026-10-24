import asyncio
import html
import logging
import os
import pytz
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault, InputRichMessage

# Импорт роутеров
from handlers import common, new_route, favorite_route, admin, inline
from handlers import subscription
from middlewares import UserRegisterMiddleware
from request import parser, get_result
import db.db as db
import keyboards.keyboards as kb

logger = logging.getLogger(__name__)

# Сколько подписок обрабатываем одновременно (каждая — запрос к сайту ИжГЭТ)
SUBSCRIPTION_CONCURRENCY = 5
# Если планировщик отстал (сон ноутбука, долгая пауза), догоняем не больше стольких минут
MAX_CATCH_UP = timedelta(minutes=10)


async def send_subscription(bot: Bot, sub_id: int, user_id: int, fav_id: int):
    try:
        target = db.get_favorite(user_id, fav_id)
        if not target:
            return
        _, route, snt, dsnt, timeint, custom_name = target
        html_text = await get_result(timeint=timeint, snt=snt, dsnt=dsnt, route=route)
        name = html.escape(custom_name or f"Маршрут {route}")

        await bot.send_rich_message(
            chat_id=user_id,
            rich_message=InputRichMessage(html=f"🔔 <b>{name}</b><br><br>{html_text}"),
            reply_markup=kb.get_donate_kb()
        )
    except Exception:
        logger.exception("Ошибка рассылки подписки sub_id=%s", sub_id)


async def send_subscription_notifications(bot: Bot, notify_time: str):
    subs = db.get_due_subscriptions(notify_time)
    if not subs:
        return
    semaphore = asyncio.Semaphore(SUBSCRIPTION_CONCURRENCY)

    async def limited(sub):
        async with semaphore:
            await send_subscription(bot, *sub)

    await asyncio.gather(*(limited(sub) for sub in subs))


async def subscription_scheduler(bot: Bot):
    """Раз в минуту запускает рассылку подписок.

    Рассылка идёт в фоне, поэтому медленный сайт ИжГЭТ не задерживает следующую минуту.
    Минуты, пропущенные из-за задержек, догоняются (но не больше MAX_CATCH_UP).
    """
    tz = pytz.timezone('Europe/Samara')
    running = set()  # держим ссылки на задачи, чтобы их не собрал GC
    last_minute = datetime.now(tz).replace(second=0, microsecond=0) - timedelta(minutes=1)
    while True:
        try:
            now_minute = datetime.now(tz).replace(second=0, microsecond=0)
            if now_minute - last_minute > MAX_CATCH_UP:
                logger.warning("Планировщик подписок отстал, пропускаю минуты до %s", now_minute - MAX_CATCH_UP)
                last_minute = now_minute - MAX_CATCH_UP
            while last_minute < now_minute:
                last_minute += timedelta(minutes=1)
                task = asyncio.create_task(send_subscription_notifications(bot, last_minute.strftime("%H:%M")))
                running.add(task)
                task.add_done_callback(running.discard)
        except Exception:
            logger.exception("Ошибка в планировщике подписок")
        await asyncio.sleep(10)


async def main():
    # 1. Инициализация БД
    db.create_tables()
    print("Database initialized.")

    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        print("Error: BOT_TOKEN is missing in .env")
        return

    bot = Bot(
        token=bot_token, 
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher()

    # 3. Регистрация Middleware
    dp.update.outer_middleware(UserRegisterMiddleware())

    # 4. Подключение роутеров
    # admin — первым: иначе текстовый реплай админа перехватит заглушка из common
    dp.include_router(admin.router)
    dp.include_router(common.router)
    dp.include_router(new_route.router)
    dp.include_router(favorite_route.router)
    dp.include_router(subscription.router)
    dp.include_router(inline.router)

    # 5. Меню команд
    commands = [
        BotCommand(command="start", description="Начало работы"),
        BotCommand(command="new", description="Найти транспорт"),
        BotCommand(command="favorites", description="Мои маршруты"),
        BotCommand(command="support", description="Вопрос разработчику"),
        BotCommand(command="donate", description="Поддержать проект"),
    ]
    
    try:
        await bot.delete_my_commands()
        await bot.set_my_commands(commands, scope=BotCommandScopeDefault(), language_code="ru")
        await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
        
        print("Bot started!")
        await bot.delete_webhook(drop_pending_updates=True)
        scheduler_task = asyncio.create_task(subscription_scheduler(bot))  # noqa: F841 — ссылка не даёт GC собрать задачу
        await dp.start_polling(bot)
    finally:
        await parser.close()
        await bot.session.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")
