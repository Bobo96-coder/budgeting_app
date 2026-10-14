import os
import sqlite3
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from flask import (
    Flask, flash, g, redirect, render_template, request,
    session, url_for
)
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "budget.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-only-change-this-key")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
# Enable this when deploying behind HTTPS:
# app.config["SESSION_COOKIE_SECURE"] = True

csrf = CSRFProtect(app)


def get_db():
    """Open one SQLite connection for the current request."""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create database tables if they do not exist yet."""
    db = sqlite3.connect(DATABASE)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL COLLATE NOCASE UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS budgets (
            user_id INTEGER PRIMARY KEY,
            monthly_income REAL NOT NULL DEFAULT 0,
            monthly_limit REAL NOT NULL DEFAULT 0,
            savings_goal REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL CHECK (amount > 0),
            category TEXT NOT NULL DEFAULT 'Other',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """)
    db.commit()
    db.close()


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "info")
            return redirect(url_for("login"))
        return view(**kwargs)
    return wrapped_view


@app.route("/")
def home():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if len(username) < 3 or len(username) > 30:
            flash("Username must be between 3 and 30 characters.", "error")
        elif not username.replace("_", "").replace("-", "").isalnum():
            flash("Use only letters, numbers, underscores, or hyphens in your username.", "error")
        elif len(password) < 8:
            flash("Password must be at least 8 characters long.", "error")
        elif password != confirm_password:
            flash("The passwords do not match.", "error")
        else:
            db = get_db()
            try:
                cursor = db.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, generate_password_hash(password))
                )
                user_id = cursor.lastrowid
                db.execute("INSERT INTO budgets (user_id) VALUES (?)", (user_id,))
                db.commit()
                session.clear()
                session["user_id"] = user_id
                session["username"] = username
                flash("Account created. Welcome to your budget dashboard!", "success")
                return redirect(url_for("dashboard"))
            except sqlite3.IntegrityError:
                db.rollback()
                flash("That username is already taken. Please choose another.", "error")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_db().execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Incorrect username or password.", "error")
        else:
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("You are now logged in.", "success")
            return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    user_id = session["user_id"]

    budget = db.execute(
        "SELECT monthly_income, monthly_limit, savings_goal FROM budgets WHERE user_id = ?",
        (user_id,)
    ).fetchone()

    expenses = db.execute(
        """SELECT id, description, amount, category, created_at
           FROM expenses WHERE user_id = ?
           ORDER BY created_at DESC, id DESC""",
        (user_id,)
    ).fetchall()

    total_expenses = sum(float(item["amount"]) for item in expenses)
    remaining_budget = float(budget["monthly_limit"]) - total_expenses
    remaining_income = float(budget["monthly_income"]) - total_expenses

    category_totals = {}
    for item in expenses:
        category_totals[item["category"]] = (
            category_totals.get(item["category"], 0) + float(item["amount"])
        )

    return render_template(
        "dashboard.html",
        budget=budget,
        expenses=expenses,
        total_expenses=total_expenses,
        remaining_budget=remaining_budget,
        remaining_income=remaining_income,
        category_totals=category_totals,
    )


@app.route("/set-budget", methods=["POST"])
@login_required
def set_budget():
    try:
        income = float(request.form.get("monthly_income", ""))
        limit = float(request.form.get("monthly_limit", ""))
        goal = float(request.form.get("savings_goal", "0"))

        if not all(value >= 0 and value < 1_000_000_000 for value in (income, limit, goal)):
            raise ValueError
    except (TypeError, ValueError):
        flash("Enter valid, non-negative amounts.", "error")
        return redirect(url_for("dashboard"))

    db = get_db()
    db.execute(
        """UPDATE budgets
           SET monthly_income = ?, monthly_limit = ?, savings_goal = ?
           WHERE user_id = ?""",
        (income, limit, goal, session["user_id"])
    )
    db.commit()
    flash("Your budget settings have been saved.", "success")
    return redirect(url_for("dashboard"))


@app.route("/add-expense", methods=["POST"])
@login_required
def add_expense():
    description = request.form.get("description", "").strip()
    category = request.form.get("category", "Other").strip()
    try:
        amount = float(request.form.get("amount", ""))
    except (TypeError, ValueError):
        amount = 0

    allowed_categories = {
        "Food", "Transport", "Entertainment", "Bills",
        "Shopping", "Health", "Education", "Other"
    }
    if category not in allowed_categories:
        category = "Other"

    if not description or len(description) > 100:
        flash("Description is required and must be 100 characters or fewer.", "error")
    elif not (0 < amount < 1_000_000_000):
        flash("Enter an expense amount greater than zero.", "error")
    else:
        db = get_db()
        db.execute(
            """INSERT INTO expenses (user_id, description, amount, category)
               VALUES (?, ?, ?, ?)""",
            (session["user_id"], description, amount, category)
        )
        db.commit()
        flash("Expense added.", "success")

    return redirect(url_for("dashboard"))


@app.route("/delete-expense/<int:expense_id>", methods=["POST"])
@login_required
def delete_expense(expense_id):
    db = get_db()
    cursor = db.execute(
        "DELETE FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, session["user_id"])
    )
    db.commit()
    if cursor.rowcount:
        flash("Expense deleted.", "success")
    else:
        flash("Expense not found.", "error")
    return redirect(url_for("dashboard"))


# Create the database tables automatically when the app starts.
init_db()

if __name__ == "__main__":
    # Debug mode is for local development only. Turn it off when deploying.
    app.run(debug=True)
