import random
import logging
from aiogram import Router, types
from aiogram.types import URLInputFile
from aiogram.filters import CommandStart, Command
import db.db as db
import keyboards.keyboards as kb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()

STICKER_ID = 'CAACAgIAAxkBAAEH3Ppj9xWKbtQ-kWtb6uKkwvE8EbGCMQAC9ScAAp-e8Enjve-XHgojSS4E'

@router.message(CommandStart())
async def process_start_command(message: types.Message):
    try:
        await message.reply(
            """
Привет! 👋
Я бот с расписанием трамваев в г.Ижевск 🚃
Доступные команды:
- /new - Выбрать новый маршрут
- /favorites - Посмотреть избранные маршруты
- /add_favorite - Добавить маршрут в избранное
- /delete_favorite - Удалить маршрут из избранного
- /description - Описание бота
- /developer - Узнать о создателе
Для начала работы нажми /new и выбери интересующий маршрут! 🚉
            """        
        )
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await message.reply("Произошла ошибка при запуске бота.")

@router.message(Command('developer'))
async def process_developer_command(message: types.Message):
    try:
        await message.answer("Там я", reply_markup=kb.WebAppMe)
    except Exception as e:
        logger.error(f"Error in developer command: {e}")
        await message.reply("Произошла ошибка при отображении информации о разработчике.")

@router.message(Command('help'))
async def process_help_command(message: types.Message):
    try:
        msg = "Тут и так простое управление, как ты не смог(ла) разобраться?"
        await message.reply(msg)
        await message.answer_sticker(STICKER_ID)
    except Exception as e:
        logger.error(f"Error in help command: {e}")
        await message.reply("Произошла ошибка при обработке команды помощи.")

@router.message(Command('description'))
async def process_description_command(message: types.Message):
    try:
        msg = '''Уважаемые пассажиры, данная информационная система позволяет Вам рассчитать время отправления и прибытия на указанных остановочных пунктах трамваев. Напоминаем, что согласно правил технической эксплуатации трамвая существует допуск на отклонение от расписания +2 мин. (опоздание), -1 мин. (нагон).
Обращаем ваше внимание на то, что расписания для будних дней, субботы и воскресенья могут отличаться.
Данная информация основана на расписании движения трамваев, при условии отсутствия задержек в линии.'''
        await message.reply(msg)
    except Exception as e:
        logger.error(f"Error in description command: {e}")
        await message.reply("Произошла ошибка при отображении описания.")

@router.message(Command('statistics'))
async def cmd_statistics(message: types.Message):
    try:
        if message.from_user.id != 842331262:
            return
        
        day_usage_count = db.get_day_usage_count()
        favorite_route_count = db.get_favorite_route_count()
        user_count = db.get_user_count()
        
        await message.reply(
            f"""
Количество пользователей: {user_count}
Количество избранных маршрутов: {favorite_route_count}
Количество запросов за текущий день: {day_usage_count}
            """
        )
    except Exception as e:
        logger.error(f"Error in statistics command: {e}")
        await message.reply("Произошла ошибка при получении статистики.")

@router.message(Command('dice'))
async def cmd_dice(message: types.Message):
    try:
        dice = ['🎲', '🎯', '🏀', '⚽', '🎰', '🎳']
        await message.answer_dice(emoji=random.choice(dice))
    except Exception as e:
        logger.error(f"Error in dice command: {e}")
        await message.reply("Произошла ошибка при бросании кубика.")