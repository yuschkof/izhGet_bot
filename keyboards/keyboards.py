from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import WebAppInfo


WebAppMe = ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(
                        text="Дурачье", 
                        web_app=WebAppInfo(url='https://yuschkof.fun')
                    )
                ]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )



inline_kb_time = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text='30 мин.', callback_data='time30'),
        InlineKeyboardButton(text='60 мин.', callback_data='time60'),
        InlineKeyboardButton(text='90 мин.', callback_data='time90')
    ]
])


inline_kb_route = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text='1', callback_data='route1'),
        InlineKeyboardButton(text='10', callback_data='route10'),
        InlineKeyboardButton(text='11', callback_data='route11')],
    [
        InlineKeyboardButton(text='12', callback_data='route12'),
        InlineKeyboardButton(text='2', callback_data='route2'),
        InlineKeyboardButton(text='3', callback_data='route3')],
    [
        InlineKeyboardButton(text='4', callback_data='route4'),
        InlineKeyboardButton(text='5', callback_data='route5'),
        InlineKeyboardButton(text='7', callback_data='route7')
    ],
    [
        InlineKeyboardButton(text='8', callback_data='route8'),
        InlineKeyboardButton(text='9', callback_data='route9'),
        InlineKeyboardButton(text='Все', callback_data='route0')
    ]
])

inline_40 = InlineKeyboardButton(text='Банк «Зенит»', callback_data='new4000')
inline_37 = InlineKeyboardButton(text='Больница', callback_data='new3700')
inline_26 = InlineKeyboardButton(text='Буммаш', callback_data='new2600')
inline_9 = InlineKeyboardButton(text='Воткинская линия', callback_data='new900')
inline_50 = InlineKeyboardButton(text='Дом Дружбы народов', callback_data='new5000')
inline_2 = InlineKeyboardButton(text='Железнодорожный вокзал', callback_data='new200')
inline_3 = InlineKeyboardButton(text='Завод мин.вод', callback_data='new300')
inline_21 = InlineKeyboardButton(text='Зоопарк', callback_data='new2100')
inline_67 = InlineKeyboardButton(text='Италмас', callback_data='new6700')
inline_68 = InlineKeyboardButton(text='Карлутская набережная', callback_data='new6800')
inline_17 = InlineKeyboardButton(text='Магазин «Океан»', callback_data='new1700')
inline_52 = InlineKeyboardButton(text='Международный университет', callback_data='new5200')
inline_62 = InlineKeyboardButton(text='Молдавская', callback_data='new6200')
inline_18 = InlineKeyboardButton(text='Монтажный техникум', callback_data='new1800')
inline_20 = InlineKeyboardButton(text='Парк им.Кирова', callback_data='new2800')
inline_33 = InlineKeyboardButton(text='Пер. Воткинский', callback_data='new3300')
inline_10 = InlineKeyboardButton(text='Пер. Октябрьский', callback_data='new1000')
inline_34 = InlineKeyboardButton(text='Пер. Профсоюзный', callback_data='new340')
inline_32 = InlineKeyboardButton(text='Пер. Уральский', callback_data='new3200')
inline_16 = InlineKeyboardButton(text='Пер. Широкий', callback_data='new1600')
inline_29 = InlineKeyboardButton(text='Покровская церковь', callback_data='new2900')
inline_61 = InlineKeyboardButton(text='Проспект Калашникова', callback_data='new6100')
inline_55 = InlineKeyboardButton(text='Радио “Адам”', callback_data='new5500')
inline_38 = InlineKeyboardButton(text='Речка Карлутка', callback_data='new3800')
inline_14 = InlineKeyboardButton(text='Свято-Михайловский собор', callback_data='new1400')
inline_27 = InlineKeyboardButton(text='Северный рынок', callback_data='new2700')
inline_19 = InlineKeyboardButton(text='Сельхозакадемия', callback_data='new1900')
inline_25 = InlineKeyboardButton(text='Сквер металлургов', callback_data='new2500')
inline_8 = InlineKeyboardButton(text='Трамвайное депо', callback_data='new800')
inline_22 = InlineKeyboardButton(text='Ул. 30 лет Победы', callback_data='new2200')
inline_63 = InlineKeyboardButton(text='Ул. 40 лет Победы', callback_data='new6300')
inline_23 = InlineKeyboardButton(text='Ул. 6-я Подлесная', callback_data='new2300')
inline_24 = InlineKeyboardButton(text='Ул. 9-я Подлесная', callback_data='new2400')
inline_64 = InlineKeyboardButton(text='Ул. Бабушкина', callback_data='new6400')
inline_43 = InlineKeyboardButton(text='Ул. Братская', callback_data='new4300')
inline_39 = InlineKeyboardButton(text='Ул. Воровского', callback_data='new3900')
inline_59 = InlineKeyboardButton(text='Ул. Ворошилова', callback_data='new5900')
inline_4 = InlineKeyboardButton(text='Ул. Гагарина', callback_data='new400')
inline_35 = InlineKeyboardButton(text='Ул. Герцена', callback_data='new3500')
inline_46 = InlineKeyboardButton(text='Ул. Загородная', callback_data='new4600')
inline_11 = InlineKeyboardButton(text='Ул. К.Либкнехта', callback_data='new1100')
inline_45 = InlineKeyboardButton(text='Ул. Кирпичная', callback_data='new4500')
inline_53 = InlineKeyboardButton(text='Ул. Коммунаров', callback_data='new5300')
inline_51 = InlineKeyboardButton(text='Ул. Краева', callback_data='new5100')
inline_41 = InlineKeyboardButton(text='Ул. Красноармейская', callback_data='new4100')
inline_56 = InlineKeyboardButton(text='Ул. Л.Толстого', callback_data='new5600')
inline_7 = InlineKeyboardButton(text='Ул. Магистральная', callback_data='new700')
inline_47 = InlineKeyboardButton(text='Ул. Можарова', callback_data='new4700')
inline_1 = InlineKeyboardButton(text='Ул. Московская', callback_data='new100')
inline_48 = InlineKeyboardButton(text='Ул. Огнеупорная', callback_data='new4800')
inline_65 = InlineKeyboardButton(text='Ул. Орджоникидзе', callback_data='new6500')
inline_58 = InlineKeyboardButton(text='Ул. Промышленная', callback_data='new5800')
inline_60 = InlineKeyboardButton(text='Ул. Т.Барамзиной', callback_data='new6000')
inline_30 = InlineKeyboardButton(text='Ул. Тимирязева', callback_data='new3000')
inline_54 = InlineKeyboardButton(text='Ул. Удмуртская', callback_data='new5400')
inline_36 = InlineKeyboardButton(text='ул. Халтурина-Реабилитационный центр “Адели”', callback_data='new3600')
inline_57 = InlineKeyboardButton(text='Ул. Шишкина', callback_data='new5700')
inline_5 = InlineKeyboardButton(text='Хозяйственная база', callback_data='new500')
inline_66 = InlineKeyboardButton(text='Центр', callback_data='new6600')
inline_12 = InlineKeyboardButton(text='Центральная мечеть', callback_data='new1200')
inline_15 = InlineKeyboardButton(text='Центральный универмаг', callback_data='new1500')
inline_31 = InlineKeyboardButton(text='Школа № 64', callback_data='new3100')
inline_28 = InlineKeyboardButton(text='Школа № 79', callback_data='new2800')
inline_6 = InlineKeyboardButton(text='Южная автостанция', callback_data='new600')
inline_44 = InlineKeyboardButton(text='Южный рынок', callback_data='new4400')
inline_13 = InlineKeyboardButton(text='Центр (сев.)', callback_data='new1300')
inline_42 = InlineKeyboardButton(text='Центр (вост.)', callback_data='new4200')
inline_49 = InlineKeyboardButton(text='Центр (южн.)', callback_data='new4900')

inline_kb0 = InlineKeyboardMarkup(row_width=2, inline_keyboard=[
    [inline_40, inline_37],
    [inline_26, inline_9],
    [inline_50, inline_2],
    [inline_3, inline_21],
    [inline_67, inline_68],
    [inline_17, inline_52],
    [inline_62, inline_18],
    [inline_20, inline_33],
    [inline_10, inline_34],
    [inline_32, inline_16],
    [inline_29, inline_61],
    [inline_55, inline_38],
    [inline_14, inline_27],
    [inline_19, inline_25],
    [inline_8, inline_22],
    [inline_63, inline_23],
    [inline_24, inline_64],
    [inline_43, inline_39],
    [inline_59, inline_4],
    [inline_35, inline_46],
    [inline_11, inline_45],
    [inline_53, inline_51],
    [inline_41, inline_56],
    [inline_7, inline_47],
    [inline_1, inline_48],
    [inline_65, inline_58],
    [inline_60, inline_30],
    [inline_54, inline_57],
    [inline_36],
    [inline_5, inline_66],
    [inline_12, inline_15],
    [inline_31, inline_28],
    [inline_6, inline_44],
])


inline_kb1 = InlineKeyboardMarkup(row_width=2, inline_keyboard=[
    [inline_25, inline_24],
    [inline_23, inline_22],
    [inline_21, inline_28],
    [inline_19, inline_18],
    [inline_17, inline_16],
    [inline_15, inline_14],
    [inline_66, inline_12],
    [inline_11, inline_10],
    [inline_9, inline_8],
    [inline_7, inline_6],
    [inline_5, inline_4],
    [inline_3, inline_2],
    [inline_1],
])


inline_kb10 = InlineKeyboardMarkup(row_width=2, inline_keyboard=[
    [inline_25, inline_24],
    [inline_23, inline_22],
    [inline_21, inline_28],
    [inline_19, inline_18],
    [inline_17, inline_16],
    [inline_15, inline_14],
    [inline_66, inline_41],
    [inline_40, inline_39],
    [inline_38, inline_37],
    [inline_36, inline_64],
    [inline_63, inline_62],
    [inline_61, inline_60],
    [inline_67, inline_59]
])


inline_kb11 = InlineKeyboardMarkup(row_width=2, inline_keyboard=[
    [inline_58, inline_50],
    [inline_68, inline_51],
    [inline_65, inline_38],
    [inline_37, inline_36],
    [inline_64, inline_63],
    [inline_62, inline_61],
    [inline_60, inline_67],
    [inline_59]
])


inline_kb12 = InlineKeyboardMarkup(row_width=2, inline_keyboard=[
    [inline_1, inline_2],
    [inline_3, inline_4],
    [inline_5, inline_6],
    [inline_7, inline_8],
    [inline_9, inline_10],
    [inline_11, inline_12],
    [inline_66, inline_41],
    [inline_40, inline_39],
    [inline_38, inline_37],
    [inline_36, inline_64],
    [inline_63, inline_62],
    [inline_61, inline_60],
    [inline_67, inline_59]
])


inline_kb2 = InlineKeyboardMarkup(row_width=2, inline_keyboard=[
    [inline_58, inline_50],
    [inline_68, inline_51],
    [inline_65, inline_39],
    [inline_40, inline_41],
    [inline_66, inline_14],
    [inline_15, inline_16],
    [inline_17, inline_52],
    [inline_53, inline_54],
    [inline_55, inline_56],
    [inline_57, inline_30],
    [inline_29, inline_28],
    [inline_27, inline_26]
])


inline_kb3 = InlineKeyboardMarkup(row_width=2, inline_keyboard=[
    [inline_58, inline_50],
    [inline_68, inline_51],
    [inline_65, inline_39],
    [inline_40, inline_41],
    [inline_66, inline_12],
    [inline_11, inline_10],
    [inline_9, inline_8],
    [inline_7, inline_6],
    [inline_5, inline_4],
    [inline_3, inline_1],
    [inline_1],
])


inline_kb4 = InlineKeyboardMarkup(row_width=2, inline_keyboard=[
    [inline_25, inline_24],
    [inline_23, inline_22],
    [inline_21, inline_28],
    [inline_19, inline_18],
    [inline_17, inline_16],
    [inline_15, inline_14],
    [inline_66, inline_41],
    [inline_40, inline_39],
    [inline_65, inline_51],
    [inline_68, inline_50],
    [inline_58]
])


inline_kb5 = InlineKeyboardMarkup(row_width=2, inline_keyboard=[
    [inline_48, inline_47],
    [inline_46, inline_45],
    [inline_44, inline_43],
    [inline_4, inline_5],
    [inline_6, inline_7],
    [inline_8, inline_9],
    [inline_10, inline_11],
    [inline_12, inline_66],
    [inline_41, inline_40],
    [inline_39, inline_38],
    [inline_37, inline_36],
    [inline_35, inline_34],
    [inline_33, inline_32],
    [inline_31, inline_30],
    [inline_29, inline_28],
    [inline_27, inline_26]
])


inline_kb7 = InlineKeyboardMarkup(row_width=2, inline_keyboard=[
    [inline_25, inline_24],
    [inline_23, inline_22],
    [inline_21, inline_28],
    [inline_19, inline_18],
    [inline_17, inline_52],
    [inline_53, inline_54],
    [inline_55, inline_56],
    [inline_57, inline_30],
    [inline_29, inline_28],
    [inline_27, inline_26]
])


inline_kb8 = InlineKeyboardMarkup(row_width=2, inline_keyboard=[
    [inline_58, inline_50],
    [inline_68, inline_51],
    [inline_65, inline_38],
    [inline_37, inline_36],
    [inline_64, inline_35],
    [inline_34, inline_33],
    [inline_32, inline_31],
    [inline_30, inline_29],
    [inline_28, inline_27],
    [inline_26]
])


inline_kb9 = InlineKeyboardMarkup(row_width=2, inline_keyboard=[
    [inline_1, inline_2],
    [inline_3, inline_4],
    [inline_5, inline_6],
    [inline_7, inline_8],
    [inline_9, inline_10],
    [inline_11, inline_12],
    [inline_66, inline_14],
    [inline_15, inline_16],
    [inline_17, inline_52],
    [inline_53, inline_54],
    [inline_55, inline_56],
    [inline_57, inline_30],
    [inline_29, inline_28],
    [inline_27, inline_26]
])


kb_dict = {
    '0': inline_kb0,
    '1': inline_kb1,
    '10': inline_kb10,
    '11': inline_kb11,
    '12': inline_kb12,
    '2': inline_kb2,
    '3': inline_kb3,
    '4': inline_kb4,
    '5': inline_kb5,
    '7': inline_kb7,
    '8': inline_kb8,
    '9': inline_kb9,
}
