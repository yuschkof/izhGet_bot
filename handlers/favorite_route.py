import html

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InputRichMessage
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import db.db as db
import keyboards.keyboards as kb
from keyboards.keyboards import FavCallback
from request import get_result

router = Router()
# Отдельный роутер для кнопок внизу: в main.py он стоит раньше common (иначе нажатие
# съест заглушка неизвестных сообщений), а основной роутер избранного — на прежнем месте
pinned_router = Router()

# Больше кнопок внизу займут полэкрана — быстрый доступ теряет смысл
PIN_LIMIT = 4

# Состояния для переименования
class FavEdit(StatesGroup):
    waiting_for_new_name = State()


def pinned_button(message: Message):
    """Фильтр: текст совпадает с закреплённой кнопкой этого пользователя. Отдаёт ID маршрута."""
    if not message.text or not message.from_user or message.text.startswith("/"):
        return False  # команды всегда остаются командами
    for fav_id, route, custom_name in db.get_pinned_favorites(message.from_user.id):
        if kb.pinned_button_text(route, custom_name) == message.text:
            return {"pinned_fav_id": fav_id}
    return False


def _pinned_kb(user_id):
    return kb.get_pinned_kb(db.get_pinned_favorites(user_id))


def _route_kb(user_id, fav_id):
    """Кнопки под расписанием избранного маршрута."""
    return kb.get_delete_kb(fav_id, db.get_subscription(user_id, fav_id), db.is_pinned(user_id, fav_id))


async def _show_route(bot, chat_id, message_id, user_id, fav):
    """Загружает расписание и подставляет его в сообщение message_id."""
    fav_id, route, snt, dsnt, timeint, _ = fav
    text_result = await get_result(timeint=timeint, snt=snt, dsnt=dsnt, route=route)
    await bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        rich_message=InputRichMessage(html=text_result),
        reply_markup=_route_kb(user_id, fav_id)
    )


# Нажатие кнопки внизу работает из любого состояния, как команда, —
# кроме ввода нового названия, где такой текст — это и есть новое название
@pinned_router.message(F.chat.type == "private", ~StateFilter(FavEdit.waiting_for_new_name), pinned_button)
async def on_pinned_button(message: Message, state: FSMContext, pinned_fav_id: int):
    await state.clear()
    user_id = message.from_user.id
    fav = db.get_favorite(user_id, pinned_fav_id)
    if not fav:
        return
    loading = await message.answer("⏳ Загружаю расписание...")
    await _show_route(message.bot, message.chat.id, loading.message_id, user_id, fav)

@router.message(Command("favorites"))
async def cmd_favorites(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    favorites = db.get_favorite_routes(user_id)
    
    if not favorites:
        await message.answer("У вас пока нет избранных маршрутов. Создайте маршрут через /new и нажмите 'Добавить в избранное'.")
        return

    markup = kb.get_favorites_list_kb(favorites)
    await message.bot.send_rich_message(
        chat_id=message.chat.id,
        rich_message=InputRichMessage(html="<h2>⭐ Ваши избранные маршруты:</h2>"),
        reply_markup=markup
    )

@router.callback_query(FavCallback.filter(F.action == "select"))
async def on_favorite_click(call: CallbackQuery, callback_data: FavCallback):
    fav_id = int(callback_data.id)
    user_id = call.from_user.id
    
    target_fav = db.get_favorite(user_id, fav_id)

    if not target_fav:
        await call.answer("Маршрут не найден", show_alert=True)
        return
    
    await call.message.edit_text("⏳ Загружаю расписание...", reply_markup=None)
    await _show_route(call.bot, call.message.chat.id, call.message.message_id, user_id, target_fav)


# === ЗАКРЕПЛЕНИЕ ВНИЗУ ===

def _parse_fav_id(callback_data: FavCallback):
    try:
        return int(callback_data.id)
    except ValueError:
        return None


@router.callback_query(FavCallback.filter(F.action == "pin"))
async def on_pin(call: CallbackQuery, callback_data: FavCallback):
    user_id = call.from_user.id
    fav_id = _parse_fav_id(callback_data)
    fav = db.get_favorite(user_id, fav_id) if fav_id is not None else None
    if not fav:
        await call.answer("Маршрут не найден", show_alert=True)
        return

    pinned = db.get_pinned_favorites(user_id)
    name = kb.pinned_button_text(fav[1], fav[5])
    if any(p[0] == fav_id for p in pinned):
        # Повторное нажатие на старом экране: менять нечего (edit с той же разметкой упал бы)
        await call.answer("Маршрут уже закреплён внизу")
        return
    if len(pinned) >= PIN_LIMIT:
        await call.answer(f"Можно закрепить до {PIN_LIMIT} маршрутов — сначала открепи один.", show_alert=True)
        return
    if name in {kb.pinned_button_text(r, n) for _, r, n in pinned}:
        await call.answer(f"Внизу уже есть маршрут «{name}». Переименуй этот, чтобы различать кнопки.", show_alert=True)
        return

    db.set_pinned(user_id, fav_id, True)
    await call.answer()
    await call.message.edit_reply_markup(reply_markup=_route_kb(user_id, fav_id))
    # Reply-клавиатуру можно поставить только новым сообщением
    await call.message.answer(
        f"📌 «{html.escape(name)}» закреплён внизу — жми кнопку, чтобы сразу открыть расписание.",
        reply_markup=_pinned_kb(user_id)
    )


@router.callback_query(FavCallback.filter(F.action == "unpin"))
async def on_unpin(call: CallbackQuery, callback_data: FavCallback):
    user_id = call.from_user.id
    fav_id = _parse_fav_id(callback_data)
    fav = db.get_favorite(user_id, fav_id) if fav_id is not None else None
    if not fav:
        await call.answer("Маршрут не найден", show_alert=True)
        return

    if not db.set_pinned(user_id, fav_id, False):
        await call.answer("Маршрут уже откреплён")
        return
    await call.answer()
    await call.message.edit_reply_markup(reply_markup=_route_kb(user_id, fav_id))
    name = kb.pinned_button_text(fav[1], fav[5])
    await call.message.answer(f"📍 «{html.escape(name)}» откреплён.", reply_markup=_pinned_kb(user_id))

# === ЛОГИКА ПЕРЕИМЕНОВАНИЯ ===

# 1. Нажали кнопку "Переименовать"
@router.callback_query(FavCallback.filter(F.action == "rename_ask"))
async def on_rename_ask(call: CallbackQuery, callback_data: FavCallback, state: FSMContext):
    fav_id = callback_data.id
    # Запоминаем ID маршрута, который хотим переименовать
    await state.update_data(editing_fav_id=fav_id)
    
    text = (
        "<h3>✍️ Переименование маршрута</h3>\n"
        "<p>Введите новое название для этого маршрута:</p>\n"
        "<blockquote><i>Например: Домой или На работу</i></blockquote>"
    )
    await call.bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        rich_message=InputRichMessage(html=text),
        reply_markup=kb.get_cancel_rename_kb()
    )
    await state.set_state(FavEdit.waiting_for_new_name)

# 2. Пользователь прислал текст с новым именем
@router.message(FavEdit.waiting_for_new_name)
async def on_new_name_input(message: Message, state: FSMContext):
    data = await state.get_data()
    fav_id = data.get('editing_fav_id')
    new_name = (message.text or "").strip()

    if not new_name:
        await message.answer("⚠️ Пришлите название текстом.")
        return

    # Иначе кнопка внизу с таким названием выглядела бы как команда
    if new_name.startswith("/"):
        await message.answer("⚠️ Название не может начинаться с «/». Попробуйте другое.")
        return

    # Ограничим длину имени, чтобы не ломать кнопки
    if len(new_name) > 30:
        await message.answer("⚠️ Название слишком длинное. Попробуйте короче (до 30 символов).")
        return

    user_id = message.from_user.id
    # Кнопки внизу узнаются по названию, поэтому у закреплённых маршрутов оно должно быть уникальным
    pinned = db.get_pinned_favorites(user_id)
    is_pinned = any(str(p[0]) == str(fav_id) for p in pinned)
    if is_pinned and any(str(p[0]) != str(fav_id) and kb.pinned_button_text(p[1], p[2]) == new_name for p in pinned):
        await message.answer("⚠️ Внизу уже есть маршрут с таким названием. Придумайте другое.")
        return

    # Сохраняем в БД (только если маршрут принадлежит пользователю)
    if not db.rename_favorite_route(fav_id, user_id, new_name):
        await state.clear()
        await message.answer("❌ Маршрут не найден.")
        return

    await message.answer(
        f"✅ Маршрут переименован в «<b>{html.escape(new_name)}</b>»!",
        parse_mode="HTML",
        reply_markup=_pinned_kb(user_id) if is_pinned else None
    )
    
    await cmd_favorites(message, state)
    await state.clear()


@router.callback_query(F.data == "cancel_rename")
async def on_rename_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.delete()
    await call.answer("Переименование отменено")


@router.callback_query(FavCallback.filter(F.action == "del"))
async def on_favorite_delete(call: CallbackQuery, callback_data: FavCallback):
    fav_id = callback_data.id
    user_id = call.from_user.id
    was_pinned = db.is_pinned(user_id, fav_id)
    db.delete_favorite_route(fav_id, user_id)

    await call.answer("🗑 Маршрут удален", show_alert=True)
    await call.message.delete()
    if was_pinned:
        await call.message.answer("📍 Кнопка маршрута убрана снизу.", reply_markup=_pinned_kb(user_id))
    

@router.callback_query(F.data == "back_to_favorites")
async def on_back_to_favorites(call: CallbackQuery):
    # Берем правильный ID пользователя, который нажал на кнопку
    user_id = call.from_user.id
    
    # Достаем его избранное из базы
    favorites = db.get_favorite_routes(user_id)
    
    if not favorites:
        await call.message.edit_text(
            text="У вас пока нет избранных маршрутов. Создайте маршрут через /new и нажмите 'Добавить в избранное'.",
            reply_markup=None
        )
        return

    # Генерируем клавиатуру и плавно меняем текст и кнопки
    markup = kb.get_favorites_list_kb(favorites)
    await call.message.bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        rich_message=InputRichMessage(html="<h2>⭐ Ваши избранные маршруты:</h2>"),
        reply_markup=markup
    )