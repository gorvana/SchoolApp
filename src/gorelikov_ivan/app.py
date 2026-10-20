from flask import Flask, render_template, request, jsonify
import bcrypt
import mysql.connector

app = Flask(__name__)  s

def connection():
    cnx = mysql.connector.connect(
            host="185.114.247.43",
            port=3306,
            database="sch688_vvedenie",
            user="sch688_vvedenie",
            password="Qwerty123")
    return cnx

@app.route('/user_register', methods=['POST'])
def user_register():
    req = request.get_json()
    cnx = connection()
    
    name = req['name']
    login = req['email']
    password = req['password']

    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()               
    hashed = bcrypt.hashpw(password_bytes, salt)

    date = (name, login, hashed.decode("utf-8"))
    cur = cnx.cursor()
    try:
        rows = cur.execute('INSERT INTO `users`(`username`, `email`, `password_hash`) VALUES (%s, %s, %s)', date)
    except:
        return {'result': False}
    cnx.commit()
    cnx.close()

    return {'result': True}

# # Fetch one result
# row = cur.fetchone()
# print("Current date is: {0}".format(row[0]))

# # Close connection
# cnx.close()

@app.route("/user_login", methods=['POST'])
def user_login():
    login = request.form.get('username', '').strip()
    password = request.form.get('password_hash', '')

    cnx = connection()

    try:
        cur = cnx.cursor()
        cur.execute('SELECT * FROM users WHERE email=%s AND password_hash=%s', (login,))

        users = cur.fetchone()

        if user in None:
            return "Неверный логин или пароль", 401

        password_bytes = password.encode("utf-8")
        stored_hash = user[2].encode("utf-8")

        if bcrypt.checkpw(password_bytes, stored_hash):
            return "Авторизаця успешна"
        return "Неверный логин или пароль", 401

    finally:
        cnx.close()

@app.route("/")
def registration():
    return render_template('registration.html')

@app.route("/login")
def login():
    return render_template('login.html')
app.run()