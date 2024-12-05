from flask import Blueprint, render_template, redirect, request, session, current_app
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
from os import path
import re

reg = Blueprint('reg', __name__)

# Регулярное выражение для проверки допустимых символов в логине и пароле
VALID_INPUT_PATTERN = re.compile(r'^[A-Za-z0-9@#$%^&+=_-]+$')

def is_valid_input(input_str):
#    Проверяет, соответствует ли строка допустимому шаблону.

    return bool(VALID_INPUT_PATTERN.match(input_str))

def db_connect():
#   Устанавливает подключение к базе данных.
    
    if current_app.config['DB_TYPE'] == 'postgres':
        # Подключение к базе PostgreSQL
        conn = psycopg2.connect(
            host='127.0.0.1',
            database='storage_room',
            user='alina',
            password='123'
        )
        cur = conn.cursor(cursor_factory=RealDictCursor)
    else:
        # Подключение к SQLite
        dir_path = path.dirname(path.realpath(__file__))
        db_path = path.join(dir_path, "database.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

    return conn, cur

def db_close(conn, cur):
#    Закрывает подключение к базе данных.

    conn.commit()
    cur.close()
    conn.close()

@reg.route('/registration/register', methods=['GET', 'POST'])
def register():
#    Управляет процессом регистрации пользователей.
    if 'login' in session:
        # Перенаправление на главную страницу, если пользователь уже вошел в систему
        return redirect('/')

    if request.method == 'GET':
        # Отображение страницы регистрации
        return render_template('registration/register.html')
    
    # Получение данных из формы
    login = request.form.get('login')
    password = request.form.get('password')

    # Проверка на заполненность полей
    if not (login and password):
        return render_template('registration/register.html', error='Заполните все поля')

    # Проверка логина и пароля на допустимые символы
    if not is_valid_input(login):
        return render_template('registration/register.html', error='Логин содержит недопустимые символы')
    
    if not is_valid_input(password):
        return render_template('registration/register.html', error='Пароль содержит недопустимые символы')

    # Подключение к базе данных
    conn, cur = db_connect()
    
    # Проверка на существование пользователя
    if current_app.config['DB_TYPE'] == 'postgres':
        cur.execute("SELECT login FROM users WHERE login=%s;", (login,))
    else:
        cur.execute("SELECT login FROM users WHERE login=?;", (login,))
        
    if cur.fetchone():
        db_close(conn, cur)
        return render_template('registration/register.html', error='Такой пользователь уже существует')

    # Хеширование пароля и добавление нового пользователя
    password_hash = generate_password_hash(password)
    if current_app.config['DB_TYPE'] == 'postgres':
        cur.execute("INSERT INTO users (login, password) VALUES (%s, %s);", (login, password_hash))
    else:    
        cur.execute("INSERT INTO users (login, password) VALUES (?, ?);", (login, password_hash))
    db_close(conn, cur)

    # Отображение страницы успешной регистрации
    return render_template('registration/success.html', login=login)

@reg.route('/registration/login', methods=['GET', 'POST'])
def login():
#    Управляет процессом входа пользователя в систему.

    if 'login' in session:
        # Перенаправление на главную страницу, если пользователь уже вошел в систему
        return redirect('/')

    if request.method == 'GET':
        # Отображение страницы входа
        return render_template('registration/login.html')
    
    # Получение данных из формы
    login = request.form.get('login')
    password = request.form.get('password')

    # Проверка на заполненность полей
    if not (login and password):
        return render_template('registration/login.html', error='Заполните все поля')

    # Проверка логина и пароля на допустимые символы
    if not is_valid_input(login):
        return render_template('registration/login.html', error='Логин содержит недопустимые символы')
    
    if not is_valid_input(password):
        return render_template('registration/login.html', error='Пароль содержит недопустимые символы')

    # Подключение к базе данных
    conn, cur = db_connect()
    
    # Поиск пользователя в базе данных
    if current_app.config['DB_TYPE'] == 'postgres':
        cur.execute("SELECT * FROM users WHERE login=%s;", (login,))
    else:
        cur.execute("SELECT * FROM users WHERE login=?;", (login,))
        
    user = cur.fetchone()

    # Проверка существования пользователя и корректности пароля
    if not user:
        db_close(conn, cur)
        return render_template('registration/login.html', error='Логин и/или пароль неверны')

    if not check_password_hash(user['password'], password):
        db_close(conn, cur)
        return render_template('registration/login.html', error='Логин и/или пароль неверны')

    # Сохранение логина в сессии
    session['login'] = login
    db_close(conn, cur)

    # Отображение страницы успешного входа
    return render_template('registration/success_login.html', login=login)

@reg.route('/registration/logout')
def logout():
#    Управляет процессом выхода пользователя из системы.

    session.pop('login', None)  # Удаление логина из сессии
    return redirect('/')

@reg.route('/registration/delete_account', methods=['POST'])
def delete_account():
#    Удаляет аккаунт текущего пользователя.

    if 'login' not in session:
        # Перенаправление на главную страницу, если пользователь не вошел в систему
        return redirect('/')

    login = session['login']
    conn, cur = db_connect()
    
    # Удаление пользователя из базы данных
    if current_app.config['DB_TYPE'] == 'postgres':
        cur.execute("DELETE FROM users WHERE login=%s;", (login,))
    else:
        cur.execute("DELETE FROM users WHERE login=?;", (login,))
        
    db_close(conn, cur)

    # Удаление логина из сессии
    session.pop('login', None)
    return redirect('/')
