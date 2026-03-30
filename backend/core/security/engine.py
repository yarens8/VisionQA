from __future__ import annotations

import io
import re
from typing import Dict, List, Optional

from PIL import Image, ImageDraw

from core.accessibility.engine import (
    _crop_to_base64,
    _detect_text_regions,
    _image_to_base64,
    _normalize_base64_image,
)


PII_PATTERNS = [
    ("email-exposure", "Maskelenmemis e-posta bilgisi gorunuyor", "medium", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I), "Kullaniciya acik bir e-posta adresi ekranda gorunuyor. Bu durum gereksiz veri ifsasi yaratabilir.", "E-posta bilgisini maskele veya sadece gerekli baglamda goster."),
    ("phone-exposure", "Maskelenmemis telefon bilgisi gorunuyor", "medium", re.compile(r"(?:(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{3}\)?[\s-]?)\d{3}[\s-]?\d{2,4}[\s-]?\d{2,4})"), "Telefon benzeri bir veri acik sekilde gorunuyor. Bu durum PII ifsasi riskini artirabilir.", "Telefon bilgisini parcali maskele veya sadece gerekli oldugunda goster."),
    ("token-exposure", "Token veya gizli anahtar benzeri veri gorunuyor", "high", re.compile(r"\b(?:bearer\s+[a-z0-9\-._~+/]+=*|sk_live_[a-z0-9]+|api[_-]?key|secret[_-]?key|x-api-key|authorization:\s*bearer)\b", re.I), "Token veya gizli anahtar benzeri bir ifade gorunuyor. Bu durum dogrudan gizli bilgi ifsasi olabilir.", "Token, key ve secret degerlerini istemci yuzeyinde asla acik gostermemelisin."),
    ("card-exposure", "Kart benzeri hassas veri gorunuyor", "high", re.compile(r"\b(?:\d[ -]*?){13,19}\b"), "Kart numarasina benzeyen bir veri gorunuyor. Bu alanin acik sekilde gosterilmesi ciddi guvenlik ve uyum riski yaratabilir.", "Kart numaralarini son 4 hane disinda maskele ve gorunur yuzeyden kaldir."),
]

DEBUG_PATTERNS = [
    ("stack-trace", "Stack trace veya exception detaylari gorunuyor", "high", re.compile(r"\b(traceback|exception|stack trace|nullreferenceexception|typeerror|referenceerror|sqlsyntaxerror|syntax error|stacktrace|unhandled exception|line \d+)\b", re.I), "Detayli hata izi son kullanici ekranina siziyor. Bu durum ic sistem yapisi ve kod akisi hakkinda fazla bilgi verebilir.", "Uretim ortaminda detayli exception ve stack trace ciktisini kullaniciya gostermeyi kapat."),
    ("debug-page", "Debug veya framework hata sayfasi sinyali var", "medium", re.compile(r"\b(debug|developer exception page|whitelabel error page|laravel|django|werkzeug|nextjs|express)\b", re.I), "Framework veya debug moduna ait hata ekranlari son kullaniciya gorunuyor olabilir.", "Debug modunu kapat ve son kullaniciya sade, guvenli hata mesaji goster."),
    ("config-exposure", "Ic konfigurasyon veya ortam bilgisi gorunuyor", "medium", re.compile(r"\b(localhost|127\.0\.0\.1|internal|staging|production|redis|postgres|mongodb|\.env|/var/www|c:\\\\|d:\\\\)\b", re.I), "Ortama veya servis altyapisina ait bilgi son kullanici ekranina siziyor olabilir.", "Environment, host, path ve servis detaylarini son kullanici ekranindan kaldir."),
]

AUTH_CONTEXT = re.compile(r"\b(login|sign in|signin|giris|password|sifre|otp|verification code|email address|telefon numarasi|remember me|forgot password)\b", re.I)
SEARCH_CONTEXT = re.compile(r"\b(search|ara|query|filter|sonuc|results)\b", re.I)
UPLOAD_CONTEXT = re.compile(r"\b(upload|yukle|dosya sec|choose file|drag and drop|attachment)\b", re.I)
ADMIN_CONTEXT = re.compile(r"\b(admin|dashboard|users|roles|permissions|settings|yonetici)\b", re.I)
PAYMENT_CONTEXT = re.compile(r"\b(card|payment|checkout|iban|odeme|credit card|billing)\b", re.I)
API_CONTEXT = re.compile(r"\b(api|json|graphql|endpoint|response|request|status code)\b", re.I)
ERROR_ENUMERATION_CONTEXT = re.compile(r"\b(user not found|email not found|wrong password|invalid password|hesap bulunamadi)\b", re.I)
SQL_SIGNAL = re.compile(r"\b(select|union|where|order by|drop table|insert into|sql)\b", re.I)
XSS_SIGNAL = re.compile(r"\b(<script>|javascript:|onerror=|alert\()\b", re.I)
ID_SIGNAL = re.compile(r"\b(user_id|account_id|customer_id|id=|/users/\d+|/accounts/\d+)\b", re.I)


def _best_text_region_for_match(text_regions: List[Dict], pattern: re.Pattern[str]) -> Optional[Dict]:
    for region in text_regions:
        if pattern.search(str(region.get("text", ""))):
            return region
    return text_regions[0] if text_regions else None


def _infer_contexts(text: str, url: Optional[str]) -> dict[str, bool]:
    combined = f"{text}\n{url or ''}"
    return {
        "auth": bool(AUTH_CONTEXT.search(combined)),
        "search": bool(SEARCH_CONTEXT.search(combined)),
        "upload": bool(UPLOAD_CONTEXT.search(combined)),
        "admin": bool(ADMIN_CONTEXT.search(combined)),
        "payment": bool(PAYMENT_CONTEXT.search(combined)),
        "api": bool(API_CONTEXT.search(combined) or (url and "/api" in url.lower())),
        "enumeration": bool(ERROR_ENUMERATION_CONTEXT.search(combined)),
        "sql": bool(SQL_SIGNAL.search(combined)),
        "xss": bool(XSS_SIGNAL.search(combined)),
        "idor": bool(ID_SIGNAL.search(combined)),
    }


def _rank_contexts(contexts: dict[str, bool]) -> list[str]:
    ordered = [
        "auth",
        "upload",
        "admin",
        "payment",
        "api",
        "search",
        "enumeration",
        "sql",
        "xss",
        "idor",
    ]
    return [name for name in ordered if contexts.get(name)]


def _playbook_steps_for(attack_type: str) -> list[str]:
    playbooks = {
        "brute-force": [
            "Tek kullanicida ard arda hatali denemeler ile rate-limit davranisini olc.",
            "Dagitilmis deneme ritminde lockout/captcha davranisini kontrol et.",
            "Basarisiz giris sonrasi telemetry ve alert izlerini dogrula.",
        ],
        "account-enumeration": [
            "Var olan ve olmayan hesaplarla ayni endpoint'e istek at.",
            "Hata mesaji govdesi, status code ve response time farklarini karsilastir.",
            "Password reset ve forgot-password akislarinda da ayni farki ara.",
        ],
        "sql-injection": [
            "Boolean-based SQLi payload'lariyla davranis farki olc.",
            "Error-based payload ile backend hata izi ve query ipucu ara.",
            "Union ve time-based varyasyonlari kontrollu sekilde dene.",
        ],
        "xss": [
            "Reflected payload'i response body veya DOM icinde geri donuyor mu kontrol et.",
            "Stored XSS icin kalici alanlara harmless payload kaydet.",
            "CSP ve output encoding davranisini ayni senaryoda gozle.",
        ],
        "file-upload-abuse": [
            "Double-extension ve mime mismatch dosyalari dene.",
            "Script icerikli veya beklenmeyen binary uzantilarini kontrol et.",
            "Yukleme sonrasi dosya erisim URL'lerinde execution/download farkini izle.",
        ],
        "authorization-bypass": [
            "Dusuk yetkili kullaniciyla yuksek yetkili route/path'leri dene.",
            "ID degisimi ile baska kaynaklara erisim var mi kontrol et.",
            "UI gizli olsa bile backend endpoint dogrudan acik mi test et.",
        ],
        "idor-mass-assignment": [
            "Kaynak ID degerini manipule et ve sahiplik kontrolunu dene.",
            "Beklenmeyen alanlari payload'a ekleyip alan filtrelemesini olc.",
            "Read/update/delete akislarinda nesne seviye authz farklarini ara.",
        ],
    }
    return playbooks.get(attack_type, ["Kontrollu negatif senaryolarla davranis farklarini olc."])


def _priority_for(severity: str, confidence: int) -> int:
    base = 1 if severity == "high" else 2 if severity == "medium" else 3
    return base if confidence >= 75 else min(4, base + 1)


def _payload_families_for(attack_type: str) -> list[str]:
    mapping = {
        "brute-force": ["credential-stuffing", "password-spray", "rate-limit-bypass"],
        "account-enumeration": ["response-diff", "timing-diff", "forgot-password-enumeration"],
        "sql-injection": ["boolean-based", "error-based", "union-based", "time-based"],
        "xss": ["reflected", "stored", "dom-based"],
        "file-upload-abuse": ["double-extension", "mime-mismatch", "content-sniffing"],
        "authorization-bypass": ["forced-browsing", "privilege-jump", "hidden-route-access"],
        "idor-mass-assignment": ["object-id-tampering", "field-overposting", "ownership-bypass"],
    }
    return mapping.get(attack_type, ["generic-negative-probe"])


def _role_scenarios_for(attack_type: str) -> list[str]:
    if attack_type in {"authorization-bypass", "idor-mass-assignment"}:
        return ["anon vs user", "user vs admin", "tenant-a vs tenant-b"]
    if attack_type in {"brute-force", "account-enumeration"}:
        return ["known account vs unknown account", "locked user vs active user"]
    return ["single-user negative scenario", "authenticated vs unauthenticated"]


def _score_from_counts(high_count: int, medium_count: int, low_count: int, floor: int) -> int:
    return max(floor, 100 - high_count * 26 - medium_count * 14 - low_count * 8)


def _build_overlay(image: Image.Image, findings: List[Dict]) -> str:
    overlay = image.convert("RGBA")
    draw = ImageDraw.Draw(overlay, "RGBA")
    for finding in findings[:8]:
        box = finding["bounding_box"]
        x1 = box["x"]
        y1 = box["y"]
        x2 = x1 + box["width"]
        y2 = y1 + box["height"]
        color = (248, 113, 113, 220) if finding["severity"] == "high" else (251, 191, 36, 220) if finding["severity"] == "medium" else (56, 189, 248, 220)
        draw.rectangle((x1, y1, x2, y2), outline=color, width=3)
        draw.rounded_rectangle((x1, max(0, y1 - 24), x1 + 34, max(0, y1) + 4), radius=8, fill=color)
        draw.text((x1 + 11, max(0, y1 - 18)), str(finding["id"]), fill=(15, 23, 42, 255))
    return _image_to_base64(overlay)


class SecurityEngine:
    def analyze_image(
        self,
        image_base64: str,
        *,
        platform: str = "web",
        response_text: str = "",
        response_headers: Optional[Dict[str, str]] = None,
        url: Optional[str] = None,
    ) -> Dict:
        image_bytes = _normalize_base64_image(image_base64)
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        text_regions = _detect_text_regions(image)
        all_text = " ".join(str(region.get("text", "")) for region in text_regions)
        combined_text = f"{all_text}\n{response_text or ''}".strip()
        contexts = _infer_contexts(combined_text, url)

        visual_findings: List[Dict] = []
        surface_findings: List[Dict] = []
        attack_hypotheses: List[Dict] = []
        attack_chains: List[Dict] = []
        root_causes: List[Dict] = []

        def build_finding(
            bucket: List[Dict],
            *,
            title: str,
            severity: str,
            layer: str,
            category: str,
            description: str,
            recommendation: str,
            region: Optional[Dict] = None,
            evidence: str = "",
        ) -> Dict:
            if region and len(region.get("box", [])) == 4:
                x1, y1, x2, y2 = [int(value) for value in region["box"]]
            else:
                x1, y1, x2, y2 = 0, 0, image.width, min(image.height, max(80, image.height // 3))
            finding = {
                "id": len(visual_findings) + len(surface_findings) + 1,
                "title": title,
                "severity": severity,
                "layer": layer,
                "category": category,
                "description": description,
                "bounding_box": {
                    "x": x1,
                    "y": y1,
                    "width": max(1, x2 - x1),
                    "height": max(1, y2 - y1),
                },
                "crop_image_base64": _crop_to_base64(image, x1, y1, max(1, x2 - x1), max(1, y2 - y1)),
                "recommendation": recommendation,
                "evidence": evidence[:180] or (region or {}).get("text", "")[:180],
            }
            bucket.append(finding)
            return finding

        for category, title, severity, pattern, description, recommendation in PII_PATTERNS + DEBUG_PATTERNS:
            match = pattern.search(combined_text)
            if not match:
                continue
            build_finding(
                visual_findings,
                title=title,
                severity=severity,
                layer="visual",
                category=category,
                description=description,
                recommendation=recommendation,
                region=_best_text_region_for_match(text_regions, pattern),
                evidence=match.group(0),
            )

        headers = {str(k).lower(): str(v) for k, v in (response_headers or {}).items()}
        header_checks = [
            ("content-security-policy", "CSP eksik veya zayif olabilir", "medium", "Tarayici tarafinda XSS etkisini azaltan CSP basligi gorunmuyor.", "Content-Security-Policy basligi ekleyerek izinli kaynaklari sinirla."),
            ("x-frame-options", "Clickjacking korumasi eksik olabilir", "medium", "X-Frame-Options basligi gorunmuyor. Sayfa frame icinde acilabilir.", "X-Frame-Options veya frame-ancestors CSP direktifi ekle."),
            ("x-content-type-options", "MIME sniffing korumasi eksik olabilir", "low", "X-Content-Type-Options basligi gorunmuyor.", "X-Content-Type-Options: nosniff basligini ekle."),
            ("referrer-policy", "Referrer policy eksik olabilir", "low", "Referrer-Policy basligi gorunmuyor.", "Referrer-Policy ile hassas yonlendirme bilgisini sinirla."),
        ]
        for header_name, title, severity, description, recommendation in header_checks:
            if headers and header_name not in headers:
                build_finding(
                    surface_findings,
                    title=title,
                    severity=severity,
                    layer="surface",
                    category="header-hardening",
                    description=description,
                    recommendation=recommendation,
                    evidence=header_name,
                )

        set_cookie = headers.get("set-cookie", "")
        if set_cookie:
            lowered_cookie = set_cookie.lower()
            if "secure" not in lowered_cookie:
                build_finding(surface_findings, title="Session cookie Secure flag tasimiyor olabilir", severity="medium", layer="surface", category="cookie-hardening", description="Set-Cookie icinde Secure niteligine dair net bir sinyal gorunmuyor.", recommendation="Session cookie'lerde Secure, HttpOnly ve SameSite niteliklerini zorunlu kil.", evidence=set_cookie)
            if "httponly" not in lowered_cookie:
                build_finding(surface_findings, title="Session cookie HttpOnly flag tasimiyor olabilir", severity="medium", layer="surface", category="cookie-hardening", description="HttpOnly olmadan cookie istemci script'leri tarafindan okunabilir hale gelebilir.", recommendation="Kimlik ve oturum cookie'lerinde HttpOnly bayragini ac.", evidence=set_cookie)
            if "samesite" not in lowered_cookie:
                build_finding(surface_findings, title="Session cookie SameSite korumasi tasimiyor olabilir", severity="low", layer="surface", category="cookie-hardening", description="SameSite tanimi olmayan cookie'ler CSRF riskini artirabilir.", recommendation="SameSite=Lax veya gerekiyorsa SameSite=Strict tercih et.", evidence=set_cookie)

        if url and url.startswith("http://"):
            build_finding(surface_findings, title="HTTPS kullanilmiyor", severity="high", layer="surface", category="transport-security", description="Sayfa HTTP uzerinden aciliyor. Trafik sifrelenmeden iletilebilir.", recommendation="Canli ortamlarda HTTPS zorunlu hale getir ve HSTS etkinlestir.", evidence=url)

        if ERROR_ENUMERATION_CONTEXT.search(combined_text):
            build_finding(surface_findings, title="Hata mesaji account enumeration sinyali tasiyor", severity="medium", layer="surface", category="error-leakage", description="Kullanici adi ve parola hatalarini ayri anlatan mesajlar hesap varligi bilgisini sizdirabilir.", recommendation="Auth hata mesaji dilini normalize et ve kullanici yok/parola yanlis ayrimini son kullaniciya acma.", evidence=ERROR_ENUMERATION_CONTEXT.search(combined_text).group(0))

        if "access-control-allow-origin: *" in combined_text.lower() or headers.get("access-control-allow-origin") == "*":
            build_finding(surface_findings, title="Genis CORS izinleri gorunuyor olabilir", severity="medium", layer="surface", category="cors-hardening", description="Yildizli CORS politikasi gereksiz genis alan aciyor olabilir.", recommendation="CORS izinlerini guvenilir origin listesi ile sinirla.", evidence=headers.get("access-control-allow-origin", "*"))

        ranked_contexts = _rank_contexts(contexts)
        primary_context = ranked_contexts[0] if ranked_contexts else "generic"

        def add_hypothesis(title: str, severity: str, attack_type: str, target_surface: str, rationale: str, confidence: int, evidence: List[str], recommended_test: str, preconditions: List[str], inferred_context: Optional[str] = None) -> None:
            evidence_count = len([item for item in evidence if item])
            adjusted_confidence = min(96, confidence + max(0, evidence_count - 1) * 4 + (4 if severity == "high" else 0))
            attack_hypotheses.append(
                {
                    "id": len(attack_hypotheses) + 1,
                    "title": title,
                    "severity": severity,
                    "attack_type": attack_type,
                    "inferred_context": inferred_context or primary_context,
                    "target_surface": target_surface,
                    "rationale": rationale,
                    "confidence": adjusted_confidence,
                    "priority": _priority_for(severity, adjusted_confidence),
                    "payload_families": _payload_families_for(attack_type),
                    "role_scenarios": _role_scenarios_for(attack_type),
                    "evidence": evidence[:5],
                    "recommended_test": recommended_test,
                    "preconditions": preconditions[:4],
                    "playbook_steps": _playbook_steps_for(attack_type),
                }
            )

        if contexts["auth"]:
            add_hypothesis(
                "Credential abuse ve brute force hipotezi olustu",
                "high" if any(item["category"] in {"error-leakage", "debug-page"} for item in surface_findings) else "medium",
                "brute-force",
                "auth-flow",
                "Login benzeri bir akis gorunuyor. Kimlik dogrulama ekranlari rate limit, lockout ve hata mesaji dili acisindan hedef olur.",
                84,
                [item["title"] for item in visual_findings[:2]] + [item["title"] for item in surface_findings[:2]] or ["login / password sinyali"],
                "Tekil ve artan hizlarda basit credential stuffing, lockout ve rate-limit senaryolari kos.",
                ["Login formu aktif olmali", "Rate-limit / captcha davranisi gozlenmeli"],
            )
        if contexts["enumeration"] or any(item["category"] == "error-leakage" for item in surface_findings):
            add_hypothesis(
                "Account enumeration testi denenmeli",
                "medium",
                "account-enumeration",
                "auth-messages",
                "Auth hata dili kullanici varligi hakkinda farkli sinyal veriyor olabilir.",
                79,
                [item["evidence"] for item in surface_findings if item["category"] == "error-leakage"] or ["user not found / wrong password ayrimi"],
                "Var olan ve olmayan hesaplarla cevap farki, response body ve sure farki kontrolu yap.",
                ["Auth endpoint'ine kontrollu istek atilabilmeli"],
            )
        if contexts["search"] or contexts["sql"]:
            add_hypothesis(
                "Input yuzeyi icin SQL injection hipotezi var",
                "high" if contexts["sql"] or any(item["category"] == "stack-trace" for item in visual_findings) else "medium",
                "sql-injection",
                "input-query-surface",
                "Arama veya input benzeri yuzeyler ve SQL/hata sinyalleri birlikte gorunuyor. Bu, query birlestirme veya yetersiz validation riskini isaret edebilir.",
                82 if contexts["sql"] else 68,
                [item["title"] for item in visual_findings if item["category"] in {"stack-trace", "config-exposure"}] or ["search / query context"],
                "Tek tirnak, union, boolean-based ve hata tabanli SQLi payload'lariyla kontrollu negatif test kos.",
                ["Input veya arama alani ulasilabilir olmali", "Backend response body gozlenmeli"],
            )
        if contexts["search"] or contexts["xss"]:
            add_hypothesis(
                "Reflected XSS veya unsafe output encoding hipotezi var",
                "medium",
                "xss",
                "search-or-input",
                "Input alanlari ve tarayici tarafli rendering yuzeyleri script/encoding testleri icin uygundur.",
                74 if contexts["xss"] else 61,
                ["input/search context", "response rendering surface"],
                "Reflected ve stored XSS icin temel payload'larla output encoding ve CSP davranisini test et.",
                ["Input degeri response veya DOM icinde geri donmeli"],
            )
        if contexts["upload"]:
            add_hypothesis(
                "File upload abuse hipotezi var",
                "high",
                "file-upload-abuse",
                "upload-flow",
                "Upload yuzeyleri content-type bypass, extension karisimi ve malware tasima gibi riskler dogurur.",
                86,
                ["upload / choose file sinyali"],
                "Double-extension, buyuk boyut, script icerikli ve beklenmeyen mime-type dosyalariyla upload kontrollerini dene.",
                ["Dosya yukleme aksiyonu calisiyor olmali"],
            )
        if contexts["admin"] or contexts["idor"]:
            add_hypothesis(
                "Forced browsing veya yetkilendirme atlama hipotezi var",
                "high",
                "authorization-bypass",
                "admin-or-resource-surface",
                "Admin/panel veya kaynak kimligi tasiyan yuzeyler authz kontrolu acisindan kritik olur.",
                81,
                ["admin / roles / id-based path sinyali"],
                "Rol degistirmeden panel path'leri, ID parametreleri ve farkli kaynaklara erisimi dene.",
                ["Kimlikli ve sinirli yetkili iki farkli kullanici profili olmali"],
            )
        if contexts["api"]:
            add_hypothesis(
                "API tarafinda IDOR veya mass assignment riski denenmeli",
                "medium",
                "idor-mass-assignment",
                "api-surface",
                "API/JSON yuzeyi gorunuyor. Bu tip endpoint'ler nesne seviyesinde yetki ve alan filtreleme zaaflari tasiyabilir.",
                71,
                ["api/json/endpoint sinyali"],
                "ID degistirme, beklenmeyen alan gonderme ve kaynak sahipligi manipule etme senaryolari kos.",
                ["API request/response yapisi gozlenebilmeli"],
            )

        findings = visual_findings + surface_findings

        def add_chain(title: str, severity: str, summary: str, linked_layers: List[str], evidence: List[str], attack_path: List[str], remediation_path: List[str], linked_hypothesis_ids: List[int], linked_finding_ids: List[int], confidence: int, linked_modules: List[str]) -> None:
            attack_chains.append(
                {
                    "id": len(attack_chains) + 1,
                    "title": title,
                    "severity": severity,
                    "confidence": confidence,
                    "summary": summary,
                    "linked_layers": linked_layers,
                    "linked_modules": linked_modules,
                    "linked_hypothesis_ids": linked_hypothesis_ids[:6],
                    "linked_finding_ids": linked_finding_ids[:8],
                    "evidence": evidence[:6],
                    "attack_path": attack_path[:5],
                    "remediation_path": remediation_path[:5],
                }
            )

        if contexts["auth"] and any(h["attack_type"] == "brute-force" for h in attack_hypotheses) and any(item["category"] == "error-leakage" for item in surface_findings):
            add_chain("Auth abuse attack chain sinyali olustu", "high", "Login ekrani, ayristirici hata mesaji ve saldiri hipotezleri birlikte credential abuse zinciri olusturuyor.", ["visual", "surface", "hypothesis"], [item["title"] for item in surface_findings if item["category"] == "error-leakage"] + ["auth flow context"], ["Login yuzeyi tespit edildi", "Auth hata dili hesap varligi bilgisi veriyor olabilir", "Brute force veya enumeration testi uygulanabilir", "Guclu lockout/rate-limit yoksa hesap suistimali kolaylasir"], ["Auth hata mesaji dilini normalize et", "Rate-limit, lockout ve captcha stratejisini ekle", "Suspicious login telemetry'sini izle"], [item["id"] for item in attack_hypotheses if item["attack_type"] in {"brute-force", "account-enumeration"}], [item["id"] for item in surface_findings if item["category"] == "error-leakage"], 86, ["security", "api"])
        if any(item["category"] in {"stack-trace", "config-exposure"} for item in visual_findings) and any(h["attack_type"] == "sql-injection" for h in attack_hypotheses):
            add_chain("Input to backend exception chain riski var", "high", "Input yuzeyi ile detayli hata/stack trace sinyalleri birlikte backend query veya validation zaafini aciga cikariyor olabilir.", ["visual", "hypothesis", "correlation"], [item["title"] for item in visual_findings if item["category"] in {"stack-trace", "config-exposure"}], ["Saldirgan input alanina zararli payload yollar", "Backend hata veya exception detayi response/screenshot'ta gorunur", "Bu bilgi ile query yapisi veya framework davranisi keskinlestirilir", "Sonraki exploit denemeleri daha hedefli hale gelir"], ["Parameterized query ve server-side validation kullan", "Exception sanitization uygula", "Uretim modunda debug detaylarini kapat"], [item["id"] for item in attack_hypotheses if item["attack_type"] == "sql-injection"], [item["id"] for item in visual_findings if item["category"] in {"stack-trace", "config-exposure"}], 82, ["security", "api", "database"])
        if any(item["category"] == "header-hardening" for item in surface_findings) and any(h["attack_type"] == "xss" for h in attack_hypotheses):
            add_chain("Client-side exploit amplification chain sinyali var", "medium", "Header sertlestirme eksikleri ve XSS hipotezi birlikte istemci tarafli exploit etkisini buyutebilir.", ["surface", "hypothesis", "correlation"], [item["title"] for item in surface_findings if item["category"] == "header-hardening"], ["Input veya rendering yuzeyi script enjeksiyonuna acik olabilir", "CSP veya frame korumalari zayifsa exploit etkisi artar", "Tarayici katmaninda savunma bariyerleri azaldigi icin istismar kolaylasir"], ["CSP ve related security headers ekle", "Output encoding ve template escaping sertlestir", "DOM sink kullanimini denetle"], [item["id"] for item in attack_hypotheses if item["attack_type"] == "xss"], [item["id"] for item in surface_findings if item["category"] == "header-hardening"], 73, ["security", "web"])

        def add_root_cause(title: str, severity: str, summary: str, linked_categories: List[str], recommendations: List[str], taxonomy: str, confidence: int, remediation_bundles: dict[str, List[str]]) -> None:
            root_causes.append(
                {
                    "id": len(root_causes) + 1,
                    "title": title,
                    "severity": severity,
                    "taxonomy": taxonomy,
                    "confidence": confidence,
                    "summary": summary,
                    "linked_categories": linked_categories[:6],
                    "recommendations": recommendations[:5],
                    "remediation_bundles": remediation_bundles,
                }
            )

        if any(item["category"] in {"stack-trace", "debug-page", "config-exposure"} for item in visual_findings):
            add_root_cause("Exception sanitization ve ortam ayrimi zayif olabilir", "high", "Debug ayrintilarinin son kullanici yuzeyine sizmasi, uretim-hata yonetimi ayriminin net olmadigini gosterebilir.", [item["category"] for item in visual_findings if item["category"] in {"stack-trace", "debug-page", "config-exposure"}], ["Uretim ortaminda detayli exception render etme", "Framework debug page'lerini kapat", "Error telemetry ile user-facing mesaj katmanini ayir"], "error-handling", 88, {"immediate": ["Debug ekranini kapat", "Son kullanici hata mesajini sadeleştir"], "backend": ["Exception middleware sanitization ekle"], "testing": ["Regression olarak error page exposure testi ekle"]})
        if any(item["category"] in {"header-hardening", "cookie-hardening", "transport-security", "cors-hardening"} for item in surface_findings):
            add_root_cause("Surface hardening baseline'i eksik olabilir", "medium", "Header, cookie ve transport sertlestirmesi parca parca eksik gorunuyor. Bu durum savunma derinligini azaltir.", [item["category"] for item in surface_findings if item["category"] in {"header-hardening", "cookie-hardening", "transport-security", "cors-hardening"}], ["Standart header policy seti tanimla", "Cookie security attribute'lerini varsayilan yap", "HTTPS ve HSTS politikasini zorunlu kil"], "hardening-baseline", 80, {"immediate": ["Eksik header setini tamamla"], "infra": ["TLS ve HSTS policy zorunlulugu ekle"], "testing": ["Header baseline smoke test'i yaz"]})
        if any(h["attack_type"] in {"brute-force", "account-enumeration"} for h in attack_hypotheses):
            add_root_cause("Auth flow defensive controls yetersiz olabilir", "medium", "Login ve hesap dogrulama akislarinda suistimali yavaslatacak kontrol katmanlari zayif olabilir.", ["brute-force", "account-enumeration"], ["Rate-limit / lockout / MFA stratejisi ekle", "Auth hata dili ve sure davranisini normalize et", "Risk-based authentication telemetry kullan"], "authentication-defense", 76, {"immediate": ["Auth hata dilini normalize et"], "backend": ["Rate-limit ve lockout ekle"], "testing": ["Credential abuse negatif testleri otomatiklestir"]})

        visual_high = sum(1 for item in visual_findings if item["severity"] == "high")
        visual_medium = sum(1 for item in visual_findings if item["severity"] == "medium")
        visual_low = sum(1 for item in visual_findings if item["severity"] == "low")
        surface_high = sum(1 for item in surface_findings if item["severity"] == "high")
        surface_medium = sum(1 for item in surface_findings if item["severity"] == "medium")
        surface_low = sum(1 for item in surface_findings if item["severity"] == "low")
        hypothesis_high = sum(1 for item in attack_hypotheses if item["severity"] == "high")
        hypothesis_medium = sum(1 for item in attack_hypotheses if item["severity"] == "medium")
        hypothesis_low = sum(1 for item in attack_hypotheses if item["severity"] == "low")
        chain_high = sum(1 for item in attack_chains if item["severity"] == "high")
        chain_medium = sum(1 for item in attack_chains if item["severity"] == "medium")
        chain_low = sum(1 for item in attack_chains if item["severity"] == "low")

        visual_score = _score_from_counts(visual_high, visual_medium, visual_low, 28)
        surface_score = _score_from_counts(surface_high, surface_medium, surface_low, 28)
        hypothesis_score = _score_from_counts(hypothesis_high, hypothesis_medium, hypothesis_low, 24)
        correlation_score = _score_from_counts(chain_high, chain_medium, chain_low, 24)
        overall_score = int((visual_score * 0.32) + (surface_score * 0.28) + (hypothesis_score * 0.22) + (correlation_score * 0.18))

        attack_hypotheses.sort(key=lambda item: (item["priority"], -item["confidence"]))
        attack_chains.sort(key=lambda item: (-item["confidence"], item["severity"] != "high"))
        root_causes.sort(key=lambda item: (-item["confidence"], item["severity"] != "high"))
        attack_readiness = max(18, min(96, int((len(attack_hypotheses) * 12) + (len(attack_chains) * 16) + (100 - overall_score) * 0.4)))

        if findings or attack_hypotheses or attack_chains:
            overview = f"Security Intelligence taramasi {len(findings)} bulgu, {len(attack_hypotheses)} saldiri hipotezi ve {len(attack_chains)} attack chain sinyali uretti. Odak alanlari veri ifsasi, surface hardening ve baglama gore denenmesi gereken saldiri siniflari oldu."
        else:
            overview = "Security Intelligence taramasi gorunur bir veri ifsasi, belirgin surface zafiyeti veya saldiri hipotezi uretmedi."

        layer_summary = {
            "visual": {"score": visual_score, "count": len(visual_findings), "overview": "Screenshot, OCR ve metadata tabanli gorunur riskler."},
            "surface": {"score": surface_score, "count": len(surface_findings), "overview": "URL, response body, header ve transport hardening sinyalleri."},
            "hypotheses": {"score": hypothesis_score, "count": len(attack_hypotheses), "overview": "Baglama gore denenmesi gereken saldiri hipotezleri ve test fikirleri."},
            "correlation": {"score": correlation_score, "count": len(attack_chains) + len(root_causes), "overview": "Katmanlar arasi iliski, attack chain ve muhtemel kok neden yorumlari."},
        }

        cross_module_hints = []
        if any(h["attack_type"] in {"sql-injection", "idor-mass-assignment"} for h in attack_hypotheses):
            cross_module_hints.append(
                {
                    "module": "api-test",
                    "reason": "Input ve API yuzeyi birlikte request/response tabanli negatif testleri hakli cikariyor.",
                    "suggested_action": "Ayni URL veya ilgili endpoint icin 4.8 API modulunde negatif schema ve authz senaryolari kos.",
                    "priority": 1,
                }
            )
        if any(h["attack_type"] == "sql-injection" for h in attack_hypotheses):
            cross_module_hints.append(
                {
                    "module": "db-test",
                    "reason": "SQLi veya query davranisi sinyalleri veritabani katmanina dogru zincir riski tasiyor.",
                    "suggested_action": "4.10 DB modulunde query timing, schema ve riskli sorgu sinyallerini kontrol et.",
                    "priority": 1,
                }
            )
        if any(h["attack_type"] in {"brute-force", "account-enumeration"} for h in attack_hypotheses):
            cross_module_hints.append(
                {
                    "module": "scenarios",
                    "reason": "Role-based ve multi-user auth suistimali senaryolari icin coklu profil kurgusu gerekiyor.",
                    "suggested_action": "Farkli kullanici/rol profilleri ile auth ve resource erisim senaryolari olustur.",
                    "priority": 2,
                }
            )

        unique_recommendations = list(dict.fromkeys([item["recommendation"] for item in findings] + [item["recommended_test"] for item in attack_hypotheses] + [step for chain in attack_chains for step in chain["remediation_path"]] + [step for cause in root_causes for step in cause["recommendations"]]))

        return {
            "platform": platform,
            "image": {"width": image.width, "height": image.height},
            "overall_score": overall_score,
            "overview": overview,
            "visual_score": visual_score,
            "surface_score": surface_score,
            "hypothesis_score": hypothesis_score,
            "correlation_score": correlation_score,
            "findings": findings[:10],
            "visual_findings": visual_findings[:6],
            "surface_findings": surface_findings[:6],
            "attack_hypotheses": attack_hypotheses[:6],
            "attack_chains": attack_chains[:4],
            "root_causes": root_causes[:4],
            "artifacts": {"overlay_image_base64": _build_overlay(image, findings), "source_image_base64": _image_to_base64(image)},
            "header_summary": {"checked": len(header_checks), "missing": len([item for item in surface_findings if item["category"] == "header-hardening"])},
            "layer_summary": layer_summary,
            "context_profile": {
                "primary_context": primary_context,
                "detected_contexts": ranked_contexts,
                "attack_readiness": attack_readiness,
            },
            "cross_module_hints": cross_module_hints,
            "recommendations": unique_recommendations or ["Response header sertlestirmesini, auth hata dili ve exception sanitization katmanini tekrar kontrol et."],
        }
