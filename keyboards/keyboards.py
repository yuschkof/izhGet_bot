from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


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

inline_40 = InlineKeyboardButton(text='Банк «Зенит»', callback_data='40')
inline_37 = InlineKeyboardButton(text='Больница', callback_data='37')
inline_26 = InlineKeyboardButton(text='Буммаш', callback_data='26')
inline_9 = InlineKeyboardButton(text='Воткинская линия', callback_data='9')
inline_50 = InlineKeyboardButton(text='Дом Дружбы народов', callback_data='50')
inline_2 = InlineKeyboardButton(text='Железнодорожный вокзал', callback_data='2')
inline_3 = InlineKeyboardButton(text='Завод мин.вод', callback_data='3')
inline_21 = InlineKeyboardButton(text='Зоопарк', callback_data='21')
inline_67 = InlineKeyboardButton(text='Италмас', callback_data='67')
inline_68 = InlineKeyboardButton(text='Карлутская набережная', callback_data='68')
inline_17 = InlineKeyboardButton(text='Магазин «Океан»', callback_data='17')
inline_52 = InlineKeyboardButton(text='Международный университет', callback_data='52')
inline_62 = InlineKeyboardButton(text='Молдавская', callback_data='62')
inline_18 = InlineKeyboardButton(text='Монтажный техникум', callback_data='18')
inline_20 = InlineKeyboardButton(text='Парк им.Кирова', callback_data='28')
inline_33 = InlineKeyboardButton(text='Пер. Воткинский', callback_data='33')
inline_10 = InlineKeyboardButton(text='Пер. Октябрьский', callback_data='10')
inline_34 = InlineKeyboardButton(text='Пер. Профсоюзный', callback_data='34')
inline_32 = InlineKeyboardButton(text='Пер. Уральский', callback_data='32')
inline_16 = InlineKeyboardButton(text='Пер. Широкий', callback_data='16')
inline_29 = InlineKeyboardButton(text='Покровская церковь', callback_data='29')
inline_61 = InlineKeyboardButton(text='Проспект Калашникова', callback_data='61')
inline_55 = InlineKeyboardButton(text='Радио “Адам”', callback_data='55')
inline_38 = InlineKeyboardButton(text='Речка Карлутка', callback_data='38')
inline_14 = InlineKeyboardButton(text='Свято-Михайловский собор', callback_data='14')
inline_27 = InlineKeyboardButton(text='Северный рынок', callback_data='27')
inline_19 = InlineKeyboardButton(text='Сельхозакадемия', callback_data='19')
inline_25 = InlineKeyboardButton(text='Сквер металлургов', callback_data='25')
inline_8 = InlineKeyboardButton(text='Трамвайное депо', callback_data='8')
inline_22 = InlineKeyboardButton(text='Ул. 30 лет Победы', callback_data='22')
inline_63 = InlineKeyboardButton(text='Ул. 40 лет Победы', callback_data='63')
inline_23 = InlineKeyboardButton(text='Ул. 6-я Подлесная', callback_data='23')
inline_24 = InlineKeyboardButton(text='Ул. 9-я Подлесная', callback_data='24')
inline_64 = InlineKeyboardButton(text='Ул. Бабушкина', callback_data='64')
inline_43 = InlineKeyboardButton(text='Ул. Братская', callback_data='43')
inline_39 = InlineKeyboardButton(text='Ул. Воровского', callback_data='39')
inline_59 = InlineKeyboardButton(text='Ул. Ворошилова', callback_data='59')
inline_4 = InlineKeyboardButton(text='Ул. Гагарина', callback_data='4')
inline_35 = InlineKeyboardButton(text='Ул. Герцена', callback_data='35')
inline_46 = InlineKeyboardButton(text='Ул. Загородная', callback_data='46')
inline_11 = InlineKeyboardButton(text='Ул. К.Либкнехта', callback_data='11')
inline_45 = InlineKeyboardButton(text='Ул. Кирпичная', callback_data='45')
inline_53 = InlineKeyboardButton(text='Ул. Коммунаров', callback_data='53')
inline_51 = InlineKeyboardButton(text='Ул. Краева', callback_data='51')
inline_41 = InlineKeyboardButton(text='Ул. Красноармейская', callback_data='41')
inline_56 = InlineKeyboardButton(text='Ул. Л.Толстого', callback_data='56')
inline_7 = InlineKeyboardButton(text='Ул. Магистральная', callback_data='7')
inline_47 = InlineKeyboardButton(text='Ул. Можарова', callback_data='47')
inline_1 = InlineKeyboardButton(text='Ул. Московская', callback_data='1')
inline_48 = InlineKeyboardButton(text='Ул. Огнеупорная', callback_data='48')
inline_65 = InlineKeyboardButton(text='Ул. Орджоникидзе', callback_data='65')
inline_58 = InlineKeyboardButton(text='Ул. Промышленная', callback_data='58')
inline_60 = InlineKeyboardButton(text='Ул. Т.Барамзиной', callback_data='60')
inline_30 = InlineKeyboardButton(text='Ул. Тимирязева', callback_data='30')
inline_54 = InlineKeyboardButton(text='Ул. Удмуртская', callback_data='54')
inline_36 = InlineKeyboardButton(text='ул. Халтурина-Реабилитационный центр “Адели”', callback_data='36')
inline_57 = InlineKeyboardButton(text='Ул. Шишкина', callback_data='57')
inline_5 = InlineKeyboardButton(text='Хозяйственная база', callback_data='5')
inline_66 = InlineKeyboardButton(text='Центр', callback_data='66')
inline_12 = InlineKeyboardButton(text='Центральная мечеть', callback_data='12')
inline_15 = InlineKeyboardButton(text='Центральный универмаг', callback_data='15')
inline_31 = InlineKeyboardButton(text='Школа № 64', callback_data='31')
inline_28 = InlineKeyboardButton(text='Школа № 79', callback_data='28')
inline_6 = InlineKeyboardButton(text='Южная автостанция', callback_data='6')
inline_44 = InlineKeyboardButton(text='Южный рынок', callback_data='44')
inline_13 = InlineKeyboardButton(text='Центр (сев.)', callback_data='13')
inline_42 = InlineKeyboardButton(text='Центр (вост.)', callback_data='42')
inline_49 = InlineKeyboardButton(text='Центр (южн.)', callback_data='49')

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
