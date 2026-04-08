from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import sqlite3
import uuid
import io
import csv
import numpy as np
import pandas as pd
from datetime import datetime
import re

app = FastAPI(title="Ultimate Expense Analytics API", description="Enterprise-grade analytics backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = "db.sqlite3"

# Hardcoded budgets for demonstration (Proactive Analytics)
BUDGETS = {
    "Dining": 3000,
    "Groceries": 15000,
    "Utilities": 5000,
    "Entertainment": 4000,
    "Transportation": 7000,
    "Travel": 10000,
    "Rent": 20000,
    "Healthcare": 3000,
    "Shopping": 8000,
    "Miscellaneous": 5000
}

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def filter_clause(start_date: str, end_date: str):
    if start_date and end_date:
        return " WHERE date >= ? AND date <= ?", (start_date, end_date)
    return "", ()

def filter_clause_and(start_date: str, end_date: str):
    if start_date and end_date:
        return " AND date >= ? AND date <= ?", (start_date, end_date)
    return "", ()

# ----------------------------------------------------
# 1. TEMPORAL & SUMMARY ENDPOINTS
# ----------------------------------------------------
@app.get("/api/months")
def get_available_months():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT substr(date, 1, 7) as month FROM expenses ORDER BY month DESC")
    rows = cursor.fetchall()
    conn.close()
    return [row["month"] for row in rows]

@app.get("/api/summary")
def get_summary(start_date: str = None, end_date: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    where, params = filter_clause(start_date, end_date)
    cursor.execute(f"SELECT COUNT(*) as total_transactions, SUM(amount) as total_expenses FROM expenses {where}", params)
    row = cursor.fetchone()
    conn.close()
    return {
        "total_transactions": row["total_transactions"] or 0, 
        "total_expenses": row["total_expenses"] or 0
    }

@app.get("/api/expenses/category")
def get_category_expenses(start_date: str = None, end_date: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    where, params = filter_clause(start_date, end_date)
    cursor.execute(f"SELECT category, SUM(amount) as total FROM expenses {where} GROUP BY category ORDER BY total DESC", params)
    rows = cursor.fetchall()
    conn.close()
    return [{"category": row["category"], "total": round(row["total"] or 0, 2)} for row in rows]

@app.get("/api/expenses/trend")
def get_expense_trend(group_by: str = "month"):
    # Allow daily/weekly switching for the trend line, default month over month
    conn = get_db_connection()
    cursor = conn.cursor()
    if group_by == "day":
        cursor.execute("SELECT date as time_val, SUM(amount) as total FROM expenses GROUP BY date ORDER BY date DESC LIMIT 60")
    else:
        cursor.execute("SELECT substr(date, 1, 7) as time_val, SUM(amount) as total FROM expenses GROUP BY time_val ORDER BY time_val ASC")
        
    rows = cursor.fetchall()
    conn.close()
    
    if group_by == "day":
        rows = list(reversed(rows)) # Return chronologically
        
    return [{"time": row["time_val"], "total": round(row["total"], 2)} for row in rows]

# ----------------------------------------------------
# 2. ADVANCED DATA SCIENCE & ML ENDPOINTS
# ----------------------------------------------------
@app.get("/api/prediction")
def get_prediction():
    """Simple Linear Regression to predict next month's spending"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT substr(date, 1, 7) as month, SUM(amount) as total FROM expenses GROUP BY month ORDER BY month ASC")
    rows = cursor.fetchall()
    conn.close()
    
    if len(rows) < 3:
        return {"predicted_next_month": 0, "status": "Not enough data"}
        
    # ML: Linear Regression using numpy (X = month index, Y = total spend)
    y = np.array([row["total"] for row in rows])
    x = np.arange(len(y))
    
    # Fit line: y = mx + c
    coefficient = np.polyfit(x, y, 1)
    poly = np.poly1d(coefficient)
    
    next_month_idx = len(y)
    prediction = poly(next_month_idx)
    
    return {
        "status": "success",
        "predicted_next_month": max(0, round(prediction, 2)),
        "current_month_actual": round(y[-1], 2),
        "trend_slope": round(coefficient[0], 2)
    }

@app.get("/api/health")
def get_financial_health():
    """Calculates a composite 0-100 Health Score"""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Check current month spend vs total theoretical budget
    this_month = datetime.now().strftime("%Y-%m")
    cursor.execute("SELECT SUM(amount) as total FROM expenses WHERE substr(date, 1, 7) = ?", (this_month,))
    spend = cursor.fetchone()["total"] or 0
    conn.close()
    
    max_budget = sum(BUDGETS.values())
    
    # Simple logic: If you spend exactly the budget, score = 50. Less spend = higher score.
    if max_budget == 0: return {"score": 100}
    ratio = spend / max_budget
    score = max(0, min(100, 100 - (ratio * 50)))
    
    # Increase score if spend is historically consistent (low std dev) - Simplified
    
    return {"score": round(score), "message": "Excellent" if score > 80 else "Needs Attention"}

@app.get("/api/budgets")
def get_budget_alerts(start_date: str = None, end_date: str = None):
    """Proactive analytics returning progress against budget (showing 80% alerts)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    # If no date filter, just use current month to make sense of 'monthly budget'
    if not start_date:
        this_month = datetime.now().strftime("%Y-%m")
        where, params = " WHERE substr(date, 1, 7) = ?", (this_month,)
    else:
        where, params = filter_clause(start_date, end_date)
        
    cursor.execute(f"SELECT category, SUM(amount) as total FROM expenses {where} GROUP BY category", params)
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for row in rows:
        cat = row["category"]
        spend = row["total"]
        limit = BUDGETS.get(cat, 5000) # Default if not defined
        percent = (spend / limit) * 100
        
        status = "safe"
        if percent >= 80 and percent < 100: status = "warning"
        elif percent >= 100: status = "danger"
        
        results.append({
            "category": cat,
            "spent": round(spend, 2),
            "limit": limit,
            "percent": min(100, round(percent, 1)), # Cap visual at 100%
            "status": status
        })
    return results

# ----------------------------------------------------
# 3. CRUD & DATA PIPELINE ENDPOINTS
# ----------------------------------------------------
@app.get("/api/transactions")
def get_recent_transactions(limit: int = 50, start_date: str = None, end_date: str = None, category: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM expenses"
    params = []
    
    where_parts = []
    if start_date and end_date:
        where_parts.append("date >= ? AND date <= ?")
        params.extend([start_date, end_date])
    if category:
        where_parts.append("category = ?")
        params.append(category)
        
    if where_parts:
        query += " WHERE " + " AND ".join(where_parts)
        
    query += " ORDER BY date DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

class TransactionCreate(BaseModel):
    amount: float
    merchant: str
    category: str
    date: str = None

@app.post("/api/transactions")
def add_transaction(txn: TransactionCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    txn_id = f"TXN-M-{str(uuid.uuid4())[:8].upper()}"
    txn_date = txn.date if txn.date else datetime.now().strftime("%Y-%m-%d")
    cursor.execute("INSERT INTO expenses (transaction_id, date, amount, merchant, category, description, status) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                  (txn_id, txn_date, txn.amount, txn.merchant, txn.category, "Manual", "Completed"))
    conn.commit()
    conn.close()
    return {"status": "success", "transaction_id": txn_id}

@app.delete("/api/transactions/{transaction_id}")
def delete_transaction(transaction_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses WHERE transaction_id = ?", (transaction_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/upload")
async def bulk_upload(file: UploadFile = File(...)):
    """Accepts CSV bulk statement, cleans using Pandas, inserts to SQLite"""
    content = await file.read()
    # Simulate ETL processing via Pandas
    df = pd.read_csv(io.StringIO(content.decode("utf-8")))
    
    # Assuming CSV has 'date', 'amount', 'merchant', 'category'
    if 'transaction_id' not in df.columns:
        df['transaction_id'] = [f"TXN-U-{str(uuid.uuid4())[:8].upper()}" for _ in range(len(df))]
    if 'status' not in df.columns:
        df['status'] = 'Completed'
    if 'description' not in df.columns:
        df['description'] = 'Bulk Upload'
        
    conn = sqlite3.connect(DB_FILE)
    df.to_sql("expenses", conn, if_exists="append", index=False)
    conn.close()
    
    return {"status": "success", "rows_inserted": len(df)}

@app.get("/api/export")
def export_transactions():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM expenses ORDER BY date DESC LIMIT 5000")
    rows = cursor.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["transaction_id", "date", "amount", "merchant", "category", "description", "status"])
    for row in rows:
        writer.writerow([row["transaction_id"], row["date"], row["amount"], row["merchant"], row["category"], row["description"], row["status"]])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=cleaned_expenses.csv"})

# ----------------------------------------------------
# 4. STATIC FRONTEND MOUNT
# ----------------------------------------------------
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
