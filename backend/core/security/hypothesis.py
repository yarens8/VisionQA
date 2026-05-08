"""
Attack Hypothesis Generator
==============================
Generates attack hypotheses based on the inferred security context
and findings from visual/surface rules.

Each hypothesis represents a potential attack vector with playbook
steps, payload families, and confidence scoring.
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.security.context import SecurityContext


# ---------------------------------------------------------------------------
# Playbook / payload / role databases
# ---------------------------------------------------------------------------

_PLAYBOOKS: Dict[str, List[str]] = {
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

_PAYLOAD_FAMILIES: Dict[str, List[str]] = {
    "brute-force": ["credential-stuffing", "password-spray", "rate-limit-bypass"],
    "account-enumeration": ["response-diff", "timing-diff", "forgot-password-enumeration"],
    "sql-injection": ["boolean-based", "error-based", "union-based", "time-based"],
    "xss": ["reflected", "stored", "dom-based"],
    "file-upload-abuse": ["double-extension", "mime-mismatch", "content-sniffing"],
    "authorization-bypass": ["forced-browsing", "privilege-jump", "hidden-route-access"],
    "idor-mass-assignment": ["object-id-tampering", "field-overposting", "ownership-bypass"],
}

_ROLE_SCENARIOS: Dict[str, List[str]] = {
    "authorization-bypass": ["anon vs user", "user vs admin", "tenant-a vs tenant-b"],
    "idor-mass-assignment": ["anon vs user", "user vs admin", "tenant-a vs tenant-b"],
    "brute-force": ["known account vs unknown account", "locked user vs active user"],
    "account-enumeration": ["known account vs unknown account", "locked user vs active user"],
}
_DEFAULT_ROLE_SCENARIOS = ["single-user negative scenario", "authenticated vs unauthenticated"]


# ---------------------------------------------------------------------------
# Hypothesis data
# ---------------------------------------------------------------------------


def _priority_for(severity: str, confidence: int) -> int:
    base = 1 if severity == "high" else 2 if severity == "medium" else 3
    return base if confidence >= 75 else min(4, base + 1)


def _build_hypothesis(
    *,
    title: str,
    severity: str,
    attack_type: str,
    target_surface: str,
    rationale: str,
    confidence: int,
    evidence: List[str],
    recommended_test: str,
    preconditions: List[str],
    inferred_context: str,
) -> Dict[str, Any]:
    """Build a single hypothesis dict."""
    evidence_count = len([item for item in evidence if item])
    adjusted_confidence = min(
        96,
        confidence + max(0, evidence_count - 1) * 4 + (4 if severity == "high" else 0),
    )
    return {
        "id": 0,  # Assigned later
        "title": title,
        "severity": severity,
        "attack_type": attack_type,
        "inferred_context": inferred_context,
        "target_surface": target_surface,
        "rationale": rationale,
        "confidence": adjusted_confidence,
        "priority": _priority_for(severity, adjusted_confidence),
        "payload_families": _PAYLOAD_FAMILIES.get(attack_type, ["generic-negative-probe"]),
        "role_scenarios": _ROLE_SCENARIOS.get(attack_type, _DEFAULT_ROLE_SCENARIOS),
        "evidence": evidence[:5],
        "recommended_test": recommended_test,
        "preconditions": preconditions[:4],
        "playbook_steps": _PLAYBOOKS.get(attack_type, ["Kontrollu negatif senaryolarla davranis farklarini olc."]),
    }


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------


def generate_hypotheses(
    security_context: SecurityContext,
    visual_findings: List[Dict[str, Any]],
    surface_findings: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Generate attack hypotheses based on context + existing findings.

    Returns a list of hypothesis dicts, sorted by priority and confidence.
    """
    primary = security_context.primary
    hypotheses: List[Dict[str, Any]] = []

    if security_context.auth:
        has_error_leak = any(
            item.get("category") in {"error-leakage", "debug-page"}
            for item in surface_findings
        )
        hypotheses.append(_build_hypothesis(
            title="Credential abuse ve brute force hipotezi olustu",
            severity="high" if has_error_leak else "medium",
            attack_type="brute-force",
            target_surface="auth-flow",
            rationale="Login benzeri bir akis gorunuyor. Kimlik dogrulama ekranlari rate limit, lockout ve hata mesaji dili acisindan hedef olur.",
            confidence=84,
            evidence=(
                [item.get("title", "") for item in visual_findings[:2]]
                + [item.get("title", "") for item in surface_findings[:2]]
            ) or ["login / password sinyali"],
            recommended_test="Tekil ve artan hizlarda basit credential stuffing, lockout ve rate-limit senaryolari kos.",
            preconditions=["Login formu aktif olmali", "Rate-limit / captcha davranisi gozlenmeli"],
            inferred_context=primary,
        ))

    if security_context.enumeration or any(
        item.get("category") == "error-leakage" for item in surface_findings
    ):
        hypotheses.append(_build_hypothesis(
            title="Account enumeration testi denenmeli",
            severity="medium",
            attack_type="account-enumeration",
            target_surface="auth-messages",
            rationale="Auth hata dili kullanici varligi hakkinda farkli sinyal veriyor olabilir.",
            confidence=79,
            evidence=(
                [item.get("evidence", "") for item in surface_findings if item.get("category") == "error-leakage"]
                or ["user not found / wrong password ayrimi"]
            ),
            recommended_test="Var olan ve olmayan hesaplarla cevap farki, response body ve sure farki kontrolu yap.",
            preconditions=["Auth endpoint'ine kontrollu istek atilabilmeli"],
            inferred_context=primary,
        ))

    if security_context.search or security_context.sql:
        has_trace = any(
            item.get("category") == "stack-trace" for item in visual_findings
        )
        hypotheses.append(_build_hypothesis(
            title="Input yuzeyi icin SQL injection hipotezi var",
            severity="high" if security_context.sql or has_trace else "medium",
            attack_type="sql-injection",
            target_surface="input-query-surface",
            rationale="Arama veya input benzeri yuzeyler ve SQL/hata sinyalleri birlikte gorunuyor.",
            confidence=82 if security_context.sql else 68,
            evidence=(
                [item.get("title", "") for item in visual_findings if item.get("category") in {"stack-trace", "config-exposure"}]
                or ["search / query context"]
            ),
            recommended_test="Tek tirnak, union, boolean-based ve hata tabanli SQLi payload'lariyla kontrollu negatif test kos.",
            preconditions=["Input veya arama alani ulasilabilir olmali", "Backend response body gozlenmeli"],
            inferred_context=primary,
        ))

    if security_context.search or security_context.xss:
        hypotheses.append(_build_hypothesis(
            title="Reflected XSS veya unsafe output encoding hipotezi var",
            severity="medium",
            attack_type="xss",
            target_surface="search-or-input",
            rationale="Input alanlari ve tarayici tarafli rendering yuzeyleri script/encoding testleri icin uygundur.",
            confidence=74 if security_context.xss else 61,
            evidence=["input/search context", "response rendering surface"],
            recommended_test="Reflected ve stored XSS icin temel payload'larla output encoding ve CSP davranisini test et.",
            preconditions=["Input degeri response veya DOM icinde geri donmeli"],
            inferred_context=primary,
        ))

    if security_context.upload:
        hypotheses.append(_build_hypothesis(
            title="File upload abuse hipotezi var",
            severity="high",
            attack_type="file-upload-abuse",
            target_surface="upload-flow",
            rationale="Upload yuzeyleri content-type bypass, extension karisimi ve malware tasima gibi riskler dogurur.",
            confidence=86,
            evidence=["upload / choose file sinyali"],
            recommended_test="Double-extension, buyuk boyut, script icerikli ve beklenmeyen mime-type dosyalariyla upload kontrollerini dene.",
            preconditions=["Dosya yukleme aksiyonu calisiyor olmali"],
            inferred_context=primary,
        ))

    if security_context.admin or security_context.idor:
        hypotheses.append(_build_hypothesis(
            title="Forced browsing veya yetkilendirme atlama hipotezi var",
            severity="high",
            attack_type="authorization-bypass",
            target_surface="admin-or-resource-surface",
            rationale="Admin/panel veya kaynak kimligi tasiyan yuzeyler authz kontrolu acisindan kritik olur.",
            confidence=81,
            evidence=["admin / roles / id-based path sinyali"],
            recommended_test="Rol degistirmeden panel path'leri, ID parametreleri ve farkli kaynaklara erisimi dene.",
            preconditions=["Kimlikli ve sinirli yetkili iki farkli kullanici profili olmali"],
            inferred_context=primary,
        ))

    if security_context.api:
        hypotheses.append(_build_hypothesis(
            title="API tarafinda IDOR veya mass assignment riski denenmeli",
            severity="medium",
            attack_type="idor-mass-assignment",
            target_surface="api-surface",
            rationale="API/JSON yuzeyi gorunuyor. Bu tip endpoint'ler nesne seviyesinde yetki ve alan filtreleme zaaflari tasiyabilir.",
            confidence=71,
            evidence=["api/json/endpoint sinyali"],
            recommended_test="ID degistirme, beklenmeyen alan gonderme ve kaynak sahipligi manipule etme senaryolari kos.",
            preconditions=["API request/response yapisi gozlenebilmeli"],
            inferred_context=primary,
        ))

    # Assign sequential IDs and sort
    for idx, h in enumerate(hypotheses, start=1):
        h["id"] = idx

    hypotheses.sort(key=lambda item: (item["priority"], -item["confidence"]))
    return hypotheses
