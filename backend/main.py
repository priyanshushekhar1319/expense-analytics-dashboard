from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
import uuid
import io
import csv
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import bcrypt
import jwt

# SQLAlchemy imports
from database import get_db, User, Expense

app = FastAPI(title="Ultimate Expense Analytics API", description="Enterprise-grade SaaS backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
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
        
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return UserResponse(id=user.id, username=user.username, role=user.role)

def check_admin(current_user: UserResponse = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized. Admins only.")
    return current_user

@app.post("/api/register")
def register_user(user: UserInit, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered")
        
    salt = bcrypt.gensalt()
    hashed_pw = bcrypt.hashpw(user.password.encode('utf-8'), salt).decode('utf-8')
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    new_user = User(
        username=user.username, 
        password_hash=hashed_pw, 
        role="user", 
        created_at=now, 
        full_name=user.full_name
    )
    db.add(new_user)
    db.commit()
    return {"status": "success", "message": "User created successfully"}

@app.post("/api/login")
def login_user(user: UserInit, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    
    if not db_user or not bcrypt.checkpw(user.password.encode('utf-8'), db_user.password_hash.encode('utf-8')):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.utcnow() + access_token_expires
    to_encode = {"sub": db_user.username, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return {"access_token": encoded_jwt, "token_type": "bearer", "role": db_user.role}

@app.get("/api/me")
def get_me(current_user: UserResponse = Depends(get_current_user)):
    return current_user

# ----------------------------------------------------
# ADMIN CONSOLE ENDPOINTS
# ----------------------------------------------------
@app.get("/api/admin/stats")
def get_admin_stats(admin: UserResponse = Depends(check_admin), db: Session = Depends(get_db)):
    total_users = db.query(User).count()
    total_txns = db.query(Expense).count()
    
    # Left join to get stats per user
    results = db.query(
        User.id, 
        User.username, 
        User.role, 
        User.created_at, 
        func.count(Expense.id).label('txn_count'), 
        func.sum(Expense.amount).label('total_spend')
    ).outerjoin(Expense, User.id == Expense.user_id).group_by(User.id).order_by(User.created_at.desc()).all()
    
    users = []
    for r in results:
        users.append({
            "id": r.id, "username": r.username, "role": r.role, 
            "created_at": r.created_at, "txn_count": r.txn_count, "total_spend": r.total_spend
        })
    
    return {
        "status": "success",
        "aggregate": {"total_users": total_users, "total_transactions": total_txns},
        "users": users
    }

# ----------------------------------------------------
# SECURED HELPER FUNCTIONS
# ----------------------------------------------------
def apply_date_filter(query, start_date: str, end_date: str):
    if start_date and end_date:
        return query.filter(Expense.date >= start_date, Expense.date <= end_date)
    return query

# ----------------------------------------------------
# 1. TEMPORAL & SUMMARY ENDPOINTS
# ----------------------------------------------------
@app.get("/api/months")
def get_available_months(current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    # substr(date, 1, 7) is SQLite specific. To be DB agnostic, we can pull distinct dates and truncate in python
    # For small SaaS, this is fast enough.
    dates = db.query(Expense.date).filter(Expense.user_id == current_user.id).all()
    months = sorted(list(set([d[0][:7] for d in dates if d[0]])), reverse=True)
    return months

@app.get("/api/summary")
def get_summary(start_date: str = None, end_date: str = None, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(func.count(Expense.id), func.sum(Expense.amount)).filter(Expense.user_id == current_user.id)
    query = apply_date_filter(query, start_date, end_date)
    result = query.first()
    
    return {
        "total_transactions": result[0] or 0, 
        "total_expenses": result[1] or 0
    }

@app.get("/api/expenses/category")
def get_category_expenses(start_date: str = None, end_date: str = None, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Expense.category, func.sum(Expense.amount).label('total')).filter(Expense.user_id == current_user.id)
    query = apply_date_filter(query, start_date, end_date)
    results = query.group_by(Expense.category).order_by(func.sum(Expense.amount).desc()).all()
    
    return [{"category": r.category, "total": round(r.total or 0, 2)} for r in results]

@app.get("/api/expenses/trend")
def get_expense_trend(group_by: str = "month", current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    # DB Agnostic Group By Month
    # We fetch all, and group in Python to avoid Postgres vs SQLite substring logic conflicts
    expenses = db.query(Expense.date, Expense.amount).filter(Expense.user_id == current_user.id).all()
    
    grouped = {}
    for d, a in expenses:
        if not d: continue
        key = d if group_by == "day" else d[:7]
        grouped[key] = grouped.get(key, 0) + (a or 0)
        
    sorted_keys = sorted(grouped.keys())
    # If daily, get last 60
    if group_by == "day":
        sorted_keys = sorted_keys[-60:]
        
    return [{"time": k, "total": round(grouped[k], 2)} for k in sorted_keys]

# ----------------------------------------------------
# 2. ADVANCED DATA SCIENCE & ML ENDPOINTS
# ----------------------------------------------------
@app.get("/api/prediction")
def get_prediction(current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    expenses = db.query(Expense.date, Expense.amount).filter(Expense.user_id == current_user.id).all()
    grouped = {}
    for d, a in expenses:
        if not d: continue
        m = d[:7]
        grouped[m] = grouped.get(m, 0) + (a or 0)
        
    sorted_months = sorted(grouped.keys())
    if len(sorted_months) < 3:
        return {"predicted_next_month": 0, "status": "Not enough data"}
        
    y = np.array([grouped[m] for m in sorted_months])
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
def get_financial_health(current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    this_month = datetime.now().strftime("%Y-%m")
    
    # DB agnostic trick: fetch all for the user and sum valid ones
    expenses = db.query(Expense.date, Expense.amount).filter(Expense.user_id == current_user.id).all()
    spend = sum([a for d, a in expenses if d and d.startswith(this_month)])
    
    max_budget = sum(BUDGETS.values())
    if max_budget == 0: return {"score": 100}
    ratio = spend / max_budget
    score = max(0, min(100, 100 - (ratio * 50)))
    
    return {"score": round(score), "message": "Excellent" if score > 80 else "Needs Attention"}

@app.get("/api/budgets")
def get_budget_alerts(start_date: str = None, end_date: str = None, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Expense.category, func.sum(Expense.amount).label('total')).filter(Expense.user_id == current_user.id)
    
    if not start_date:
        this_month = datetime.now().strftime("%Y-%m")
        # For simplicity, we can do python-side filtering or exact query. Let's do exact query using LIKE for DB agnostic
        query = query.filter(Expense.date.like(f"{this_month}%"))
    else:
        query = apply_date_filter(query, start_date, end_date)
        
    results = query.group_by(Expense.category).all()
    
    cat_spent = {r.category: (r.total or 0) for r in results}
    
    response = []
    # Display all budgets, even if 0 spent
    for cat, limit in BUDGETS.items():
        spend = cat_spent.get(cat, 0)
        percent = (spend / limit) * 100
        
        status = "safe"
        if percent >= 80 and percent < 100: status = "warning"
        elif percent >= 100: status = "danger"
        
        response.append({
            "category": cat,
            "spent": round(spend, 2),
            "limit": limit,
            "percent": min(100, round(percent, 1)),
            "status": status
        })
    return response

class ChatMessage(BaseModel):
    message: str

@app.post("/api/chat")
def ai_chat(msg: ChatMessage, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    text = msg.message.lower()
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
        # SQLA case-insensitive match
        t = db.query(func.sum(Expense.amount)).filter(Expense.user_id == uid, func.lower(Expense.category) == c).scalar() or 0
        response = f"Aapne '{c.title()}' pe total ₹{t:,.2f} spend kiya hai. Iska limit ₹{BUDGETS[c.title()]:,.2f} hai."

    elif top_intent == "highest":
        res = db.query(Expense.category, func.sum(Expense.amount).label('t')).filter(Expense.user_id == uid).group_by(Expense.category).order_by(func.sum(Expense.amount).desc()).first()
        if res: response = f"Aapne sabse zyada '{res.category}' pe spend kiya hai (Total: ₹{res.t:,.2f})."
        else: response = "Abhi koi transactions nahi mile."
        
    elif top_intent == "lowest":
        res = db.query(Expense.category, func.sum(Expense.amount).label('t')).filter(Expense.user_id == uid).group_by(Expense.category).order_by(func.sum(Expense.amount).asc()).first()
        if res: response = f"Aapka sabse kam kharch '{res.category}' category me hua hai (₹{res.t:,.2f})."
        else: response = "Data nahi mila."

    elif top_intent == "total":
        t = db.query(func.sum(Expense.amount)).filter(Expense.user_id == uid).scalar() or 0
        response = f"Aapka overall Recorded Spend abhi tak ₹{t:,.2f} hai."

    elif top_intent == "avg":
        expenses = db.query(Expense.date, Expense.amount).filter(Expense.user_id == uid).all()
        months = set([d[:7] for d, a in expenses if d])
        total = sum([a for d, a in expenses if a])
        a = (total / len(months)) if len(months) > 0 else 0
        response = f"Aapka Average Monthly expense lagbhag ₹{a:,.2f} aata hai."

    elif top_intent == "save":
        res = db.query(Expense.category, func.sum(Expense.amount).label('t')).filter(Expense.user_id == uid).group_by(Expense.category).order_by(func.sum(Expense.amount).desc()).first()
        if res: response = f"Agar aap apne top expense '{res.category}' pe 15% bachat karein, toh monthly ₹{res.t*0.15:,.2f} bach jayenge."
        else: response = "Sufficient data nahi hai suggestions dene ke liye."

    elif top_intent == "predict":
        response = "Aapka data Linear Regression se analyze ho raha hai prediction box mein. Aap waise normally budget me chal rahe hain."

    return {"reply": response}

# ----------------------------------------------------
# 3. CRUD & DATA PIPELINE ENDPOINTS
# ----------------------------------------------------
@app.get("/api/transactions")
def get_recent_transactions(limit: int = 50, start_date: str = None, end_date: str = None, category: str = None, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Expense).filter(Expense.user_id == current_user.id)
    query = apply_date_filter(query, start_date, end_date)
    if category:
        query = query.filter(Expense.category == category)
        
    results = query.order_by(Expense.date.desc()).limit(limit).all()
    return results

class TransactionCreate(BaseModel):
    amount: float
    merchant: str
    category: str
    date: str = None

@app.post("/api/transactions")
def add_transaction(txn: TransactionCreate, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    txn_id = f"TXN-M-{str(uuid.uuid4())[:8].upper()}"
    txn_date = txn.date if txn.date else datetime.now().strftime("%Y-%m-%d")
    
    new_txn = Expense(
        user_id=current_user.id,
        transaction_id=txn_id,
        date=txn_date,
        amount=txn.amount,
        merchant=txn.merchant,
        category=txn.category,
        description="Manual",
        status="Completed"
    )
    db.add(new_txn)
    db.commit()
    return {"status": "success", "transaction_id": txn_id}

@app.delete("/api/transactions/{transaction_id}")
def delete_transaction(transaction_id: str, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    expense = db.query(Expense).filter(Expense.transaction_id == transaction_id, Expense.user_id == current_user.id).first()
    if expense:
        db.delete(expense)
        db.commit()
    return {"status": "success"}

@app.post("/api/upload")
async def bulk_upload(file: UploadFile = File(...), current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    content = await file.read()
    df = pd.read_csv(io.StringIO(content.decode("utf-8")))
    
    rows_to_insert = []
    
    for _, row in df.iterrows():
        txn_id = f"TXN-U-{str(uuid.uuid4())[:8].upper()}"
        status = 'Completed' if 'status' not in row else row['status']
        desc = 'Bulk Upload' if 'description' not in row else row['description']
        
        ex = Expense(
            user_id=current_user.id,
            transaction_id=txn_id,
            date=str(row['date']),
            amount=float(row['amount']),
            merchant=str(row['merchant']),
            category=str(row['category']),
            description=desc,
            status=status
        )
        rows_to_insert.append(ex)
        
    db.add_all(rows_to_insert)
    db.commit()
    
    return {"status": "success", "rows_inserted": len(rows_to_insert)}

@app.get("/api/export")
def export_transactions(current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    expenses = db.query(Expense).filter(Expense.user_id == current_user.id).order_by(Expense.date.desc()).limit(5000).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["transaction_id", "date", "amount", "merchant", "category", "description", "status"])
    for row in expenses:
        writer.writerow([row.transaction_id, row.date, row.amount, row.merchant, row.category, row.description, row.status])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=cleaned_expenses.csv"})

# ----------------------------------------------------
# 4. STATIC FRONTEND MOUNT
# ----------------------------------------------------
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
