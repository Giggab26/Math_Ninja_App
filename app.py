import os
import random
import logging
from flask import Flask, render_template, request, session, redirect, url_for
from flask_mail import Mail, Message
from functools import wraps
from dotenv import load_dotenv

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default-secret')

# Configure Flask-Mail for SendGrid
app.config['MAIL_SERVER'] = 'smtp.sendgrid.net'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'apikey'  # This is literal for SendGrid
app.config['MAIL_PASSWORD'] = os.getenv('SENDGRID_API_KEY')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

mail = Mail(app)

# Simple in-memory user store (replace with a database for production)
users = {}

# Decorator to protect routes that need login
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# Signup route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        if username in users:
            return render_template('signup.html', error="Username already exists")
        users[username] = password
        session['username'] = username

        # Send email notification on new signup
        try:
            msg = Message(
                subject=f"🧠 New Signup: {username}",
                recipients=["jumamaxwell185@gmail.com"],
                body=f"User '{username}' just signed up."
            )
            mail.send(msg)
            app.logger.debug(f"Signup email sent for user {username}")
        except Exception as e:
            app.logger.error(f"Failed to send signup email: {e}")

        return redirect(url_for('index'))
    return render_template('signup.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        if users.get(username) == password:
            session['username'] = username

            # Send email notification on login
            try:
                msg = Message(
                    subject=f"🚀 User Login: {username}",
                    recipients=["jumamaxwell185@gmail.com"],
                    body=f"User '{username}' just logged in."
                )
                mail.send(msg)
                app.logger.debug(f"Login email sent for user {username}")
            except Exception as e:
                app.logger.error(f"Failed to send login email: {e}")

            return redirect(url_for('index'))
        return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

# Logout route
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# Generate random math question
def generate_math_question():
    a = random.randint(1, 20)
    b = random.randint(1, 20)
    operator = random.choice(['+', '-', '*'])
    answer = eval(f"{a} {operator} {b}")
    question_text = f"What is {a} {operator} {b}?"
    return question_text, str(answer)

# Homepage - show question (login required)
@app.route('/')
@login_required
def index():
    question, answer = generate_math_question()
    session['question'] = question
    session['answer'] = answer
    return render_template('math.html', question=question)

# Handle quiz answer submission
@app.route('/submit', methods=['POST'])
@login_required
def submit():
    user_answer = request.form.get('answer', '').strip()
    correct_answer = session.get('answer', '')
    question = session.get('question', 'No question')
    is_correct = user_answer == correct_answer
    return render_template('math.html', is_correct=is_correct, question=question)

if __name__ == '__main__':
    app.run(debug=True)
