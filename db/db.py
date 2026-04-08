import sqlite3
import logging
from contextlib import contextmanager

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@contextmanager
def connection_db():
    conn = sqlite3.connect('izhGet.db')
    try:
        yield conn
    finally:
        conn.close()

def create_tables():
    """Создание всех необходимых таблиц при старте"""
    with connection_db() as conn:
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            user_name TEXT,
            first_name TEXT,
            last_name TEXT,
            is_premium TEXT
        )''')
        
        # Таблица избранного
        # route: номер маршрута, snt: код старта, dsnt: код финиша, timeint: интервал
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorite_route (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            route TEXT,
            snt TEXT,
            dsnt TEXT,
            timeint TEXT,
            custom_name TEXT
        )''')

        # Таблица статистики
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS statistics (
            day TEXT PRIMARY KEY,
            uses INTEGER DEFAULT 0,
            unknown_messages INTEGER DEFAULT 0,
            new_users INTEGER DEFAULT 0
        )''')
        # Добавляем колонки если их нет (для существующих БД)
        for col in ('unknown_messages', 'new_users'):
            try:
                cursor.execute(f'ALTER TABLE statistics ADD COLUMN {col} INTEGER DEFAULT 0')
            except Exception:
                pass

        # Таблица подписок на расписание
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            fav_id INTEGER,
            notify_time TEXT,
            is_active INTEGER DEFAULT 1
        )''')

        # Таблица уникальных активных пользователей по дням (DAU)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_active (
            day TEXT,
            user_id INTEGER,
            PRIMARY KEY (day, user_id)
        )''')
        
        conn.commit()

def add_user(user_info: dict) -> bool:
    """Добавляет пользователя. Возвращает True если пользователь новый."""
    with connection_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM users WHERE user_id = ?', (user_info['user_id'],))
        if cursor.fetchone():
            return False

        cursor.execute(
            'INSERT INTO users (user_id, user_name, first_name, last_name, is_premium) VALUES (?, ?, ?, ?, ?)',
            (user_info['user_id'], user_info['user_name'], user_info['first_name'],
             user_info['last_name'], str(user_info['is_premium']))
        )
        conn.commit()
        return True

# --- Избранное ---

def add_favorite_route(user_id, route, snt, dsnt, timeint, custom_name):
    """Добавляет маршрут в избранное, если его там нет. Возвращает ID записи или None"""
    with connection_db() as conn:
        cursor = conn.cursor()
        
        # Проверяем по базовым параметрам, существует ли уже такой маршрут
        cursor.execute(
            'SELECT 1 FROM favorite_route WHERE user_id = ? AND route = ? AND snt = ? AND dsnt = ? AND timeint = ?',
            (user_id, route, snt, dsnt, timeint)
        )
        if cursor.fetchone():
            return None # Уже есть, возвращаем None
        
        # Записываем новый маршрут вместе с его сгенерированным именем
        cursor.execute(
            'INSERT INTO favorite_route (user_id, route, snt, dsnt, timeint, custom_name) VALUES (?, ?, ?, ?, ?, ?)',
            (user_id, route, snt, dsnt, timeint, custom_name)
        )
        conn.commit()
        
        # Возвращаем ID только что созданной строчки
        return cursor.lastrowid

def get_favorite_routes(user_id):
    """Возвращает: (id, route, snt, dsnt, timeint, custom_name)"""
    with connection_db() as conn:
        cursor = conn.cursor()
        # Теперь выбираем и custom_name
        cursor.execute('SELECT id, route, snt, dsnt, timeint, custom_name FROM favorite_route WHERE user_id = ?', (user_id,))
        return cursor.fetchall()
    
def rename_favorite_route(fav_id, new_name):
    """Устанавливает пользовательское название для маршрута"""
    with connection_db() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE favorite_route SET custom_name = ? WHERE id = ?', (new_name, fav_id))
        conn.commit()
        return cursor.rowcount > 0

def delete_favorite_route(fav_id, user_id):
    """Удаляет избранное по ID, только если принадлежит user_id"""
    with connection_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM favorite_route WHERE id = ? AND user_id = ?', (fav_id, user_id))
        conn.commit()
        return cursor.rowcount > 0

# --- Статистика ---

def _upsert_statistics(cursor, date_str):
    """Гарантирует наличие строки за дату."""
    cursor.execute('INSERT OR IGNORE INTO statistics (day, uses) VALUES (?, 0)', (date_str,))


def update_uses_statistics(date_str):
    """Увеличивает счетчик запросов расписания на сегодня."""
    with connection_db() as conn:
        cursor = conn.cursor()
        _upsert_statistics(cursor, date_str)
        cursor.execute('UPDATE statistics SET uses = COALESCE(uses, 0) + 1 WHERE day = ?', (date_str,))
        conn.commit()


def update_unknown_messages_statistics(user_id: int):
    """Увеличивает счетчик неизвестных сообщений на сегодня."""
    from datetime import datetime
    import pytz
    date_str = datetime.now(pytz.timezone('Europe/Samara')).strftime("%d.%m.%Y")
    with connection_db() as conn:
        cursor = conn.cursor()
        _upsert_statistics(cursor, date_str)
        cursor.execute('UPDATE statistics SET unknown_messages = unknown_messages + 1 WHERE day = ?', (date_str,))
        conn.commit()


def update_new_user_statistics(date_str: str):
    """Увеличивает счетчик новых пользователей на сегодня."""
    with connection_db() as conn:
        cursor = conn.cursor()
        _upsert_statistics(cursor, date_str)
        cursor.execute('UPDATE statistics SET new_users = new_users + 1 WHERE day = ?', (date_str,))
        conn.commit()

def get_statistics():
    """Возвращает статистику за последние 30 дней, сортируя правильно по дате"""
    with connection_db() as conn:
        cursor = conn.cursor()
        
        # Мы используем substr, чтобы вырезать Год, Месяц и День и склеить их для сортировки
        # day имеет формат 02.01.2026
        # substr(day, 7, 4) -> 2026 (год)
        # substr(day, 4, 2) -> 01 (месяц)
        # substr(day, 1, 2) -> 02 (день)
        
        cursor.execute('''
            SELECT s.day, s.uses, s.unknown_messages, s.new_users,
                   COUNT(da.user_id) AS dau
            FROM statistics s
            LEFT JOIN daily_active da ON da.day = s.day
            GROUP BY s.day
            ORDER BY substr(s.day, 7, 4) || substr(s.day, 4, 2) || substr(s.day, 1, 2) DESC
            LIMIT 30
        ''')
        return cursor.fetchall()

# --- Подписки ---

def add_subscription(user_id, fav_id, notify_time):
    """Добавляет или обновляет подписку. Возвращает ID записи."""
    with connection_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id FROM subscriptions WHERE user_id = ? AND fav_id = ?',
            (user_id, fav_id)
        )
        existing = cursor.fetchone()
        if existing:
            cursor.execute(
                'UPDATE subscriptions SET notify_time = ?, is_active = 1 WHERE id = ?',
                (notify_time, existing[0])
            )
            conn.commit()
            return existing[0]
        cursor.execute(
            'INSERT INTO subscriptions (user_id, fav_id, notify_time) VALUES (?, ?, ?)',
            (user_id, fav_id, notify_time)
        )
        conn.commit()
        return cursor.lastrowid

def get_subscription(user_id, fav_id):
    """Возвращает (id, user_id, fav_id, notify_time, is_active) или None."""
    with connection_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, user_id, fav_id, notify_time, is_active FROM subscriptions WHERE user_id = ? AND fav_id = ?',
            (user_id, fav_id)
        )
        return cursor.fetchone()

def delete_subscription(sub_id, user_id):
    """Удаляет подписку по ID, только если принадлежит user_id."""
    with connection_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM subscriptions WHERE id = ? AND user_id = ?', (sub_id, user_id))
        conn.commit()
        return cursor.rowcount > 0

def get_due_subscriptions(notify_time: str):
    """Возвращает активные подписки с заданным временем: [(id, user_id, fav_id), ...]"""
    with connection_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, user_id, fav_id FROM subscriptions WHERE notify_time = ? AND is_active = 1',
            (notify_time,)
        )
        return cursor.fetchall()


def track_daily_active(user_id: int, date_str: str):
    """Фиксирует активность пользователя за день. Дубли игнорируются."""
    with connection_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT OR IGNORE INTO daily_active (day, user_id) VALUES (?, ?)',
            (date_str, user_id)
        )
        conn.commit()


def get_subscriptions_count() -> int:
    with connection_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM subscriptions WHERE is_active = 1')
        return cursor.fetchone()[0]


def get_favorites_count() -> int:
    with connection_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM favorite_route')
        return cursor.fetchone()[0]


def get_users_count():
    with connection_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        return cursor.fetchone()[0]
    
def get_all_users():
    """Возвращает список ID всех пользователей: [123, 456, 789]"""
    with connection_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users')
        # fetchall возвращает список кортежей [(123,), (456,)], превращаем в плоский список
        return [row[0] for row in cursor.fetchall()]