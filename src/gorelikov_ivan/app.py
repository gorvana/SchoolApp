from flask import Flask, render_template, request, jsonify
import bcrypt
import mysql.connector

app = Flask(__name__)

def connection():
    cnx = mysql.connector.connect(
            host="185.114.247.43",
            port=3306,
            database="sch688_vvedenie",
            user="sch688_vvedenie",
            password="Qwerty123")
    return cnx

def hash_password(password):
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)

    return hashed.decode("utf-8")


def check_password(password, password_hash):
    password_bytes = password.encode("utf-8")
    hash_bytes = password_hash.encode("utf-8")

    return bcrypt.checkpw(password_bytes, hash_bytes)

def user_register():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            'result': False,
            'message': 'Некорректные данные'
        }), 400

    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not all(isinstance(value, str) for value in (name, email, password)):
        return jsonify({
            'result': False,
            'message': 'Заполните все поля'
        }), 400

    name = name.strip()
    email = email.strip().lower()

    if not name or not email or not password.strip():
        return jsonify({
            'result': False,
            'message': 'Заполните все поля'
        }), 400

    cnx = None
    cur = None

    try:
        cnx = connection()
        cur = cnx.cursor()

        cur.execute(
            'SELECT 1 FROM users WHERE email = %s',
            (email,)
        )

        if cur.fetchone() is not None:
            return jsonify({
                'result': False,
                'message': 'Пользователь с таким email уже существует'
            }), 409

        password_hash = hash_password(password)

        cur.execute(
            'INSERT INTO users (username, email, password_hash) '
            'VALUES (%s, %s, %s)',
            (name, email, password_hash)
        )

        cnx.commit()

        return jsonify({
            'result': True,
            'message': 'Регистрация прошла успешно'
        })

    except mysql.connector.IntegrityError:
        if cnx is not None:
            cnx.rollback()

        return jsonify({
            'result': False,
            'message': 'Пользователь с таким email уже существует'
        }), 409

    except mysql.connector.Error:
        if cnx is not None:
            cnx.rollback()

        app.logger.exception('Ошибка при регистрации')

        return jsonify({
            'result': False,
            'message': 'Ошибка при работе с базой данных'
        }), 500

    finally:
        if cur is not None:
            cur.close()

        if cnx is not None:
            cnx.close()

# # Fetch one result
# row = cur.fetchone()
# print("Current date is: {0}".format(row[0]))

# # Close connection
# cnx.close()

@app.route("/user_login", methods=['POST'])
def user_login():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            'result': False,
            'message': 'Некорректные данные'
        }), 400

    email = data.get('email')
    password = data.get('password')

    if not isinstance(email, str) or not isinstance(password, str):
        return jsonify({
            'result': False,
            'message': 'Заполните все поля'
        }), 400

    email = email.strip().lower()

    if not email or not password:
        return jsonify({
            'result': False,
            'message': 'Заполните все поля'
        }), 400

    cnx = None
    cur = None

    try:
        cnx = connection()
        cur = cnx.cursor()

        cur.execute(
            'SELECT password_hash FROM users WHERE email = %s',
            (email,)
        )

        user = cur.fetchone()

        if user is None:
            return jsonify({
                'result': False,
                'message': 'Неверный email или пароль'
            }), 401

        password_hash = user[0]

        if check_password(password, password_hash):
            return jsonify({
                'result': True,
                'message': 'Авторизация прошла успешно'
            })

        return jsonify({
            'result': False,
            'message': 'Неверный email или пароль'
        }), 401

    except mysql.connector.Error:
        app.logger.exception('Ошибка при авторизации')

        return jsonify({
            'result': False,
            'message': 'Ошибка при работе с базой данных'
        }), 500

    finally:
        if cur is not None:
            cur.close()

        if cnx is not None:
            cnx.close()

@app.route("/")
def registration():
    return render_template('registration.html')


@app.route("/login")
def login():
    return render_template('login.html')


if __name__ == "__main__":
    app.run()