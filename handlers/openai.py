import os
import openai
from dotenv import load_dotenv
from aiogram import Router
from aiogram import types
from aiogram.filters import CommandObject, Command

router = Router()
load_dotenv()
admin_id = os.getenv('ADMIN_ID')
openai.api_key = os.getenv("OPENAI_API_KEY")


@router.message(Command('openai'))
async def process_new_command(message: types.Message, command: CommandObject):
    if str(message.from_user.id) == str(admin_id):
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": command.args}
            ]
        )
        await message.answer(text=str(completion.choices[0].message.content))
    else:
        await message.answer("Вы не админ, чтоб задавать такие вопросы")

