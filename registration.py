from flask import Blueprint, render_template, redirect, request, session, current_app
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
from os import path

reg = Blueprint('reg', __name__)


def db_connect():
    if current_app.config['DB_TYPE'] == 'postgres':
        conn = psycopg2.connect(
            host='127.0.0.1',
            database='alina_terehova_knowledge_base',
            user='alina_terehova_knowledge_base',
            password='12345'
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

@reg.route('/registration/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('registration/register.html')
    
    login = request.form.get('login')
    password = request.form.get('password')

    if not (login and password):
        return render_template('registration/register.html', error='Заполните все поля')

    conn, cur = db_connect()
    
    if current_app.config['DB_TYPE'] == 'postgres':
        cur.execute("SELECT login FROM users WHERE login=%s;", (login,))
    else:
        cur.execute("SELECT login FROM users WHERE login=?;", (login,))
        
    if cur.fetchone():
        db_close(conn, cur)
        return render_template('registration/register.html', error='Такой пользователь уже существует')

    password_hash = generate_password_hash(password)
    if current_app.config['DB_TYPE'] == 'postgres':
        cur.execute("INSERT INTO users (login, password) VALUES (%s, %s);", (login, password_hash))
    else:    
        cur.execute("INSERT INTO users (login, password) VALUES (?, ?);", (login, password_hash))
    db_close(conn, cur)
    return render_template('registration/success.html', login=login)

@reg.route('/registration/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('registration/login.html')
    
    login = request.form.get('login')
    password = request.form.get('password')

    if not (login and password):
        return render_template('registration/login.html', error='Заполните все поля')

    conn, cur = db_connect()
    
    if current_app.config['DB_TYPE'] == 'postgres':
        cur.execute("SELECT * FROM users WHERE login=%s;", (login,))
    else:
        cur.execute("SELECT * FROM users WHERE login=?;", (login,))
        
    user = cur.fetchone()

    if not user:
        db_close(conn, cur)
        return render_template('registration/login.html', error='Логин и/или пароль неверны')

    if not check_password_hash(user['password'], password):
        db_close(conn, cur)
        return render_template('registration/login.html', error='Логин и/или пароль неверны')

    session['login'] = login
    db_close(conn, cur)
    return render_template('registration/success_login.html', login=login)

@reg.route('/registration/create', methods=['GET', 'POST'])
def create():
    login = session.get('login')
    if not login:
        return redirect('/registration/login')

    if request.method == 'GET':
        return render_template('registration/create_article.html')
    
    title = request.form.get('title')
    article_text = request.form.get('article_text')
    is_favourate = request.form.get('is_favourate') == 'on'  
    is_public = request.form.get('is_public') == 'on'  

    if not title or not article_text:  
        return render_template('registration/create_article.html', error='Заполните все поля')  

    conn, cur = db_connect()

    if current_app.config['DB_TYPE'] == 'postgres':
        cur.execute("SELECT * FROM users WHERE login=%s;", (login,))
    else:
        cur.execute("SELECT * FROM users WHERE login=?;", (login,))
        
    user_id = cur.fetchone()['id']

    if current_app.config['DB_TYPE'] == 'postgres':
        cur.execute("INSERT INTO articles (user_id, title, article_text, is_favourate, is_public)\
                     VALUES (%s, %s, %s, %s, %s);",
                    (user_id, title, article_text, is_favourate, is_public))
    else:
        cur.execute("INSERT INTO articles (user_id, title, article_text, is_favourate, is_public) \
                    VALUES (?, ?, ?, ?, ?);",
                    (user_id, title, article_text, is_favourate, is_public))

    db_close(conn, cur)
    return redirect('/registration')

@reg.route('/registration/list')
def list():
    login = session.get('login')
    conn, cur = db_connect()


    if current_app.config['DB_TYPE'] == 'postgres':
        if login:
            cur.execute(""" 
                SELECT * FROM articles WHERE user_id = (SELECT id FROM users WHERE login=%s)
                ORDER BY is_favourate DESC;
            """, (login,))
        else:
            cur.execute(""" 
                SELECT * FROM articles WHERE is_public = TRUE
                ORDER BY is_favourate DESC;
            """)
    else:
        if login:
            cur.execute(""" 
                SELECT * FROM articles WHERE user_id = (SELECT id FROM users WHERE login=?)
                ORDER BY is_favourate DESC;
            """, (login,))
        else:
            cur.execute(""" 
                SELECT * FROM articles WHERE is_public = TRUE
                ORDER BY is_favourate DESC;
            """)

    articles = cur.fetchall()
    db_close(conn, cur)

    if not articles:
        return render_template('/registration/articles.html', articles=[], message='У вас нет ни одной статьи.')  

    return render_template('/registration/articles.html', articles=articles) 

@reg.route('/registration/logout')
def logout():
    session.pop('login', None) 
    return redirect('/')

@reg.route('/registration/edit/<int:article_id>', methods=['GET', 'POST'])
def edit(article_id):
    login = session.get('login')
    if not login:
        return redirect('/registration/login')

    conn, cur = db_connect()

    if current_app.config['DB_TYPE'] == 'postgres':
        cur.execute("SELECT * FROM articles WHERE id=%s;", (article_id,))
    else:
        cur.execute("SELECT * FROM articles WHERE id=?;", (article_id,))

    article = cur.fetchone()
    db_close(conn, cur)

    if not article:
        return render_template('registration/articles.html', message='Статья не найдена.')

    if request.method == 'GET':
        return render_template('registration/edit_article.html', article=article)

    title = request.form.get('title')
    article_text = request.form.get('article_text')
    is_favourate = request.form.get('is_favourate') == 'on'  
    is_public = request.form.get('is_public') == 'on'  

    if not title or not article_text:
        return render_template('registration/edit_article.html', article=article, error='Заполните все поля')

    conn, cur = db_connect()
    if current_app.config['DB_TYPE'] == 'postgres':
        cur.execute("UPDATE articles SET title=%s, article_text=%s, is_favourate=%s, is_public=%s WHERE id=%s;",
                    (title, article_text, is_favourate, is_public, article_id))
    else:
        cur.execute("UPDATE articles SET title=?, article_text=?, is_favourate=?, is_public=? WHERE id=?;",
                    (title, article_text, is_favourate, is_public, article_id))

    db_close(conn, cur)
    return redirect('/registration/list')

@reg.route('/registration/delete/<int:article_id>', methods=['POST'])
def delete(article_id):
    login = session.get('login')
    if not login:
        return redirect('/registration/login')

    conn, cur = db_connect()
    if current_app.config['DB_TYPE'] == 'postgres':
        cur.execute("DELETE FROM articles WHERE id=%s;", (article_id,))
    else:
        cur.execute("DELETE FROM articles WHERE id=?;", (article_id,))
    
    db_close(conn, cur)
    return redirect('/registration/list')

@reg.route('/registration/users')
def users():
    login = session.get('login')
    conn, cur = db_connect()

    if current_app.config['DB_TYPE'] == 'postgres':
        cur.execute("SELECT login FROM users;")
    else:
        cur.execute("SELECT login FROM users;")

    users = cur.fetchall()
    db_close(conn, cur)

    return render_template('registration/users.html', users=users)  