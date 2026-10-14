# PocketPlan Budgeting App

A beginner-friendly Flask budgeting app with account registration, login, budget settings, expense tracking, and savings goals.

## Features

- User registration and login
- Password hashing with Werkzeug
- Separate budget and expenses for each account
- Set monthly income, spending limit, and savings goal
- Add and delete expenses
- SQLite database created automatically
- CSRF protection for forms
- Responsive dashboard styling

## Run locally

1. Install Python 3.10 or newer.
2. Open this folder in VS Code.
3. Create a virtual environment (recommended):

   ```bash
   python -m venv .venv
   ```

4. Activate it:

   **Windows PowerShell**
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   **Windows Command Prompt**
   ```bat
   .venv\Scripts\activate.bat
   ```

5. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

6. Copy `.env.example` to `.env`, then replace the secret with a long random value. Keep `.env` private and do not commit it.
7. Start the app:

   ```bash
   python app.py
   ```

8. Open http://127.0.0.1:5000 in your browser and create an account.

The SQLite database (`budget.db`) is created automatically when the app starts. It is excluded from Git because it contains account and budget data.

## Before deploying

- Set a strong, unique `FLASK_SECRET_KEY` using your hosting provider's environment-variable settings.
- Turn off Flask debug mode (`debug=False`).
- Use HTTPS and enable secure session cookies.
- Consider database backups, rate limiting, password reset flows, and production hosting configuration.
- This starter app is for learning and local use; review security and deployment needs before using it for real financial data.
