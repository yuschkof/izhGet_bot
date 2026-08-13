from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

# --- Фабрики колбэков ---
class TransportCallback(CallbackData, prefix="tr"):
    action: str  # 'time', 'route', 'station'
    value: str   # Значение

class FavCallback(CallbackData, prefix="fav"):
    action: str
    id: str

class SubCallback(CallbackData, prefix="sub"):
    action: str  # 'ask', 'del'
    id: str      # fav_id или sub_id

def make_fav_add_data(route, snt, dsnt, timeint):
    return f"{route}_{snt}_{dsnt}_{timeint}"


def get_dynamic_stations_kb(stations_dict: dict, action: str):
    """
    Генерирует Inline-клавиатуру из словаря остановок.
    
    :param stations_dict: словарь вида {'1900': 'Аграрный университет', ...}
    :param action: 'station' (для начальной) или 'dest_station' (для конечной)
    """
    builder = InlineKeyboardBuilder()
    
    if not stations_dict:
        builder.button(text="🚫 Остановки не найдены", callback_data="ignore")
        return builder.as_markup()

    # Сортируем остановки по алфавиту для удобства пользователей
    sorted_stations = sorted(stations_dict.items(), key=lambda item: item[1])

    for stn_id, stn_name in sorted_stations:
        builder.button(
            text=stn_name, 
            callback_data=TransportCallback(action=action, value=str(stn_id))
        )
    
    # Выстраиваем по 2 кнопки в ряд
    builder.adjust(2)
    
    # Добавляем кнопки Навигации
    if action == 'station':
        builder.row(
            InlineKeyboardButton(text="🔙 Назад", callback_data="route_back_route"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="route_cancel")
        )
    elif action == 'dest_station':
        builder.row(
            InlineKeyboardButton(text="🔙 Назад", callback_data="route_back_station"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="route_cancel")
        )
        
    return builder.as_markup()


def get_time_keyboard():
    builder = InlineKeyboardBuilder()
    
    builder.button(text='30 мин.', callback_data=TransportCallback(action='time', value='30'))
    builder.button(text='60 мин.', callback_data=TransportCallback(action='time', value='60'))
    builder.button(text='90 мин.', callback_data=TransportCallback(action='time', value='90'))

    builder.button(text='6 час.', callback_data=TransportCallback(action='time', value='360'))
    builder.button(text='12 час.', callback_data=TransportCallback(action='time', value='720'))
    builder.button(text='24 час.', callback_data=TransportCallback(action='time', value='1440'))

    builder.adjust(3)
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="route_cancel"))
    return builder.as_markup()


def get_routes_keyboard():
    builder = InlineKeyboardBuilder()
    # Правильная (числовая) сортировка маршрутов:
    routes = ['1', '2', '3', '4', '5', '7', '8', '9', '10', '11', '12', '0']
    for r in routes:
        text = "Все" if r == '0' else r
        builder.button(text=text, callback_data=TransportCallback(action='route', value=r))
    builder.adjust(4)
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="route_back_time"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="route_cancel")
    )
    return builder.as_markup()


def get_favorites_list_kb(user_routes):
    builder = InlineKeyboardBuilder()
    
    for route_data in user_routes:
        # Индексы: 0:id, 1:route, 2:snt, 3:dsnt, 4:timeint, 5:custom_name
        fav_id = route_data[0]
        route = route_data[1]
        
        # Достаем custom_name
        custom_name = route_data[5] if len(route_data) > 5 else None
        
        # Если custom_name есть в базе - показываем его, иначе ставим заглушку
        text = custom_name if custom_name else f"🚋 Маршрут {route}"
        
        builder.button(text=text, callback_data=FavCallback(action='select', id=str(fav_id)))
    
    builder.adjust(1)
    return builder.as_markup()


def get_after_result_kb(route, snt, dsnt, timeint, is_favorite=False):
    """Кнопка под расписанием"""
    builder = InlineKeyboardBuilder()

    if not is_favorite:
        data_str = make_fav_add_data(route, snt, dsnt, timeint)
        builder.button(text="❤️ Добавить в избранное", callback_data=FavCallback(action='add', id=data_str))

    data_str = make_fav_add_data(route, snt, dsnt, timeint)
    builder.button(text="🔄 Обновить", callback_data=FavCallback(action='refresh', id=data_str))
    return builder.as_markup()


def get_delete_kb(fav_id, has_subscription=False):
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Переименовать", callback_data=FavCallback(action='rename_ask', id=str(fav_id)))
    builder.button(text="❌ Удалить", callback_data=FavCallback(action='del', id=str(fav_id)))
    sub_text = "🔕 Подписка активна" if has_subscription else "🔔 Подписаться"
    builder.button(text=sub_text, callback_data=SubCallback(action='ask', id=str(fav_id)))
    builder.button(text="🔙 Назад к списку", callback_data="back_to_favorites")
    builder.adjust(2, 1, 1)
    return builder.as_markup()


def get_sub_manage_kb(sub_id, fav_id):
    """Клавиатура управления активной подпиской."""
    builder = InlineKeyboardBuilder()
    # id кодирует оба значения, чтобы после удаления вернуться к маршруту
    builder.button(text="🔕 Отписаться", callback_data=SubCallback(action='del', id=f"{sub_id}_{fav_id}"))
    builder.button(text="✏️ Изменить время", callback_data=SubCallback(action='edit', id=str(fav_id)))
    builder.button(text="🔙 Назад", callback_data=f"sub_back_{fav_id}")
    builder.adjust(2, 1)
    return builder.as_markup()


def get_cancel_sub_kb(fav_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="Отмена", callback_data=f"sub_back_{fav_id}")
    return builder.as_markup()


def get_cancel_rename_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="Отмена", callback_data="cancel_rename")
    return builder.as_markup()

def get_cancel_support_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel_support")
    return builder.as_markup()