import asyncio
import os
import time
from routers.audit_router import run_full_audit, AuditRequest

async def main():
    print("=" * 60)
    print("🎬 MEGA ORKESTRATÖR CANLI ŞOVU BAŞLIYOR...")
    print("=" * 60)
    print("1. LLM (Yapay Zeka) hedefin kimliğini analiz ediyor...")
    await asyncio.sleep(2)
    
    print("2. Dinamik test senaryoları yazılıyor...")
    await asyncio.sleep(2)
    
    print("3. Tarayıcı açılıyor (Kaslar devreye giriyor)...")
    await asyncio.sleep(1)
    
    req = AuditRequest(
        url="https://www.saucedemo.com/", 
        run_execution=True, 
        headless=False  # TARAYICIYI EKRANDA GÖSTER!
    )
    
    res = await run_full_audit(req)
    
    print("\n" + "="*60)
    print("📊 FİNAL AUDIT RAPORU ÖZETİ")
    print("="*60)
    print(f"Durum: {res.status.upper()}")
    print(f"Toplam Süre: {res.duration_sec} saniye")
    print()
    
    print("🔍 1. KİMLİK (IDENTITY) SONUÇLARI:")
    print(f"   Sayfa Tipi: {res.identity_report.get('page_type', 'Bilinmiyor')}")
    print(f"   Bulunan İş Kuralları: {len(res.identity_report.get('business_rules', []))} kural tespit edildi")
    print()
    
    print("📝 2. DİNAMİK TEST ÜRETİMİ:")
    print(f"   Toplam Üretilen Test: {res.generated_cases_summary.get('total_generated')}")
    print(f"   - Happy Path: {res.generated_cases_summary.get('happy_path_count')}")
    print(f"   - Negative Path: {res.generated_cases_summary.get('negative_path_count')}")
    print()
    
    print("👁️ 3. GÖRSEL ANOMALİ (VAD) SONUÇLARI:")
    print(f"   Görsel Kalite Skoru: {res.vad_report.get('overall_score')}/100")
    print(f"   Bulunan Anomali Sayısı: {res.vad_report.get('total_anomalies')}")
    print(f"   VAD Özeti: {res.vad_report.get('summary')}")
    print()
    
    print("🧠 4. KÖK NEDEN (RCA) ANALİZİ:")
    print(f"   Değerlendirme: {res.root_cause_analysis.get('overall_assessment')}")
    rca_items = res.root_cause_analysis.get('root_cause_analysis', [])
    if rca_items:
        for item in rca_items:
            print(f"   - [Hata]: {item.get('anomaly_type')}")
            print(f"     [Çözüm]: {item.get('fix_recommendation')}")
    
    print("\n" + "="*60)
    print("ŞOV BİTTİ! Terminalden sonuçları inceleyebilirsin.")

if __name__ == "__main__":
    asyncio.run(main())
