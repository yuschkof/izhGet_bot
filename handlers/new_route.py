from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import keyboards.keyboards as kb
from keyboards.keyboards import TransportCallback, FavCallback
from request import get_result, parser
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
    await call.message.edit_text("⏳ Загружаю список остановок...", reply_markup=None)
    current_dt = parser._get_current_datetime()['date']
    stations = await parser.get_stations(route=route, dt=current_dt)
    if not stations:
        await call.message.edit_text("🚫 Не удалось загрузить остановки. Попробуйте позже.")
        await state.clear()
        return
    markup = kb.get_dynamic_stations_kb(stations, action='station')
    await call.message.edit_text("Выберите начальную остановку:", reply_markup=markup)
    await state.set_state(RouteOrder.waiting_for_start)


@router.callback_query(TransportCallback.filter(F.action == "station"))
async def on_start_selected(call: CallbackQuery, callback_data: TransportCallback, state: FSMContext):
    snt = callback_data.value
    await state.update_data(snt=snt)
    data = await state.get_data()
	
    await call.message.edit_text("⏳ Загружаю конечные остановки...", reply_markup=None)
    current_dt = parser._get_current_datetime()['date']
    destinations = await parser.get_destinations(route=data['route'], dt=current_dt, stn=snt)
    if not destinations:
        await call.message.edit_text("🚫 Не удалось загрузить конечные остановки. Попробуйте позже.")
        await state.clear()
        return
    markup = kb.get_dynamic_stations_kb(destinations, action='dest_station')
    await call.message.edit_text("Выберите конечную остановку:", reply_markup=markup)
    await state.set_state(RouteOrder.waiting_for_end)

	
@router.callback_query(TransportCallback.filter(F.action == "dest_station"))
async def on_end_selected(call: CallbackQuery, callback_data: TransportCallback, state: FSMContext):
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

@router.callback_query(FavCallback.filter(F.action == "refresh"))
async def on_refresh_schedule(call: CallbackQuery, callback_data: FavCallback):
    try:
        route, snt, dsnt, timeint = callback_data.id.split('_')
    except ValueError:
        await call.answer("Ошибка данных", show_alert=True)
        return

    await call.answer("Обновляю...")
    text_result = await get_result(timeint=timeint, snt=snt, dsnt=dsnt, route=route)
    markup = kb.get_after_result_kb(route, snt, dsnt, timeint)
    await call.message.edit_text(text_result, parse_mode="HTML", reply_markup=markup)


@router.callback_query(FavCallback.filter(F.action == "add"))
async def on_add_favorite(call: CallbackQuery, callback_data: FavCallback):
    try:
        await call.answer("Сохраняю маршрут...", show_alert=False)
        route, snt, dsnt, timeint = callback_data.id.split('_') 
        user_id = call.from_user.id
        current_dt = parser._get_current_datetime()['date']
        
        # Получаем названия с сайта
        stations = await parser.get_stations(route=route, dt=current_dt)
        destinations = await parser.get_destinations(route=route, dt=current_dt, stn=snt)
        
        snt_name = stations.get(snt, "Неизвестная остановка")
        dsnt_name = destinations.get(dsnt, "Неизвестная остановка")
        
        # === ФОРМИРУЕМ НАЗВАНИЕ КНОПКИ ===
        default_name = f"🚌 {route}: {snt_name} ➝ {dsnt_name}"
        
        # Функция теперь возвращает ID записи или None
        fav_id = db.add_favorite_route(user_id, route, snt, dsnt, timeint, custom_name=default_name)
        
        if fav_id is not None:
            # Получаем клавиатуру управления по ID
            markup = kb.get_delete_kb(fav_id)
            
            # Меняем только кнопки! Текст расписания не трогаем.
            await call.message.edit_reply_markup(reply_markup=markup)
            
            # Всплывающее уведомление об успехе
            await call.answer("✅ Маршрут сохранен!", show_alert=False)
        else:
            await call.answer("❌ Этот маршрут уже есть в избранном.", show_alert=True)
            
    except Exception as e:
        print(f"Ошибка добавления: {e}")
        await call.answer("🚫 Ошибка обработки данных", show_alert=True)