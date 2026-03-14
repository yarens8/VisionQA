"""
VisionQA — Canlı AI Vizyon İnceleyici (Vision Inspector)
========================================================
Bu script Docker'dan gelen element verilerini görselleştirir.
DINO analizi Docker tarafında yapılır, bu script sadece gösterim yapar.
"""
import asyncio
import sys
import os
import json
import requests

from playwright.async_api import async_playwright
from dotenv import load_dotenv

# .env dosyasını yükle (Groq API key için)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def call_llm(prompt, system_prompt="You are a QA expert."):
    """Groq API'ye senkron istek gönderir."""
    if not GROQ_API_KEY:
        return '{"error": "GROQ_API_KEY bulunamadı"}'
    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 4096,
                "response_format": {"type": "json_object"}
            },
            timeout=60
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"LLM Hatası: {e}")
    return ""


def _prepare_elements_for_overlay(elements, src_viewport, dst_viewport):
    """Kaynak viewport'tan canlı gösterim viewport'una güvenli ölçekleme yapar."""
    if not elements:
        return []

    src_w = max(1, int((src_viewport or {}).get("width", 1280)))
    src_h = max(1, int((src_viewport or {}).get("height", 720)))
    dst_w = max(1, int((dst_viewport or {}).get("width", src_w)))
    dst_h = max(1, int((dst_viewport or {}).get("height", src_h)))

    scale_x = dst_w / src_w
    scale_y = dst_h / src_h

    cleaned = []
    for el in elements:
        try:
            label = el.get("label", "unknown")
            score = float(el.get("score", 0))
            box = el.get("box", [])
            if len(box) != 4:
                continue
            if score < 0.30:
                continue

            x1, y1, x2, y2 = [float(v) for v in box]
            x1 = max(0.0, min(dst_w - 1.0, x1 * scale_x))
            y1 = max(0.0, min(dst_h - 1.0, y1 * scale_y))
            x2 = max(0.0, min(dst_w - 1.0, x2 * scale_x))
            y2 = max(0.0, min(dst_h - 1.0, y2 * scale_y))

            w = x2 - x1
            h = y2 - y1
            if w < 18 or h < 12:
                continue

            area_ratio = (w * h) / float(dst_w * dst_h)
            if area_ratio > 0.45:
                continue

            cleaned.append({
                "label": label,
                "score": score,
                "box": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)]
            })
        except Exception:
            continue

    cleaned.sort(key=lambda x: -x["score"])
    return cleaned[:70]


async def run_vision_inspector(url, elements=None, source_viewport=None):
    print(f"\n{'='*60}")
    print(f"  VisionQA — Canli AI Vizyon Inceleyici")
    print(f"  URL: {url}")
    print(f"  Element Sayisi: {len(elements) if elements else 'Bilinmiyor'}")
    print(f"{'='*60}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--start-maximized"])
        viewport = source_viewport or {"width": 1280, "height": 720}
        context = await browser.new_context(viewport=viewport)
        page = await context.new_page()

        # Sayfaya git
        print("  Sayfaya gidiliyor...")
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)

        # ═══ AI PANELİNİ OLUŞTUR ═══
        print("  AI Paneli aciliyor...")
        await page.evaluate("""() => {
            if (!document.getElementById('vq-style')) {
                const style = document.createElement('style');
                style.id = 'vq-style';
                style.textContent = `
                    #vq-panel.vq-collapsed {
                        transform: translateX(calc(100% - 42px));
                        opacity: 0.95;
                    }
                    #vq-panel.vq-collapsed #vq-body {
                        display: none;
                    }
                    #vq-toggle {
                        cursor: pointer;
                        border: 1px solid #00aa55;
                        background: #001d10;
                        color: #00ff88;
                        border-radius: 8px;
                        font-size: 11px;
                        font-weight: 700;
                        padding: 4px 8px;
                    }
                    #vq-fab {
                        position: fixed;
                        right: 10px;
                        top: 160px;
                        z-index: 2147483648;
                        cursor: pointer;
                        border: 1px solid #00aa55;
                        background: #001d10;
                        color: #00ff88;
                        border-radius: 10px;
                        font-size: 12px;
                        font-weight: 800;
                        padding: 8px 10px;
                        box-shadow: 0 0 12px rgba(0,255,136,0.25);
                    }
                    #vq-fab:hover {
                        background: #00331f;
                    }
                `;
                document.head.appendChild(style);
            }

            const panelWidth = Math.min(340, Math.max(260, Math.floor(window.innerWidth * 0.24)));
            const panel = document.createElement('div');
            panel.id = 'vq-panel';
            panel.setAttribute('style',
                'position:fixed;right:0;top:12px;width:' + panelWidth + 'px;height:calc(100vh - 24px);' +
                'background:rgba(8,8,24,0.96);border-left:2px solid #00ff00;' +
                'border-radius:12px;box-shadow:-8px 0 30px rgba(0,255,0,0.16);z-index:2147483647;' +
                'font-family:Consolas,monospace;color:#e0e0e0;overflow-y:auto;padding:0;' +
                'transition:transform 180ms ease;'
            );
            panel.classList.add('vq-collapsed');

            const hdr = document.createElement('div');
            hdr.setAttribute('style',
                'background:linear-gradient(90deg,#001a00,#003300);' +
                'padding:10px 12px;border-bottom:2px solid #00ff00;position:sticky;top:0;z-index:1;' +
                'display:flex;align-items:center;justify-content:space-between;gap:8px;'
            );
            hdr.innerHTML = '<div style="display:flex;align-items:center;gap:10px;min-width:0;">' +
                '<span style="font-size:22px;">🤖</span>' +
                '<div><div style="color:#00ff00;font-size:15px;font-weight:bold;letter-spacing:2px;">VisionQA AI</div>' +
                '<div style="color:#00aa00;font-size:10px;">Autonomous Intelligence Engine</div></div></div>';
            panel.appendChild(hdr);

            const body = document.createElement('div');
            body.id = 'vq-body';
            body.setAttribute('style', 'padding:14px 18px;');
            panel.appendChild(body);

            document.body.appendChild(panel);

            let fab = document.getElementById('vq-fab');
            if (!fab) {
                fab = document.createElement('button');
                fab.id = 'vq-fab';
                fab.textContent = 'AI';
                fab.setAttribute('title', 'AI panelini ac/kapat');
                document.body.appendChild(fab);
            }
            fab.addEventListener('click', () => {
                panel.classList.toggle('vq-collapsed');
                fab.textContent = panel.classList.contains('vq-collapsed') ? 'AI' : 'HIDE';
            });
        }""")
        await asyncio.sleep(0.3)

        # Yardımcı: Panele mesaj ekle
        async def add_msg(icon, title, body_text, color="#00ff00"):
            safe = body_text.replace("'", "\\'").replace("\n", "\\n")
            title_safe = title.replace("'", "\\'")
            await page.evaluate(f"""() => {{
                var c = document.getElementById('vq-body');
                if(!c) return;
                var d = document.createElement('div');
                d.setAttribute('style',
                    'margin-bottom:14px;padding:10px 14px;background:rgba(0,255,0,0.03);' +
                    'border:1px solid rgba(0,255,0,0.12);border-left:3px solid {color};' +
                    'border-radius:0 6px 6px 0;'
                );
                d.innerHTML = '<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">' +
                    '<span style="font-size:16px;">{icon}</span>' +
                    '<span style="color:{color};font-weight:bold;font-size:12px;letter-spacing:1px;">{title_safe}</span></div>' +
                    '<div style="color:#ccc;font-size:11px;line-height:1.6;white-space:pre-wrap;">' + '{safe}' + '</div>';
                c.appendChild(d);
                c.scrollTop = c.scrollHeight;
            }}""")

        # Yardımcı: Panele test case kartı ekle
        async def add_test_card(idx, title, category, risk):
            icons = {"happy_path":"✅","negative_path":"❌","edge_case":"⚠️","security":"🔒"}
            colors = {"happy_path":"#22c55e","negative_path":"#ef4444","edge_case":"#f59e0b","security":"#a855f7"}
            ic = icons.get(category, "📝")
            co = colors.get(category, "#00ff00")
            cat_label = category.replace("_"," ").upper()
            safe_t = title.replace("'", "\\'")
            await page.evaluate(f"""() => {{
                var c = document.getElementById('vq-body');
                if(!c) return;
                var d = document.createElement('div');
                d.setAttribute('style',
                    'margin-bottom:6px;padding:8px 12px;background:rgba(255,255,255,0.03);' +
                    'border:1px solid {co}33;border-radius:5px;display:flex;align-items:flex-start;gap:8px;'
                );
                d.innerHTML = '<span style="font-size:14px;margin-top:1px;">{ic}</span>' +
                    '<div><div style="color:{co};font-size:9px;font-weight:bold;letter-spacing:1px;margin-bottom:2px;">{cat_label} - {risk.upper()}</div>' +
                    '<div style="color:#ddd;font-size:11px;">{safe_t}</div></div>';
                c.appendChild(d);
                c.scrollTop = c.scrollHeight;
            }}""")

        # ═══ ADIM 1: Sayfa Yüklendi ═══
        await add_msg("🌐", "SAYFA YUKLENDI", f"URL: {url}\\nSayfa basariyla acildi.", "#00ff00")
        await asyncio.sleep(1)

        # ═══ ADIM 2: DINO Sonuçlarını Göster ═══
        normalized_elements = []
        if elements and len(elements) > 0:
            normalized_elements = _prepare_elements_for_overlay(
                elements,
                source_viewport or viewport,
                viewport
            )
            # Element özeti
            label_counts = {}
            for el in normalized_elements:
                lbl = el.get("label", "unknown")
                label_counts[lbl] = label_counts.get(lbl, 0) + 1
            summary = f"Toplam {len(normalized_elements)} element tespit edildi:\\n"
            for lbl, cnt in label_counts.items():
                summary += f"  - {lbl}: {cnt} adet\\n"

            await add_msg("🔍", f"DINO: {len(normalized_elements)} ELEMENT BULUNDU", summary, "#00aaff")
            await asyncio.sleep(1)

            # Kutuları çiz (sabit overlay katmanında; sayfa layoutunu bozmaz)
            await page.evaluate("""(elements) => {
                let root = document.getElementById('vq-overlay-root');
                if (!root) {
                    root = document.createElement('div');
                    root.id = 'vq-overlay-root';
                    root.setAttribute('style',
                        'position:fixed;inset:0;pointer-events:none;z-index:999998;overflow:hidden;'
                    );
                    document.body.appendChild(root);
                }
                root.innerHTML = '';

                elements.forEach(function(elem, index) {
                    var box = elem.box;
                    var label = elem.label;
                    var score = (elem.score * 100).toFixed(1);
                    var w = box[2] - box[0];
                    var h = box[3] - box[1];

                    var div = document.createElement('div');
                    div.setAttribute('style',
                        'position:absolute;left:'+box[0]+'px;top:'+box[1]+'px;width:'+w+'px;height:'+h+'px;' +
                        'border:3px solid #00FF00;box-shadow:0 0 15px #00FF00,inset 0 0 15px #00FF00;' +
                        'background:rgba(0,255,0,0.1);pointer-events:none;z-index:999999;' +
                        'transition:all 0.5s ease-in-out;transform:scale(1.5);opacity:0;'
                    );
                    setTimeout(function() {
                        div.style.transform = 'scale(1)';
                        div.style.opacity = '1';
                    }, index * 50);

                    var title = document.createElement('div');
                    title.innerText = label + ' (' + score + '%)';
                    title.setAttribute('style',
                        'position:absolute;top:-25px;left:-3px;background:#00FF00;color:#000;' +
                        'padding:2px 8px;font-size:12px;font-weight:bold;border-radius:4px 4px 0 0;white-space:nowrap;'
                    );
                    div.appendChild(title);
                    root.appendChild(div);
                });
            }""", normalized_elements)
            print("  DINO kutulari cizildi!")
            await asyncio.sleep(2)
        else:
            await add_msg("⚠️", "ELEMENT VERISI YOK", "Docker DINO verisi gondermedi.\\nURL bazli analiz yapiliyor...", "#f59e0b")

        # ═══ ADIM 3: LLM Sayfa Analizi ═══
        await add_msg("🧠", "LLM ANALIZ BASLIYOR", "Groq (Llama 3.3 70B) sayfayi tanimliyor...", "#a855f7")
        await asyncio.sleep(0.5)

        elements_text = ""
        if elements:
            for i, el in enumerate(normalized_elements[:30], 1):
                elements_text += f"  {i}. {el.get('label','?')} (skor: {el.get('score',0):.2f})\n"

        identity_prompt = f"""Analyze this web page and describe what you see in Turkish.

URL: {url}
Detected UI Elements:
{elements_text if elements_text else 'No elements detected, infer from URL.'}

Return JSON:
{{
    "page_description": "Bu sayfada ne gordugunun 3-4 cumlelik Turkce aciklamasi.",
    "page_type": "login|checkout|search|homepage|product|...",
    "element_list": ["element1", "element2", ...]
}}"""

        print("  LLM sayfa analizi yapiliyor...")
        identity_raw = call_llm(identity_prompt)
        identity = {}
        try:
            identity = json.loads(identity_raw)
        except:
            identity = {"page_description": "Sayfa analiz edilemedi.", "page_type": "unknown", "element_list": []}

        page_desc = identity.get("page_description", "Analiz yapilamadi.")
        page_type = identity.get("page_type", "unknown")
        el_list = identity.get("element_list", [])
        print(f"  LLM Sonuc: {page_type}")

        desc_text = f"Sayfa Tipi: {page_type.upper()}\\n\\n{page_desc}"
        if el_list:
            desc_text += "\\n\\nElementler:\\n"
            for e in el_list:
                desc_text += f"  - {e}\\n"

        await add_msg("📋", "SAYFA KIMLIGI BELIRLENDI", desc_text, "#22c55e")
        await asyncio.sleep(3)

        # ═══ ADIM 4: Test Case Üretimi Bilgisi ═══
        # Not: Gerçek test case üretimi ve DB kaydı backend /cases/generate akışında yapılır.
        # Burada ikinci bir LLM test üretimi yapmıyoruz; aksi halde paneldeki sayı ile
        # kütüphane/dashbord sayısı farklı görünebiliyor.
        await add_msg(
            "📝",
            "TEST SENARYOLARI BACKEND'DE URETILIYOR",
            "Canli panel yalnizca gorsel analiz ve sayfa kimligi gosterir. "
            "Nihai test adetini Test Library ekraninda goren sayi temsil eder.",
            "#f59e0b"
        )

        # ═══ FINAL ═══
        await add_msg("🏁", "ANALIZ TAMAMLANDI", "AI vizyonu tamamlandi.\\nPencere 15 saniye sonra kapanacak.", "#00ff00")

        report_path = os.path.join(os.path.dirname(__file__), "vision_report.png")
        await page.screenshot(path=report_path, full_page=False)
        print(f"  Rapor kaydedildi: {report_path}")

        await asyncio.sleep(15)
        print("  Tarayici kapaniyor.")
        await browser.close()


if __name__ == "__main__":
    # JSON dosyasından oku (Bridge'den) veya sadece URL ile çalış
    if len(sys.argv) > 1 and sys.argv[1].endswith('.json'):
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            data = json.load(f)
        target_url = data.get("url", "https://www.saucedemo.com")
        target_elements = data.get("elements", None)
        target_viewport = data.get("source_viewport", None)
        try:
            os.remove(sys.argv[1])
        except:
            pass
    else:
        target_url = sys.argv[1] if len(sys.argv) > 1 else "https://www.saucedemo.com"
        target_elements = None
        target_viewport = None

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(run_vision_inspector(target_url, target_elements, target_viewport))
