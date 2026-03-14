import asyncio
import sys
import os
import json

# Proje dizinini yola ekle
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from playwright.async_api import async_playwright

# ═══════════════════════════════════════════════════════
#  DEPLOY PANELİ (TEST YÜRÜTME DURUMU)
# ═══════════════════════════════════════════════════════

DEPLOY_PANEL_INJECT = """
(testTitle) => {
    const panel = document.createElement('div');
    panel.id = 'visionqa-deploy-panel';
    panel.style.cssText = `
        position: fixed; right: 0; top: 0;
        width: 420px; height: 100vh;
        background: linear-gradient(180deg, rgba(10,10,30,0.97) 0%, rgba(5,5,20,0.99) 100%);
        border-left: 2px solid #3b82f6;
        box-shadow: -10px 0 40px rgba(59,130,246,0.15);
        z-index: 99999999;
        font-family: 'Consolas', 'Courier New', monospace;
        color: #E0E0E0;
        overflow-y: auto;
        padding: 0;
        transition: transform 0.5s cubic-bezier(0.16, 1, 0.3, 1);
        transform: translateX(100%);
    `;

    const header = document.createElement('div');
    header.style.cssText = `
        background: linear-gradient(90deg, #001030 0%, #002060 100%);
        padding: 16px 20px;
        border-bottom: 2px solid #3b82f6;
        position: sticky; top: 0; z-index: 1;
    `;
    header.innerHTML = `
        <div style="display:flex;align-items:center;gap:10px;">
            <span style="font-size:24px;">🚀</span>
            <div>
                <div style="color:#3b82f6;font-size:16px;font-weight:bold;letter-spacing:2px;">TEST DEPLOY</div>
                <div style="color:#60a5fa;font-size:11px;margin-top:2px;">${testTitle}</div>
            </div>
        </div>
    `;
    panel.appendChild(header);

    const content = document.createElement('div');
    content.id = 'visionqa-deploy-content';
    content.style.cssText = 'padding: 16px 20px;';
    panel.appendChild(content);

    document.body.appendChild(panel);
    setTimeout(() => { panel.style.transform = 'translateX(0)'; }, 100);
}
"""

def deploy_step_script(step_num, total, action, target, status="running", detail=""):
    """Deploy paneline bir adım satırı ekleyen JS kodu üretir."""
    status_icons = {"running": "⏳", "success": "✅", "failed": "❌", "skipped": "⏭️"}
    status_colors = {"running": "#f59e0b", "success": "#22c55e", "failed": "#ef4444", "skipped": "#6b7280"}
    icon = status_icons.get(status, "⏳")
    color = status_colors.get(status, "#f59e0b")
    safe_target = target.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
    safe_detail = detail.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")

    return f"""
    () => {{
        const content = document.getElementById('visionqa-deploy-content');
        if (!content) return;

        // Eğer bu adım için zaten bir satır varsa güncelle
        let row = document.getElementById('deploy-step-{step_num}');
        if (row) {{
            row.querySelector('.step-icon').textContent = '{icon}';
            row.querySelector('.step-status').style.color = '{color}';
            row.querySelector('.step-status').textContent = '{status.upper()}';
            if ('{safe_detail}') {{
                let det = row.querySelector('.step-detail');
                if (!det) {{
                    det = document.createElement('div');
                    det.className = 'step-detail';
                    det.style.cssText = 'color:#888;font-size:10px;margin-top:4px;';
                    row.appendChild(det);
                }}
                det.textContent = `{safe_detail}`;
            }}
            return;
        }}

        row = document.createElement('div');
        row.id = 'deploy-step-{step_num}';
        row.style.cssText = `
            margin-bottom: 10px; padding: 10px 14px;
            background: rgba(59,130,246,0.05);
            border: 1px solid rgba(59,130,246,0.15);
            border-left: 3px solid {color};
            border-radius: 0 6px 6px 0;
            opacity: 0; transform: translateY(8px);
            transition: all 0.3s ease;
        `;

        row.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div style="display:flex;align-items:center;gap:8px;">
                    <span class="step-icon" style="font-size:14px;">{icon}</span>
                    <span style="color:#ccc;font-size:12px;"><b style="color:#3b82f6;">Adım {step_num}/{total}</b> · {action.upper()}</span>
                </div>
                <span class="step-status" style="color:{color};font-size:10px;font-weight:bold;">{status.upper()}</span>
            </div>
            <div style="color:#aaa;font-size:11px;margin-top:4px;word-break:break-all;">{safe_target}</div>
        `;

        content.appendChild(row);
        content.scrollTop = content.scrollHeight;
        setTimeout(() => {{
            row.style.opacity = '1';
            row.style.transform = 'translateY(0)';
        }}, 50);
    }}
    """

def deploy_result_script(passed, failed, total):
    """Deploy sonuç kartını panele ekleyen JS kodu üretir."""
    success = passed == total
    color = "#22c55e" if success else "#ef4444"
    icon = "🎉" if success else "💥"
    label = "TEST BAŞARILI" if success else "TEST BAŞARISIZ"

    return f"""
    () => {{
        const content = document.getElementById('visionqa-deploy-content');
        if (!content) return;

        const card = document.createElement('div');
        card.style.cssText = `
            margin-top: 20px; padding: 20px;
            background: {color}11;
            border: 2px solid {color};
            border-radius: 10px;
            text-align: center;
            opacity: 0; transform: scale(0.9);
            transition: all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        `;
        card.innerHTML = `
            <div style="font-size:40px;margin-bottom:8px;">{icon}</div>
            <div style="color:{color};font-size:18px;font-weight:bold;letter-spacing:2px;">{label}</div>
            <div style="color:#aaa;font-size:12px;margin-top:8px;">Geçen: {passed}/{total} · Başarısız: {failed}/{total}</div>
        `;
        content.appendChild(card);
        content.scrollTop = content.scrollHeight;
        setTimeout(() => {{
            card.style.opacity = '1';
            card.style.transform = 'scale(1)';
        }}, 100);
    }}
    """


# ═══════════════════════════════════════════════════════
#  TEST YÜRÜTME
# ═══════════════════════════════════════════════════════

async def run_deploy_inspector(url: str, test_title: str, steps: list):
    print(f"\n{'='*60}")
    print(f"🚀 [Deploy Inspector] Canlı Test Yürütme: {test_title}")
    print(f"   URL: {url} | Adım Sayısı: {len(steps)}")
    print(f"{'='*60}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=['--start-maximized'])
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()

        # Sayfaya git
        print("🌐 Sayfaya gidiliyor...")
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(1)

        # Deploy panelini aç
        await page.evaluate(DEPLOY_PANEL_INJECT, test_title)
        await asyncio.sleep(0.5)

        passed = 0
        failed = 0
        total = len(steps)

        for i, step in enumerate(steps):
            step_num = i + 1
            action = step.get("action", "interact")
            target = step.get("target", "")
            value = step.get("value", "")
            expected = step.get("expected", "")

            print(f"   [{step_num}/{total}] {action.upper()}: {target}")

            # Panelde "çalışıyor" göster
            await page.evaluate(deploy_step_script(step_num, total, action, target, "running"))
            await asyncio.sleep(0.5)

            try:
                if action == "navigate":
                    await page.goto(target, wait_until="networkidle", timeout=30000)
                elif action == "wait":
                    if target == "networkidle":
                        await page.wait_for_load_state("networkidle", timeout=10000)
                    else:
                        await asyncio.sleep(2)
                elif action == "click":
                    try:
                        el = page.locator(target).first
                        await el.click(timeout=5000)
                    except:
                        # Soft fail — cookie banners vs. bulunamazsa atla
                        if "cookie" in target.lower() or "accept" in target.lower():
                            await page.evaluate(deploy_step_script(step_num, total, action, target, "skipped", "Opsiyonel element bulunamadı, atlandı."))
                            continue
                        raise
                elif action == "type":
                    el = page.locator(target).first
                    await el.fill(value, timeout=5000)
                elif action == "verify":
                    el = page.locator(target).first
                    await el.wait_for(state="visible", timeout=5000)
                elif action == "hover":
                    el = page.locator(target).first
                    await el.hover(timeout=5000)
                elif action == "scroll":
                    await page.evaluate("window.scrollBy(0, 300)")
                elif action == "select":
                    el = page.locator(target).first
                    await el.select_option(value, timeout=5000)

                # Başarılı
                await page.evaluate(deploy_step_script(step_num, total, action, target, "success", expected))
                passed += 1
                print(f"      ✅ Başarılı")

            except Exception as e:
                error_msg = str(e)[:100]
                await page.evaluate(deploy_step_script(step_num, total, action, target, "failed", error_msg))
                failed += 1
                print(f"      ❌ Hata: {error_msg}")

            await asyncio.sleep(0.5)

        # Sonuç kartı
        await page.evaluate(deploy_result_script(passed, failed, total))
        print(f"\n🏁 Test Sonucu: {passed}/{total} adım başarılı, {failed} başarısız")

        # Ekranda 10 saniye tut
        await asyncio.sleep(10)

        print("🛑 Tarayıcı kapanıyor.")
        await browser.close()

    return {"passed": passed, "failed": failed, "total": total}


if __name__ == "__main__":
    import tempfile

    if len(sys.argv) > 1 and sys.argv[1].endswith('.json'):
        # Bridge'den JSON dosyası ile çağrıldı
        json_path = sys.argv[1]
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        test_url = data.get("url", "https://www.saucedemo.com")
        test_title = data.get("test_title", "Adsız Test")
        test_steps = data.get("steps", [])
        # Geçici JSON dosyasını temizle
        try:
            os.remove(json_path)
        except:
            pass
    else:
        # Doğrudan çalıştırma (test amaçlı)
        test_url = sys.argv[1] if len(sys.argv) > 1 else "https://www.saucedemo.com"
        test_title = "Demo Test"
        test_steps = [
            {"action": "navigate", "target": test_url, "value": "", "expected": "Sayfa yüklendi"},
            {"action": "wait", "target": "networkidle", "value": "", "expected": "Ağ trafiği bitti"},
            {"action": "type", "target": "input[placeholder='Username']", "value": "standard_user", "expected": "Kullanıcı adı girildi"},
            {"action": "type", "target": "input[placeholder='Password']", "value": "secret_sauce", "expected": "Şifre girildi"},
            {"action": "click", "target": "input[type='submit']", "value": "", "expected": "Login butonuna tıklandı"},
            {"action": "verify", "target": ".inventory_list", "value": "", "expected": "Ürün listesi göründü"}
        ]

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(run_deploy_inspector(test_url, test_title, test_steps))
