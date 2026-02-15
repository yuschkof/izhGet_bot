from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

# --- Фабрики колбэков ---
class TransportCallback(CallbackData, prefix="tr"):
    action: str  # 'time', 'route', 'station'
    value: str   # Значение

class FavCallback(CallbackData, prefix="fav"):
    action: str  # 'select', 'add', 'del'
    id: str      # id записи в БД (для del/select) или параметры (для add)

# Кодировщик для кнопки "Добавить" (так как данных много, а лимит 64 байта)
# Формат value в FavCallback для action='add': "route:snt:dsnt:time"
def make_fav_add_data(route, snt, dsnt, timeint):
    return f"{route}_{snt}_{dsnt}_{timeint}"

# Базовые списки (сегменты)
R1 = [
    ('Ул. Московская', '100'), ('Железнодорожный вокзал', '200'), ('Завод мин.вод', '300'),
    ('Ул. Гагарина', '400'), ('Хозяйственная база', '500'), ('Южная автостанция', '600'),
    ('Ул. Магистральная', '700'), ('Трамвайное депо', '800'), ('Воткинская линия', '900'),
    ('Пер. Октябрьский', '1000'), ('Ул. К.Либкнехта', '1100'), ('Центральная мечеть', '1200'),
    ('Центр', '6600'), ('Свято-Михайловский собор', '1400'), ('Центральный универмаг', '1500'),
    ('Пер. Широкий', '1600'), ('Магазин «Океан»', '1700'), ('Монтажный техникум', '1800'),
    ('Сельхозакадемия', '1900'), ('Зоопарк', '2100'), ('Ул. 30 лет Победы', '2200'),
    ('Ул. 6-я Подлесная', '2300'), ('Ул. 9-я Подлесная', '2400'), ('Сквер металлургов', '2500')
]

R2 = [
    ('Ул. Промышленная', '5800'), ('Ул. Шишкина', '5700'), ('Ул. Л.Толстого', '5600'),
    ('Радио “Адам”', '5500'), ('Ул. Удмуртская', '5400'), ('Ул. Коммунаров', '5300'),
    ('Международный университет', '5200'), ('Ул. Краева', '5100'), ('Дом Дружбы народов', '5000'),
    ('Центр', '6600'), ('Ул. Герцена', '3500'), ('Пер. Профсоюзный', '340'), ('Пер. Воткинский', '3300'),
    ('Пер. Уральский', '3200'), ('Школа № 64', '3100'), ('Ул. Тимирязева', '3000'),
    ('Покровская церковь', '2900'), ('Школа № 79', '2800'), ('Северный рынок', '2700'), ('Буммаш', '2600')
]

R5 = [
    ('Буммаш', '2600'), ('Северный рынок', '2700'), ('Школа № 79', '2800'), ('Покровская церковь', '2900'),
    ('Ул. Тимирязева', '3000'), ('Школа № 64', '3100'), ('Пер. Уральский', '3200'), ('Пер. Воткинский', '3300'),
    ('Пер. Профсоюзный', '340'), ('Ул. Герцена', '3500'), ('Центр', '6600'), ('Центральная мечеть', '1200'),
    ('Ул. К.Либкнехта', '1100'), ('Пер. Октябрьский', '1000'), ('Воткинская линия', '900'), ('Трамвайное депо', '800'),
    ('Ул. Магистральная', '700'), ('Южная автостанция', '600'), ('Хозяйственная база', '500'), ('Ул. Гагарина', '400'),
    ('Ул. Братская', '4300'), ('Южный рынок', '4400'), ('Ул. Кирпичная', '4500'), ('Ул. Загородная', '4600'),
    ('Ул. Можарова', '4700'), ('Ул. Огнеупорная', '4800')
]

R10 = [
    ('Ул. Ворошилова', '5900'), ('Ул. Т.Барамзиной', '6000'), ('Проспект Калашникова', '6100'),
    ('Молдавская', '6200'), ('Ул. 40 лет Победы', '6300'), ('Ул. Бабушкина', '6400'),
    ('ул. Халтурина', '3600'), ('Больница', '3700'), ('Речка Карлутка', '3800'),
    ('Ул. Воровского', '3900'), ('Банк «Зенит»', '4000'), ('Ул. Красноармейская', '4100'),
    ('Центр', '6600'), ('Свято-Михайловский собор', '1400'), ('Центральный универмаг', '1500'),
    ('Пер. Широкий', '1600'), ('Магазин «Океан»', '1700'), ('Монтажный техникум', '1800'),
    ('Сельхозакадемия', '1900'), ('Зоопарк', '2100'), ('Ул. 30 лет Победы', '2200'),
    ('Ул. 6-я Подлесная', '2300'), ('Ул. 9-я Подлесная', '2400'), ('Сквер металлургов', '2500')
]

# Сборка маршрутов
R3 = [s for s in R1 if int(s[1]) <= 6600] + [s for s in reversed(R2) if int(s[1]) < 6600]
R4 = [s for s in R2 if int(s[1]) >= 5000 or s[1] == '6600'] + [s for s in R1 if int(s[1]) > 6600 or s[1] == '2500']
R7 = [s for s in R5 if int(s[1]) >= 2600 and int(s[1]) != 4800] + [s for s in R1 if int(s[1]) > 1400]
R8 = R2 
R9 = [s for s in R1 if int(s[1]) <= 6600] + [s for s in reversed(R5) if int(s[1]) >= 2600 and int(s[1]) != 4800]
R11 = [s for s in R2 if int(s[1]) >= 5000 or s[1] == '6600'] + [s for s in reversed(R10) if int(s[1]) != 2500 and int(s[1]) != 6600]
R12 = [s for s in R1 if int(s[1]) <= 6600] + [s for s in reversed(R10) if int(s[1]) != 2500 and int(s[1]) != 6600]

# Главный словарь данных
ROUTES_STATIONS = {
    '1': R1,
    '2': R2,
    '3': list(set(R3)),
    '4': list(set(R4)),
    '5': R5,
    '7': list(set(R7)),
    '8': R8,
    '9': list(set(R9)),
    '10': R10,
    '11': list(set(R11)),
    '12': list(set(R12)),
    # '0' оставляем пустым здесь, он обрабатывается динамически в функции
}

def get_station_name(code):
    """Поиск имени станции по коду (нужно для отображения в избранном)"""
    for stations in ROUTES_STATIONS.values():
        for name, c in stations:
            if c == str(code):
                return name
    return code # Если не нашли, вернем код

# --- Клавиатуры ---

def get_main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Дурачье", web_app=WebAppInfo(url='https://yuschkof.fun'))]
            # Можно добавить кнопку "Статистика" для админов тут, если нужно
        ],
        resize_keyboard=True
    )

def get_time_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text='30 мин.', callback_data=TransportCallback(action='time', value='30'))
    builder.button(text='60 мин.', callback_data=TransportCallback(action='time', value='60'))
    builder.button(text='90 мин.', callback_data=TransportCallback(action='time', value='90'))
    builder.adjust(3)
    return builder.as_markup()

def get_routes_keyboard():
    builder = InlineKeyboardBuilder()
    routes = ['1', '10', '11', '12', '2', '3', '4', '5', '7', '8', '9', '0']
    for r in routes:
        text = "Все" if r == '0' else r
        builder.button(text=text, callback_data=TransportCallback(action='route', value=r))
    builder.adjust(4)
    return builder.as_markup()

def get_stations_keyboard(route_id: str):
    builder = InlineKeyboardBuilder()
    stations = []
    
    if route_id == '0':
        unique = set()
        for r_list in ROUTES_STATIONS.values():
            for s in r_list: unique.add(s)
        stations = list(unique)
    else:
        stations = ROUTES_STATIONS.get(route_id, [])
    
    # Сортировка по алфавиту
    stations = sorted(list(set(stations)), key=lambda x: x[0])

    if not stations:
        builder.button(text="Нет данных", callback_data="ignore")
    
    for name, code in stations:
        builder.button(text=name, callback_data=TransportCallback(action='station', value=code))
    
    builder.adjust(2)
    return builder.as_markup()

# --- Клавиатуры Избранного ---

def get_favorites_list_kb(favorites):
    builder = InlineKeyboardBuilder()
    
    if not favorites:
        return None

    for fav in favorites:
        # Распаковываем 6 значений (добавилось custom_name)
        # Если в базе старые записи без custom_name, оно вернется как None
        fav_id, route, snt, dsnt, timeint, custom_name = fav
        
        if custom_name:
            # Если есть свое имя, используем его
            text = f"⭐ {custom_name}"
        else:
            # Иначе стандартное описание
            snt_name = get_station_name(snt)
            dsnt_name = get_station_name(dsnt)
            text = f"🚌 {route}: {snt_name} ➝ {dsnt_name}"
        
        builder.button(text=text, callback_data=FavCallback(action='select', id=str(fav_id)))
    
    builder.adjust(1)
    return builder.as_markup()

def get_after_result_kb(route, snt, dsnt, timeint, is_favorite=False):
    """Кнопка под расписанием"""
    builder = InlineKeyboardBuilder()
    
    if not is_favorite:
        # Упаковываем данные для добавления
        data_str = make_fav_add_data(route, snt, dsnt, timeint)
        builder.button(text="❤️ Добавить в избранное", callback_data=FavCallback(action='add', id=data_str))
    
    builder.button(text="🔄 Обновить", callback_data="refresh_schedule") # Можно реализовать позже
    return builder.as_markup()

def get_delete_kb(fav_id):
    builder = InlineKeyboardBuilder()
    # Две кнопки в ряд: Переименовать и Удалить
    builder.button(text="✏️ Переименовать", callback_data=FavCallback(action='rename_ask', id=str(fav_id)))
    builder.button(text="❌ Удалить", callback_data=FavCallback(action='del', id=str(fav_id)))
    builder.adjust(2)
    return builder.as_markup()

def get_cancel_rename_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="Отмена", callback_data="cancel_rename")
    return builder.as_markup()