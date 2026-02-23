"""Drop all tables and recreate them. Run with caution: python reset_db.py"""
from database import engine
from models import Base
from sqlalchemy import text

# Drop all tables
with engine.connect() as conn:
    conn.execute(text("DROP SCHEMA public CASCADE"))
    conn.execute(text("CREATE SCHEMA public"))
    conn.commit()
    print("Dropped all tables.")

# Recreate
Base.metadata.create_all(bind=engine)
print("Tables created successfully.")
