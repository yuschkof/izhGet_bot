from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import db.db as db
import keyboards.keyboards as kb
from keyboards.keyboards import FavCallback
from request import get_result

router = Router()

# Состояния для переименования
class FavEdit(StatesGroup):
    waiting_for_new_name = State()

@router.message(Command("favorites"))
async def cmd_favorites(message: Message):
    user_id = message.from_user.id
    favorites = db.get_favorite_routes(user_id)
    
    if not favorites:
        await message.answer("У вас пока нет избранных маршрутов. Создайте маршрут через /new и нажмите 'Добавить в избранное'.")
        return

    markup = kb.get_favorites_list_kb(favorites)
    from aiogram.types import InputRichMessage
    await message.bot.send_rich_message(
        chat_id=message.chat.id,
        rich_message=InputRichMessage(html="<h2>⭐ Ваши избранные маршруты:</h2>"),
        reply_markup=markup
    )

@router.callback_query(FavCallback.filter(F.action == "select"))
async def on_favorite_click(call: CallbackQuery, callback_data: FavCallback):
    fav_id = int(callback_data.id)
    user_id = call.from_user.id
    
    favorites = db.get_favorite_routes(user_id)
    # Ищем маршрут (теперь кортеж из 6 элементов)
    target_fav = next((f for f in favorites if f[0] == fav_id), None)
    
    if not target_fav:
        await call.answer("Маршрут не найден", show_alert=True)
        return
    
    # Распаковываем (custom_name нам тут не нужен для запроса, но он есть в кортеже)
    _, route, snt, dsnt, timeint, _ = target_fav
    
    await call.message.edit_text("⏳ Загружаю расписание...", reply_markup=None)
    
    text_result = await get_result(
        timeint=timeint,
        snt=snt,
        dsnt=dsnt,
        route=route
    )
    
    sub = db.get_subscription(user_id, fav_id)
    markup = kb.get_delete_kb(fav_id, has_subscription=bool(sub))
    from aiogram.types import InputRichMessage
    await call.message.bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        rich_message=InputRichMessage(html=text_result),
        reply_markup=markup
    )

# === ЛОГИКА ПЕРЕИМЕНОВАНИЯ ===

# 1. Нажали кнопку "Переименовать"
@router.callback_query(FavCallback.filter(F.action == "rename_ask"))
async def on_rename_ask(call: CallbackQuery, callback_data: FavCallback, state: FSMContext):
    fav_id = callback_data.id
    # Запоминаем ID маршрута, который хотим переименовать
    await state.update_data(editing_fav_id=fav_id)
    
    from aiogram.types import InputRichMessage
    text = (
        "<h3>✍️ Переименование маршрута</h3>\n"
        "<p>Введите новое название для этого маршрута:</p>\n"
        "<blockquote><i>Например: Домой или На работу</i></blockquote>"
    )
    await call.bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        rich_message=InputRichMessage(html=text),
        reply_markup=kb.get_cancel_rename_kb()
    )
    await state.set_state(FavEdit.waiting_for_new_name)

# 2. Пользователь прислал текст с новым именем
@router.message(FavEdit.waiting_for_new_name)
async def on_new_name_input(message: Message, state: FSMContext):
    data = await state.get_data()
    fav_id = data.get('editing_fav_id')
    new_name = message.text
    
    # Ограничим длину имени, чтобы не ломать кнопки
    if len(new_name) > 30:
        await message.answer("⚠️ Название слишком длинное. Попробуйте короче (до 30 символов).")
        return

    # Сохраняем в БД
    db.rename_favorite_route(fav_id, new_name)
    
    await message.answer(f"✅ Маршрут переименован в «<b>{new_name}</b>»!", parse_mode="HTML")
    
    await cmd_favorites(message)
    await state.clear()


@router.callback_query(F.data == "cancel_rename")
async def on_rename_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.delete()
    await call.answer("Переименование отменено")


@router.callback_query(FavCallback.filter(F.action == "del"))
async def on_favorite_delete(call: CallbackQuery, callback_data: FavCallback):
    fav_id = callback_data.id
    user_id = call.from_user.id
    db.delete_favorite_route(fav_id, user_id)
    
    await call.answer("🗑 Маршрут удален", show_alert=True)
    await call.message.delete()
    

@router.callback_query(F.data == "back_to_favorites")
async def on_back_to_favorites(call: CallbackQuery):
    # Берем правильный ID пользователя, который нажал на кнопку
    user_id = call.from_user.id
    
    # Достаем его избранное из базы
    favorites = db.get_favorite_routes(user_id)
    
    if not favorites:
        await call.message.edit_text(
            text="У вас пока нет избранных маршрутов. Создайте маршрут через /new и нажмите 'Добавить в избранное'.",
            reply_markup=None
        )
        return

    # Генерируем клавиатуру и плавно меняем текст и кнопки
    markup = kb.get_favorites_list_kb(favorites)
    from aiogram.types import InputRichMessage
    await call.message.bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        rich_message=InputRichMessage(html="<h2>⭐ Ваши избранные маршруты:</h2>"),
        reply_markup=markup
    )