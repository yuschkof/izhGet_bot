import re
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InputRichMessage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import db.db as db
import keyboards.keyboards as kb
import reminders
from keyboards.keyboards import SubCallback
from request import get_result, parser

router = Router()

MODE_TEXT = (
    "<b>🔔 Как присылать?</b>\n\n"
    "<b>📋 Расписание в заданное время</b> — каждый день в выбранное время бот пришлёт расписание "
    "этого маршрута. Удобно, если хочешь сам посмотреть ближайшие рейсы.\n\n"
    "<b>🚶 Напомнить, когда выходить</b> — укажи, к какому времени ты готов выйти и сколько идти "
    "до остановки. Бот сам найдёт первый рейс после этого времени и напишет ровно тогда, когда пора "
    "выходить, плюс подскажет следующий рейс на случай, если не успеешь."
)
DAYS_TEXT = "📅 В какие дни присылать?"
LEAD_TEXT = "⏱ За сколько минут предупредить? (сколько тебе идти до остановки)"
TIME_TEXT = {
    reminders.MODE_SCHEDULE: "🕗 Во сколько присылать расписание?",
    reminders.MODE_REMIND: "🕗 Во сколько ты готов выйти? Я найду первый рейс не раньше этого времени.",
}
TIME_HINT = "\n\nВведите время в формате <b>ЧЧ:ММ</b>, например: <code>07:30</code> или <code>8:00</code>"
STALE_TEXT = "⌛ Настройка устарела (бот перезапускался). Начни заново: /favorites"


class SubEdit(StatesGroup):
    waiting_for_time = State()


async def _show_favorite(call: CallbackQuery, user_id: int, fav_id: int):
    """Загружает и показывает расписание избранного маршрута."""
    target = db.get_favorite(user_id, fav_id)
    if not target:
        await call.message.edit_text("❌ Маршрут не найден.", reply_markup=None)
        return
    _, route, snt, dsnt, timeint, _ = target
    await call.message.edit_text("⏳ Загружаю расписание...", reply_markup=None)
    text_result = await get_result(timeint=timeint, snt=snt, dsnt=dsnt, route=route)
    markup = kb.get_delete_kb(fav_id, db.get_subscription(user_id, fav_id))
    # Расписание содержит <table> — его понимает только rich_message
    await call.bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        rich_message=InputRichMessage(html=text_result),
        reply_markup=markup
    )


def _parse_time(text: str):
    """Парсит строку ЧЧ:ММ. Возвращает 'HH:MM' или None при ошибке."""
    match = re.match(r'^(\d{1,2}):(\d{2})$', text.strip())
    if not match:
        return None
    h, m = int(match.group(1)), int(match.group(2))
    if not (0 <= h <= 23 and 0 <= m <= 59):
        return None
    return f"{h:02d}:{m:02d}"


async def _get_setup(call: CallbackQuery, state: FSMContext, *keys):
    """Данные настройки подписки. FSM живёт в памяти и теряется при перезапуске бота —
    тогда кнопки старого сообщения сообщают об этом, а не падают с KeyError."""
    data = await state.get_data()
    if all(data.get(k) for k in keys):
        return data
    await state.clear()
    await call.answer()
    await call.message.edit_text(STALE_TEXT, reply_markup=None)
    return None


async def _start_setup(call: CallbackQuery, state: FSMContext, fav_id: int):
    await state.clear()
    await state.update_data(sub_fav_id=fav_id)
    await call.message.edit_text(MODE_TEXT, parse_mode="HTML", reply_markup=kb.get_sub_mode_kb(fav_id))


async def _ask_time(call: CallbackQuery, state: FSMContext, mode: str, fav_id: int):
    await call.message.edit_text(TIME_TEXT[mode] + TIME_HINT, parse_mode="HTML",
                                 reply_markup=kb.get_cancel_sub_kb(fav_id))
    await state.set_state(SubEdit.waiting_for_time)


@router.callback_query(SubCallback.filter(F.action == "ask"))
async def on_sub_ask(call: CallbackQuery, callback_data: SubCallback, state: FSMContext):
    fav_id = int(callback_data.id)
    user_id = call.from_user.id

    fav = db.get_favorite(user_id, fav_id)
    if not fav:
        await call.answer("Маршрут не найден", show_alert=True)
        return

    existing = db.get_subscription(user_id, fav_id)
    if existing:
        sub_id, _, _, notify_time, _, mode, days, lead_min = existing
        await call.message.edit_text(
            f"🔔 <b>Подписка активна</b>\n\n{reminders.summary_text(mode, days, notify_time, lead_min, fav[4])}",
            parse_mode="HTML",
            reply_markup=kb.get_sub_manage_kb(sub_id, fav_id)
        )
        await call.answer()
        return

    await _start_setup(call, state, fav_id)
    await call.answer()


@router.callback_query(SubCallback.filter(F.action == "edit"))
async def on_sub_edit(call: CallbackQuery, callback_data: SubCallback, state: FSMContext):
    await _start_setup(call, state, int(callback_data.id))
    await call.answer()


@router.callback_query(SubCallback.filter(F.action == "mode"))
async def on_sub_mode(call: CallbackQuery, callback_data: SubCallback, state: FSMContext):
    if callback_data.id not in (reminders.MODE_SCHEDULE, reminders.MODE_REMIND):
        await call.answer()
        return
    data = await _get_setup(call, state, 'sub_fav_id')
    if data is None:
        return
    await state.update_data(sub_mode=callback_data.id)
    await call.message.edit_text(DAYS_TEXT, reply_markup=kb.get_sub_days_kb(data['sub_fav_id']))
    await call.answer()


@router.callback_query(SubCallback.filter(F.action == "days"))
async def on_sub_days(call: CallbackQuery, callback_data: SubCallback, state: FSMContext):
    if callback_data.id not in reminders.DAYS_LABELS:
        await call.answer()
        return
    data = await _get_setup(call, state, 'sub_fav_id', 'sub_mode')
    if data is None:
        return
    await state.update_data(sub_days=callback_data.id)
    if data['sub_mode'] == reminders.MODE_REMIND:
        await call.message.edit_text(LEAD_TEXT, reply_markup=kb.get_sub_lead_kb(data['sub_fav_id']))
    else:
        await _ask_time(call, state, data['sub_mode'], data['sub_fav_id'])
    await call.answer()


@router.callback_query(SubCallback.filter(F.action == "lead"))
async def on_sub_lead(call: CallbackQuery, callback_data: SubCallback, state: FSMContext):
    if callback_data.id not in {str(m) for m in reminders.LEAD_CHOICES}:
        await call.answer()
        return
    data = await _get_setup(call, state, 'sub_fav_id', 'sub_mode', 'sub_days')
    if data is None:
        return
    await state.update_data(sub_lead=int(callback_data.id))
    await _ask_time(call, state, data['sub_mode'], data['sub_fav_id'])
    await call.answer()


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
    await state.clear()
    fav_id, mode, days = data.get('sub_fav_id'), data.get('sub_mode'), data.get('sub_days')
    lead_min = data.get('sub_lead') if mode == reminders.MODE_REMIND else None
    if not (fav_id and mode and days) or (mode == reminders.MODE_REMIND and not lead_min):
        await message.answer(STALE_TEXT)
        return

    user_id = message.from_user.id
    fav = db.get_favorite(user_id, fav_id)
    if not fav:
        await message.answer("❌ Маршрут не найден.")
        return
    _, route, snt, dsnt, timeint, _ = fav

    text = reminders.confirmation_text(mode, days, notify_time, lead_min, timeint)
    db.add_subscription(user_id, fav_id, notify_time, mode=mode, days=days, lead_min=lead_min)

    if mode == reminders.MODE_REMIND:
        # Ловим опечатки вроде 3:00 вместо 8:00, пока пользователь ещё здесь
        today = parser._get_current_datetime()['date']
        departures = await parser.get_departures(route, snt, dsnt, today, notify_time, reminders.PLAN_WINDOW_MIN)
        if departures == []:
            text += f"\n\n⚠️ После {notify_time} в течение часа рейсов не нашлось — проверь время."

    await message.answer(text)


@router.callback_query(SubCallback.filter(F.action == "del"))
async def on_sub_delete(call: CallbackQuery, callback_data: SubCallback):
    try:
        sub_id, fav_id = map(int, callback_data.id.split("_"))
    except ValueError:
        await call.answer()
        return
    user_id = call.from_user.id
    if db.delete_subscription(sub_id, user_id):
        await call.answer("🔕 Подписка отменена")
    else:
        await call.answer("Подписка не найдена", show_alert=True)
    await _show_favorite(call, user_id, fav_id)


@router.callback_query(F.data.startswith("sub_back_"))
async def on_sub_back(call: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        fav_id = int(call.data.split("_")[-1])
    except ValueError:
        await call.answer()
        return
    user_id = call.from_user.id
    await call.answer()
    await _show_favorite(call, user_id, fav_id)
