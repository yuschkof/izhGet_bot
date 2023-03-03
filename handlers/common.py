from aiogram import Router
from aiogram import types
from aiogram.types import URLInputFile
from .new_route import check_state
import random
router = Router()

schema = 'https://psv4.userapi.com/c237231/u142865105/docs/d20/137d946e0c5c/schema.png?extra=A1DE1OSRep6DKMCgvtCq5-G' \
         '-mhIC7F_C7egRC8l4D_vZKpyzIRgTIi5FbPD_6UGgbPV4vqBFMkoflAQOJuSo4ZnDiDWdiSYjDRhCmqUvT04ttf7VT24_IeZ9f4cFN9' \
         '-apuB3W7o45xnHfhR5KatLIA '
sticker = r'CAACAgIAAxkBAAEH3Ppj9xWKbtQ-kWtb6uKkwvE8EbGCMQAC9ScAAp-e8Enjve-XHgojSS4E'


@router.message(commands=['start'])
async def process_start_command(message: types.Message):
    check_state(message.from_user.id)
    await message.reply(
        "Привет!\nЯ бот с расписанием трамваев в г.Ижевск\nДля выбора маршрута нажми /new"
    )
    await message.reply("Теперь я в Германии")


@router.message(commands=['help'])
async def process_help_command(message: types.Message):
    check_state(message.from_user.id)
    msg = "Тут и так простое управление, как ты не смог(ла) разобраться?"
    await message.reply(msg)
    await message.answer_sticker(sticker)


@router.message(commands=['description'])
async def process_description_command(message: types.Message):
    check_state(message.from_user.id)
    msg = '''Уважаемые пассажиры, данная информационная система позволяет Вам рассчитать время отправления и прибытия на указанных остановочных пунктах трамваев. Напоминаем, что согласно правил технической эксплуатации трамвая существует допуск на отклонение от расписания +2 мин. (опоздание), -1 мин. (нагон).
Обращаем ваше внимание на то, что расписания для будних дней, субботы и воскресенья могут отличаться.
Данная информация основана на расписании движения трамваев, при условии отсутствия задержек в линии.'''
    await message.reply(msg)
    await message.answer_photo(photo=URLInputFile(schema))


@router.message(commands="dice")
async def cmd_dice(message: types.Message):
    check_state(message.from_user.id)
    dice = ['🎲', '🎯', '🏀', '⚽', '🎰', '🎳']
    await message.answer_dice(emoji=random.choice(dice))
