import asyncio
import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv
from handlers import common, new_route, favorite_route

async def main():
    # Bot commands definition
    commands = [
        {"command": "start", "description": "Начать диалог"},
        {"command": "new", "description": "Новый маршрут"},
        {"command": "favorites", "description": "Избранные маршруты"},
        {"command": "add_favorite", "description": "Добавить избранный маршрут"},
        {"command": "delete_favorite", "description": "Удалить избранный маршрут"},
        {"command": "developer", "description": "Создатель"},
        {"command": "description", "description": "Описание"},
        {"command": "help", "description": "Помощь"},
        {"command": "dice", "description": "На удачу"}
    ]
    # Load environment variables
    load_dotenv()
    bot_token = os.getenv('BOT_TOKEN')
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize bot and dispatcher with DefaultBotProperties
    bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode='HTML'))
    dp = Dispatcher()
    
    # Include routers
    dp.include_router(common.router)
    dp.include_router(new_route.router)
    dp.include_router(favorite_route.router)
    
    # Set bot commands
    await bot.set_my_commands(commands, language_code="ru")
    
    # Start polling
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Error starting bot: {e}")

if __name__ == '__main__':
    asyncio.run(main())