from database import Base, engine, SessionLocal, User, Expense
from datetime import datetime
import uuid
import bcrypt
import os

# Create all tables (drops them first to ensure clean slate)
# If using SQLite, we can just delete the file.
from database import DATABASE_URL
if "sqlite" in DATABASE_URL:
    try:
        os.remove('db.sqlite3')
    except OSError:
        pass

# Create tables via SQLAlchemy
print("Dropping existing tables if they exist...")
Base.metadata.drop_all(bind=engine)

print("Creating new schema...")
Base.metadata.create_all(bind=engine)

db = SessionLocal()

# 1. Create Admin user
print("Seeding admin account...")
salt = bcrypt.gensalt()
hashed_pw = bcrypt.hashpw("admin123".encode('utf-8'), salt).decode('utf-8')
now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

admin_user = User(
    username="admin",
    password_hash=hashed_pw,
    role="admin",
    created_at=now,
    full_name="Admin User"
)
db.add(admin_user)
db.commit()
db.refresh(admin_user)
admin_id = admin_user.id

# 2. Prepare user's custom exact data under the admin account
print("Seeding historical expense data...")
today = datetime.now().strftime('%Y-%m-%d')
initial_data = [
    Expense(user_id=admin_id, transaction_id=f"TXN-{str(uuid.uuid4())[:8]}", date=today, amount=3000.0, merchant="Room Owner", category="Rent", description="Room Rent", status="Completed"),
    Expense(user_id=admin_id, transaction_id=f"TXN-{str(uuid.uuid4())[:8]}", date=today, amount=1000.0, merchant="Massi", category="Utilities", description="Massi / Maid", status="Completed"),
    Expense(user_id=admin_id, transaction_id=f"TXN-{str(uuid.uuid4())[:8]}", date=today, amount=2000.0, merchant="Local Store", category="Groceries", description="Food (Rasan)", status="Completed"),
    Expense(user_id=admin_id, transaction_id=f"TXN-{str(uuid.uuid4())[:8]}", date=today, amount=250.0, merchant="Street Food", category="Dining", description="Roll", status="Completed"),
    Expense(user_id=admin_id, transaction_id=f"TXN-{str(uuid.uuid4())[:8]}", date=today, amount=500.0, merchant="Date", category="Entertainment", description="Girlfriend", status="Completed"),
    Expense(user_id=admin_id, transaction_id=f"TXN-{str(uuid.uuid4())[:8]}", date=today, amount=400.0, merchant="Cafe", category="Dining", description="Coffee", status="Completed"),
]

db.add_all(initial_data)
db.commit()
db.close()

print("Multi-tenant database initialized via SQLAlchemy ORM!")
print("Admin user created (admin / admin123) with personal seeded data.")
