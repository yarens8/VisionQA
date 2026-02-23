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

# SQLAlchemy engine oluştur
if DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        echo=False
    )
else:
    # ⚠️ ÇALIŞMA NOTU: Eğer DATABASE_URL yoksa (CI ortamı gibi), 
    # projenin çökmemesi için geçici bir SQLite oluşturuyoruz.
    print("⚠️ DATABASE_URL bulunamadı, geçici SQLite kullanılıyor.")
    engine = create_engine("sqlite:///./visionqa_temp.db", connect_args={"check_same_thread": False})

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
