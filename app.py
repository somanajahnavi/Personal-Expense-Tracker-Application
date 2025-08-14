from flask import Flask, render_template, request, redirect, session, flash, url_for
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv

app = Flask(__name__)
app.secret_key = os.urandom(24)

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # Create users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    # Create transactions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            type TEXT NOT NULL,
            date TEXT NOT NULL,
            note TEXT,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# -- INDEX --
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT * FROM transactions WHERE user_id=? ORDER BY date DESC", (user_id,))
    transactions = c.fetchall()

    c.execute("SELECT SUM(amount) FROM transactions WHERE type='income' AND user_id=?", (user_id,))
    income = c.fetchone()[0] or 0

    c.execute("SELECT SUM(amount) FROM transactions WHERE type='expense' AND user_id=?", (user_id,))
    expense = c.fetchone()[0] or 0

    balance = income - expense

    conn.close()

    return render_template('index.html', transactions=transactions, balance=balance, income=income, expense=expense)

# -- ADD --
@app.route('/add', methods=['GET', 'POST'])
def add_transaction():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        amount = float(request.form['amount'])
        category = request.form['category']
        type_ = request.form['type']
        date = request.form['date']
        note = request.form['note']
        user_id = session['user_id']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO transactions (amount, category, type, date, note, user_id) VALUES (?, ?, ?, ?, ?, ?)",
                  (amount, category, type_, date, note, user_id))
        conn.commit()
        conn.close()
        return redirect('/')
    
    return render_template('add.html')

# -- HISTORY --
@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM transactions WHERE user_id=? ORDER BY date DESC", (user_id,))
    transactions = c.fetchall()
    conn.close()
    
    return render_template('history.html', transactions=transactions)

# -- REGISTER --
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            flash("Registration successful! Please log in.")
            return redirect('/login')
        except sqlite3.IntegrityError:
            flash("Username already exists.")
        finally:
            conn.close()
    
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT id, password FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['username'] = username
            return redirect('/')
        else:
            flash("Invalid login credentials.")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# -- DELETE --
@app.route('/delete/<int:id>')
def delete_transaction(id):
    if 'user_id' not in session:
        return redirect('/login')
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", (id, session['user_id']))
    conn.commit()
    conn.close()
    flash("Transaction deleted successfully")
    return redirect('/history')

# -- EDIT --
@app.route('/edit/<int:id>', methods = ['GET', 'POST'])
def edit_transaction(id):
    if 'user_id' not in session:
        flash("You must login in to edit transctions.")
        return redirect('/login')
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    if request.method == 'POST':
        amount = float(request.form['amount'])
        category = request.form['category']
        type_ = request.form['type']
        date = request.form['date']
        note = request.form['note']
        
        c.execute('''
                  UPDATE transactions
                  SET amount = ?, category = ?, type = ?, date = ?, note = ?
                  WHERE id = ? AND user_id = ?'''
                  , (amount, category, type_, date, note, id, session['user_id']))
        conn.commit()
        conn.close()
        flash('Transaction updated Successfully!')
        return redirect('/history')
    
    # GET request - fetch current data
    c.execute('SELECT * FROM transactions WHERE id = ? AND user_id = ?', (id, session['user_id']))
    transaction = c.fetchone()
    conn.close()
    
    if transaction:
        return render_template('edit.html', transaction= transaction)
    else:
        flash('Transaction not found.')
        return redirect('/history')

# =========================
# Run App
# =========================

if __name__ == '__main__':
    app.run(debug=True)
