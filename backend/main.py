from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import sqlite3

app = FastAPI(title="Expense Analytics API", description="API for the End-to-End Expense Analytics Dashboard")

# Enable CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = "db.sqlite3"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/api/summary")
def get_summary():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total_transactions, SUM(amount) as total_expenses FROM expenses")
    row = cursor.fetchone()
    conn.close()
    return {"total_transactions": row["total_transactions"], "total_expenses": row["total_expenses"]}

@app.get("/api/expenses/category")
def get_category_expenses():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT category, SUM(amount) as total FROM expenses GROUP BY category ORDER BY total DESC")
    rows = cursor.fetchall()
    conn.close()
    return [{"category": row["category"], "total": round(row["total"], 2)} for row in rows]

@app.get("/api/expenses/trend")
def get_expense_trend():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT substr(date, 1, 7) as month, SUM(amount) as total FROM expenses GROUP BY month ORDER BY month")
    rows = cursor.fetchall()
    conn.close()
    return [{"month": row["month"], "total": round(row["total"], 2)} for row in rows]

@app.get("/api/transactions")
def get_recent_transactions(limit: int = 50):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM expenses ORDER BY date DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# Mount the static frontend
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

