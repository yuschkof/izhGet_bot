from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import keyboards.keyboards as kb
from keyboards.keyboards import TransportCallback, FavCallback
from request import get_result
import db.db as db

router = Router()

class RouteOrder(StatesGroup):
    waiting_for_time = State()
    waiting_for_route = State()
    waiting_for_start = State()
    waiting_for_end = State()

@router.message(Command("new"))
async def cmd_new(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Показать рейсы в ближайшие?", reply_markup=kb.get_time_keyboard())
    await state.set_state(RouteOrder.waiting_for_time)

@router.callback_query(TransportCallback.filter(F.action == "time"))
async def on_time_selected(call: CallbackQuery, callback_data: TransportCallback, state: FSMContext):
    await state.update_data(timeint=callback_data.value)
    await call.message.edit_text("Выберите маршрут:", reply_markup=kb.get_routes_keyboard())
    await state.set_state(RouteOrder.waiting_for_route)

@router.callback_query(TransportCallback.filter(F.action == "route"))
async def on_route_selected(call: CallbackQuery, callback_data: TransportCallback, state: FSMContext):
    route = callback_data.value
    await state.update_data(route=route)
    markup = kb.get_stations_keyboard(route)
    await call.message.edit_text(f"Маршрут {route}. Откуда едем?", reply_markup=markup)
    await state.set_state(RouteOrder.waiting_for_start)

@router.callback_query(RouteOrder.waiting_for_start, TransportCallback.filter(F.action == "station"))
async def on_start_station(call: CallbackQuery, callback_data: TransportCallback, state: FSMContext):
    await state.update_data(snt=callback_data.value)
    data = await state.get_data()
    markup = kb.get_stations_keyboard(data['route'])
    await call.message.edit_text("Куда едем?", reply_markup=markup)
    await state.set_state(RouteOrder.waiting_for_end)

@router.callback_query(RouteOrder.waiting_for_end, TransportCallback.filter(F.action == "station"))
async def on_end_station(call: CallbackQuery, callback_data: TransportCallback, state: FSMContext):
    dsnt = callback_data.value
    data = await state.get_data()
    
    await call.message.edit_text("⏳ Получаю расписание...", reply_markup=None)
    
    text_result = await get_result(
        timeint=data['timeint'],
        snt=data['snt'],
        dsnt=dsnt,
        route=data['route']
    )
    
    # Кнопка добавления в избранное
    markup = kb.get_after_result_kb(data['route'], data['snt'], dsnt, data['timeint'])
    
    await call.message.edit_text(text_result, parse_mode="HTML", reply_markup=markup)
    await state.clear()

# Обработчик нажатия на кнопку "Добавить в избранное"
@router.callback_query(FavCallback.filter(F.action == "add"))
async def on_add_favorite(call: CallbackQuery, callback_data: FavCallback):
    # === ИСПРАВЛЕНИЕ ЗДЕСЬ ===
    try:
        # Разбираем строку по разделителю "_" вместо ":"
        route, snt, dsnt, timeint = callback_data.id.split('_') 
        
        user_id = call.from_user.id
        
        success = db.add_favorite_route(user_id, route, snt, dsnt, timeint)
        
        if success:
            await call.answer("✅ Маршрут добавлен в избранное!", show_alert=True)
            # Убираем кнопку добавления, чтобы не жали дважды
            await call.message.edit_reply_markup(reply_markup=None)
        else:
            await call.answer("Этот маршрут уже в избранном.", show_alert=True)
            
    except Exception as e:
        await call.answer("Ошибка добавления.", show_alert=True)
        print(f"Error adding fav: {e}")