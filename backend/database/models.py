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


class AnalysisJob(Base):
    """Asenkron analiz orkestrasyonu icin ortak job kaydi"""
    __tablename__ = "analysis_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_type = Column(String(100), nullable=False, index=True)
    module_name = Column(String(100), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="queued", index=True)
    target = Column(String(1000), nullable=True)
    request_payload = Column(JSON, nullable=False, default=dict)
    result_payload = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    celery_task_id = Column(String(255), nullable=True)
    source_record_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<AnalysisJob(id={self.id}, module='{self.module_name}', status='{self.status}')>"


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


class AccessibilityAnalysisRecord(Base):
    """Accessibility analiz geçmişi - screenshot/URL tabanlı kayıtlar"""
    __tablename__ = "accessibility_analysis_records"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False, default="web")
    source_type = Column(String(50), nullable=False)  # upload | url
    source_label = Column(String(255), nullable=True)
    source_url = Column(String(1000), nullable=True)
    overall_score = Column(Integer, nullable=False, default=0)
    findings_count = Column(Integer, nullable=False, default=0)
    overview = Column(Text, nullable=True)
    analysis_payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AccessibilityAnalysisRecord(id={self.id}, source_type='{self.source_type}', platform='{self.platform}')>"


class UiuxAnalysisRecord(Base):
    """UI/UX analiz geçmişi - screenshot tabanlı kayıtlar"""
    __tablename__ = "uiux_analysis_records"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False, default="web")
    source_type = Column(String(50), nullable=False, default="upload")
    source_label = Column(String(255), nullable=True)
    overall_score = Column(Integer, nullable=False, default=0)
    findings_count = Column(Integer, nullable=False, default=0)
    overview = Column(Text, nullable=True)
    analysis_payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<UiuxAnalysisRecord(id={self.id}, source_type='{self.source_type}', platform='{self.platform}')>"


class SecurityAnalysisRecord(Base):
    """Security analiz geçmişi - screenshot/URL ve simulation baglamli kayıtlar"""
    __tablename__ = "security_analysis_records"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False, default="web")
    source_type = Column(String(50), nullable=False, default="upload")
    source_label = Column(String(255), nullable=True)
    source_url = Column(String(1000), nullable=True)
    overall_score = Column(Integer, nullable=False, default=0)
    findings_count = Column(Integer, nullable=False, default=0)
    overview = Column(Text, nullable=True)
    analysis_payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<SecurityAnalysisRecord(id={self.id}, source_type='{self.source_type}', platform='{self.platform}')>"


class DatasetAnalysisRecord(Base):
    """Dataset analiz geçmişi - JSON/ZIP annotation analiz kayıtları"""
    __tablename__ = "dataset_analysis_records"

    id = Column(Integer, primary_key=True, index=True)
    dataset_name = Column(String(255), nullable=False, default="Dataset v1")
    source_type = Column(String(50), nullable=False, default="json")
    source_label = Column(String(255), nullable=True)
    overall_score = Column(Integer, nullable=False, default=0)
    quality_grade = Column(String(10), nullable=False, default="E")
    findings_count = Column(Integer, nullable=False, default=0)
    detail_errors_count = Column(Integer, nullable=False, default=0)
    total_records = Column(Integer, nullable=False, default=0)
    analysis_payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<DatasetAnalysisRecord(id={self.id}, dataset_name='{self.dataset_name}')>"


class ApiAnalysisRecord(Base):
    """API analiz geçmişi - endpoint kalite ve negatif kontrol kayıtları"""
    __tablename__ = "api_analysis_records"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False, default="api")
    source_type = Column(String(50), nullable=False, default="endpoint")
    source_label = Column(String(255), nullable=True)
    source_url = Column(String(1000), nullable=True)
    overall_score = Column(Integer, nullable=False, default=0)
    findings_count = Column(Integer, nullable=False, default=0)
    overview = Column(Text, nullable=True)
    analysis_payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ApiAnalysisRecord(id={self.id}, source_url='{self.source_url}')>"


class DbAnalysisRecord(Base):
    """Database kalite analiz geçmişi - query/table audit kayıtları"""
    __tablename__ = "db_analysis_records"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False, default="database")
    source_type = Column(String(50), nullable=False, default="quality-audit")
    source_label = Column(String(255), nullable=True)
    source_url = Column(String(1000), nullable=True)
    overall_score = Column(Integer, nullable=False, default=0)
    findings_count = Column(Integer, nullable=False, default=0)
    overview = Column(Text, nullable=True)
    analysis_payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<DbAnalysisRecord(id={self.id}, source_label='{self.source_label}')>"


class PerformanceAnalysisRecord(Base):
    """Performance analiz geçmişi - web/API/DB performans kayıtları"""
    __tablename__ = "performance_analysis_records"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False, default="web")
    source_type = Column(String(50), nullable=False, default="mixed")
    source_label = Column(String(255), nullable=True)
    source_url = Column(String(1000), nullable=True)
    overall_score = Column(Integer, nullable=False, default=0)
    findings_count = Column(Integer, nullable=False, default=0)
    overview = Column(Text, nullable=True)
    analysis_payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<PerformanceAnalysisRecord(id={self.id}, source_url='{self.source_url}')>"


class MobileAnalysisRecord(Base):
    """Mobile analiz geçmişi - screenshot/metadata tabanlı mobil kalite kayıtları"""
    __tablename__ = "mobile_analysis_records"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False, default="android")
    source_type = Column(String(50), nullable=False, default="metadata")
    source_label = Column(String(255), nullable=True)
    source_url = Column(String(1000), nullable=True)
    overall_score = Column(Integer, nullable=False, default=0)
    findings_count = Column(Integer, nullable=False, default=0)
    overview = Column(Text, nullable=True)
    analysis_payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<MobileAnalysisRecord(id={self.id}, platform='{self.platform}', source_type='{self.source_type}')>"


class JiraTicketDraft(Base):
    """Final Report aksiyon kartlarından uretilen Jira ticket taslaklari"""
    __tablename__ = "jira_ticket_drafts"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    provider = Column(String(50), nullable=False, default="jira")
    ticket_key = Column(String(100), nullable=False, index=True)
    source_module = Column(String(100), nullable=False, index=True)
    source_type = Column(String(100), nullable=False, default="final_report_action")
    source_ref = Column(String(255), nullable=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String(50), nullable=False, default="medium")
    status = Column(String(50), nullable=False, default="draft")
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project")

    def __repr__(self):
        return f"<JiraTicketDraft(id={self.id}, project_id={self.project_id}, source='{self.source_module}')>"


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
