import sqlite3
import os
from datetime import datetime
import uuid

DB_FILE = 'db.sqlite3'

# Remove existing database to wipe the slate clean
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

# 1. Create table
cursor.execute('''
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id TEXT UNIQUE,
    date TEXT,
    amount REAL,
    merchant TEXT,
    category TEXT,
    description TEXT,
    status TEXT
)
''')

# 2. Prepare user's custom exact data
today = datetime.now().strftime('%Y-%m-%d')
initial_data = [
    (f"TXN-{str(uuid.uuid4())[:8]}", today, 3000.0, "Room Owner", "Rent", "Room Rent", "Completed"),
    (f"TXN-{str(uuid.uuid4())[:8]}", today, 1000.0, "Massi", "Utilities", "Massi / Maid", "Completed"),
    (f"TXN-{str(uuid.uuid4())[:8]}", today, 2000.0, "Local Store", "Groceries", "Food (Rasan)", "Completed"),
    (f"TXN-{str(uuid.uuid4())[:8]}", today, 250.0, "Street Food", "Dining", "Roll", "Completed"),
    (f"TXN-{str(uuid.uuid4())[:8]}", today, 500.0, "Date", "Entertainment", "Girlfriend", "Completed"),
    (f"TXN-{str(uuid.uuid4())[:8]}", today, 400.0, "Cafe", "Dining", "Coffee", "Completed"),
]

# 3. Insert specific records
cursor.executemany('''
INSERT INTO expenses 
(transaction_id, date, amount, merchant, category, description, status) 
VALUES (?, ?, ?, ?, ?, ?, ?)
''', initial_data)

conn.commit()
conn.close()

print("Database reset successfully with Priyanshu's custom personal data.")
