import sqlite3
import os
from datetime import datetime
import uuid
import bcrypt

DB_FILE = 'db.sqlite3'

# Remove existing database to wipe the slate clean
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

# 1. Create users table
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at TEXT NOT NULL,
    full_name TEXT
)
''')

# 2. Create expenses table with user_id
cursor.execute('''
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    transaction_id TEXT UNIQUE,
    date TEXT,
    amount REAL,
    merchant TEXT,
    category TEXT,
    description TEXT,
    status TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
''')

now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# 3. Create Admin user
salt = bcrypt.gensalt()
hashed_pw = bcrypt.hashpw("admin123".encode('utf-8'), salt).decode('utf-8')
cursor.execute('INSERT INTO users (username, password_hash, role, created_at, full_name) VALUES (?, ?, ?, ?, ?)',
              ("admin", hashed_pw, "admin", now, "Admin User"))
admin_id = cursor.lastrowid

# 4. Prepare user's custom exact data under the admin account
today = datetime.now().strftime('%Y-%m-%d')
initial_data = [
    (admin_id, f"TXN-{str(uuid.uuid4())[:8]}", today, 3000.0, "Room Owner", "Rent", "Room Rent", "Completed"),
    (admin_id, f"TXN-{str(uuid.uuid4())[:8]}", today, 1000.0, "Massi", "Utilities", "Massi / Maid", "Completed"),
    (admin_id, f"TXN-{str(uuid.uuid4())[:8]}", today, 2000.0, "Local Store", "Groceries", "Food (Rasan)", "Completed"),
    (admin_id, f"TXN-{str(uuid.uuid4())[:8]}", today, 250.0, "Street Food", "Dining", "Roll", "Completed"),
    (admin_id, f"TXN-{str(uuid.uuid4())[:8]}", today, 500.0, "Date", "Entertainment", "Girlfriend", "Completed"),
    (admin_id, f"TXN-{str(uuid.uuid4())[:8]}", today, 400.0, "Cafe", "Dining", "Coffee", "Completed"),
]

# 5. Insert specific records
cursor.executemany('''
INSERT INTO expenses 
(user_id, transaction_id, date, amount, merchant, category, description, status) 
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
''', initial_data)

conn.commit()
conn.close()

print("Multi-tenant database initialized! Admin user created (admin / admin123) with personal seeded data.")
