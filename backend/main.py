"""
VisionQA Backend - Main Application
FastAPI entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import check_database_connection

# FastAPI uygulaması oluştur
app = FastAPI(
    title="VisionQA API",
    description="AI-Powered Universal Software Quality & Testing Platform",
    version="1.0.0"
)

# CORS (Frontend'in backend'e erişmesi için)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# HEALTH CHECK ENDPOINT
# ============================================

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


# ============================================
# API ENDPOINTS (İleride eklenecek)
# ============================================

# @app.get("/api/platforms")
# def get_platforms():
#     """Desteklenen platformları listele"""
#     return ["web", "mobile", "desktop", "api", "database"]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
