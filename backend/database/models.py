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
    """Proje modeli - Kullanıcıların oluşturduğu ana çatılar (Örn: Trendyol)"""
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    platforms = Column(JSON, nullable=False)  # ["web", "mobile_ios", "api"]
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # İlişkiler
    pages = relationship("Page", back_populates="project", cascade="all, delete-orphan", passive_deletes=True)
    test_runs = relationship("TestRun", back_populates="project", cascade="all, delete-orphan", passive_deletes=True)
    test_cases = relationship("TestCase", back_populates="project", cascade="all, delete-orphan", passive_deletes=True)
    
    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}')>"


class Page(Base):
    """Sayfa modeli - Proje altındaki farklı URL'ler (Örn: Login Sayfası, Sepet Sayfası)"""
    __tablename__ = "pages"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)  # "Login Sayfası"
    url = Column(String(500), nullable=False)   # "https://www.trendyol.com/login"
    description = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # İlişkiler
    project = relationship("Project", back_populates="pages")
    test_cases = relationship("TestCase", back_populates="page", cascade="all, delete-orphan", passive_deletes=True)

    def __repr__(self):
        return f"<Page(id={self.id}, name='{self.name}', url='{self.url}')>"


class TestRun(Base):
    """Test çalıştırma modeli - Her test execution kaydı"""
    __tablename__ = "test_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    page_id = Column(Integer, ForeignKey("pages.id"), nullable=True) # Hangi URL üzerinde koştu
    platform = Column(SQLEnum(PlatformType), nullable=False)
    module_name = Column(String(100), nullable=False)
    target = Column(String(500), nullable=False)
    test_case_id = Column(Integer, ForeignKey("test_cases.id"), nullable=True)
    status = Column(SQLEnum(TestStatus), default=TestStatus.PENDING)
    
    config = Column(JSON, nullable=True)
    logs = Column(Text, nullable=True)
    
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # İlişkiler
    project = relationship("Project", back_populates="test_runs")
    page = relationship("Page") # Page silinince TestRun null'a çekilebilir veya cascade edilebilir.
    test_case = relationship("TestCase", back_populates="test_runs")
    findings = relationship("Finding", back_populates="test_run", cascade="all, delete-orphan", passive_deletes=True)
    
    def __repr__(self):
        return f"<TestRun(id={self.id}, platform='{self.platform}', status='{self.status}')>"


class Finding(Base):
    """Bulgu modeli - Test'lerde bulunan hatalar/sorunlar"""
    __tablename__ = "findings"
    
    id = Column(Integer, primary_key=True, index=True)
    test_run_id = Column(Integer, ForeignKey("test_runs.id"), nullable=False)
    
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(50), nullable=False)
    category = Column(String(100), nullable=False)
    screenshot_url = Column(String(500), nullable=True)
    extra_data = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # İlişkiler
    test_run = relationship("TestRun", back_populates="findings")
    
    def __repr__(self):
        return f"<Finding(id={self.id}, severity='{self.severity}', title='{self.title}')>"


class TestCase(Base):
    """Test Case Modeli - Artık bir Sayfaya (URL) bağlı"""
    __tablename__ = "test_cases"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    page_id = Column(Integer, ForeignKey("pages.id"), nullable=True) # Yeni sayfa bağlantısı
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), default="happy_path") # happy_path, negative_path, edge_case, security
    status = Column(String(50), default="draft")
    priority = Column(String(50), default="medium")
    platform = Column(String(50), default="web") # PlatformType: web, api, mobile_android vs.
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # İlişkiler
    steps = relationship("TestStep", back_populates="test_case", cascade="all, delete-orphan", order_by="TestStep.order", passive_deletes=True)
    test_runs = relationship("TestRun", back_populates="test_case", cascade="all, delete-orphan", passive_deletes=True)
    project = relationship("Project", back_populates="test_cases")
    page = relationship("Page", back_populates="test_cases")


class TestStep(Base):
    """Test Adımı Modeli - Senaryonun her bir aksiyonu"""
    __tablename__ = "test_steps"

    id = Column(Integer, primary_key=True, index=True)
    test_case_id = Column(Integer, ForeignKey("test_cases.id"), nullable=False)
    
    order = Column(Integer, nullable=False)
    action = Column(String(100), nullable=False)
    target = Column(String(255), nullable=True)
    value = Column(Text, nullable=True)
    expected_result = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # İlişkiler
    test_case = relationship("TestCase", back_populates="steps")
