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
    await message.answer("⭐ Ваши избранные маршруты:", reply_markup=markup)

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
    
    # Показываем кнопки "Переименовать" и "Удалить"
    markup = kb.get_delete_kb(fav_id)
    await call.message.edit_text(text_result, parse_mode="HTML", reply_markup=markup)

# === ЛОГИКА ПЕРЕИМЕНОВАНИЯ ===

# 1. Нажали кнопку "Переименовать"
@router.callback_query(FavCallback.filter(F.action == "rename_ask"))
async def on_rename_ask(call: CallbackQuery, callback_data: FavCallback, state: FSMContext):
    fav_id = callback_data.id
    # Запоминаем ID маршрута, который хотим переименовать
    await state.update_data(editing_fav_id=fav_id)
    
    await call.message.edit_text(
        "✍️ Введите новое название для этого маршрута:\n"
        "(например: <i>Домой</i> или <i>На работу</i>)",
        parse_mode="HTML",
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
    
    # Возвращаем список избранного
    await cmd_favorites(message)
    await state.clear()

# 3. Отмена переименования
@router.callback_query(F.data == "cancel_rename")
async def on_rename_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.delete()
    await call.answer("Переименование отменено")

# === ЛОГИКА УДАЛЕНИЯ ===
@router.callback_query(FavCallback.filter(F.action == "del"))
async def on_favorite_delete(call: CallbackQuery, callback_data: FavCallback):
    fav_id = callback_data.id
    db.delete_favorite_route(fav_id)
    await call.answer("Маршрут удален", show_alert=True)
    # Возвращаем обновленный список
    # await cmd_favorites(call.message) # Можно так, или просто удалить сообщение:
    await call.message.delete()
    await call.message.answer("🗑 Маршрут удален.")