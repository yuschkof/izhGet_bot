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
            from datetime import datetime
            import pytz
            date_str = datetime.now(pytz.timezone('Europe/Samara')).strftime("%d.%m.%Y")

            is_new = db.add_user({
                'user_id': user.id,
                'user_name': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_premium': user.is_premium
            })
            if is_new:
                db.update_new_user_statistics(date_str)

            db.track_daily_active(user.id, date_str)
        return await handler(event, data)