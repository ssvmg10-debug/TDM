"""SQLAlchemy engine and session; base for models."""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=False,
    # Disable insertmanyvalues to avoid UUID sentinel mismatch with PostgreSQL
    use_insertmanyvalues=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
