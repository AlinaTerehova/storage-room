from flask import Blueprint, render_template, request, session, jsonify, current_app
import psycopg2
from psycopg2.extras import RealDictCursor
from os import path
import sqlite3

room = Blueprint('room', __name__)

def db_connect():
    if current_app.config['DB_TYPE'] == 'postgres':
        conn = psycopg2.connect(
            host='127.0.0.1',
            database='storage_room',
            user='alina',
            password='123'
        )
        cur = conn.cursor(cursor_factory=RealDictCursor)
    else:
        dir_path = path.dirname(path.realpath(__file__))
        db_path = path.join(dir_path, "database.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

    return conn, cur

def db_close(conn, cur):
    conn.commit()
    cur.close()
    conn.close()

@room.route('/storage_room/')
def lab():
    return render_template('storage_room/room.html')

# Получение информации о комнатах
@room.route('/storage_room/rooms', methods=['GET'])
def get_rooms():
    login = session.get('login')  # Проверяем, авторизован ли пользователь
    conn, cur = db_connect()
    
    # Получаем список всех комнат
    cur.execute("SELECT * FROM rooms")
    rooms = cur.fetchall()
    
    # Подсчитываем свободные и занятые комнаты
    total_rooms = len(rooms)
    occupied_rooms = sum(1 for room in rooms if room['tenant'])
    free_rooms = total_rooms - occupied_rooms
    
    # Если пользователь не авторизован, заменяем имена на "Зарезервировано"
    if not login:
        for room in rooms:
            if room['tenant']:
                room['tenant'] = 'Зарезервирована'
    
    db_close(conn, cur)
    return jsonify({'rooms': rooms, 'free': free_rooms, 'occupied': occupied_rooms}), 200



# Забронирование комнаты
@room.route('/storage_room/rooms/booking/<int:room_number>', methods=['POST'])
def booking(room_number):
    login = session.get('login')
    if not login:
        return jsonify({'error': 'Пожалуйста, авторизуйтесь'}), 401  # Ошибка: Не авторизован

    conn, cur = db_connect()

    # Проверяем, сколько комнат уже забронировано пользователем
    cur.execute("SELECT COUNT(*) as count FROM rooms WHERE tenant = %s", (login,))
    count = cur.fetchone()['count']

    if count >= 5:
        db_close(conn, cur)
        return jsonify({'error': 'Вы не можете забронировать больше 5 комнат'}), 403  # Ошибка: Достигнуто ограничение

    # Проверяем, занята ли комната
    cur.execute("SELECT tenant FROM rooms WHERE number = %s", (room_number,))
    room = cur.fetchone()

    if room and room['tenant']:
        db_close(conn, cur)
        return jsonify({'error': 'Комната уже забронирована'}), 400  # Ошибка: Комната уже забронирована

    # Бронируем комнату
    cur.execute("UPDATE rooms SET tenant = %s WHERE number = %s", (login, room_number))
    db_close(conn, cur)
    return jsonify({'result': 'Успешно забронировано'}), 200  # Успех

# Отмена бронирования
@room.route('/storage_room/cancellation/<int:room_number>', methods=['POST'])
def cancellation(room_number):
    login = session.get('login')
    if not login:
        return jsonify({'error': 'Не авторизован'}), 401  # Ошибка: Не авторизован

    conn, cur = db_connect()

    # Проверяем, кто арендует комнату
    cur.execute("SELECT tenant FROM rooms WHERE number = %s", (room_number,))
    room = cur.fetchone()

    if room and room['tenant'] != login:
        db_close(conn, cur)
        return jsonify({'error': 'Вы не можете снять чужую бронь'}), 403  # Ошибка: Доступ запрещен

    # Отменяем бронирование
    cur.execute("UPDATE rooms SET tenant = NULL WHERE number = %s", (room_number,))
    db_close(conn, cur)
    return jsonify({'result': 'Бронирование отменено'}), 200  # Успех

# Освобождение комнаты
@room.route('/storage_room/rooms/release/<int:room_number>', methods=['POST'])
def release(room_number):
    login = session.get('login')
    if not login:
        return jsonify({'error': 'Пожалуйста, авторизуйтесь'}), 401  # Ошибка: Не авторизован

    conn, cur = db_connect()

    # Проверяем, кто арендует комнату
    cur.execute("SELECT tenant FROM rooms WHERE number = %s", (room_number,))
    room = cur.fetchone()

    if room and room['tenant'] != login:
        db_close(conn, cur)
        return jsonify({'error': 'Вы не можете снять чужую бронь'}), 403  # Ошибка: Доступ запрещен

    # Освобождаем комнату
    cur.execute("UPDATE rooms SET tenant = NULL WHERE number = %s", (room_number,))
    db_close(conn, cur)
    return jsonify({'result': 'Комната освобождена'}), 200  # Успех
