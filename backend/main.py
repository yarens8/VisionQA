import sys
import asyncio

# ⚡ WINDOWS DÜZELTMESİ (Playwright İçin)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from typing import List
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from database import check_database_connection, get_db
from database.models import Project as ProjectModel
from sqlalchemy.orm import Session
import schemas

# FastAPI uygulaması oluştur
app = FastAPI(
    title="VisionQA API",
    description="AI-Powered Universal Software Quality & Testing Platform",
    version="1.0.0"
)

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
    # Database bağlantısını kontrol et
    db_status = "connected" if check_database_connection() else "disconnected"
    
    return {
        "status": "ok",
        "service": "visionqa-backend",
        "database": db_status,
        "database_type": "PostgreSQL",
        "port": 8000
    }


from routers import projects_router, execution_router

# Router Bağlantıları
app.include_router(projects_router.router)
app.include_router(execution_router.router)

