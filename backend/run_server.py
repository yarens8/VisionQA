
import sys
import asyncio
import uvicorn

# ⚡ WINDOWS KESİN DÜZELTME (Playwright İçin)
# Bu ayar, sunucu başlamadan ÖNCE yapılmalı.
if sys.platform == "win32" and hasattr(asyncio, "WindowsProactorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

if __name__ == "__main__":
    print("🚀 VisionQA Backend Başlatılıyor (Windows Fix Aktif)...")
    # Reload modu KAPALI (Windows Fix'in çalışması için tek process şart!)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
