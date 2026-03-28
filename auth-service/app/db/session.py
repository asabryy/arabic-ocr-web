from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings

settings = Settings()

# Create engine and session factory
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Dependency: provide a database session and ensure it is closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
