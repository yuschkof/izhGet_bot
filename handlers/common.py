from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
import db.db as db

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        "Я бот для просмотра расписания транспорта ИжГЭТ.\n"
        "Помогаю быстро узнать, когда приедет твой трамвай или троллейбус.\n\n"
        "⚠️ <b>Важно:</b> Я не являюсь официальным ботом ИжГЭТ. "
        "Данные берутся с открытого сайта, поэтому я не несу ответственности за возможные неточности в расписании или опоздания транспорта.\n\n"
        "🔎 Жми /new — найти маршрут\n"
        "⭐ Жми /favorites — сохраненные маршруты"
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "Команды бота:\n"
        "/new - Поиск расписания\n"
        "/favorites - Избранное\n"
    )

@router.message(Command("stat"))
async def cmd_stat(message: Message):
    if message.from_user.id != 842331262:
            return
    
    # Простая текстовая статистика
    users_count = db.get_users_count()
    stats_data = db.get_statistics() # Список кортежей (дата, просмотры)
    
    text = f"📊 <b>Статистика бота</b>\n\n"
    text += f"👥 Всего пользователей: {users_count}\n\n"
    text += "📅 Активность за последние дни:\n"
    
    if not stats_data:
        text += "Нет данных."
    else:
        for day, uses in stats_data[:10]: # Показываем последние 10 дней
            text += f"• {day}: {uses} запросов\n"
            
    await message.answer(text, parse_mode="HTML")