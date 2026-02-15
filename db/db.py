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
            timeint TEXT
        )''')

        # Таблица статистики
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS statistics (
            day TEXT PRIMARY KEY,
            uses INTEGER DEFAULT 0
        )''')
        
        conn.commit()

def add_user(user_info: dict):
    with connection_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM users WHERE user_id = ?', (user_info['user_id'],))
        if cursor.fetchone():
            return
        
        cursor.execute(
            'INSERT INTO users (user_id, user_name, first_name, last_name, is_premium) VALUES (?, ?, ?, ?, ?)',
            (user_info['user_id'], user_info['user_name'], user_info['first_name'], 
             user_info['last_name'], str(user_info['is_premium']))
        )
        conn.commit()

# --- Избранное ---

def add_favorite_route(user_id, route, snt, dsnt, timeint):
    """Добавляет маршрут в избранное, если его там нет"""
    with connection_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT 1 FROM favorite_route WHERE user_id = ? AND route = ? AND snt = ? AND dsnt = ? AND timeint = ?',
            (user_id, route, snt, dsnt, timeint)
        )
        if cursor.fetchone():
            return False # Уже есть
        
        cursor.execute(
            'INSERT INTO favorite_route (user_id, route, snt, dsnt, timeint) VALUES (?, ?, ?, ?, ?)',
            (user_id, route, snt, dsnt, timeint)
        )
        conn.commit()
        return True

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

def delete_favorite_route(fav_id):
    """Удаляет избранное по его ID"""
    with connection_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM favorite_route WHERE id = ?', (fav_id,))
        conn.commit()
        return cursor.rowcount > 0

# --- Статистика ---

def update_uses_statistics(date_str):
    """Увеличивает счетчик использования бота на сегодня"""
    with connection_db() as conn:
        cursor = conn.cursor()
        # Пытаемся обновить
        cursor.execute('UPDATE statistics SET uses = uses + 1 WHERE day = ?', (date_str,))
        
        # Если ничего не обновилось (строки нет), вставляем новую
        if cursor.rowcount == 0:
            cursor.execute('INSERT INTO statistics (day, uses) VALUES (?, 1)', (date_str,))
        
        conn.commit()

def get_statistics():
    """Возвращает статистику за последние 30 дней, сортируя правильно по дате"""
    with connection_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT day, uses 
            FROM statistics 
            ORDER BY substr(day, 7, 4) || substr(day, 4, 2) || substr(day, 1, 2) DESC 
            LIMIT 30
        ''')
        return cursor.fetchall()

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