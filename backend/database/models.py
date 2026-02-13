"""
VisionQA Backend - Database Models
SQLAlchemy ORM models for PostgreSQL
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from database import Base
import enum


class PlatformType(str, enum.Enum):
    """Desteklenen platformlar"""
    WEB = "web"
    MOBILE_IOS = "mobile_ios"
    MOBILE_ANDROID = "mobile_android"
    DESKTOP_WINDOWS = "desktop_windows"
    DESKTOP_MACOS = "desktop_macos"
    DESKTOP_LINUX = "desktop_linux"
    API = "api"
    DATABASE = "database"


class TestStatus(str, enum.Enum):
    """Test durumları"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Project(Base):
    """Proje modeli - Kullanıcıların oluşturduğu projeler"""
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    platforms = Column(JSON, nullable=False)  # ["web", "mobile_ios", "api"]
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # İlişkiler
    test_runs = relationship("TestRun", back_populates="project", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}')>"


class TestRun(Base):
    """Test çalıştırma modeli - Her test execution kaydı"""
    __tablename__ = "test_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    platform = Column(SQLEnum(PlatformType), nullable=False)
    module_name = Column(String(100), nullable=False)  # "autonomous_tester", "bug_analyzer", vs.
    target = Column(String(500), nullable=False)  # URL, app path, API endpoint, vs.
    status = Column(SQLEnum(TestStatus), default=TestStatus.PENDING)
    
    # Test detayları
    config = Column(JSON, nullable=True)  # Test konfigürasyonu
    logs = Column(Text, nullable=True)  # Çalıştırma logları
    
    # Zamanlar
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # İlişkiler
    project = relationship("Project", back_populates="test_runs")
    findings = relationship("Finding", back_populates="test_run", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TestRun(id={self.id}, platform='{self.platform}', status='{self.status}')>"


class Finding(Base):
    """Bulgu modeli - Test'lerde bulunan hatalar/sorunlar"""
    __tablename__ = "findings"
    
    id = Column(Integer, primary_key=True, index=True)
    test_run_id = Column(Integer, ForeignKey("test_runs.id"), nullable=False)
    
    # Bulgu detayları
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(50), nullable=False)  # "critical", "high", "medium", "low"
    category = Column(String(100), nullable=False)  # "security", "performance", "accessibility", vs.
    
    # Ek bilgiler
    screenshot_url = Column(String(500), nullable=True)  # Screenshot path/URL
    extra_data = Column(JSON, nullable=True)  # Ek bilgiler (coords, metrics, vs.)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # İlişkiler
    test_run = relationship("TestRun", back_populates="findings")
    
    def __repr__(self):
        return f"<Finding(id={self.id}, severity='{self.severity}', title='{self.title}')>"
