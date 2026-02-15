from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
import db.db as db

class UserRegisterMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler,
        event: TelegramObject,
        data: dict
    ):
        user = data.get("event_from_user")
        if user:
            # Пытаемся добавить пользователя. Функция в БД оптимизирована
            # и не упадет, если юзер уже есть.
            db.add_user({
                'user_id': user.id,
                'user_name': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_premium': user.is_premium
            })
        return await handler(event, data)