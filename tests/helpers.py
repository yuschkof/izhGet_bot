"""Общие помощники тестов: заглушка Telegram API и сборка апдейтов."""
import datetime
from typing import NamedTuple

from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.types import Update, Message, Chat, User, CallbackQuery


class Call(NamedTuple):
    method: str
    chat_id: int | None
    text: str | None
    markup: object


class FakeSession(BaseSession):
    """Вместо Telegram API: запоминает вызовы и возвращает правдоподобный ответ."""

    def __init__(self):
        super().__init__()
        self.calls: list[Call] = []

    async def make_request(self, bot, method, timeout=None):
        rich = getattr(method, "rich_message", None)
        self.calls.append(Call(
            type(method).__name__,
            getattr(method, "chat_id", None),
            getattr(method, "text", None) or (rich.html if rich else None),
            getattr(method, "reply_markup", None),
        ))
        returning = method.__returning__
        if returning is Message:
            return Message.model_validate({
                "message_id": 1,
                "date": datetime.datetime.now(),
                "chat": {"id": getattr(method, "chat_id", None) or 1, "type": "private"},
                "text": getattr(method, "text", None),
            })
        if hasattr(returning, "model_validate"):
            raise NotImplementedError(
                f"FakeSession: no fake response for {type(method).__name__}")
        return True

    async def close(self):
        pass

    async def stream_content(self, *args, **kwargs):
        yield b""


def make_bot() -> tuple[Bot, list[Call]]:
    session = FakeSession()
    return Bot("42:TEST", session=session), session.calls


def button_texts(markup) -> list[str]:
    return [b.text for row in markup.inline_keyboard for b in row]


def _user(user_id: int) -> User:
    return User(id=user_id, is_bot=False, first_name="T")


def callback_update(user_id: int, data: str) -> Update:
    message = Message(message_id=10, date=datetime.datetime.now(),
                      chat=Chat(id=user_id, type="private"), text="screen")
    return Update(update_id=1, callback_query=CallbackQuery(
        id="1", from_user=_user(user_id), chat_instance="c", data=data, message=message))


def text_update(user_id: int, text: str) -> Update:
    return Update(update_id=2, message=Message(
        message_id=11, date=datetime.datetime.now(), chat=Chat(id=user_id, type="private"),
        from_user=_user(user_id), text=text))
