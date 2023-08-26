from flask import Flask, render_template, request, redirect, url_for, flash
import os
import sqlite3
from datetime import datetime
from werkzeug.utils import secure_filename
from pydub import AudioSegment

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = 'your_secret_key'

# Create SQLite database
db_path = 'user_db.sqlite'
conn = sqlite3.connect(db_path)
conn.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                password TEXT NOT NULL
            )''')
conn.execute('''CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                upload_date TEXT NOT NULL,
                duration INTEGER NOT NULL,
                size INTEGER NOT NULL,
                extension TEXT NOT NULL
            )''')
conn.close()

def get_user_id(username):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username=?", (username,))
    user_id = cursor.fetchone()
    conn.close()
    return user_id[0] if user_id else None

def get_password(username):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE username=?", (username,))
    user_id = cursor.fetchone()
    conn.close()
    return user_id[0] if user_id else None


def calculate_total_duration(user_id):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(duration) FROM uploads WHERE user_id=?", (user_id,))
    total_duration = cursor.fetchone()[0] or 0
    conn.close()
    return total_duration

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user_id = get_user_id(username)
        password_check = get_password(username)

        if user_id is not None:
            if password == password_check:
                return redirect(url_for('dashboard', user_id=user_id))
            else:
                flash('Incorrect Password. Please try again.', 'error')
        else:
            flash('Invalid credentials. Please try again.', 'error')

        

    return render_template('login.html')

@app.route('/dashboard/<int:user_id>', methods=['GET', 'POST'])
def dashboard(user_id):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE id=?", (user_id,))
    username = cursor.fetchone()[0]
    
    if request.method == 'POST':
        uploaded_files = request.files.getlist('file')
        total_duration = calculate_total_duration(user_id)
        warning = ''

        for file in uploaded_files:
            if file.filename == '':
                continue

            filename = secure_filename(file.filename)
            upload_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            extension = os.path.splitext(filename)[1]
            
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            audio = AudioSegment.from_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            duration = len(audio) // 1000  # duration in seconds
            size = os.path.getsize(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            if total_duration + duration > 600:
                warning = 'Total duration exceeds 10 minutes'
            else:
                cursor.execute("INSERT INTO uploads (user_id, filename, upload_date, duration, size, extension) VALUES (?, ?, ?, ?, ?, ?)",
                               (user_id, filename, upload_date, duration, size, extension))
                conn.commit()
                total_duration += duration

        if warning:
            flash(warning, 'warning')
        else:
            flash('Files uploaded successfully!', 'success')

    cursor.execute("SELECT filename, upload_date, duration, size, extension FROM uploads WHERE user_id=?", (user_id,))
    uploads = cursor.fetchall()
    conn.close()
    
    return render_template('dashboard.html', username=username, uploads=uploads)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

if __name__ == '__main__':
    app.run(debug=True)