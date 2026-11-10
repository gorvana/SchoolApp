from flask import Flask, render_template, request, jsonify, session, redirect
import bcrypt
from llama_cpp import Llama
import mysql.connector

REPO_ID = "bartowski/Qwen2.5-0.5B-Instruct-GGUF"
FILENAME = "Qwen2.5-0.5B-Instruct-Q4_K_M.gguf"

print(f"Загрузка модели {FILENAME} из {REPO_ID}...")
llm = Llama.from_pretrained(
    repo_id=REPO_ID,
    filename=FILENAME,
    n_ctx=2048,
    verbose=False
)
print("Модель успешно загружена.")

app = Flask(__name__)
app.secret_key = "1581"

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

@app.route("/user_register", methods=['POST'])
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
            print("aaa")
            return jsonify({
                'result': False,
                'message': 'Неверный email или пароль'
            }), 401

        if check_password(password, user['password_hash']):
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']

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

@app.route('/api/chat', methods=['POST'])
def api_chat():
    if 'user_id' not in session:
        return jsonify({'error': 'не авторизован'}), 401

    req = request.get_json(silent=True) or {}
    message = (req.get('message') or '').strip()

    if not message:
        return jsonify({'error': 'пустое сообщение'}), 400

    prompt = (
        f"<|im_start|>system\n"
        f"Ты полезный ассистент. Отвечай кратко и по-русски."
        f"<|im_end|>\n"
        f"<|im_start|>user\n{message}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )

    output = llm(
        prompt,
        max_tokens=150,
        temperature=0.7,
        stop=["<|im_end|>"]
    )

    reply = output['choices'][0]['text'].strip()

    return jsonify({'reply': reply})


@app.route('/profile')
def profile_page():
    if 'user_id' not in session:
        return redirect('/login')

    cnx = connection()

    try:
        cur = cnx.cursor(dictionary=True)

        cur.execute(
            'SELECT id, username, email, balance FROM users WHERE id = %s',
            (session['user_id'],)
        )

        user = cur.fetchone()

    finally:
        cur.close()
        cnx.close()

    if not user:
        session.clear()
        return redirect('/login')

    return render_template('profile.html', user=user)


@app.route('/logout', methods=['POST'])
def api_logout():
    session.clear()
    return redirect('/login')


@app.route('/transactions')
def transactions_page():
    if 'user_id' not in session:
        return redirect('/login')

    cnx = connection()

    try:
        cur = cnx.cursor(dictionary=True)

        cur.execute(
            '''SELECT id, amount, type, cost, description, balance_after, created_at
               FROM transactions
               WHERE user_id = %s
               ORDER BY created_at DESC, id DESC''',
            (session['user_id'],)
        )

        transactions = cur.fetchall()

    finally:
        cur.close()
        cnx.close()

    return render_template('transactions.html', transactions=transactions)


if __name__ == "__main__":
    app.run()