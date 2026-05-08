"""
Attack Chain & Root Cause Analysis
=====================================
Correlates visual findings, surface findings, and attack hypotheses
to detect multi-layer attack chains and infer root causes.
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.security.context import SecurityContext


# ---------------------------------------------------------------------------
# Attack chains
# ---------------------------------------------------------------------------

def build_attack_chains(
    security_context: SecurityContext,
    visual_findings: List[Dict[str, Any]],
    surface_findings: List[Dict[str, Any]],
    attack_hypotheses: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Detect cross-layer attack chains.

    Each chain links findings from different layers (visual, surface,
    hypothesis) that together represent a compounding risk.
    """
    chains: List[Dict[str, Any]] = []

    # Chain 1: Auth abuse
    if (
        security_context.auth
        and any(h.get("attack_type") == "brute-force" for h in attack_hypotheses)
        and any(item.get("category") == "error-leakage" for item in surface_findings)
    ):
        chains.append({
            "id": len(chains) + 1,
            "title": "Auth abuse attack chain sinyali olustu",
            "severity": "high",
            "confidence": 86,
            "summary": "Login ekrani, ayristirici hata mesaji ve saldiri hipotezleri birlikte credential abuse zinciri olusturuyor.",
            "linked_layers": ["visual", "surface", "hypothesis"],
            "linked_modules": ["security", "api"],
            "linked_hypothesis_ids": [
                h["id"] for h in attack_hypotheses
                if h.get("attack_type") in {"brute-force", "account-enumeration"}
            ][:6],
            "linked_finding_ids": [
                item["id"] for item in surface_findings
                if item.get("category") == "error-leakage"
            ][:8],
            "evidence": (
                [item.get("title", "") for item in surface_findings if item.get("category") == "error-leakage"]
                + ["auth flow context"]
            )[:6],
            "attack_path": [
                "Login yuzeyi tespit edildi",
                "Auth hata dili hesap varligi bilgisi veriyor olabilir",
                "Brute force veya enumeration testi uygulanabilir",
                "Guclu lockout/rate-limit yoksa hesap suistimali kolaylasir",
            ],
            "remediation_path": [
                "Auth hata mesaji dilini normalize et",
                "Rate-limit, lockout ve captcha stratejisini ekle",
                "Suspicious login telemetry'sini izle",
            ],
        })

    # Chain 2: Input → backend exception
    if (
        any(item.get("category") in {"stack-trace", "config-exposure"} for item in visual_findings)
        and any(h.get("attack_type") == "sql-injection" for h in attack_hypotheses)
    ):
        chains.append({
            "id": len(chains) + 1,
            "title": "Input to backend exception chain riski var",
            "severity": "high",
            "confidence": 82,
            "summary": "Input yuzeyi ile detayli hata/stack trace sinyalleri birlikte backend query veya validation zaafini aciga cikariyor olabilir.",
            "linked_layers": ["visual", "hypothesis", "correlation"],
            "linked_modules": ["security", "api", "database"],
            "linked_hypothesis_ids": [
                h["id"] for h in attack_hypotheses
                if h.get("attack_type") == "sql-injection"
            ][:6],
            "linked_finding_ids": [
                item["id"] for item in visual_findings
                if item.get("category") in {"stack-trace", "config-exposure"}
            ][:8],
            "evidence": [
                item.get("title", "") for item in visual_findings
                if item.get("category") in {"stack-trace", "config-exposure"}
            ][:6],
            "attack_path": [
                "Saldirgan input alanina zararli payload yollar",
                "Backend hata veya exception detayi response/screenshot'ta gorunur",
                "Bu bilgi ile query yapisi veya framework davranisi keskinlestirilir",
                "Sonraki exploit denemeleri daha hedefli hale gelir",
            ],
            "remediation_path": [
                "Parameterized query ve server-side validation kullan",
                "Exception sanitization uygula",
                "Uretim modunda debug detaylarini kapat",
            ],
        })

    # Chain 3: Client-side exploit amplification
    if (
        any(item.get("category") == "header-hardening" for item in surface_findings)
        and any(h.get("attack_type") == "xss" for h in attack_hypotheses)
    ):
        chains.append({
            "id": len(chains) + 1,
            "title": "Client-side exploit amplification chain sinyali var",
            "severity": "medium",
            "confidence": 73,
            "summary": "Header sertlestirme eksikleri ve XSS hipotezi birlikte istemci tarafli exploit etkisini buyutebilir.",
            "linked_layers": ["surface", "hypothesis", "correlation"],
            "linked_modules": ["security", "web"],
            "linked_hypothesis_ids": [
                h["id"] for h in attack_hypotheses
                if h.get("attack_type") == "xss"
            ][:6],
            "linked_finding_ids": [
                item["id"] for item in surface_findings
                if item.get("category") == "header-hardening"
            ][:8],
            "evidence": [
                item.get("title", "") for item in surface_findings
                if item.get("category") == "header-hardening"
            ][:6],
            "attack_path": [
                "Input veya rendering yuzeyi script enjeksiyonuna acik olabilir",
                "CSP veya frame korumalari zayifsa exploit etkisi artar",
                "Tarayici katmaninda savunma bariyerleri azaldigi icin istismar kolaylasir",
            ],
            "remediation_path": [
                "CSP ve related security headers ekle",
                "Output encoding ve template escaping sertlestir",
                "DOM sink kullanimini denetle",
            ],
        })

    chains.sort(key=lambda item: (-item["confidence"], item["severity"] != "high"))
    return chains


# ---------------------------------------------------------------------------
# Root causes
# ---------------------------------------------------------------------------

def build_root_causes(
    visual_findings: List[Dict[str, Any]],
    surface_findings: List[Dict[str, Any]],
    attack_hypotheses: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Infer root causes from the aggregate finding and hypothesis set.
    """
    causes: List[Dict[str, Any]] = []

    # Debug/exception exposure root cause
    if any(item.get("category") in {"stack-trace", "debug-page", "config-exposure"} for item in visual_findings):
        causes.append({
            "id": len(causes) + 1,
            "title": "Exception sanitization ve ortam ayrimi zayif olabilir",
            "severity": "high",
            "taxonomy": "error-handling",
            "confidence": 88,
            "summary": "Debug ayrintilarinin son kullanici yuzeyine sizmasi, uretim-hata yonetimi ayriminin net olmadigini gosterebilir.",
            "linked_categories": [
                item.get("category") for item in visual_findings
                if item.get("category") in {"stack-trace", "debug-page", "config-exposure"}
            ][:6],
            "recommendations": [
                "Uretim ortaminda detayli exception render etme",
                "Framework debug page'lerini kapat",
                "Error telemetry ile user-facing mesaj katmanini ayir",
            ],
            "remediation_bundles": {
                "immediate": ["Debug ekranini kapat", "Son kullanici hata mesajini sadeleştir"],
                "backend": ["Exception middleware sanitization ekle"],
                "testing": ["Regression olarak error page exposure testi ekle"],
            },
        })

    # Surface hardening gap
    hardening_categories = {"header-hardening", "cookie-hardening", "transport-security", "cors-hardening"}
    if any(item.get("category") in hardening_categories for item in surface_findings):
        causes.append({
            "id": len(causes) + 1,
            "title": "Surface hardening baseline'i eksik olabilir",
            "severity": "medium",
            "taxonomy": "hardening-baseline",
            "confidence": 80,
            "summary": "Header, cookie ve transport sertlestirmesi parca parca eksik gorunuyor. Bu durum savunma derinligini azaltir.",
            "linked_categories": [
                item.get("category") for item in surface_findings
                if item.get("category") in hardening_categories
            ][:6],
            "recommendations": [
                "Standart header policy seti tanimla",
                "Cookie security attribute'lerini varsayilan yap",
                "HTTPS ve HSTS politikasini zorunlu kil",
            ],
            "remediation_bundles": {
                "immediate": ["Eksik header setini tamamla"],
                "infra": ["TLS ve HSTS policy zorunlulugu ekle"],
                "testing": ["Header baseline smoke test'i yaz"],
            },
        })

    # Auth defense gaps
    if any(h.get("attack_type") in {"brute-force", "account-enumeration"} for h in attack_hypotheses):
        causes.append({
            "id": len(causes) + 1,
            "title": "Auth flow defensive controls yetersiz olabilir",
            "severity": "medium",
            "taxonomy": "authentication-defense",
            "confidence": 76,
            "summary": "Login ve hesap dogrulama akislarinda suistimali yavaslatacak kontrol katmanlari zayif olabilir.",
            "linked_categories": ["brute-force", "account-enumeration"],
            "recommendations": [
                "Rate-limit / lockout / MFA stratejisi ekle",
                "Auth hata dili ve sure davranisini normalize et",
                "Risk-based authentication telemetry kullan",
            ],
            "remediation_bundles": {
                "immediate": ["Auth hata dilini normalize et"],
                "backend": ["Rate-limit ve lockout ekle"],
                "testing": ["Credential abuse negatif testleri otomatiklestir"],
            },
        })

    causes.sort(key=lambda item: (-item["confidence"], item["severity"] != "high"))
    return causes
