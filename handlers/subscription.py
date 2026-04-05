import re
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import db.db as db
import keyboards.keyboards as kb
from keyboards.keyboards import SubCallback
from request import get_result

router = Router()


class SubEdit(StatesGroup):
    waiting_for_time = State()


async def _show_favorite(call: CallbackQuery, user_id: int, fav_id: int):
    """Загружает и показывает расписание избранного маршрута."""
    favorites = db.get_favorite_routes(user_id)
    target = next((f for f in favorites if f[0] == fav_id), None)
    if not target:
        await call.message.edit_text("❌ Маршрут не найден.", reply_markup=None)
        return
    _, route, snt, dsnt, timeint, _ = target
    await call.message.edit_text("⏳ Загружаю расписание...", reply_markup=None)
    text_result = await get_result(timeint=timeint, snt=snt, dsnt=dsnt, route=route)
    sub = db.get_subscription(user_id, fav_id)
    markup = kb.get_delete_kb(fav_id, has_subscription=bool(sub))
    await call.message.edit_text(text_result, parse_mode="HTML", reply_markup=markup)


def _parse_time(text: str):
    """Парсит строку ЧЧ:ММ. Возвращает 'HH:MM' или None при ошибке."""
    match = re.match(r'^(\d{1,2}):(\d{2})$', text.strip())
    if not match:
        return None
    h, m = int(match.group(1)), int(match.group(2))
    if not (0 <= h <= 23 and 0 <= m <= 59):
        return None
    return f"{h:02d}:{m:02d}"


@router.callback_query(SubCallback.filter(F.action == "ask"))
async def on_sub_ask(call: CallbackQuery, callback_data: SubCallback, state: FSMContext):
    fav_id = int(callback_data.id)
    user_id = call.from_user.id

    favorites = db.get_favorite_routes(user_id)
    fav = next((f for f in favorites if f[0] == fav_id), None)
    timeint = fav[4] if fav else "?"

    existing = db.get_subscription(user_id, fav_id)
    if existing:
        sub_id, _, _, notify_time, _ = existing
        await call.message.edit_text(
            f"🔔 <b>Подписка активна</b>\n\n"
            f"Каждый день в <b>{notify_time}</b> бот пришлёт расписание на ближайшие <b>{timeint} мин.</b>",
            parse_mode="HTML",
            reply_markup=kb.get_sub_manage_kb(sub_id, fav_id)
        )
        return

    await state.update_data(sub_fav_id=fav_id)
    await call.message.edit_text(
        f"🔔 <b>Подписка на расписание</b>\n\n"
        f"Каждый день в указанное время бот пришлёт расписание на ближайшие <b>{timeint} мин.</b>\n\n"
        "Введите время в формате <b>ЧЧ:ММ</b>\n"
        "Например: <code>07:30</code> или <code>8:00</code>",
        parse_mode="HTML",
        reply_markup=kb.get_cancel_sub_kb(fav_id)
    )
    await state.set_state(SubEdit.waiting_for_time)


@router.callback_query(SubCallback.filter(F.action == "edit"))
async def on_sub_edit(call: CallbackQuery, callback_data: SubCallback, state: FSMContext):
    fav_id = int(callback_data.id)
    await state.update_data(sub_fav_id=fav_id)
    await call.message.edit_text(
        "✏️ Введите новое время в формате <b>ЧЧ:ММ</b>\n"
        "Например: <code>08:00</code>",
        parse_mode="HTML",
        reply_markup=kb.get_cancel_sub_kb(fav_id)
    )
    await state.set_state(SubEdit.waiting_for_time)


@router.message(SubEdit.waiting_for_time)
async def on_sub_time_input(message: Message, state: FSMContext):
    notify_time = _parse_time(message.text or "")
    if not notify_time:
        await message.answer(
            "⚠️ Неверный формат. Введите время как <b>ЧЧ:ММ</b>, например: <code>07:30</code>",
            parse_mode="HTML"
        )
        return

    data = await state.get_data()
    fav_id = data['sub_fav_id']
    user_id = message.from_user.id

    favorites = db.get_favorite_routes(user_id)
    fav = next((f for f in favorites if f[0] == fav_id), None)
    timeint = fav[4] if fav else "?"

    db.add_subscription(user_id, fav_id, notify_time)
    await state.clear()
    await message.answer(
        f"✅ Подписка оформлена! Каждый день в <b>{notify_time}</b> буду присылать расписание на ближайшие <b>{timeint} мин.</b>",
        parse_mode="HTML"
    )


@router.callback_query(SubCallback.filter(F.action == "del"))
async def on_sub_delete(call: CallbackQuery, callback_data: SubCallback):
    sub_id, fav_id = map(int, callback_data.id.split("_"))
    user_id = call.from_user.id
    db.delete_subscription(sub_id, user_id)
    await call.answer("🔕 Подписка отменена")
    await _show_favorite(call, user_id, fav_id)


@router.callback_query(F.data.startswith("sub_back_"))
async def on_sub_back(call: CallbackQuery, state: FSMContext):
    await state.clear()
    fav_id = int(call.data.split("_")[-1])
    user_id = call.from_user.id
    await _show_favorite(call, user_id, fav_id)
