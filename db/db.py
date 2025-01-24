import sqlite3
from datetime import datetime
import pytz

def connection_db():
    return sqlite3.connect('izhGet.db')


def add_user(user_info):
    connection = connection_db()
    cursor = connection.cursor()

    if is_user_exists(user_info):
        connection.close()
        return

    cursor.execute('INSERT INTO users (user_id, user_name, first_name, last_name, is_premium) VALUES (?, ?, ?, ?, ?)',
                   (user_info['user_id'], user_info['user_name'], user_info['first_name'], user_info['last_name'],
                    user_info['is_premium']))

    connection.commit()
    connection.close()


def is_user_exists(user_info):
    connection = connection_db()
    cursor = connection.cursor()

    cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_info['user_id'],))
    results = cursor.fetchall()
    connection.close()
    if not results:
        return False
    return True


def add_favorite_route(route_info):
    connection = connection_db()
    cursor = connection.cursor()
    if is_route_exists(route_info):
        connection.close()
        return False
    cursor.execute('INSERT INTO favorite_route (user_id, route, snt, dsnt, timeint) VALUES (?, ?, ?, ?, ?)',
                   (route_info['user_id'], route_info['route'], route_info['snt'], route_info['dsnt'],
                    route_info['timeint']))
    connection.commit()
    connection.close()
    return True


def delete_favorite_route(route_info):
    connection = connection_db()
    cursor = connection.cursor()
    if not is_route_exists(route_info):
        connection.close()
        return False
    cursor.execute(
        'DELETE FROM favorite_route WHERE user_id = ? AND route = ? AND snt = ? AND dsnt = ? AND timeint = ?',
        (route_info['user_id'], route_info['route'], route_info['snt'], route_info['dsnt'],
         route_info['timeint']))
    connection.commit()
    connection.close()
    return True


def is_route_exists(route_info):
    connection = connection_db()
    cursor = connection.cursor()

    text = 'SELECT * FROM favorite_route WHERE user_id = ? AND route = ? AND snt = ? AND dsnt = ? AND timeint = ?'
    cursor.execute(text, (
        route_info['user_id'], route_info['route'], route_info['snt'], route_info['dsnt'], route_info['timeint']))
    results = cursor.fetchall()
    connection.close()
    if not results:
        return False
    return True


def get_favorite_routes(user_id):
    connection = connection_db()
    cursor = connection.cursor()

    cursor.execute('SELECT * FROM favorite_route WHERE user_id = ?', (user_id,))
    results = cursor.fetchall()
    connection.close()
    return results


def get_route_name(route_id):
    connection = connection_db()
    cursor = connection.cursor()

    cursor.execute('SELECT name FROM routes WHERE id = ?', (route_id,))
    results = cursor.fetchall()
    connection.close()
    return results[0][0]


def create_tabel_statistics():
    connection = connection_db()
    cursor = connection.cursor()

    cursor.execute("""
    CREATE TABLE if not exists "statistics" (
        "day"	NUMERIC UNIQUE,
	    "uses"	INTEGER
    );
    """)
    connection.commit()
    connection.close()


def update_uses_statistics(day):
    connection = connection_db()
    cursor = connection.cursor()

    if not is_day_exist(day):
        create_day(day)

    cursor.execute('UPDATE statistics SET uses = uses + 1 WHERE day = ?', (day, ))

    connection.commit()
    connection.close()


def is_day_exist(day):
    connection = connection_db()
    cursor = connection.cursor()

    text = 'SELECT * FROM statistics WHERE day = ?'
    cursor.execute(text, (day, ))
    results = cursor.fetchall()
    connection.close()
    if not results:
        return False
    return True


def create_day(day):
    connection = connection_db()
    cursor = connection.cursor()

    cursor.execute('INSERT INTO statistics (day, uses) VALUES (?, ?)',
                   (day, 1))
    connection.commit()
    connection.close()
    return True


def get_user_count():
    connection = connection_db()
    cursor = connection.cursor()

    cursor.execute('SELECT Count (*) as UserCount From users')
    results = cursor.fetchall()
    connection.close()
    return results[0][0]


def get_favorite_route_count():
    connection = connection_db()
    cursor = connection.cursor()

    cursor.execute('SELECT Count (*) as FavoriteRouteCount From favorite_route')
    results = cursor.fetchall()
    connection.close()
    return results[0][0]


def get_day_usage_count():
    connection = connection_db()
    cursor = connection.cursor()

    tz = pytz.timezone('Asia/Dubai')
    now = datetime.now(tz)
    current_date = now.strftime("%d.%m.%Y")

    cursor.execute('SELECT uses as UsageCount From statistics WHERE day = ?', (current_date, ))
    results = cursor.fetchall()
    connection.close()
    if len(results) == 0:
        return 0
    return results[0][0]