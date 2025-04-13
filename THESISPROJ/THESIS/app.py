from flask import Flask, render_template, request, redirect, url_for, flash
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import mysql.connector
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # change this later

# Initialize extensions
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Connect to MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="qweqwe", 
    database="learning_game"
)
cursor = db.cursor(dictionary=True)

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

# Load user from DB
@login_manager.user_loader
def load_user(user_id):
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    if user:
        return User(user['id'], user['username'], user['password'])
    return None

# Routes

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user and bcrypt.check_password_hash(user['password'], password):
            login_user(User(user['id'], user['username'], user['password']))
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            flash('Username already exists.', 'danger')
            return redirect(url_for('register'))

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_pw))
        db.commit()
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', username=current_user.username)


@app.route('/roadmap')
@login_required
def roadmap():
    return render_template('roadmap.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/game')
@login_required
def game():
    # Get current difficulty
    cursor.execute("SELECT current_difficulty FROM user_progress WHERE user_id = %s", (current_user.id,))
    row = cursor.fetchone()

    # If new player, add to progress
    if not row:
        cursor.execute("INSERT INTO user_progress (user_id) VALUES (%s)", (current_user.id,))
        db.commit()
        difficulty = 'easy'
    else:
        difficulty = row['current_difficulty']

    # Fetch a random question from that difficulty
    cursor.execute("SELECT * FROM questions WHERE difficulty = %s", (difficulty,))
    questions = cursor.fetchall()
    question = random.choice(questions) if questions else None

    return render_template('game.html', question=question)

@app.route('/submit-answer', methods=['POST'])
@login_required
def submit_answer():
    user_answer = request.form['answer']
    question_id = request.form['question_id']

    # Get the correct answer from DB
    cursor.execute("SELECT * FROM questions WHERE id = %s", (question_id,))
    question = cursor.fetchone()

    is_correct = user_answer.strip() == question['correct_answer'].strip()

    # Update progress based on answer
    if is_correct:
        cursor.execute("""
            UPDATE user_progress 
            SET correct_answers = correct_answers + 1 
            WHERE user_id = %s
        """, (current_user.id,))
    else:
        cursor.execute("""
            UPDATE user_progress 
            SET wrong_answers = wrong_answers + 1 
            WHERE user_id = %s
        """, (current_user.id,))
    
    # Fetch current stats
    cursor.execute("SELECT correct_answers, wrong_answers FROM user_progress WHERE user_id = %s", (current_user.id,))
    stats = cursor.fetchone()
    total = stats['correct_answers'] + stats['wrong_answers']
    accuracy = stats['correct_answers'] / total if total > 0 else 0

    # Adjust difficulty
    if accuracy >= 0.8:
        new_diff = 'hard'
    elif accuracy >= 0.5:
        new_diff = 'medium'
    else:
        new_diff = 'easy'

    cursor.execute("UPDATE user_progress SET current_difficulty = %s WHERE user_id = %s", (new_diff, current_user.id))
    db.commit()

    return redirect(url_for('game'))




if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
