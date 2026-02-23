
import sys
import asyncio
import schemas
from typing import List
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# ⚡ WINDOWS DÜZELTMESİ (Playwright İçin)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from database import check_database_connection, get_db, engine, Base
from database.models import Project as ProjectModel
from routers import (
    projects_router, 
    execution_router, 
    stats_router, 
    cases_router, 
    api_test_router, 
    db_test_router, 
    report_router, 
    scenario_router
)

# FastAPI uygulaması oluştur
app = FastAPI(
    title="VisionQA API",
    description="AI-Powered Universal Software Quality & Testing Platform",
    version="1.0.0"
)

# 🛠️ Veritabanı Tablonlarını Oluştur
Base.metadata.create_all(bind=engine)

# CORS (Frontend'in backend'e erişmesi için)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    """Ana endpoint - Backend'in çalıştığını gösterir"""
    return {
        "message": "VisionQA Backend çalışıyor! 🚀",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health")
def health_check():
    """Health check endpoint - Docker, CI/CD için"""
    db_status = "connected" if check_database_connection() else "disconnected"
    return {
        "status": "ok",
        "service": "visionqa-backend",
        "database": db_status,
        "database_type": "PostgreSQL",
        "port": 8000
    }

# Router Bağlantıları
app.include_router(projects_router.router)
app.include_router(execution_router.router)
app.include_router(stats_router.router)
app.include_router(cases_router.router)
app.include_router(api_test_router.router)
app.include_router(db_test_router.router)
app.include_router(report_router.router)
app.include_router(scenario_router.router)
