import logging
from typing import List, Dict, Any

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import keyboards.keyboards_favorite as kb
from request import get_result
import db.db as db

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# State machine for favorite route selection
class FavoriteRouteSelection(StatesGroup):
    selecting_time = State()
    selecting_route = State()
    selecting_start_point = State()
    selecting_destination = State()

router = Router()

@router.message(Command('favorites'))
async def process_favorites_command(message: Message):
    try:
        favorites_route = db.get_favorite_routes(message.from_user.id)
        if not favorites_route:
            await message.answer("Избранные маршруты отсутствуют")
            return
        await message.answer(
            "Избранные маршруты", 
            reply_markup=get_keyboard(favorites_route, "check")
        )
    except Exception as e:
        logger.error(f"Error in favorites command: {e}")
        await message.answer("Произошла ошибка при получении избранных маршрутов")

@router.message(Command('add_favorite'))
async def process_add_favorite_command(message: Message, state: FSMContext):
    try:
        user_info = {
            'user_id': message.from_user.id,
            'user_name': message.from_user.username,
            'first_name': message.from_user.first_name,
            'last_name': message.from_user.last_name,
            'is_premium': message.from_user.is_premium
        }
        db.add_user(user_info)
        
        await state.set_state(FavoriteRouteSelection.selecting_time)
        await message.answer(
            "Добавить в избранное. Показать рейсы в ближайшие?", 
            reply_markup=kb.inline_kb_time
        )
    except Exception as e:
        logger.error(f"Error in add_favorite command: {e}")
        await message.answer("Произошла ошибка при добавлении маршрута")

@router.callback_query(FavoriteRouteSelection.selecting_time, F.data.startswith('favorite_time'))
async def favorite_time_selection(callback: CallbackQuery, state: FSMContext):
    try:
        time_interval = callback.data.split('favorite_time')[1]
        await state.update_data(timeint=time_interval)
        await state.set_state(FavoriteRouteSelection.selecting_route)
        
        await callback.message.edit_text(
            text='Показать остановки для маршрута:',
            reply_markup=kb.inline_kb_route
        )
    except Exception as e:
        logger.error(f"Error in time selection: {e}")
        await callback.answer("Произошла ошибка при выборе времени")

@router.callback_query(FavoriteRouteSelection.selecting_route, F.data.startswith('favorite_route'))
async def favorite_route_selection(callback: CallbackQuery, state: FSMContext):
    try:
        route = callback.data.split('route')[1]
        await state.update_data(route=route)
        await state.set_state(FavoriteRouteSelection.selecting_start_point)
        
        current_keyboard = kb.kb_dict.get(route)
        await callback.message.edit_text(
            text='Пункт отправления:',
            reply_markup=current_keyboard
        )
    except Exception as e:
        logger.error(f"Error in route selection: {e}")
        await callback.answer("Произошла ошибка при выборе маршрута")

@router.callback_query(FavoriteRouteSelection.selecting_start_point, F.data.startswith('favorite'))
async def favorite_start_point_selection(callback: CallbackQuery, state: FSMContext):
    try:
        start_point = callback.data.split('favorite')[1]
        await state.update_data(snt=start_point)
        await state.set_state(FavoriteRouteSelection.selecting_destination)
        
        current_keyboard = kb.kb_dict.get((await state.get_data())['route'])
        await callback.message.edit_text(
            text='Пункт назначения:',
            reply_markup=current_keyboard
        )
    except Exception as e:
        logger.error(f"Error in start point selection: {e}")
        await callback.answer("Произошла ошибка при выборе пункта отправления")

@router.callback_query(FavoriteRouteSelection.selecting_destination, F.data.startswith('favorite'))
async def favorite_destination_selection(callback: CallbackQuery, state: FSMContext):
    try:
        destination = callback.data.split('favorite')[1]
        data = await state.get_data()
        data['dsnt'] = destination
        
        route_info = {
            'user_id': callback.from_user.id,
            'route': data['route'],
            'snt': data['snt'],
            'dsnt': data['dsnt'],
            'timeint': data['timeint']
        }
        
        await state.clear()
        
        if not db.add_favorite_route(route_info):
            await callback.message.edit_text(
                text="Такой маршрут уже добавлен",
                reply_markup=None,
                parse_mode='HTML'
            )
            return
        
        await callback.message.edit_text(
            text="Маршрут добавлен в избранное.\nДля просмотра используйте /favorites",
            reply_markup=None,
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error in destination selection: {e}")
        await callback.answer("Произошла ошибка при добавлении маршрута")

@router.callback_query(F.data.startswith('check_favorite'))
async def favorite_show_route(callback: CallbackQuery):
    try:
        data_string = callback.data.split('check_favorite_')[1]
        route, snt, dsnt, timeint = map(int, data_string.split('_'))
        result = get_result(timeint, snt, dsnt, route)
        
        await callback.message.edit_text(
            text=result,
            reply_markup=None,
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error in showing favorite route: {e}")
        await callback.answer("Произошла ошибка при отображении маршрута")

@router.message(Command('delete_favorite'))
async def process_delete_favorite_command(message: Message):
    try:
        favorites_route = db.get_favorite_routes(message.from_user.id)
        if not favorites_route:
            await message.answer("Избранные маршруты отсутствуют")
            return
        await message.answer(
            "Выберете маршрут для удаления", 
            reply_markup=get_keyboard(favorites_route, "delete")
        )
    except Exception as e:
        logger.error(f"Error in delete_favorite command: {e}")
        await message.answer("Произошла ошибка при получении избранных маршрутов")

@router.callback_query(F.data.startswith('delete_favorite'))
async def favorite_delete_route(callback: CallbackQuery):
    try:
        data_string = callback.data.split('delete_favorite_')[1]
        route, snt, dsnt, timeint = map(int, data_string.split('_'))
        route_info = {
            'user_id': callback.from_user.id,
            'route': route,
            'snt': snt,
            'dsnt': dsnt,
            'timeint': timeint
        }

        if not db.delete_favorite_route(route_info):
            await callback.message.edit_text(
                text="Не удалось удалить избранный маршрут",
                reply_markup=None,
                parse_mode='HTML'
            )
            return
        
        await callback.message.edit_text(
            text="Избранный маршрут удален.\nДля просмотра используйте /favorites",
            reply_markup=None,
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error in deleting favorite route: {e}")
        await callback.answer("Произошла ошибка при удалении маршрута")

def create_button(data: List[Any], callback_name: str) -> InlineKeyboardButton:
    start_name = db.get_route_name(data[2])
    dest_name = db.get_route_name(data[3])
    time_interval = data[4]
    text = f"№{data[1]}: {start_name} → {dest_name} ({time_interval})"
    callback_data = f"{callback_name}_favorite_{data[1]}_{data[2]}_{data[3]}_{data[4]}"
    return InlineKeyboardButton(text=text, callback_data=callback_data)

def get_keyboard(favorite_routes: List[List[Any]], callback_name: str) -> InlineKeyboardMarkup:
    buttons = [[create_button(item, callback_name)] for item in favorite_routes]
    return InlineKeyboardMarkup(inline_keyboard=buttons)