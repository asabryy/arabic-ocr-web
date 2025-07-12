import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import time
import sqlalchemy
from sqlalchemy.exc import OperationalError

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

MAX_RETRIES = 10

for i in range(MAX_RETRIES):
    try:
        engine = sqlalchemy.create_engine(DATABASE_URL)
        connection = engine.connect()
        break
    except OperationalError:
        print(f"DB not ready yet, retrying ({i+1}/{MAX_RETRIES})...")
        time.sleep(3)
else:
    raise Exception("MySQL did not become available in time.")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()