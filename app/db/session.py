from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.models.clothing import Base

DATABASE_URL = "sqlite:///./fashion.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    execution_options={"sqlite_journal_mode": "WAL"},
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
