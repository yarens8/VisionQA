
import pytest
import asyncio
import sys
import os

# Backend root dizinini path'e ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from executors.web.web_executor import WebExecutor

@pytest.mark.asyncio
async def test_web_executor_headless_navigation():
    """
    CI Ortamı İçin Web Executor Testi
    - Headless modda tarayıcı açar.
    - Basit bir siteye (example.com) gider.
    - Başlığı doğrular.
    """
    print("\n🧪 [CI Test] Web Executor Headless Modu Başlatılıyor...")
    
    # CI ortamında MUTLAKA headless=True olmalı
    executor = WebExecutor(headless=True)
    
    try:
        await executor.start()
        assert executor.page is not None, "Page objesi oluşturulamadı"
        
        await executor.navigate("https://example.com")
        
        title = await executor.page.title()
        print(f"✅ Sayfa Başlığı: {title}")
        
        # Basit doğrulama
        assert "Example Domain" in title
        
    except Exception as e:
        pytest.fail(f"Web Executor Test Hatası: {str(e)}")
        
    finally:
        await executor.stop()
