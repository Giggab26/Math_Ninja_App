import os
import json
import random
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, session, redirect, url_for
from flask_mail import Mail
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# -------------------- Setup --------------------
logging.basicConfig(level=logging.DEBUG)
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default-secret')

# Flask-Mail config (SendGrid)
app.config['MAIL_SERVER'] = 'smtp.sendgrid.net'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'apikey'
app.config['MAIL_PASSWORD'] = os.getenv('SENDGRID_API_KEY')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
mail = Mail(app)

# JSON file to store user data
USER_FILE = 'users.json'
GRADES = [f'grade{i}' for i in range(1, 10)] + ['calculus', 'advanced']

# -------------------- Helper functions --------------------
def load_users():
    if os.path.exists(USER_FILE):
        with open(USER_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(data):
    with open(USER_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def generate_math_question(grade):
    """Generate a question depending on grade"""
    if grade in GRADES[:3]:  # Grade 1-3: basic
        a, b = random.randint(1, 10), random.randint(1, 10)
        operator = random.choice(['+', '-'])
    elif grade in GRADES[3:6]:  # Grade 4-6: medium
        a, b = random.randint(1, 20), random.randint(1, 20)
        operator = random.choice(['+', '-', '*'])
    elif grade in GRADES[6:9]:  # Grade 7-9: division included
        a, b = random.randint(10, 50), random.randint(1, 10)
        operator = random.choice(['+', '-', '*', '/'])
    elif grade == 'calculus':
        a, b = random.randint(1, 10), random.randint(1, 5)
        operator = '^'  # simple power for demo
    else:  # advanced
        a, b = random.randint(10, 50), random.randint(1, 10)
        operator = random.choice(['+', '-', '*', '/'])
    
    if operator == '/':
        answer = round(a / b, 2)
    elif operator == '^':
        answer = a ** b
    else:
        answer = eval(f"{a}{operator}{b}")
    
    question_text = f"What is {a} {operator} {b}?"
    return question_text, str(answer)

# -------------------- Routes --------------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    session.pop('username', None)
    users = load_users()
    
    if request.method == 'POST':
        username = request.form['username'].strip().lower()
        password = request.form['password'].strip()

        if username in users:
            return render_template('signup.html', error="Username already exists")

        # Initialize progress per grade
        progress = {grade: {'correct':0,'attempts':0} for grade in GRADES}

        users[username] = {
            "password": generate_password_hash(password),
            "progress": progress,
            "streak": 0,
            "badges": [],
            "last_login": None
        }
        save_users(users)
        session['username'] = username

        return redirect(url_for('dashboard'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    users = load_users()
    if request.method == 'POST':
        username = request.form['username'].strip().lower()
        password = request.form['password'].strip()

        if username in users and check_password_hash(users[username]['password'], password):
            session['username'] = username

            # Handle streak
            today = datetime.now().date()
            last_login = users[username]['last_login']
            last_date = datetime.strptime(last_login, "%Y-%m-%d").date() if last_login else None

            if last_date:
                if today == last_date + timedelta(days=1):
                    users[username]['streak'] += 1
                elif today > last_date + timedelta(days=1):
                    users[username]['streak'] = 1
            else:
                users[username]['streak'] = 1

            users[username]['last_login'] = today.strftime("%Y-%m-%d")
            save_users(users)
            return redirect(url_for('dashboard'))

        return render_template('login.html', error="Invalid credentials")

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))


@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    users = load_users()
    username = session['username']
    user = users[username]

    # Safe calculation of total correct & attempts
    if isinstance(user['progress'], dict):
        total_correct = sum(v.get('correct',0) if isinstance(v, dict) else v for v in user['progress'].values())
        total_attempts = sum(v.get('attempts',0) if isinstance(v, dict) else 1 for v in user['progress'].values())
    else:
        total_correct = user['progress'].get('correct',0)
        total_attempts = user['progress'].get('attempts',1)

    score = int((total_correct / max(1,total_attempts))*100)
    streak = user.get('streak',0)
    badges = user.get('badges',[])

    return render_template('dashboard.html', username=username, score=score, streak=streak, badges=badges)


@app.route('/choose_quiz', methods=['GET','POST'])
@login_required
def choose_quiz():
    if request.method == 'POST':
        grade = request.form['grade']
        session['grade'] = grade
        # Generate 50 questions for this grade
        questions = [generate_math_question(grade) for _ in range(50)]
        session['questions'] = questions
        session['current_q'] = 0
        session['score'] = 0
        return redirect(url_for('quiz'))
    return render_template('choose_grade.html')


@app.route('/quiz', methods=['GET'])
@login_required
def quiz():
    questions = session.get('questions')
    current_index = session.get('current_q', 0)

    if not questions or current_index >= len(questions):
        # Quiz finished
        final_score = session.get('score', 0)
        grade = session.get('grade', 'unknown')

        # Update user progress
        users = load_users()
        username = session['username']
        user = users[username]
        progress = user['progress'].get(grade, {'correct':0,'attempts':0})
        progress['correct'] += final_score
        progress['attempts'] += len(questions) if questions else 0
        user['progress'][grade] = progress
        save_users(users)

        # Clear session quiz data
        session.pop('questions', None)
        session.pop('current_q', None)
        session.pop('score', None)
        session.pop('grade', None)

        return render_template('quiz_results.html', score=final_score)

    question, answer = questions[current_index]
    session['question'] = question
    session['answer'] = answer
    return render_template('quiz.html', question=question, q_number=current_index+1, total=len(questions))


@app.route('/submit', methods=['POST'])
@login_required
def submit():
    users = load_users()
    username = session['username']
    user = users[username]

    user_answer = request.form.get('answer','').strip()
    correct_answer = session.get('answer','')
    question = session.get('question','No question')

    # Update score in session
    if user_answer == correct_answer:
        session['score'] = session.get('score',0) + 1
        # Optional: add badge per 5 correct answers
        grade = session.get('grade')
        if grade:
            progress = user['progress'].get(grade, {'correct':0,'attempts':0})
            if (progress['correct'] + session['score']) % 5 == 0:
                user['badges'].append(f"{grade} Badge #{len(user['badges'])+1}")
    
    # Move to next question
    session['current_q'] = session.get('current_q',0) + 1

    return redirect(url_for('quiz'))


@app.route('/progress')
@login_required
def show_progress():
    users = load_users()
    username = session['username']
    progress = users[username]['progress']
    total_correct = sum(v.get('correct',0) if isinstance(v, dict) else v for v in progress.values())
    total_attempts = sum(v.get('attempts',0) if isinstance(v, dict) else 1 for v in progress.values())
    score = int((total_correct / max(1,total_attempts))*100)
    return render_template('progress.html', username=username, progress=progress, score=score)


@app.route('/faq')
def faq():
    return render_template('faq.html')

# -------------------- Test Email Route --------------------
@app.route('/test-email')
@login_required
def test_email():
    from flask_mail import Message
    try:
        msg = Message(
            subject="Test Email from NumberNinja",
            recipients=[os.getenv('MAIL_DEFAULT_SENDER')],  # your email
            body="✅ This is a test email from your Flask app!"
        )
        mail.send(msg)
        return "✅ Test email sent successfully! Check your inbox."
    except Exception as e:
        return f"❌ Error sending email: {e}"



if __name__ == '__main__':
    port = int(os.getenv('PORT',5000))
    app.run(host='0.0.0.0', port=port, debug=True)
