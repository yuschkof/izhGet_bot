import html
from aiogram import Router, Bot, F
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputRichMessageContent, InputRichMessage, ChosenInlineResult, CallbackQuery

import db.db as db
import keyboards.keyboards as kb
from request import get_result

router = Router()

@router.inline_query()
async def inline_search(query: InlineQuery):
    text = query.query.lower().strip()
    user_id = query.from_user.id

    favorites = db.get_favorite_routes(user_id)

    if not favorites:
        await query.answer(
            [],
            cache_time=1,
            is_personal=True,
            switch_pm_text="Список пуст. Создать маршрут",
            switch_pm_parameter="inline_empty"
        )
        return

    results = []

    for fav_id, route, _, _, timeint, custom_name in favorites:
        # Берем красивое имя из БД. Если его там вдруг нет (до миграции), ставим заглушку.
        title = custom_name if custom_name else f"🚌 Маршрут {route}"

        # Фильтрация (если пользователь начал вводить текст в inline-режиме)
        if text and text not in title.lower():
            continue

        results.append(
            InlineQueryResultArticle(
                id=f"fav:{fav_id}",
                title=title,
                description=f"Интервал: {timeint} мин.",
                input_message_content=InputRichMessageContent(
                    rich_message=InputRichMessage(html=f"⏳ Загружаю расписание: <b>{html.escape(title)}</b>...")
                ),
                reply_markup=kb.get_inline_loading_kb()
            )
        )

    await query.answer(results, cache_time=1, is_personal=True)


async def _edit_inline_timetable(bot: Bot, inline_message_id: str, fav):
    """Запрашивает расписание с сайта ИжГЭТ и подставляет его в inline-сообщение."""
    fav_id, route, snt, dsnt, timeint, _ = fav
    text_result = await get_result(timeint=timeint, snt=snt, dsnt=dsnt, route=route)
    await bot.edit_message_text(
        inline_message_id=inline_message_id,
        rich_message=InputRichMessage(html=text_result),
        reply_markup=kb.get_inline_result_kb(fav_id)
    )


@router.chosen_inline_result()
async def on_chosen_inline_result(chosen_result: ChosenInlineResult, bot: Bot):
    # Если кнопки не было, ID не придет
    if not chosen_result.inline_message_id:
        return

    if not chosen_result.result_id.startswith("fav:"):
        return

    try:
        fav_id = int(chosen_result.result_id.split(":")[1])
    except (IndexError, ValueError):
        return

    target_fav = db.get_favorite(chosen_result.from_user.id, fav_id)
    if not target_fav:
        await bot.edit_message_text(
            text="❌ Маршрут не найден в базе.",
            inline_message_id=chosen_result.inline_message_id
        )
        return

    await _edit_inline_timetable(bot, chosen_result.inline_message_id, target_fav)

@router.callback_query(F.data.startswith("inline_ref:"))
async def on_inline_refresh(call: CallbackQuery, bot: Bot):
    if not call.inline_message_id:
        await call.answer("Это старое сообщение, обновите заново.", show_alert=True)
        return

    try:
        fav_id = int(call.data.split(":")[1])
    except (IndexError, ValueError):
        await call.answer("Ошибка данных", show_alert=True)
        return

    target_fav = db.get_favorite(call.from_user.id, fav_id)
    if not target_fav:
        await call.answer("Маршрут не найден", show_alert=True)
        return

    await call.answer("Обновляю расписание...")

    try:
        await _edit_inline_timetable(bot, call.inline_message_id, target_fav)
    except Exception:
        # Игнорируем ошибку "Message is not modified"
        pass
