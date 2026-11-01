import asyncio
import logging
import os
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
from request import parser
import db.db as db
import scheduler


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
    # admin и кнопки внизу — раньше common: иначе текстовый реплай админа и нажатие
    # закреплённой кнопки перехватит заглушка неизвестных сообщений
    dp.include_router(admin.router)
    dp.include_router(favorite_route.pinned_router)
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
        scheduler_task = asyncio.create_task(scheduler.run(bot))  # noqa: F841 — ссылка не даёт GC собрать задачу
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
