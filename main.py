import asyncio
import logging
import os
import pytz
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault

# Импорт роутеров
from handlers import common, new_route, favorite_route, admin, inline
from handlers import subscription
from middlewares import UserRegisterMiddleware
from request import parser, get_result
import db.db as db

async def send_subscription_notifications(bot: Bot, notify_time: str):
    subs = db.get_due_subscriptions(notify_time)
    for sub_id, user_id, fav_id in subs:
        try:
            favorites = db.get_favorite_routes(user_id)
            target = next((f for f in favorites if f[0] == fav_id), None)
            if not target:
                continue
            _, route, snt, dsnt, timeint, custom_name = target
            text = await get_result(timeint=timeint, snt=snt, dsnt=dsnt, route=route)
            name = custom_name or f"Маршрут {route}"
            await bot.send_message(
                user_id,
                f"🔔 <b>{name}</b>\n\n{text}",
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Ошибка рассылки подписки sub_id={sub_id}: {e}")


async def subscription_scheduler(bot: Bot):
    tz = pytz.timezone('Europe/Samara')
    last_minute = None
    while True:
        now = datetime.now(tz)
        current_minute = now.strftime("%H:%M")
        if current_minute != last_minute:
            last_minute = current_minute
            await send_subscription_notifications(bot, current_minute)
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
    dp.include_router(common.router)
    dp.include_router(new_route.router)
    dp.include_router(favorite_route.router)
    dp.include_router(subscription.router)
    dp.include_router(admin.router)
    dp.include_router(inline.router)

    # 5. Меню команд
    commands = [
        BotCommand(command="start", description="Начало работы"),
        BotCommand(command="new", description="Найти транспорт"),
        BotCommand(command="favorites", description="Мои маршруты"),
        BotCommand(command="support", description="Вопрос разработчику"),
    ]
    
    try:
        await bot.delete_my_commands()
        await bot.set_my_commands(commands, scope=BotCommandScopeDefault(), language_code="ru")
        await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
        
        print("Bot started!")
        await bot.delete_webhook(drop_pending_updates=True)
        asyncio.create_task(subscription_scheduler(bot))
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
