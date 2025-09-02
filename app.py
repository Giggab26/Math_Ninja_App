import random
from flask import Flask, render_template, request, session, redirect, url_for

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Needed for session storage


def generate_math_question():
    a = random.randint(1, 20)
    b = random.randint(1, 20)
    operator = random.choice(['+', '-', '*'])

    if operator == '+':
        answer = a + b
    elif operator == '-':
        answer = a - b
    else:
        answer = a * b

    question_text = f"What is {a} {operator} {b}?"
    return question_text, str(answer)
@app.route('/')
def index():
    question, answer = generate_math_question()
    session['answer'] = answer
    session['question'] = question
    return render_template('math.html', question=question)

@app.route('/submit', methods=['POST'])
def submit():
    user_answer = request.form.get('answer', '').strip()
    correct_answer = session.get('answer', '')
    question = session.get('question', 'Unknown question')  # fallback text
    is_correct = user_answer == correct_answer
    return render_template('math.html', is_correct=is_correct, question=question)


if __name__ == '__main__':
    app.run(debug=True)
