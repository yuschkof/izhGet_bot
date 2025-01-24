import logging
from typing import Dict, Any

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import keyboards.keyboards as kb
from request import get_result
import db.db as db

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Определение состояний для машины состояний
class RouteSelection(StatesGroup):
    selecting_time = State()
    selecting_route = State()
    selecting_start_point = State()
    selecting_destination = State()

router = Router()

@router.message(Command('new'))
async def process_new_command(message: Message, state: FSMContext):
    """Обработка команды /new, добавление пользователя и начало выбора маршрута"""
    try:
        # Сохранение информации о пользователе
        user_info = {
            'user_id': message.from_user.id,
            'user_name': message.from_user.username,
            'first_name': message.from_user.first_name,
            'last_name': message.from_user.last_name,
            'is_premium': message.from_user.is_premium
        }
        db.add_user(user_info)

        # Установка состояния и отправка клавиатуры времени
        await state.set_state(RouteSelection.selecting_time)
        await message.answer(
            "Показать рейсы в ближайшие?", 
            reply_markup=kb.inline_kb_time
        )
    except Exception as e:
        logger.error(f"Ошибка в process_new_command: {e}")
        await message.answer("Произошла ошибка. Попробуйте снова.")

@router.callback_query(RouteSelection.selecting_time, F.data.startswith('time'))
async def process_time_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора времени"""
    try:
        time_interval = callback.data.split('time')[1]
        
        # Сохранение выбранного времени в состоянии
        await state.update_data(timeint=time_interval)
        await state.set_state(RouteSelection.selecting_route)

        await callback.message.edit_text(
            text='Показать остановки для маршрута:',
            reply_markup=kb.inline_kb_route
        )
    except Exception as e:
        logger.error(f"Ошибка в process_time_selection: {e}")
        await callback.answer("Произошла ошибка. Попробуйте снова.")

@router.callback_query(RouteSelection.selecting_route, F.data.startswith('route'))
async def process_route_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора маршрута"""
    try:
        route = callback.data.split('route')[1]
        
        # Сохранение выбранного маршрута в состоянии
        await state.update_data(route=route)
        await state.set_state(RouteSelection.selecting_start_point)

        current_keyboard = kb.kb_dict.get(route)
        await callback.message.edit_text(
            text='Пункт отправления:',
            reply_markup=current_keyboard
        )
    except Exception as e:
        logger.error(f"Ошибка в process_route_selection: {e}")
        await callback.answer("Произошла ошибка. Попробуйте снова.")

@router.callback_query(RouteSelection.selecting_start_point, F.data.startswith('new'))
async def process_start_point_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора пункта отправления"""
    try:
        start_point = callback.data.split('new')[1]
        
        # Сохранение пункта отправления в состоянии
        await state.update_data(snt=start_point)
        await state.set_state(RouteSelection.selecting_destination)

        current_keyboard = kb.kb_dict.get(
            (await state.get_data())['route']
        )
        await callback.message.edit_text(
            text='Пункт назначения:',
            reply_markup=current_keyboard
        )
    except Exception as e:
        logger.error(f"Ошибка в process_start_point_selection: {e}")
        await callback.answer("Произошла ошибка. Попробуйте снова.")

@router.callback_query(RouteSelection.selecting_destination, F.data.startswith('new'))
async def process_destination_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора пункта назначения и получение результата"""
    try:
        destination = callback.data.split('new')[1]
        
        # Получение всех данных из состояния
        data = await state.get_data()
        data['dsnt'] = destination

        # Получение результата
        result = get_result(
            data['timeint'], 
            data['snt'], 
            data['dsnt'], 
            data['route']
        )

        # Очистка состояния
        await state.clear()

        await callback.message.edit_text(
            text=result,
            reply_markup=None,
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Ошибка в process_destination_selection: {e}")
        await callback.answer("Произошла ошибка. Попробуйте снова.")

@router.message(Command('cancel'))
async def cancel_handler(message: Message, state: FSMContext):
    """Обработчик отмены текущего состояния"""
    await state.clear()
    await message.answer("Выбор маршрута отменен.")