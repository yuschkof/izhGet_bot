import hashlib
from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton, ChosenInlineResult
from keyboards.keyboards import get_station_name, FavCallback
import db.db as db
from request import get_result

router = Router()

# Хендлер 1: ПОИСК
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
            if len(fav) == 6:
                fav_id, route, snt, dsnt, timeint, custom_name = fav
            else:
                fav_id, route, snt, dsnt, timeint = fav
                custom_name = None
        except:
            continue

        snt_name = get_station_name(snt)
        dsnt_name = get_station_name(dsnt)
        title = custom_name if custom_name else f"Маршрут {route}"
        description = f"{snt_name} ➝ {dsnt_name}"

        if text:
            search_source = f"{title} {description} {route}".lower()
            if text not in search_source:
                continue

        result_id = f"fav:{fav_id}"

        # --- ИСПРАВЛЕНИЕ ЗДЕСЬ ---
        # Обязательно добавляем кнопку, чтобы Телеграм дал нам редактировать сообщение потом
        dummy_kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⏳ Загрузка...", callback_data="ignore")
        ]])

        message_content = InputTextMessageContent(
            message_text=f"⏳ <b>{title}</b>\nПодождите, получаю данные...",
            parse_mode="HTML"
        )

        item = InlineQueryResultArticle(
            id=result_id,
            title=f"⭐ {title}",
            description=description,
            input_message_content=message_content,
            reply_markup=dummy_kb, # <--- Прикрепляем кнопку
            thumb_url="https://cdn-icons-png.flaticon.com/512/1828/1828884.png",
            thumb_width=48,
            thumb_height=48
        )
        results.append(item)

    await query.answer(results, cache_time=1, is_personal=True)


# Хендлер 2: АВТО-ЗАГРУЗКА
@router.chosen_inline_result()
async def on_chosen_result(chosen_result: ChosenInlineResult, bot):
    # Если кнопки не было, ID не придет. Но теперь кнопка есть.
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
    target_fav = next((f for f in favorites if f[0] == fav_id), None)

    if not target_fav:
        await bot.edit_message_text(
            text="❌ Маршрут не найден.",
            inline_message_id=chosen_result.inline_message_id
        )
        return

    if len(target_fav) == 6:
        _, route, snt, dsnt, timeint, _ = target_fav
    else:
        _, route, snt, dsnt, timeint = target_fav

    text_result = await get_result(
        timeint=timeint,
        snt=snt,
        dsnt=dsnt,
        route=route
    )

    # Меняем кнопку "Загрузка" на "Обновить"
    markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🔄 Обновить", 
            callback_data=FavCallback(action="select", id=str(fav_id)).pack()
        )
    ]])

    try:
        await bot.edit_message_text(
            text=text_result,
            inline_message_id=chosen_result.inline_message_id,
            parse_mode="HTML",
            reply_markup=None
        )
    except Exception as e:
        print(f"Ошибка: {e}")