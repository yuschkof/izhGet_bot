from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery
import keyboards.keyboards as kb
from request import get_result
from aiogram import types

router = Router()
state = {}


@router.message(Command('new'))
async def process_new_command(message: types.Message):
    await message.answer("Показать рейсы в ближайшие?", reply_markup=kb.inline_kb_time)


@router.callback_query(lambda c: c.data.startswith('time'))
async def process_callback_button_time(callback_query: CallbackQuery):
    button_id = callback_query.data.split('time')[1]
    user_id = callback_query.from_user.id
    state.setdefault(user_id, {})

    if 'timeint' not in state[user_id]:
        state[user_id]['timeint'] = button_id
        await callback_query.message.edit_text(
            text='Показать остановки для маршрута:',
            reply_markup=kb.inline_kb_route
        )


@router.callback_query(lambda c: c.data.startswith('route'))
async def process_callback_button_route(callback_query: CallbackQuery):
    button_id = callback_query.data.split('route')[1]

    user_id = callback_query.from_user.id
    state.setdefault(user_id, {})
    currentKb = None
    if 'route' not in state[user_id]:
        state[user_id]['route'] = button_id
        currentKb = kb.kb_dict.get(state[user_id]['route'])
        await callback_query.message.edit_text(
            text='Пункт отправления:',
            reply_markup=currentKb
        )


@router.callback_query(lambda c: c.data)
async def process_callback_button(callback_query: CallbackQuery):
    button_id = callback_query.data
    print(button_id)
    user_id = callback_query.from_user.id
    if 'snt' not in state[user_id]:
        state[user_id]['snt'] = button_id
        currentKb = kb.kb_dict.get(state[user_id]['route'])
        await callback_query.message.edit_text(
            text='Пункт назначения:',
            reply_markup=currentKb
        )
    else:
        state[user_id]['dsnt'] = button_id
        timeint = state[user_id]['timeint']
        snt = state[user_id]['snt']
        dsnt = state[user_id]['dsnt']
        route = state[user_id]['route']
        stroke = get_result(timeint, snt, dsnt, route)
        del state[user_id]
        await callback_query.message.edit_text(
            text=stroke,
            reply_markup=None,
            parse_mode='HTML'
        )


def check_state(user_id):
    if user_id in state:
        print(state)
        del state[user_id]