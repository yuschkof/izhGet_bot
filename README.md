# izhGet_bot

Telegram-бот для просмотра расписания трамваев и троллейбусов г. Ижевска.  
Данные берутся с сайта [ижгэт.рф/rasp/](https://ижгэт.рф/rasp/).

> Бот не является официальным сервисом ИжГЭТ.

**Живой бот:** [@izhGet_bot](https://t.me/izhGet_bot)

---

## Возможности

- Поиск расписания по маршруту и остановкам на ближайшие 30 мин / 1 / 6 / 12 / 24 часа
- Сохранение маршрутов в избранное с пользовательскими названиями
- Подписка на маршрут — бот ежедневно присылает расписание в указанное время
- Inline-режим: поиск избранных маршрутов прямо из строки ввода (`@izhGet_bot`)
- Обращение к разработчику через `/support`

---

## Команды

| Команда | Описание |
|---|---|
| `/new` | Найти расписание (выбор маршрута и остановок) |
| `/favorites` | Мои сохранённые маршруты |
| `/support` | Написать разработчику |
| `/help` | Справка |

---

## Запуск

### Локально

```bash
# Создать виртуальное окружение
python -m venv venv

# Активировать (Linux/macOS)
source venv/bin/activate
# Активировать (Windows)
.\venv\Scripts\activate

pip install -r requirements.txt
python main.py
```

### Docker (рекомендуется)

Включает xray SOCKS5-прокси для работы в сетях с ограничениями.

```bash
docker-compose up -d
```

---

## Настройка

Создайте файл `.env` в корне проекта:

```env
BOT_TOKEN=ваш_токен_бота
ADMIN_ID=ваш_telegram_id

# Опционально — SOCKS5/HTTP прокси
# Если указан, бот проверит доступность и использует при наличии связи
PROXY_URL=socks5://127.0.0.1:1080
```

Для Docker-режима с xray создайте `xray-config.json` по образцу конфигурации Xray/V2Ray.

---

## Архитектура

```
main.py                — Точка входа: инициализация БД, прокси, роутеры, планировщик подписок
middlewares.py         — UserRegisterMiddleware: авторегистрация пользователей, DAU-трекинг
request.py             — TimetableParser: HTTP-скрапер ижгэт.рф (остановки, маршруты, расписание)
db/db.py               — SQLite-обёртка (izhGet.db): users, favorite_route, subscriptions, statistics, daily_active
handlers/
  common.py            — /start, /help, /support, /stat, fallback для неизвестных сообщений
  new_route.py         — /new: FSM-флоу (время → маршрут → начальная → конечная → результат)
  favorite_route.py    — /favorites: список, выбор, переименование, удаление
  subscription.py      — Подписки: создание, просмотр, изменение времени, отмена
  inline.py            — Inline-режим: поиск избранного, получение расписания
  admin.py             — Команды только для администратора
keyboards/
  keyboards.py         — Все InlineKeyboardBuilder-фабрики и CallbackData-классы
```

### Схема БД

| Таблица | Назначение |
|---|---|
| `users` | Зарегистрированные пользователи |
| `favorite_route` | Сохранённые маршруты (`route, snt, dsnt, timeint, custom_name`) |
| `subscriptions` | Подписки на ежедневное расписание (`fav_id, notify_time`) |
| `statistics` | Дневная статистика: запросы, новые пользователи, непонятки |
| `daily_active` | Уникальные активные пользователи по дням (DAU) |

### Callback-фабрики

| Класс | Префикс | Используется для |
|---|---|---|
| `TransportCallback(action, value)` | `tr` | Выбор времени, маршрута, остановки |
| `FavCallback(action, id)` | `fav` | Управление избранным |
| `SubCallback(action, id)` | `sub` | Управление подписками |

### Таймзона

`Europe/Samara` (UTC+4) — соответствует Ижевску (Удмуртия, без перехода на летнее время).

---

## Стек

- Python 3.10
- [aiogram 3.x](https://github.com/aiogram/aiogram)
- aiohttp + lxml
- SQLite
- Docker + [Xray-core](https://github.com/XTLS/Xray-core)
