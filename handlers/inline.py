import hashlib
from aiogram import Router, Bot, F
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton, ChosenInlineResult, CallbackQuery

import db.db as db
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

    for fav in favorites:
        try:
            # Теперь индексы такие: id(0), route(1), snt(2), dsnt(3), timeint(4), custom_name(5)
            fav_id = fav[0]
            route = fav[1]
            timeint = fav[4]
            custom_name = fav[5] if len(fav) > 5 else None
        except IndexError:
            continue

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
                input_message_content=InputTextMessageContent(
                    message_text=f"⏳ Загружаю расписание: <b>{title}</b>...",
                    parse_mode="HTML"
                ),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(
                        text="Загрузка...", 
                        callback_data="ignore"
                    )
                ]])
            )
        )

    await query.answer(results, cache_time=1, is_personal=True)


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

    user_id = chosen_result.from_user.id
    favorites = db.get_favorite_routes(user_id)
    
    # Ищем маршрут в списке
    target_fav = next((f for f in favorites if f[0] == fav_id), None)

    if not target_fav:
        await bot.edit_message_text(
            text="❌ Маршрут не найден в базе.",
            inline_message_id=chosen_result.inline_message_id
        )
        return

    # Достаем данные для запроса (route, snt, dsnt, timeint)
    try:
        route = target_fav[1]
        snt = target_fav[2]
        dsnt = target_fav[3]
        timeint = target_fav[4]
    except IndexError:
        return

    # Запрашиваем расписание напрямую с сайта ИжГЭТ
    text_result = await get_result(
        timeint=timeint,
        snt=snt,
        dsnt=dsnt,
        route=route
    )

    # Меняем кнопку "Загрузка..." на "Обновить"
    markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🔄 Обновить", 
            callback_data=f"inline_ref:{fav_id}"
        )
    ]])

    await bot.edit_message_text(
        text=text_result,
        inline_message_id=chosen_result.inline_message_id,
        reply_markup=markup,
        parse_mode="HTML"
    )

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

    user_id = call.from_user.id
    favorites = db.get_favorite_routes(user_id)
    target_fav = next((f for f in favorites if f[0] == fav_id), None)

    if not target_fav:
        await call.answer("Маршрут не найден", show_alert=True)
        return

    try:
        route = target_fav[1]
        snt = target_fav[2]
        dsnt = target_fav[3]
        timeint = target_fav[4]
    except IndexError:
        await call.answer("Ошибка данных маршрута", show_alert=True)
        return

    await call.answer("Обновляю расписание...")

    text_result = await get_result(
        timeint=timeint,
        snt=snt,
        dsnt=dsnt,
        route=route
    )

    markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🔄 Обновить", 
            callback_data=f"inline_ref:{fav_id}"
        )
    ]])

    try:
        await bot.edit_message_text(
            text=text_result,
            inline_message_id=call.inline_message_id,
            reply_markup=markup,
            parse_mode="HTML"
        )
    except Exception:
        # Игнорируем ошибку "Message is not modified"
        pass