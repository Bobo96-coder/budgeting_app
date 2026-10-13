from flask import Flask, render_template, request, redirect, url_for
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# Create the Flask application
app = Flask(__name__)

# Secret key for session management
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-key-change-later")


# Temporary example data
# We will replace this with a database later.

budget = {
    "monthly_income": 0.00,
    "monthly_limit": 0.00,
    "expenses": [],
    "savings_goal": 0.00
}


# Home page / dashboard
@app.route("/")
def index():
    total_expenses = sum(
        expense["amount"] for expense in budget["expenses"]
    )

    remaining_budget = budget["monthly_limit"] - total_expenses

    return render_template(
        "index.html",
        budget=budget,
        total_expenses=total_expenses,
        remaining_budget=remaining_budget
    )


# Set monthly income and budget limit
@app.route("/set-budget", methods=["POST"])
def set_budget():
    try:
        budget["monthly_income"] = float(
            request.form.get("monthly_income", 0)
        )
        budget["monthly_limit"] = float(
            request.form.get("monthly_limit", 0)
        )
    except ValueError:
        return "Please enter valid numbers.", 400

    return redirect(url_for("index"))


# Add a new expense
@app.route("/add-expense", methods=["POST"])
def add_expense():
    try:
        description = request.form.get("description", "").strip()
        amount = float(request.form.get("amount", 0))
        category = request.form.get("category", "Other")

        if not description or amount <= 0:
            return "Enter a description and a positive amount.", 400

        budget["expenses"].append({
            "description": description,
            "amount": amount,
            "category": category
        })

    except ValueError:
        return "Please enter a valid expense amount.", 400

    return redirect(url_for("index"))


# View all expenses
@app.route("/expenses")
def expenses():
    return {
        "expenses": budget["expenses"]
    }


# Savings goal
@app.route("/set-savings-goal", methods=["POST"])
def set_savings_goal():
    try:
        goal = float(request.form.get("savings_goal", 0))

        if goal < 0:
            return "Savings goal cannot be negative.", 400

        budget["savings_goal"] = goal

    except ValueError:
        return "Please enter a valid savings goal.", 400

    return redirect(url_for("index"))


# Start the development server
if __name__ == "__main__":
    app.run(debug=True)