@echo off
title VisionQA Backend Server 🚀
color 0A

cd backend

:: 1. Venv Kontrolü (Sadece YOKSA kurar)
if not exist "venv" (
    echo [ILK KURULUM] Virtual Environment olusturuluyor...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo [ILK KURULUM] Paketler yukleniyor (Bu islem bir kez yapilir)...
    pip install -r requirements.txt
    pip install fastapi uvicorn sqlalchemy psycopg2-binary alembic httpx requests playwright pytest
    playwright install chromium
) else (
    :: Venv varsa sadece aktif et
    call venv\Scripts\activate.bat
)

:: 2. Sunucuyu Baslat (Hızlıca!)
echo.
echo [VisionQA] Sunucu Baslatiliyor... (http://localhost:8000)
echo.
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

pause
