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

# Database URL (.env'den al) - CI/Test dostu fallback eklendi
DATABASE_URL = os.getenv("DATABASE_URL")
SQLITE_FALLBACK_URL = "sqlite:///./visionqa_temp.db"


def _build_engine():
    """DB engine'i oluştur; yapılandırılmış DB erişilemiyorsa SQLite fallback'e düş."""
    if DATABASE_URL:
        primary_engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            echo=False
        )
        try:
            with primary_engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return primary_engine
        except Exception as e:
            print(f"⚠️ DATABASE_URL erişilemiyor ({e}). Geçici SQLite fallback kullanılacak.")

    if not DATABASE_URL:
        print("⚠️ DATABASE_URL bulunamadı, geçici SQLite kullanılıyor.")

    return create_engine(SQLITE_FALLBACK_URL, connect_args={"check_same_thread": False})


# SQLAlchemy engine oluştur
engine = _build_engine()

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
    if not engine:
        print("⚠️ Database URL tanımlı değil (.env dosyası eksik)")
        return False
    
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
