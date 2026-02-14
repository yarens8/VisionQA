
import httpx
import asyncio

BASE_URL = "http://localhost:8000"

async def test_generation():
    async with httpx.AsyncClient() as client:
        # 1. Önce bir proje oluşturalım
        print("🏗️ Proje oluşturuluyor...")
        project_data = {
            "name": "VisionQA Test E-Commerce",
            "description": "Otomatik test senaryosu üretimi için demo",
            "platforms": ["web"]
        }
        
        try:
            resp = await client.post(f"{BASE_URL}/projects", json=project_data)
            if resp.status_code not in [200, 201]:
                print(f"❌ Proje oluşturulamadı: {resp.text}")
                # Belki proje zaten vardır, listeyi çekip ilkini alalım
                list_resp = await client.get(f"{BASE_URL}/projects")
                projects = list_resp.json()
                if not projects:
                    return
                project_id = projects[0]['id']
                print(f"⚠️ Mevcut proje kullanılıyor ID: {project_id}")
            else:
                project = resp.json()
                project_id = project['id']
                print(f"✅ Proje oluşturuldu ID: {project_id}")

            # 2. Şimdi AI Test Case Üretimi Başlatalım
            print(f"🧠 AI Test Case Üretimi Tetikleniyor (ID: {project_id})...")
            # Timeout'u uzun tutalım (LLM yavaş olabilir)
            gen_resp = await client.post(
                f"{BASE_URL}/projects/{project_id}/generate-cases", 
                timeout=60.0
            )

            if gen_resp.status_code == 200:
                result = gen_resp.json()
                print("\n🎉 BAŞARILI! Üretilen Test Case'ler:")
                import json
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print(f"\n❌ Başarısız ({gen_resp.status_code}): {gen_resp.text}")

        except Exception as e:
            print(f"❌ Bağlantı hatası: {str(e)}")
            print("Backend sunucusu (uvicorn) çalışıyor mu?")

if __name__ == "__main__":
    asyncio.run(test_generation())
