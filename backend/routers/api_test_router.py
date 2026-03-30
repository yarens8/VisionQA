from typing import List, Dict, Any, Optional
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from fastapi import APIRouter
from pydantic import BaseModel

from executors.api.api_executor import APIExecutor
from schemas import (
    ApiCrossModuleCorrelation,
    ApiGeneratedTest,
    ApiNegativeCheck,
    ApiScoreBreakdown,
    ApiTestAnalyzeRequest,
    ApiTestAnalyzeResponse,
    ApiTestFinding,
)

router = APIRouter(prefix="/api-test", tags=["api-test"])


class APIRequestSchema(BaseModel):
    method: str
    url: str
    headers: Optional[Dict[str, str]] = None
    body: Optional[Any] = None
    params: Optional[Dict[str, Any]] = None


def _response_text(raw_result: Dict[str, Any]) -> str:
    body = raw_result.get("response_body")
    if isinstance(body, dict):
        return str(body)
    if isinstance(body, list):
        return str(body)
    return str(body or "")


def _infer_endpoint_context(request_data: ApiTestAnalyzeRequest) -> str:
    lowered = f"{request_data.method} {request_data.url}".lower()
    if any(token in lowered for token in ("/login", "/auth", "signin", "token", "oauth")):
        return "auth"
    if any(token in lowered for token in ("/upload", "multipart", "file")):
        return "upload"
    if any(token in lowered for token in ("/search", "query=", "filter")):
        return "search"
    if any(token in lowered for token in ("/admin", "/role", "/permission")):
        return "admin"
    if any(token in lowered for token in ("/users", "/profile", "/account")):
        return "user-data"
    if request_data.method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
        return "mutation"
    return "generic"


def _response_required_fields_missing(body: Any, expected_fields: List[str]) -> List[str]:
    if not expected_fields or not isinstance(body, dict):
        return []
    return [field for field in expected_fields if field not in body or body.get(field) is None]


def _detect_api_findings(request_data: ApiTestAnalyzeRequest, raw_result: Dict[str, Any]) -> List[ApiTestFinding]:
    findings: List[ApiTestFinding] = []
    body_text = _response_text(raw_result)
    response_body = raw_result.get("response_body")
    content_type = str(raw_result.get("headers", {}).get("content-type", "")).lower()
    status_code = raw_result.get("status_code")
    duration_ms = float(raw_result.get("duration_ms", 0))
    request_headers = {k.lower(): v for k, v in (request_data.headers or {}).items()}
    lowered_url = request_data.url.lower()
    context = _infer_endpoint_context(request_data)
    missing_fields = _response_required_fields_missing(response_body, request_data.expected_fields)

    def add(
        severity: str,
        category: str,
        title: str,
        description: str,
        evidence: str,
        recommendation: str,
    ) -> None:
        findings.append(
            ApiTestFinding(
                id=len(findings) + 1,
                title=title,
                severity=severity,
                category=category,
                description=description,
                evidence=evidence,
                recommendation=recommendation,
            )
        )

    if raw_result.get("success") is False:
        add(
            "high",
            "transport-error",
            "API istegi basarisiz oldu",
            "API istegi baglanti, timeout veya transport seviyesinde hata verdi.",
            raw_result.get("error", "Unknown request failure"),
            "Endpoint erisilebilirligini, timeout politikasini ve ag/proxy ayarlarini dogrula.",
        )
        return findings

    if status_code is not None and status_code >= 500:
        add(
            "high",
            "server-error",
            "Sunucu 5xx hata kodu dondu",
            "Endpoint beklenmeyen bir sunucu hatasi uretti ve dayaniklilik riski olusturuyor.",
            f"Status code: {status_code}",
            "Sunucu loglarini incele, exception sanitization ekle ve bu endpoint icin regression testi yaz.",
        )

    if request_data.expected_status is not None and status_code != request_data.expected_status:
        add(
            "medium",
            "status-mismatch",
            "Beklenen status ile gercek status uyusmuyor",
            "API cagrisi beklenen davranistan farkli bir status code ile dondu.",
            f"Expected {request_data.expected_status}, got {status_code}",
            "Endpoint sozlesmesini ve client beklentisini hizala; gerekirse contract testi ekle.",
        )

    if duration_ms >= 2500:
        add(
            "high",
            "slow-response",
            "API yaniti belirgin sekilde yavas",
            "Response suresi yuksek ve kullanici akisinda gecikme yaratabilir.",
            f"Duration: {duration_ms:.2f} ms",
            "DB sorgularini, downstream servisleri ve cache katmanini inceleyip p95 hedefi belirle.",
        )
    elif duration_ms >= 1200:
        add(
            "medium",
            "slow-response",
            "API yaniti hedefin ustunde",
            "Response suresi kabul edilebilir seviyenin ustune cikiyor.",
            f"Duration: {duration_ms:.2f} ms",
            "Endpoint icin latency butcesi belirle ve yavas adimlari profille.",
        )

    debug_markers = ("traceback", "exception", "stack trace", "sqlstate", "syntax error", "nullreference")
    if any(marker in body_text.lower() for marker in debug_markers):
        add(
            "high",
            "error-leakage",
            "Response icinde debug veya stack trace sinyali var",
            "API cevabi son kullaniciya fazla teknik hata bilgisi sizdiriyor.",
            body_text[:180],
            "Hata cevabini sanitize et, ic hata detaylarini log katmaninda tut ve genel hata semasi kullan.",
        )

    if request_data.expected_response_type and request_data.expected_response_type.lower() not in content_type:
        add(
            "medium",
            "response-type",
            "Response tipi beklenen format ile uyusmuyor",
            "Beklenen response content-type ile gercek content-type farkli gorunuyor.",
            f"Expected type: {request_data.expected_response_type}, got: {content_type or 'unknown'}",
            "Endpoint content negotiation kurallarini ve gateway davranisini hizala.",
        )

    if missing_fields:
        add(
            "high",
            "schema-mismatch",
            "Response icinde beklenen alanlar eksik",
            "Beklenen zorunlu alanlardan bazilari response icinde bulunmuyor veya null geliyor.",
            f"Missing fields: {', '.join(missing_fields)}",
            "API response contract'ini, serializer katmanini ve breaking change riskini kontrol et.",
        )

    if "api" in lowered_url and "text/html" in content_type:
        add(
            "medium",
            "content-type",
            "API endpoint beklenmeyen HTML cevabi dondu",
            "API olarak gorunen endpoint JSON yerine HTML donuyor; hata sayfasi veya reverse proxy sapmasi olabilir.",
            f"Content-Type: {content_type}",
            "Content negotiation davranisini ve proxy yonlendirmelerini kontrol et.",
        )

    if request_data.method.upper() in {"POST", "PUT", "PATCH", "DELETE"} and 200 <= (status_code or 0) < 300 and "authorization" not in request_headers:
        add(
            "medium",
            "auth-signal",
            "Mutating endpoint yetkilendirme olmadan basarili oldu",
            "Yazma etkili istek authorization header olmadan basarili dondu. Bu kesin acik kaniti degil ama guclu bir risk sinyali.",
            f"Method {request_data.method.upper()} succeeded with status {status_code}",
            "Bu endpoint icin authn/authz gereksinimini, test account rollerini ve negatif senaryolari dogrula.",
        )

    if context in {"auth", "admin"} and 200 <= (status_code or 0) < 300 and "set-cookie" not in {k.lower(): v for k, v in raw_result.get("headers", {}).items()}:
        add(
            "low",
            "session-signal",
            "Auth akisinda session sinyali zayif",
            "Kimlik veya admin benzeri endpoint basarili donmesine ragmen belirgin bir session/token sinyali gozlenmedi.",
            f"Headers: {list(raw_result.get('headers', {}).keys())[:6]}",
            "Auth cevabinin token/session semasini ve beklenen header/response modelini dogrula.",
        )

    if len(body_text) > 200_000:
        add(
            "low",
            "payload-size",
            "Response govdesi buyuk",
            "API cevabi beklenenden buyuk olabilir ve istemci tarafinda performans baskisi yaratabilir.",
            f"Response size: {len(body_text)} chars",
            "Pagination, field projection veya daha kucuk response modelleri dusun.",
        )

    return findings


async def _run_negative_checks(executor: APIExecutor, request_data: ApiTestAnalyzeRequest) -> List[ApiNegativeCheck]:
    checks: List[ApiNegativeCheck] = []
    method = request_data.method.upper()
    context = _infer_endpoint_context(request_data)

    def add_check(name: str, status: str, summary: str, evidence: str) -> None:
        checks.append(
            ApiNegativeCheck(
                id=len(checks) + 1,
                name=name,
                status=status,
                summary=summary,
                evidence=evidence,
            )
        )

    options_result = await executor.execute_step("OPTIONS", request_data.url, headers=request_data.headers)
    if options_result.get("success"):
        allow_header = str(options_result.get("headers", {}).get("allow", "not-provided"))
        add_check(
            "method-discovery",
            "observed",
            "OPTIONS cagrisi ile endpoint method sinyali toplandi.",
            f"Allow header: {allow_header}",
        )
    else:
        add_check(
            "method-discovery",
            "blocked",
            "OPTIONS cagrisi basarisiz veya engelli.",
            options_result.get("error", "No response"),
        )

    if method == "GET":
        marker = "visionqa-reflection-marker"
        parsed = urlsplit(request_data.url)
        params = parse_qsl(parsed.query, keep_blank_values=True)
        params.append(("__visionqa_probe", marker))
        probed_url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(params), parsed.fragment))
        reflection_result = await executor.execute_step("GET", probed_url, headers=request_data.headers)
        body_text = _response_text(reflection_result)
        if marker in body_text:
            add_check(
                "reflection-probe",
                "signal",
                "Probe parametresi response govdesinde geri yansidi.",
                "Marker response body icinde bulundu.",
            )
        else:
            add_check(
                "reflection-probe",
                "clean",
                "Probe parametresi response govdesinde gorunmedi.",
                f"Status: {reflection_result.get('status_code')}",
            )

    if context == "auth":
        auth_probes = []
        for _ in range(3):
            auth_probe = await executor.execute_step(method, request_data.url, json=request_data.body, headers=request_data.headers, params=request_data.params)
            auth_probes.append(auth_probe.get("status_code"))
        if 429 in auth_probes:
            add_check(
                "rate-limit-signal",
                "present",
                "Auth endpoint tekrarli denemelerde rate limit sinyali verdi.",
                f"Observed statuses: {auth_probes}",
            )
        else:
            add_check(
                "rate-limit-signal",
                "missing",
                "Auth endpoint tekrarli denemelerde belirgin bir 429/rate-limit davranisi gostermedi.",
                f"Observed statuses: {auth_probes}",
            )

    return checks


def _generate_context_tests(request_data: ApiTestAnalyzeRequest, raw_result: Dict[str, Any]) -> List[ApiGeneratedTest]:
    context = _infer_endpoint_context(request_data)
    tests: List[ApiGeneratedTest] = []

    def add(title: str, category: str, priority: int, rationale: str, expected_signal: str, payload: Optional[str] = None) -> None:
        tests.append(
            ApiGeneratedTest(
                id=len(tests) + 1,
                title=title,
                category=category,
                priority=priority,
                rationale=rationale,
                suggested_payload=payload,
                expected_signal=expected_signal,
            )
        )

    if context == "auth":
        add("Bos sifre ile login denemesi", "validation", 1, "Auth endpointleri bos veya kisa credentials icin 4xx tabanli net cevap donmeli.", "400/401 donmeli, 500 olmamali", '{"password": ""}')
        add("Tekrarli giris denemesi", "security", 1, "Brute-force benzeri akislar icin rate limit veya lockout davranisi gozlenmeli.", "429 veya throttling sinyali", None)
        add("SQLi benzeri payload", "security", 2, "Login inputlari injection semptomlari acisindan oncelikli yuzeydir.", "{\"username\": \"' OR '1'='1\"}")
    elif context == "upload":
        add("Yanlis mime-type ile upload", "functional", 1, "Upload endpointleri dosya tipi dogrulamasi yapmali.", "415/400 veya validation error", "malicious.exe")
        add("Buyuk payload denemesi", "performance", 2, "Buyuk dosya akisinda timeout veya memory baskisi gozlenebilir.", "4xx limit cevabi veya kontrollu rejection", "oversized-file")
    elif context == "search":
        add("Cok uzun query parametresi", "validation", 1, "Search endpointleri uzun veya anlamsiz query'leri kontrollu handle etmeli.", "400/200 ama degrade olmadan", "q=aaaaaaaaaaaaaaaa")
        add("Ozel karakter/XSS probe", "security", 2, "Arama parametreleri yansima ve encoding kusurlarina adaydir.", "Payload yansimamali veya encode edilmeli", "<script>alert(1)</script>")
    elif context == "admin":
        add("Yetkisiz erisim denemesi", "security", 1, "Admin yuzeyleri rol kontrollu olmalidir.", "401/403 beklenir", None)
        add("IDOR varyasyonu", "security", 2, "Admin path'lerinde obje kimlikleri ile oynanarak yetki siniri test edilir.", "403/404 veya ayni kaynak disina cikamama", "/1 -> /2")
    else:
        add("Bozuk parametre senaryosu", "validation", 2, "Her endpoint temel validation davranisini tutarli vermelidir.", "4xx ve acik hata mesaji", None)
        add("Beklenmeyen content-type senaryosu", "contract", 3, "Response tipi sozlesme ile hizali kalmalidir.", "JSON contract korunur", None)

    if request_data.method.upper() in {"POST", "PUT", "PATCH"}:
        add("Eksik required alan denemesi", "contract", 1, "Mutating endpointler eksik alanlarda 4xx donmeli.", "422/400 ve tutarli error payload", None)

    return tests


def _score_breakdown(
    request_data: ApiTestAnalyzeRequest,
    findings: List[ApiTestFinding],
    negative_checks: List[ApiNegativeCheck],
) -> ApiScoreBreakdown:
    health = 100
    validation = 100
    security = 100
    performance = 100
    contract = 100

    for finding in findings:
        penalty = {"high": 30, "medium": 15, "low": 6}.get(finding.severity, 8)
        if finding.category in {"server-error", "transport-error", "status-mismatch"}:
            health -= penalty
        if finding.category in {"schema-mismatch", "status-mismatch", "response-type"}:
            validation -= penalty
            contract -= penalty
        if finding.category in {"auth-signal", "error-leakage", "content-type", "session-signal"}:
            security -= penalty
        if finding.category in {"slow-response", "payload-size"}:
            performance -= penalty
        if finding.category in {"schema-mismatch", "response-type"}:
            contract -= max(4, penalty // 2)

    for check in negative_checks:
        if check.status in {"signal", "missing"}:
            security -= 8

    return ApiScoreBreakdown(
        health=max(0, min(100, health)),
        validation=max(0, min(100, validation)),
        security=max(0, min(100, security)),
        performance=max(0, min(100, performance)),
        contract=max(0, min(100, contract)),
    )


def _endpoint_risk_score(request_data: ApiTestAnalyzeRequest, findings: List[ApiTestFinding], context: str) -> int:
    base = 22
    if context == "auth":
        base += 30
    elif context == "admin":
        base += 35
    elif context in {"upload", "user-data"}:
        base += 24
    elif request_data.method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
        base += 18
    base += len(findings) * 6
    if any(f.severity == "high" for f in findings):
        base += 12
    return max(0, min(100, base))


def _ai_failure_explanation(request_data: ApiTestAnalyzeRequest, raw_result: Dict[str, Any], findings: List[ApiTestFinding]) -> str:
    if not findings:
        return "Endpoint bu kosumda temel health ve contract seviyesinde temiz gorunuyor; yine de baglama ozel negatif senaryolarla derinlestirmek faydali olur."
    if any(f.category == "server-error" for f in findings):
        return "Endpoint 5xx seviyesinde hata veriyor. Bu durum eksik input validation, null kontrolu zayifligi veya exception handling katmaninin kullanici hatalarini sunucu hatasina cevirdigini gosterebilir."
    if any(f.category == "schema-mismatch" for f in findings):
        return "Response contract'i ile gercek payload uyusmuyor. Serializer, DTO veya versiyon gecisi sirasinda alan kaybi yasanmis olabilir."
    if any(f.category == "auth-signal" for f in findings):
        return "Mutating endpoint authorization olmadan basarili davranis gosterdi. Bu durum authn/authz zorunlulugunun endpoint seviyesinde tutarsiz oldugunu dusundurebilir."
    if any(f.category == "slow-response" for f in findings):
        return "Endpoint'in gecikme profili hedefin ustune cikiyor. Muhtemel nedenler verimsiz downstream cagri, cache eksigi veya DB sorgu maliyeti olabilir."
    return "Endpoint temel beklentilerden en az birinde sapma gosteriyor. Validation, content negotiation ve hata standardizasyonu birlikte gozden gecirilmeli."


def _root_cause_summary(findings: List[ApiTestFinding], context: str) -> str:
    if not findings:
        return "Belirgin kok neden sinyali yok; bir sonraki adim endpoint'e baglam ozel varyant testleri eklemek."
    categories = {finding.category for finding in findings}
    if "server-error" in categories or "error-leakage" in categories:
        return "En baskin kok neden adayi backend validation/exceptions katmaninin yetersiz olmasi."
    if "schema-mismatch" in categories or "response-type" in categories:
        return "En baskin kok neden adayi contract drift; API dokumani, serializer ve frontend beklentisi ayrismis olabilir."
    if "auth-signal" in categories and context in {"auth", "admin", "mutation"}:
        return "En baskin kok neden adayi endpoint seviyesinde eksik yetki kontrolu veya zorunlu auth policy'sinin uygulanmamasi."
    if "slow-response" in categories:
        return "En baskin kok neden adayi yavas dependency veya optimize edilmemis sorgu/servis zinciri."
    return "Bulgular daginik fakat validation ve standard response semasi en kuvvetli iyilestirme adayi gibi gorunuyor."


def _cross_module_correlation(request_data: ApiTestAnalyzeRequest, findings: List[ApiTestFinding], context: str) -> List[ApiCrossModuleCorrelation]:
    correlations: List[ApiCrossModuleCorrelation] = []

    def add(module: str, summary: str, reason: str, follow_up: str) -> None:
        correlations.append(
            ApiCrossModuleCorrelation(
                module=module,
                summary=summary,
                reason=reason,
                suggested_follow_up=follow_up,
            )
        )

    categories = {finding.category for finding in findings}
    if "slow-response" in categories:
        add("4.7 Performance", "API gecikmesi performans modulu ile derinlestirilmeli.", "Response latency bulgusu var.", "Ayni endpoint icin load profile ve p95/p99 analizi cikar.")
    if "schema-mismatch" in categories or context in {"mutation", "user-data"}:
        add("4.10 Database", "API-DB contract uyumu kontrol edilmeli.", "Payload alanlari ile tablo/kolon beklentileri ayrisiyor olabilir.", "DB tablosunda beklenen alanlari ve nullability durumunu audit et.")
    if "auth-signal" in categories or context in {"auth", "admin"}:
        add("4.5 Security", "Endpoint security modulune baglanmali.", "Auth veya yetki sinyalleri riskli gorunuyor.", "Security modulu ile aktif probing ve role senaryolari calistir.")
    if context in {"generic", "search"}:
        add("4.3 UI/UX", "Bu endpoint'i besleyen form akisi UI/UX ile birlikte gozden gecirilebilir.", "Arama veya input akislarinda API validation sapmasi olabilir.", "Ilgili formun hata mesaji ve input guidance kalitesini kontrol et.")
    return correlations


def _build_api_analysis_response(
    request_data: ApiTestAnalyzeRequest,
    raw_result: Dict[str, Any],
    findings: List[ApiTestFinding],
    negative_checks: List[ApiNegativeCheck],
) -> ApiTestAnalyzeResponse:
    penalties = {"high": 25, "medium": 12, "low": 5}
    score = 100
    for finding in findings:
        score -= penalties.get(finding.severity, 8)
    if any(check.status in {"signal", "missing"} for check in negative_checks):
        score -= 8
    score = max(0, min(100, score))

    context = _infer_endpoint_context(request_data)
    generated_tests = _generate_context_tests(request_data, raw_result)
    score_breakdown = _score_breakdown(request_data, findings, negative_checks)
    endpoint_risk_score = _endpoint_risk_score(request_data, findings, context)
    response_text = _response_text(raw_result)
    response_type = str(raw_result.get("headers", {}).get("content-type", "unknown")).split(";")[0]
    summary = (
        f"API analizi {len(findings)} bulgu, {len(negative_checks)} negatif kontrol ve "
        f"{len(generated_tests)} baglamsal test onerisi uretti. Status {raw_result.get('status_code', 'n/a')} ve sure {raw_result.get('duration_ms', 0)} ms."
    )
    ai_failure_explanation = _ai_failure_explanation(request_data, raw_result, findings)
    root_cause_summary = _root_cause_summary(findings, context)
    ai_test_summary = (
        f"{context} baglaminda en oncelikli testler: "
        + ", ".join(test.title for test in generated_tests[:3])
        if generated_tests
        else "Ek baglamsal test onerisi yok."
    )

    return ApiTestAnalyzeResponse(
        method=request_data.method.upper(),
        url=request_data.url,
        success=bool(raw_result.get("success")),
        status_code=raw_result.get("status_code"),
        duration_ms=float(raw_result.get("duration_ms", 0)),
        overall_score=score,
        endpoint_risk_score=endpoint_risk_score,
        summary=summary,
        ai_failure_explanation=ai_failure_explanation,
        ai_test_summary=ai_test_summary,
        root_cause_summary=root_cause_summary,
        endpoint_context=context,
        response_type=response_type,
        response_size=len(response_text),
        score_breakdown=score_breakdown,
        findings=findings,
        negative_checks=negative_checks,
        generated_tests=generated_tests,
        cross_module_correlation=_cross_module_correlation(request_data, findings, context),
        raw_result=raw_result,
    )


@router.post("/run")
async def run_api_request(request_data: APIRequestSchema):
    executor = APIExecutor()
    try:
        return await executor.execute_step(
            method=request_data.method,
            path=request_data.url,
            json=request_data.body,
            headers=request_data.headers,
            params=request_data.params,
        )
    finally:
        await executor.close()


@router.post("/analyze", response_model=ApiTestAnalyzeResponse)
async def analyze_api_request(request_data: ApiTestAnalyzeRequest):
    executor = APIExecutor()
    try:
        raw_result = await executor.execute_step(
            method=request_data.method,
            path=request_data.url,
            json=request_data.body,
            headers=request_data.headers,
            params=request_data.params,
        )
        findings = _detect_api_findings(request_data, raw_result)
        negative_checks = await _run_negative_checks(executor, request_data) if request_data.run_negative_checks else []
        return _build_api_analysis_response(request_data, raw_result, findings, negative_checks)
    finally:
        await executor.close()


@router.post("/batch")
async def run_batch_api_requests(requests: List[APIRequestSchema]):
    executor = APIExecutor()
    try:
        results = []
        for req in requests:
            res = await executor.execute_step(
                method=req.method,
                path=req.url,
                json=req.body,
                headers=req.headers,
                params=req.params,
            )
            results.append(res)
        return {"summary": executor.get_summary(), "results": results}
    finally:
        await executor.close()


@router.post("/load-test")
async def run_api_load_test(request_data: APIRequestSchema, count: int = 10):
    executor = APIExecutor()
    try:
        return await executor.load_test(
            method=request_data.method,
            path=request_data.url,
            count=count,
            json=request_data.body,
            headers=request_data.headers,
        )
    finally:
        await executor.close()


@router.get("/import-swagger")
async def import_swagger(url: str):
    executor = APIExecutor()
    try:
        return await executor.parse_swagger(url)
    finally:
        await executor.close()
