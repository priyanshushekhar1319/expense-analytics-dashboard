import os
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# Determine the database URL
# If DATABASE_URL is set (like in Render with PostgreSQL), use it.
# Otherwise, fallback to local SQLite DB.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///db.sqlite3")

# SQLAlchemy requires 'postgresql://' instead of 'postgres://' for recent drivers
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine_kwargs = {}
if "sqlite" in DATABASE_URL:
    # SQLite requires check_same_thread=False for FastAPI
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# MODELS
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String)
    role = Column(String, nullable=False, default="user")
    created_at = Column(String, nullable=False)
    
    expenses = relationship("Expense", back_populates="owner")

class Expense(Base):
    __tablename__ = "expenses"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    transaction_id = Column(String, unique=True, index=True)
    date = Column(String)
    amount = Column(Float)
    merchant = Column(String)
    category = Column(String)
    description = Column(String)
    status = Column(String)
    
    owner = relationship("User", back_populates="expenses")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
