import os
from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup, default_state
import db.db as db
import keyboards.keyboards as kb

router = Router()

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

class SupportState(StatesGroup):
    waiting_for_message = State()

@router.message(Command("start"))
async def cmd_start(message: Message):
    text = (
        f"<h1>Привет, {message.from_user.first_name}! 👋</h1>"
        "Я бот для просмотра расписания транспорта ИжГЭТ.<br>"
        "Помогаю быстро узнать, когда приедет твой трамвай или троллейбус.<br><br>"
        "<blockquote>⚠️ <b>Важно:</b> Я не являюсь официальным ботом ИжГЭТ. "
        "Данные берутся с открытого сайта, поэтому я не несу ответственности за возможные неточности в расписании или опоздания транспорта.</blockquote>\n"
        "<h3>Команды:</h3>"
        "🔎 Жми /new — найти маршрут<br>"
        "⭐ Жми /favorites — сохраненные маршруты<br>"
        "💖 Жми /donate — поддержать проект"
    )
    from aiogram.types import InputRichMessage
    await message.bot.send_rich_message(
        chat_id=message.chat.id,
        rich_message=InputRichMessage(html=text)
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "<h1>Частые вопросы (FAQ)</h1>\n"
        "<details><summary>▶️ <b>Как искать расписание?</b></summary>\n"
        "Используйте команду /new. Бот предложит выбрать временной интервал, нужный маршрут, а затем начальную и конечную остановки.\n</details>\n"
        "<details><summary>▶️ <b>Как добавить в избранное?</b></summary>\n"
        "После того как вы нашли нужный рейс через /new, под расписанием появится кнопка «⭐ Добавить в избранное». Нажмите её, и маршрут появится в меню /favorites.\n</details>\n"
        "<details><summary>▶️ <b>Как работают подписки?</b></summary>\n"
        "Зайдите в /favorites, нажмите на любой маршрут и выберите «🔔 Подписаться». Выберите время, и бот будет каждый день присылать расписание в нужный момент!\n</details>\n"
        "<details><summary>▶️ <b>Почему расписание не совпадает?</b></summary>\n"
        "Бот берет данные с официального сайта ИжГЭТ. Иногда сайт может не работать или данные обновляются с задержкой (например, из-за пробок или тех. причин). Бот только отображает то, что есть на сайте.\n</details>\n"
        "<details><summary>▶️ <b>Как связаться с разработчиком?</b></summary>\n"
        "Используйте команду /support, чтобы написать сообщение разработчику. Вы также можете поддержать проект через /donate!\n</details>"
    )
    from aiogram.types import InputRichMessage
    await message.bot.send_rich_message(
        chat_id=message.chat.id,
        rich_message=InputRichMessage(html=text)
    )

@router.message(Command("donate"))
async def cmd_donate(message: Message):
    await message.answer(
        "💖 <b>Поддержать проект</b>\n\n"
        "Если бот оказался вам полезен, вы можете поддержать его разработку и оплату серверов:\n"
        "👉 <a href='https://t.me/tribute/app?startapp=dzqK'>Сделать донат через Tribute</a>\n\n"
        "Спасибо за вашу поддержку! 🥰",
        disable_web_page_preview=True
    )

@router.message(Command("stat"))
async def cmd_stat(message: Message):
    if message.from_user.id != ADMIN_ID:
            return
    
    users_count = db.get_users_count()
    favorites_count = db.get_favorites_count()
    subscriptions_count = db.get_subscriptions_count()
    stats_data = db.get_statistics()

    text = "<h1>📊 Статистика бота</h1>"
    text += f"👥 Пользователей: <b>{users_count}</b><br>"
    text += f"⭐ Сохранённых маршрутов: <b>{favorites_count}</b><br>"
    text += f"🔔 Активных подписок: <b>{subscriptions_count}</b><br><br>"
    
    text += "<details><summary>📅 <b>Активность за последние 10 дней</b></summary>\n<pre>"

    if not stats_data:
        text += "Нет данных."
    else:
        for row in stats_data[:10]:
            day, uses = row[0], row[1]
            unknown = row[2] if len(row) > 2 else 0
            new_users = row[3] if len(row) > 3 else 0
            dau = row[4] if len(row) > 4 else 0
            text += f"• {day}: {uses} запр., {dau} польз."
            if new_users:
                text += f", +{new_users} нов."
            if unknown:
                text += f", {unknown} неп."
            text += "\n"
            
    text += "</pre></details>"
    from aiogram.types import InputRichMessage
    await message.bot.send_rich_message(
        chat_id=message.chat.id,
        rich_message=InputRichMessage(html=text)
    )
    

# --- ЛОГИКА ОБРАЩЕНИЯ К АДМИНУ ---

@router.message(Command("support"))
async def cmd_support(message: Message, state: FSMContext):
    await message.answer(
        "✍️ <b>Напишите ваше сообщение для разработчика.</b>\n\n"
        "⚠️ <b>ВНИМАНИЕ:</b> Этот бот <b>НЕ является официальным</b> сервисом ИжГЭТ. "
        "Создатель бота не работает в транспортной компании, никак не связан с диспетчерами и <b>НЕ ЗНАЕТ</b>, почему задерживается ваш трамвай или троллейбус (все данные автоматически берутся с открытого сайта).\n\n"
        "🛠 Если вы нашли техническую ошибку в работе самого бота (пропали кнопки, не ищется маршрут, бот завис), пожалуйста, опишите её максимально подробно. К сообщению можно прикрепить скриншот.",
        parse_mode="HTML",
        reply_markup=kb.get_cancel_support_kb()
    )
    await state.set_state(SupportState.waiting_for_message)

@router.callback_query(F.data == "cancel_support", SupportState.waiting_for_message)
async def cancel_support_callback(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("Действие отменено.", reply_markup=None)
    await call.answer()

@router.message(Command("cancel"), SupportState.waiting_for_message)
async def cancel_support(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено.")

@router.message(SupportState.waiting_for_message)
async def on_support_message(message: Message, state: FSMContext, bot: Bot):
    # Формируем шапку с информацией о пользователе
    username = f"@{message.from_user.username}" if message.from_user.username else "Без юзернейма"
    user_info = f"Пользователь: {message.from_user.full_name}\nUsername: {username}\nID: <code>{message.from_user.id}</code>"
    
    try:
        # 1. Отправляем тебе инфу о том, кто пишет
        await bot.send_message(
            ADMIN_ID, 
            f"📩 <b>Новое обращение в поддержку!</b>\n\n{user_info}\n\n<i>💡 Чтобы ответить, сделайте Reply на это сообщение или используйте:\n<code>/reply {message.from_user.id} ваш текст</code></i>", 
            parse_mode="HTML"
        )
        
        # 2. Пересылаем само сообщение (copy_to поддерживает текст, фото, видео и т.д.)
        await message.copy_to(ADMIN_ID)
        
        # 3. Благодарим пользователя
        await message.answer("✅ Ваше сообщение успешно отправлено! Спасибо за обратную связь.")
    except Exception as e:
        print(f"Ошибка при отправке сообщения админу: {e}")
        await message.answer("🚫 Произошла ошибка при отправке сообщения. Попробуйте позже.")
        
    # Выходим из состояния ожидания
    await state.clear()


# --- ЗАГЛУШКА ДЛЯ НЕИЗВЕСТНЫХ СООБЩЕНИЙ ---

@router.message(StateFilter(default_state), F.text, ~F.text.startswith('/'))
async def on_unknown_message(message: Message):
    db.update_unknown_messages_statistics(message.from_user.id)
    await message.answer(
        "Я не понимаю текстовых сообщений 🤷\n\n"
        "Используйте команды:\n"
        "/new — найти расписание\n"
        "/favorites — мои маршруты\n"
        "/help — справка\n"
        "/donate — поддержать проект\n\n"
        "Если нашли ошибку или есть вопрос — /support"
    )