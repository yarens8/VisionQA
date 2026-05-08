"""
Security Context Inference
============================
Detects what "kind" of page/surface is being analyzed (auth, search,
upload, admin, payment, api …) based on visible text and URL signals.

The inferred context drives which attack hypotheses are generated.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Context detection patterns
# ---------------------------------------------------------------------------

AUTH_CONTEXT = re.compile(
    r"\b(login|sign in|signin|giris|password|sifre|otp|verification code"
    r"|email address|telefon numarasi|remember me|forgot password)\b",
    re.I,
)
SEARCH_CONTEXT = re.compile(r"\b(search|ara|query|filter|sonuc|results)\b", re.I)
UPLOAD_CONTEXT = re.compile(
    r"\b(upload|yukle|dosya sec|choose file|drag and drop|attachment)\b", re.I
)
ADMIN_CONTEXT = re.compile(
    r"\b(admin|dashboard|users|roles|permissions|settings|yonetici)\b", re.I
)
PAYMENT_CONTEXT = re.compile(
    r"\b(card|payment|checkout|iban|odeme|credit card|billing)\b", re.I
)
API_CONTEXT = re.compile(
    r"\b(api|json|graphql|endpoint|response|request|status code)\b", re.I
)
ERROR_ENUMERATION_CONTEXT = re.compile(
    r"\b(user not found|email not found|wrong password|invalid password"
    r"|hesap bulunamadi)\b",
    re.I,
)
SQL_SIGNAL = re.compile(
    r"\b(select|union|where|order by|drop table|insert into|sql)\b", re.I
)
XSS_SIGNAL = re.compile(r"\b(<script>|javascript:|onerror=|alert\()\b", re.I)
ID_SIGNAL = re.compile(
    r"\b(user_id|account_id|customer_id|id=|/users/\d+|/accounts/\d+)\b", re.I
)


# ---------------------------------------------------------------------------
# Context profile
# ---------------------------------------------------------------------------

# Priority order: higher-risk contexts first
_CONTEXT_PRIORITY = [
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


@dataclass(frozen=True)
class SecurityContext:
    """Immutable snapshot of inferred contexts for a page."""

    auth: bool = False
    search: bool = False
    upload: bool = False
    admin: bool = False
    payment: bool = False
    api: bool = False
    enumeration: bool = False
    sql: bool = False
    xss: bool = False
    idor: bool = False

    @property
    def primary(self) -> str:
        """Highest-priority detected context, or 'generic'."""
        for name in _CONTEXT_PRIORITY:
            if getattr(self, name, False):
                return name
        return "generic"

    @property
    def ranked(self) -> List[str]:
        """All detected contexts in priority order."""
        return [name for name in _CONTEXT_PRIORITY if getattr(self, name, False)]

    def to_dict(self) -> Dict[str, bool]:
        return {name: getattr(self, name) for name in _CONTEXT_PRIORITY}


def infer_security_context(
    text: str,
    url: Optional[str] = None,
) -> SecurityContext:
    """
    Analyze combined text + URL to determine page context.

    Parameters
    ----------
    text : str
        All visible text from the page (OCR output + response body).
    url : str, optional
        The target URL.

    Returns
    -------
    SecurityContext
        Immutable context snapshot.
    """
    combined = f"{text}\n{url or ''}"
    return SecurityContext(
        auth=bool(AUTH_CONTEXT.search(combined)),
        search=bool(SEARCH_CONTEXT.search(combined)),
        upload=bool(UPLOAD_CONTEXT.search(combined)),
        admin=bool(ADMIN_CONTEXT.search(combined)),
        payment=bool(PAYMENT_CONTEXT.search(combined)),
        api=bool(
            API_CONTEXT.search(combined)
            or (url and "/api" in url.lower())
        ),
        enumeration=bool(ERROR_ENUMERATION_CONTEXT.search(combined)),
        sql=bool(SQL_SIGNAL.search(combined)),
        xss=bool(XSS_SIGNAL.search(combined)),
        idor=bool(ID_SIGNAL.search(combined)),
    )
