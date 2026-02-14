
import asyncio
from executors.web.web_executor import WebExecutor

async def run_live_test():
    print("🎬 CANLI TEST BAŞLIYOR... (Tarayıcı açılmalı!)")
    
    # Headless=False -> Tarayıcıyı GÖSTER
    executor = WebExecutor(headless=False)
    
    try:
        await executor.start()
        
        # 1. Hepsiburada'ya git
        await executor.navigate("https://www.hepsiburada.com")
        
        # 2. Bekle (Kullanıcı görsün)
        await asyncio.sleep(2)
        
        # 3. Arama kutusunu bul ve yaz (Basit bir selector)
        # Hepsiburada arama kutusu genelde 'input[type="text"]' veya benzeri
        # Ama garanti olsun diye Google deneyelim, Hepsiburada karmaşık olabilir.
        
        print("🌐 Google Testine geçiliyor...")
        await executor.navigate("https://www.google.com")
        
        # 4. Yazı Yaz
        await executor.type_input("textarea[name='q']", "VisionQA AI Testing Demo")
        await asyncio.sleep(1)
        
        # 5. Enter'a bas (Basit click yerine)
        await executor.page.keyboard.press("Enter")
        await asyncio.sleep(3)
        
        # 6. Screenshot al
        await executor.screenshot("backend/test_result.png")
        print("✅ Test Başarılı! Screenshot alındı.")

    except Exception as e:
        print(f"❌ TEST HATASI: {str(e)}")
    
    finally:
        await executor.stop()

if __name__ == "__main__":
    asyncio.run(run_live_test())
