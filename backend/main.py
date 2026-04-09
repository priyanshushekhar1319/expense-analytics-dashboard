from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
import sqlite3
import uuid
import io
import csv
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import bcrypt
import jwt

app = FastAPI(title="Ultimate Expense Analytics API", description="Enterprise-grade SaaS backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = "db.sqlite3"
SECRET_KEY = "super-secret-saas-key-that-should-be-in-env"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 24 * 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")

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

# ----------------------------------------------------
# AUTHENTICATION & MULTI-TENANCY
# ----------------------------------------------------
class UserInit(BaseModel):
    username: str
    password: str
    full_name: str = None

class UserResponse(BaseModel):
    id: int
    username: str
    role: str

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
        
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if user is None:
        raise credentials_exception
    return UserResponse(id=user["id"], username=user["username"], role=user["role"])

def check_admin(current_user: UserResponse = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized. Admins only.")
    return current_user

@app.post("/api/register")
def register_user(user: UserInit):
    conn = get_db_connection()
    existing = conn.execute("SELECT id FROM users WHERE username = ?", (user.username,)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already registered")
        
    salt = bcrypt.gensalt()
    hashed_pw = bcrypt.hashpw(user.password.encode('utf-8'), salt).decode('utf-8')
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    conn.execute("INSERT INTO users (username, password_hash, role, created_at, full_name) VALUES (?, ?, ?, ?, ?)",
                 (user.username, hashed_pw, "user", now, user.full_name))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "User created successfully"}

@app.post("/api/login")
def login_user(user: UserInit):
    conn = get_db_connection()
    db_user = conn.execute("SELECT * FROM users WHERE username = ?", (user.username,)).fetchone()
    conn.close()
    
    if not db_user or not bcrypt.checkpw(user.password.encode('utf-8'), db_user["password_hash"].encode('utf-8')):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.utcnow() + access_token_expires
    to_encode = {"sub": db_user["username"], "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return {"access_token": encoded_jwt, "token_type": "bearer", "role": db_user["role"]}

@app.get("/api/me")
def get_me(current_user: UserResponse = Depends(get_current_user)):
    return current_user

# ----------------------------------------------------
# ADMIN CONSOLE ENDPOINTS
# ----------------------------------------------------
@app.get("/api/admin/stats")
def get_admin_stats(admin: UserResponse = Depends(check_admin)):
    conn = get_db_connection()
    total_users = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    total_txns = conn.execute("SELECT COUNT(*) as c FROM expenses").fetchone()["c"]
    
    users = conn.execute("""
        SELECT u.id, u.username, u.role, u.created_at, COUNT(e.id) as txn_count, SUM(e.amount) as total_spend
        FROM users u LEFT JOIN expenses e ON u.id = e.user_id
        GROUP BY u.id ORDER BY u.created_at DESC
    """).fetchall()
    conn.close()
    
    return {
        "status": "success",
        "aggregate": {"total_users": total_users, "total_transactions": total_txns},
        "users": [dict(u) for u in users]
    }

# ----------------------------------------------------
# SECURED HELPER FUNCTIONS
# ----------------------------------------------------
def filter_clause(start_date: str, end_date: str, user_id: int):
    base = " WHERE user_id = ?"
    params = [user_id]
    if start_date and end_date:
        base += " AND date >= ? AND date <= ?"
        params.extend([start_date, end_date])
    return base, tuple(params)

# ----------------------------------------------------
# 1. TEMPORAL & SUMMARY ENDPOINTS
# ----------------------------------------------------
@app.get("/api/months")
def get_available_months(current_user: UserResponse = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT substr(date, 1, 7) as month FROM expenses WHERE user_id = ? ORDER BY month DESC", (current_user.id,))
    rows = cursor.fetchall()
    conn.close()
    return [row["month"] for row in rows]

@app.get("/api/summary")
def get_summary(start_date: str = None, end_date: str = None, current_user: UserResponse = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    where, params = filter_clause(start_date, end_date, current_user.id)
    cursor.execute(f"SELECT COUNT(*) as total_transactions, SUM(amount) as total_expenses FROM expenses {where}", params)
    row = cursor.fetchone()
    conn.close()
    return {
        "total_transactions": row["total_transactions"] or 0, 
        "total_expenses": row["total_expenses"] or 0
    }

@app.get("/api/expenses/category")
def get_category_expenses(start_date: str = None, end_date: str = None, current_user: UserResponse = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    where, params = filter_clause(start_date, end_date, current_user.id)
    cursor.execute(f"SELECT category, SUM(amount) as total FROM expenses {where} GROUP BY category ORDER BY total DESC", params)
    rows = cursor.fetchall()
    conn.close()
    return [{"category": row["category"], "total": round(row["total"] or 0, 2)} for row in rows]

@app.get("/api/expenses/trend")
def get_expense_trend(group_by: str = "month", current_user: UserResponse = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    if group_by == "day":
        cursor.execute("SELECT date as time_val, SUM(amount) as total FROM expenses WHERE user_id = ? GROUP BY date ORDER BY date DESC LIMIT 60", (current_user.id,))
    else:
        cursor.execute("SELECT substr(date, 1, 7) as time_val, SUM(amount) as total FROM expenses WHERE user_id = ? GROUP BY time_val ORDER BY time_val ASC", (current_user.id,))
        
    rows = cursor.fetchall()
    conn.close()
    
    if group_by == "day":
        rows = list(reversed(rows))
        
    return [{"time": row["time_val"], "total": round(row["total"] or 0, 2)} for row in rows]

# ----------------------------------------------------
# 2. ADVANCED DATA SCIENCE & ML ENDPOINTS
# ----------------------------------------------------
@app.get("/api/prediction")
def get_prediction(current_user: UserResponse = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT substr(date, 1, 7) as month, SUM(amount) as total FROM expenses WHERE user_id = ? GROUP BY month ORDER BY month ASC", (current_user.id,))
    rows = cursor.fetchall()
    conn.close()
    
    if len(rows) < 3:
        return {"predicted_next_month": 0, "status": "Not enough data"}
        
    y = np.array([row["total"] for row in rows])
    x = np.arange(len(y))
    
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
def get_financial_health(current_user: UserResponse = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    this_month = datetime.now().strftime("%Y-%m")
    cursor.execute("SELECT SUM(amount) as total FROM expenses WHERE user_id = ? AND substr(date, 1, 7) = ?", (current_user.id, this_month))
    spend = cursor.fetchone()["total"] or 0
    conn.close()
    
    max_budget = sum(BUDGETS.values())
    if max_budget == 0: return {"score": 100}
    ratio = spend / max_budget
    score = max(0, min(100, 100 - (ratio * 50)))
    
    return {"score": round(score), "message": "Excellent" if score > 80 else "Needs Attention"}

@app.get("/api/budgets")
def get_budget_alerts(start_date: str = None, end_date: str = None, current_user: UserResponse = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    if not start_date:
        this_month = datetime.now().strftime("%Y-%m")
        where, params = " WHERE user_id = ? AND substr(date, 1, 7) = ?", (current_user.id, this_month)
    else:
        where, params = filter_clause(start_date, end_date, current_user.id)
        
    cursor.execute(f"SELECT category, SUM(amount) as total FROM expenses {where} GROUP BY category", params)
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for row in rows:
        cat = row["category"]
        spend = row["total"] or 0
        limit = BUDGETS.get(cat, 5000)
        percent = (spend / limit) * 100
        
        status = "safe"
        if percent >= 80 and percent < 100: status = "warning"
        elif percent >= 100: status = "danger"
        
        results.append({
            "category": cat,
            "spent": round(spend, 2),
            "limit": limit,
            "percent": min(100, round(percent, 1)),
            "status": status
        })
    return results

class ChatMessage(BaseModel):
    message: str

@app.post("/api/chat")
def ai_chat(msg: ChatMessage, current_user: UserResponse = Depends(get_current_user)):
    text = msg.message.lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    uid = current_user.id
    
    categories = [k.lower() for k in BUDGETS.keys()]
    mentioned_cats = [c for c in categories if c in text]
    
    scores = {
        "highest": sum(1 for w in ["zyada", "highest", "most", "max", "top", "bada"] if w in text),
        "lowest": sum(1 for w in ["kam", "lowest", "least", "min", "bottom", "chota"] if w in text),
        "total": sum(1 for w in ["total", "kitna", "pura", "all amount", "overall"] if w in text),
        "avg": sum(1 for w in ["average", "avg", "per month"] if w in text),
        "save": sum(1 for w in ["bachaa", "save", "reduce", "cut", "bachat"] if w in text),
        "predict": sum(1 for w in ["predict", "agla", "next", "future", "kal"] if w in text)
    }
    top_intent = max(scores, key=scores.get)
    max_score = scores[top_intent]
    
    response = ""
    
    if max_score == 0 and len(mentioned_cats) == 0:
        response = "Helo ji! Aap apne 'total kharcha', 'sabse zyada spend', ya categories (Rent, Food) ke baray me pooch sakte hain."
    
    elif len(mentioned_cats) > 0 and max_score == 0:
        c = mentioned_cats[0]
        cursor.execute("SELECT SUM(amount) as t FROM expenses WHERE user_id=? AND lower(category) = ?", (uid, c,))
        res = cursor.fetchone()
        t = res["t"] or 0
        response = f"Aapne '{c.title()}' pe total ₹{t:,.2f} spend kiya hai. Iska limit ₹{BUDGETS[c.title()]:,.2f} hai."

    elif top_intent == "highest":
        cursor.execute("SELECT category, SUM(amount) as t FROM expenses WHERE user_id=? GROUP BY category ORDER BY t DESC LIMIT 1", (uid,))
        res = cursor.fetchone()
        if res: response = f"Aapne sabse zyada '{res['category']}' pe spend kiya hai (Total: ₹{res['t']:,.2f})."
        else: response = "Abhi koi transactions nahi mile."
        
    elif top_intent == "lowest":
        cursor.execute("SELECT category, SUM(amount) as t FROM expenses WHERE user_id=? GROUP BY category ORDER BY t ASC LIMIT 1", (uid,))
        res = cursor.fetchone()
        if res: response = f"Aapka sabse kam kharch '{res['category']}' category me hua hai (₹{res['t']:,.2f})."
        else: response = "Data nahi mila."

    elif top_intent == "total":
        cursor.execute("SELECT SUM(amount) as t FROM expenses WHERE user_id=?", (uid,))
        res = cursor.fetchone()
        t = res["t"] or 0
        response = f"Aapka overall Recorded Spend abhi tak ₹{t:,.2f} hai."

    elif top_intent == "avg":
        cursor.execute("SELECT SUM(amount) / COUNT(DISTINCT substr(date, 1, 7)) as avg_spend FROM expenses WHERE user_id=?", (uid,))
        res = cursor.fetchone()
        a = res["avg_spend"] or 0
        response = f"Aapka Average Monthly expense lagbhag ₹{a:,.2f} aata hai."

    elif top_intent == "save":
        cursor.execute("SELECT category, SUM(amount) as t FROM expenses WHERE user_id=? GROUP BY category ORDER BY t DESC LIMIT 1", (uid,))
        res = cursor.fetchone()
        if res: response = f"Agar aap apne top expense '{res['category']}' pe 15% bachat karein, toh monthly ₹{res['t']*0.15:,.2f} bach jayenge."
        else: response = "Sufficient data nahi hai suggestions dene ke liye."

    elif top_intent == "predict":
        response = "Aapka data Linear Regression se analyze ho raha hai prediction box mein. Aap waise normally budget me chal rahe hain."

    conn.close()
    return {"reply": response}

# ----------------------------------------------------
# 3. CRUD & DATA PIPELINE ENDPOINTS
# ----------------------------------------------------
@app.get("/api/transactions")
def get_recent_transactions(limit: int = 50, start_date: str = None, end_date: str = None, category: str = None, current_user: UserResponse = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM expenses WHERE user_id = ?"
    params = [current_user.id]
    
    if start_date and end_date:
        query += " AND date >= ? AND date <= ?"
        params.extend([start_date, end_date])
    if category:
        query += " AND category = ?"
        params.append(category)
        
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
def add_transaction(txn: TransactionCreate, current_user: UserResponse = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    txn_id = f"TXN-M-{str(uuid.uuid4())[:8].upper()}"
    txn_date = txn.date if txn.date else datetime.now().strftime("%Y-%m-%d")
    cursor.execute("INSERT INTO expenses (user_id, transaction_id, date, amount, merchant, category, description, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                  (current_user.id, txn_id, txn_date, txn.amount, txn.merchant, txn.category, "Manual", "Completed"))
    conn.commit()
    conn.close()
    return {"status": "success", "transaction_id": txn_id}

@app.delete("/api/transactions/{transaction_id}")
def delete_transaction(transaction_id: str, current_user: UserResponse = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses WHERE transaction_id = ? AND user_id = ?", (transaction_id, current_user.id))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/upload")
async def bulk_upload(file: UploadFile = File(...), current_user: UserResponse = Depends(get_current_user)):
    content = await file.read()
    df = pd.read_csv(io.StringIO(content.decode("utf-8")))
    
    if 'transaction_id' not in df.columns:
        df['transaction_id'] = [f"TXN-U-{str(uuid.uuid4())[:8].upper()}" for _ in range(len(df))]
    if 'status' not in df.columns:
        df['status'] = 'Completed'
    if 'description' not in df.columns:
        df['description'] = 'Bulk Upload'
        
    df['user_id'] = current_user.id
        
    conn = sqlite3.connect(DB_FILE)
    df.to_sql("expenses", conn, if_exists="append", index=False)
    conn.close()
    
    return {"status": "success", "rows_inserted": len(df)}

@app.get("/api/export")
def export_transactions(current_user: UserResponse = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM expenses WHERE user_id = ? ORDER BY date DESC LIMIT 5000", (current_user.id,))
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
