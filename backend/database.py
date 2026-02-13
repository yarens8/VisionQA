"""
VisionQA Backend - Database Configuration
SQLAlchemy setup for PostgreSQL
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

# Database URL (.env'den al)
DATABASE_URL = os.getenv("DATABASE_URL")

# SQLAlchemy engine oluştur
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Connection hayatta mı kontrol et
    echo=False  # SQL query'leri log'lama (debug için True yapabilirsiniz)
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Database session'ı al (FastAPI dependency için)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection():
    """Database bağlantısını test et"""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            result.fetchone()
            return True
    except Exception as e:
        print(f"❌ Database bağlantı hatası: {e}")
        return False


if __name__ == "__main__":
    # Test
    if check_database_connection():
        print("✅ PostgreSQL bağlantısı başarılı!")
    else:
        print("❌ PostgreSQL bağlantısı BAŞARISIZ!")
