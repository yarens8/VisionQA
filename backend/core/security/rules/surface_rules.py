"""
Surface Detection Rules — Headers, Cookies, Transport, CORS, Error Leakage
============================================================================
Rules that examine HTTP response headers, cookies, transport security,
and error message patterns.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from core.interfaces.types import AnalysisContext, AnalysisLayer, Finding, Severity
from core.interfaces.rules import Rule
from core.security.context import ERROR_ENUMERATION_CONTEXT


# ---------------------------------------------------------------------------
# Header hardening
# ---------------------------------------------------------------------------

_HEADER_CHECKS = [
    (
        "content-security-policy",
        "CSP eksik veya zayif olabilir",
        Severity.MEDIUM,
        "Tarayici tarafinda XSS etkisini azaltan CSP basligi gorunmuyor.",
        "Content-Security-Policy basligi ekleyerek izinli kaynaklari sinirla.",
    ),
    (
        "x-frame-options",
        "Clickjacking korumasi eksik olabilir",
        Severity.MEDIUM,
        "X-Frame-Options basligi gorunmuyor. Sayfa frame icinde acilabilir.",
        "X-Frame-Options veya frame-ancestors CSP direktifi ekle.",
    ),
    (
        "x-content-type-options",
        "MIME sniffing korumasi eksik olabilir",
        Severity.LOW,
        "X-Content-Type-Options basligi gorunmuyor.",
        "X-Content-Type-Options: nosniff basligini ekle.",
    ),
    (
        "referrer-policy",
        "Referrer policy eksik olabilir",
        Severity.LOW,
        "Referrer-Policy basligi gorunmuyor.",
        "Referrer-Policy ile hassas yonlendirme bilgisini sinirla.",
    ),
]


class HeaderHardeningRule(Rule):
    """Checks for missing security-critical HTTP response headers."""

    name = "header-hardening"
    category = "header-hardening"
    description = "HTTP response header sertlestirme kontrolu"

    def should_run(self, context: AnalysisContext) -> bool:
        return self.enabled and bool(context.response_headers)

    def evaluate(self, context: AnalysisContext, state: Dict[str, Any]) -> List[Finding]:
        headers = {
            str(k).lower(): str(v)
            for k, v in (context.response_headers or {}).items()
        }
        if not headers:
            return []

        # Store normalized headers in state for other rules
        state["normalized_headers"] = headers
        state["header_checks_total"] = len(_HEADER_CHECKS)

        findings: List[Finding] = []
        for header_name, title, severity, description, recommendation in _HEADER_CHECKS:
            if header_name not in headers:
                findings.append(Finding(
                    id=0,
                    title=title,
                    severity=severity,
                    category="header-hardening",
                    layer=AnalysisLayer.SURFACE,
                    description=description,
                    recommendation=recommendation,
                    evidence=header_name,
                ))

        state["header_missing_count"] = len(findings)
        return findings


# ---------------------------------------------------------------------------
# Cookie hardening
# ---------------------------------------------------------------------------

class CookieHardeningRule(Rule):
    """Checks Set-Cookie headers for Secure, HttpOnly, SameSite flags."""

    name = "cookie-hardening"
    category = "cookie-hardening"
    description = "Session cookie guvenlik nitelikleri kontrolu"

    def should_run(self, context: AnalysisContext) -> bool:
        if not self.enabled or not context.response_headers:
            return False
        headers = {k.lower(): v for k, v in context.response_headers.items()}
        return bool(headers.get("set-cookie", ""))

    def evaluate(self, context: AnalysisContext, state: Dict[str, Any]) -> List[Finding]:
        headers = state.get("normalized_headers") or {
            k.lower(): v for k, v in (context.response_headers or {}).items()
        }
        set_cookie = headers.get("set-cookie", "")
        if not set_cookie:
            return []

        lowered = set_cookie.lower()
        findings: List[Finding] = []

        if "secure" not in lowered:
            findings.append(Finding(
                id=0,
                title="Session cookie Secure flag tasimiyor olabilir",
                severity=Severity.MEDIUM,
                category="cookie-hardening",
                layer=AnalysisLayer.SURFACE,
                description="Set-Cookie icinde Secure niteligine dair net bir sinyal gorunmuyor.",
                recommendation="Session cookie'lerde Secure, HttpOnly ve SameSite niteliklerini zorunlu kil.",
                evidence=set_cookie[:180],
            ))

        if "httponly" not in lowered:
            findings.append(Finding(
                id=0,
                title="Session cookie HttpOnly flag tasimiyor olabilir",
                severity=Severity.MEDIUM,
                category="cookie-hardening",
                layer=AnalysisLayer.SURFACE,
                description="HttpOnly olmadan cookie istemci script'leri tarafindan okunabilir hale gelebilir.",
                recommendation="Kimlik ve oturum cookie'lerinde HttpOnly bayragini ac.",
                evidence=set_cookie[:180],
            ))

        if "samesite" not in lowered:
            findings.append(Finding(
                id=0,
                title="Session cookie SameSite korumasi tasimiyor olabilir",
                severity=Severity.LOW,
                category="cookie-hardening",
                layer=AnalysisLayer.SURFACE,
                description="SameSite tanimi olmayan cookie'ler CSRF riskini artirabilir.",
                recommendation="SameSite=Lax veya gerekiyorsa SameSite=Strict tercih et.",
                evidence=set_cookie[:180],
            ))

        return findings


# ---------------------------------------------------------------------------
# Transport security
# ---------------------------------------------------------------------------

class TransportSecurityRule(Rule):
    """Flags HTTP (non-HTTPS) URLs."""

    name = "transport-security"
    category = "transport-security"
    description = "HTTPS kullanim kontrolu"

    def should_run(self, context: AnalysisContext) -> bool:
        return self.enabled and bool(context.url)

    def evaluate(self, context: AnalysisContext, state: Dict[str, Any]) -> List[Finding]:
        if not context.url or not context.url.startswith("http://"):
            return []

        return [Finding(
            id=0,
            title="HTTPS kullanilmiyor",
            severity=Severity.HIGH,
            category="transport-security",
            layer=AnalysisLayer.SURFACE,
            description="Sayfa HTTP uzerinden aciliyor. Trafik sifrelenmeden iletilebilir.",
            recommendation="Canli ortamlarda HTTPS zorunlu hale getir ve HSTS etkinlestir.",
            evidence=context.url[:180],
        )]


# ---------------------------------------------------------------------------
# Error enumeration leakage
# ---------------------------------------------------------------------------

class ErrorEnumerationRule(Rule):
    """Detects auth error messages that may enable account enumeration."""

    name = "error-enumeration"
    category = "error-leakage"
    description = "Hesap dogrulama hata mesaji ifsasi kontrolu"

    def evaluate(self, context: AnalysisContext, state: Dict[str, Any]) -> List[Finding]:
        combined_text: str = state.get("combined_text", "")
        match = ERROR_ENUMERATION_CONTEXT.search(combined_text)
        if not match:
            return []

        return [Finding(
            id=0,
            title="Hata mesaji account enumeration sinyali tasiyor",
            severity=Severity.MEDIUM,
            category="error-leakage",
            layer=AnalysisLayer.SURFACE,
            description="Kullanici adi ve parola hatalarini ayri anlatan mesajlar hesap varligi bilgisini sizdirabilir.",
            recommendation="Auth hata mesaji dilini normalize et ve kullanici yok/parola yanlis ayrimini son kullaniciya acma.",
            evidence=match.group(0)[:180],
        )]


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

class CORSHardeningRule(Rule):
    """Detects overly permissive CORS policies."""

    name = "cors-hardening"
    category = "cors-hardening"
    description = "CORS politikasi kontrolu"

    def evaluate(self, context: AnalysisContext, state: Dict[str, Any]) -> List[Finding]:
        combined_text: str = state.get("combined_text", "")
        headers = state.get("normalized_headers", {})

        wildcard = (
            "access-control-allow-origin: *" in combined_text.lower()
            or headers.get("access-control-allow-origin") == "*"
        )
        if not wildcard:
            return []

        return [Finding(
            id=0,
            title="Genis CORS izinleri gorunuyor olabilir",
            severity=Severity.MEDIUM,
            category="cors-hardening",
            layer=AnalysisLayer.SURFACE,
            description="Yildizli CORS politikasi gereksiz genis alan aciyor olabilir.",
            recommendation="CORS izinlerini guvenilir origin listesi ile sinirla.",
            evidence=headers.get("access-control-allow-origin", "*"),
        )]
