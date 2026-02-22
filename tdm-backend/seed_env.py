"""Seed QA environment with default connection. Run after init_db."""
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
load_dotenv()

from database import SessionLocal
from models import Environment

db = SessionLocal()
try:
    if db.query(Environment).filter(Environment.name == "QA").first():
        print("QA environment already exists")
    else:
        conn = os.getenv("DATABASE_URL", "postgresql://postgres:12345@localhost:5432/tdm")
        e = Environment(name="QA", connection_string_encrypted=conn)
        db.add(e)
        db.commit()
        print("Created QA environment")
finally:
    db.close()
