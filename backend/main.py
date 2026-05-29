
import sys
import asyncio
import schemas
from typing import List
import asyncio as _asyncio

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
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
    scenario_router,
    accessibility_router,
    uiux_router,
    security_router,
    performance_router,
    dataset_router,
    mobile_router,
    vad_router,
    audit_router,
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


@app.get("/benchmark-fixtures/api/todos/1")
def benchmark_todo_fixture():
    return {
        "userId": 1,
        "id": 1,
        "title": "VisionQA benchmark todo",
        "completed": False,
    }


@app.get("/benchmark-fixtures/api/delay/2")
async def benchmark_slow_api_fixture():
    await _asyncio.sleep(2.6)
    return {
        "status": "ok",
        "message": "Delayed benchmark response",
        "delay_seconds": 2.6,
    }


@app.get("/benchmark-fixtures/pages/demoqa", response_class=HTMLResponse)
def benchmark_demoqa_page():
    return """
    <!doctype html>
    <html>
      <head><title>ToolsQA Benchmark</title></head>
      <body>
        <header style="height:140px;background:#3b98c9;color:white;text-align:center">
          <h1>TOOLSQA</h1>
          <p>Selenium Certification Training</p>
        </header>
        <main style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px;padding:24px">
          <a href="/benchmark-fixtures/pages/elements">Elements</a>
          <a href="/benchmark-fixtures/pages/forms">Forms</a>
          <a href="/benchmark-fixtures/pages/alerts">Alerts, Frame & Windows</a>
          <button>Widgets</button>
          <button>Interactions</button>
          <a href="/benchmark-fixtures/pages/book-store">Book Store Application</a>
        </main>
      </body>
    </html>
    """


@app.get("/benchmark-fixtures/pages/text-box", response_class=HTMLResponse)
def benchmark_text_box_page():
    return """
    <!doctype html>
    <html>
      <head><title>Text Box Benchmark</title></head>
      <body>
        <main>
          <h1>Text Box</h1>
          <form>
            <label>Full Name <input id="userName" type="text" placeholder="Full Name"></label>
            <label>Email <input id="userEmail" type="email" placeholder="name@example.com"></label>
            <label>Current Address <textarea id="currentAddress"></textarea></label>
            <button id="submit" type="submit">Submit</button>
          </form>
          <div role="alert" class="validation"></div>
        </main>
      </body>
    </html>
    """


@app.get("/benchmark-fixtures/pages/saucedemo-login", response_class=HTMLResponse)
def benchmark_saucedemo_login_page():
    return """
    <!doctype html>
    <html>
      <head><title>Swag Labs Benchmark</title></head>
      <body>
        <main>
          <h1>Swag Labs</h1>
          <form>
            <input id="user-name" name="user-name" type="text" placeholder="Username">
            <input id="password" name="password" type="password" placeholder="Password">
            <button id="login-button" type="submit">Login</button>
          </form>
          <p>Accepted usernames are: standard_user, locked_out_user</p>
        </main>
      </body>
    </html>
    """


@app.get("/benchmark-fixtures/pages/the-internet", response_class=HTMLResponse)
def benchmark_the_internet_page():
    return """
    <!doctype html>
    <html>
      <head><title>The Internet Benchmark</title></head>
      <body>
        <h1>Welcome to the-internet</h1>
        <ul>
          <li><a href="/benchmark-fixtures/pages/abtest">A/B Testing</a></li>
          <li><a href="/benchmark-fixtures/pages/login">Form Authentication</a></li>
          <li><a href="/benchmark-fixtures/pages/frames">Frames</a></li>
        </ul>
      </body>
    </html>
    """

# Router Bağlantıları
app.include_router(projects_router.router)
app.include_router(execution_router.router)
app.include_router(stats_router.router)
app.include_router(cases_router.router)
app.include_router(api_test_router.router)
app.include_router(db_test_router.router)
app.include_router(report_router.router)
app.include_router(scenario_router.router)
app.include_router(accessibility_router.router)
app.include_router(uiux_router.router)
app.include_router(security_router.router)
app.include_router(performance_router.router)
app.include_router(dataset_router.router)
app.include_router(mobile_router.router)
app.include_router(vad_router.router)
app.include_router(audit_router.router)
