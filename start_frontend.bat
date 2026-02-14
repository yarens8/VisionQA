@echo off
title VisionQA Frontend (Web UI) 🎨
color 0B

echo ===================================================
echo      VisionQA Frontend Baslatiliyor...
echo ===================================================
echo.

cd frontend

:: Paketler (ilk kurulum icin)
if not exist "node_modules" (
    echo [BILGI] node_modules bulunamadi! npm install yapiliyor...
    call npm install
)

echo.
echo [BAŞARILI] Tarayicida aciliyor: http://localhost:5173
echo.
call npm run dev

pause
