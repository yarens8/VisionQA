
import sys
import os
# Backend klasörünü path'e ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def run_test():
    print("🚀 Test Başlıyor...")
    test_generate_ai_cases()

def test_generate_ai_cases():
    # ... (kodun aynısı)

    # 1. Proje Oluştur
    project_payload = {
        "name": "VisionQA AI Test Project",
        "description": "Pytest ile AI Test Case Üretimi",
        "platforms": ["web"]
    }
    
    response = client.post("/projects/", json=project_payload)
    if response.status_code == 200:
        project_id = response.json()["id"]
        print(f"\n✅ Proje Oluşturuldu ID: {project_id}")
    else:
        # Belki proje zaten vardır, ilkini al
        list_resp = client.get("/projects/")
        projects = list_resp.json()
        assert len(projects) > 0, "Hiç proje yok!"
        project_id = projects[0]["id"]
        print(f"\n⚠️ Mevcut Proje Kullanılıyor ID: {project_id}")

    # 2. AI Case Generate Endpoint Çağır
    print(f"🧠 AI Case Generation Başlatılıyor (ID: {project_id})...")
    
    # Timeout uzun olabilir, TestClient senkron olduğu için bekler
    gen_response = client.post(f"/projects/{project_id}/generate-cases")
    
    assert gen_response.status_code == 200, f"AI generation failed: {gen_response.text}"
    
    data = gen_response.json()
    assert "cases" in data, "Response should contain 'cases'"
    cases = data["cases"]
    
    assert len(cases) > 0, "AI should generate at least 1 case"
    
    print("\n🎉 BAŞARILI! Üretilen Test Case'ler:")
    for case in cases:
        print(f"- {case['title']} ({len(case.get('steps', []))} steps)")

if __name__ == '__main__':
    run_test()
