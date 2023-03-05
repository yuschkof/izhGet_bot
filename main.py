import asyncio
import os
from aiogram import Bot, Dispatcher
import logging
from dotenv import load_dotenv
from handlers import common, new_route, openai


async def main():
    load_dotenv()
    botApi = os.getenv('BOT_TOKEN')
    bot = Bot(token=botApi)
    dp = Dispatcher()
    logging.basicConfig(level=logging.INFO)

    dp.include_router(common.router)
    dp.include_router(new_route.router)
    dp.include_router(openai.router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
