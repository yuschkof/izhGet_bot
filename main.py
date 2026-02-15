import asyncio
import logging
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault

# Импорт роутеров
from handlers import common, new_route, favorite_route, admin, inline
from middlewares import UserRegisterMiddleware
import db.db as db

async def main():
    load_dotenv()
    
    # 1. Инициализация БД
    db.create_tables()
    print("Database initialized.")

    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        print("Error: BOT_TOKEN is missing in .env")
        return

    # 2. Настройка бота
    bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # 3. Регистрация Middleware
    dp.update.outer_middleware(UserRegisterMiddleware())

    # 4. Подключение роутеров
    dp.include_router(common.router)
    dp.include_router(new_route.router)
    dp.include_router(favorite_route.router)
    dp.include_router(admin.router)
    dp.include_router(inline.router)

    # 5. Меню команд
    commands = [
        BotCommand(command="start", description="Начало работы"),
        BotCommand(command="new", description="Найти транспорт"),
        BotCommand(command="favorites", description="Мои маршруты"),
    ]
    await bot.delete_my_commands()
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault(), language_code="ru")
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())

    print("Bot started!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")