import asyncio
import base64
import os
import json
from routers.audit_router import run_full_audit, AuditRequest

async def main():
    print("Demo basliyor...")
    os.makedirs("demo_output", exist_ok=True)
    
    req = AuditRequest(
        url="https://www.saucedemo.com/", 
        run_execution=True, 
        headless=True
    )
    
    res = await run_full_audit(req)
    
    # Raporu JSON olarak kaydet
    with open("demo_output/audit_report.json", "w", encoding="utf-8") as f:
        json.dump(res.dict(), f, indent=2, ensure_ascii=False)
        
    # Eger anomali varsa, gorsellerini kaydet
    anomalies = res.vad_report.get("anomalies", [])
    for idx, a in enumerate(anomalies):
        if a.get("crop_base64"):
            img_data = base64.b64decode(a["crop_base64"])
            with open(f"demo_output/anomaly_{idx}.png", "wb") as f:
                f.write(img_data)
                
    print("Demo bitti. Dosyalar demo_output klasorune kaydedildi.")

if __name__ == "__main__":
    asyncio.run(main())
