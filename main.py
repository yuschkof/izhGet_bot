import os
from keyboards import keyboards as kb
from request import get_result
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from dotenv import load_dotenv
import logging

load_dotenv()
botApi = os.getenv('BOT_TOKEN')

bot = Bot(token=botApi)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)


@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
    schema = open('static/schema.png', 'rb')
    await message.reply(
        "Привет!\nЯ бот с расписанием трамваев в г.Ижевск\nДля выбора маршрута нажми /new"
    )
    await bot.send_photo(message.from_user.id, schema)


@dp.message_handler(commands=['help'])
async def process_help_command(message: types.Message):
    msg = "Тут и так простое управление, как ты не смог(ла) разобраться?"
    await message.reply(msg)
    await message.answer_sticker(
        r'CAACAgIAAxkBAAEH3Ppj9xWKbtQ-kWtb6uKkwvE8EbGCMQAC9ScAAp-e8Enjve-XHgojSS4E'
    )


@dp.message_handler(commands=['description'])
async def process_description_command(message: types.Message):
    msg = '''Уважаемые пассажиры, данная информационная система позволяет Вам рассчитать время отправления и прибытия на указанных остановочных пунктах трамваев. Напоминаем, что согласно правил технической эксплуатации трамвая существует допуск на отклонение от расписания +2 мин. (опоздание), -1 мин. (нагон).
Обращаем ваше внимание на то, что расписания для будних дней, субботы и воскресенья могут отличаться.
Данная информация основана на расписании движения трамваев, при условии отсутствия задержек в линии.'''
    schema = open('static/schema.png', 'rb')
    await message.reply(msg)
    await bot.send_photo(message.from_user.id, schema)


@dp.message_handler(commands=['new'])
async def process_new_command(message: types.Message):
    await message.answer("Показать рейсы в ближайшие?",
                         reply_markup=kb.inline_kb_time)


@dp.callback_query_handler(lambda c: c.data.startswith('time'))
async def process_callback_button_time(callback_query: types.CallbackQuery):
    button_id = callback_query.data.split('time')[1]
    user_id = callback_query.from_user.id
    state.setdefault(user_id, {})

    if 'timeint' not in state.get(user_id, {}):
        state[user_id]['timeint'] = button_id
        await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                    message_id=callback_query.message.message_id,
                                    text='Показать остановки для маршрута:',
                                    reply_markup=kb.inline_kb_route)


@dp.callback_query_handler(lambda c: c.data.startswith('route'))
async def process_callback_button_route(callback_query: types.CallbackQuery):
    button_id = callback_query.data.split('route')[1]
    user_id = callback_query.from_user.id
    state.setdefault(user_id, {})
    currentKb = None
    if 'route' not in state[user_id]:
        state[user_id]['route'] = button_id
        if button_id == '0': currentKb = kb.inline_kb0
        if button_id == '1': currentKb = kb.inline_kb1
        if button_id == '10': currentKb = kb.inline_kb10
        if button_id == '11': currentKb = kb.inline_kb11
        if button_id == '12': currentKb = kb.inline_kb12
        if button_id == '2': currentKb = kb.inline_kb2
        if button_id == '3': currentKb = kb.inline_kb3
        if button_id == '4': currentKb = kb.inline_kb4
        if button_id == '5': currentKb = kb.inline_kb5
        if button_id == '7': currentKb = kb.inline_kb7
        if button_id == '8': currentKb = kb.inline_kb8
        if button_id == '9': currentKb = kb.inline_kb9
        await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                    message_id=callback_query.message.message_id,
                                    text='Пункт отправления:',
                                    reply_markup=currentKb)


@dp.callback_query_handler(lambda c: c.data)
async def process_callback_button(callback_query: types.CallbackQuery):
    button_id = callback_query.data
    user_id = callback_query.from_user.id
    currentKb = None
    if 'snt' not in state[user_id]:
        state[user_id]['snt'] = button_id
        if state[user_id]['route'] == '0': currentKb = kb.inline_kb0
        if state[user_id]['route'] == '1': currentKb = kb.inline_kb1
        if state[user_id]['route'] == '10': currentKb = kb.inline_kb10
        if state[user_id]['route'] == '11': currentKb = kb.inline_kb11
        if state[user_id]['route'] == '12': currentKb = kb.inline_kb12
        if state[user_id]['route'] == '2': currentKb = kb.inline_kb2
        if state[user_id]['route'] == '3': currentKb = kb.inline_kb3
        if state[user_id]['route'] == '4': currentKb = kb.inline_kb4
        if state[user_id]['route'] == '5': currentKb = kb.inline_kb5
        if state[user_id]['route'] == '7': currentKb = kb.inline_kb7
        if state[user_id]['route'] == '8': currentKb = kb.inline_kb8
        if state[user_id]['route'] == '9': currentKb = kb.inline_kb9
        await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                    message_id=callback_query.message.message_id,
                                    text='Пункт назначения:',
                                    reply_markup=currentKb)
    else:
        state[user_id]['dsnt'] = button_id
        timeint = state[user_id]['timeint']
        snt = state[user_id]['snt']
        dsnt = state[user_id]['dsnt']
        route = state[user_id]['route']
        print(state)
        stroke = get_result(timeint, snt, dsnt, route)
        del state[user_id]
        await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                    message_id=callback_query.message.message_id,
                                    text=stroke,
                                    reply_markup=None,
                                    parse_mode='HTML')


@dp.message_handler(commands="dice")
async def cmd_dice(message: types.Message):
    await message.bot.send_dice(message.from_user.id, emoji="🎲")


if __name__ == '__main__':
    state = {}
    executor.start_polling(dp, skip_updates=True)
