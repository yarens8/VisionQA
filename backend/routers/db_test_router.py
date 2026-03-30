import re
import time
from typing import List, Dict, Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import inspect

from executors.database.db_executor import DatabaseExecutor
from schemas import (
    DbConstraintSummary,
    DbQualityFinding,
    DbQualityRequest,
    DbQualityResponse,
    DbSchemaSmell,
    DbScoreBreakdown,
)

router = APIRouter(prefix="/db-test", tags=["db-test"])


class DBQuerySchema(BaseModel):
    connection_string: str
    query: str
    params: Optional[Dict[str, Any]] = None


class DBSchemaValidationSchema(BaseModel):
    connection_string: str
    table_name: str
    expected_columns: List[str]


def _add_db_finding(
    findings: List[DbQualityFinding],
    severity: str,
    category: str,
    title: str,
    description: str,
    evidence: str,
    recommendation: str,
) -> None:
    findings.append(
        DbQualityFinding(
            id=len(findings) + 1,
            title=title,
            severity=severity,
            category=category,
            description=description,
            evidence=evidence,
            recommendation=recommendation,
        )
    )


def _analyze_query_text(query: str, findings: List[DbQualityFinding]) -> None:
    normalized = " ".join(query.strip().lower().split())

    if "select *" in normalized:
        _add_db_finding(
            findings,
            "medium",
            "query-shape",
            "SELECT * kullanimi bulundu",
            "Query tum kolonlari cagiriyor; bu hem performans hem de veri gereksizligi riski olusturabilir.",
            query,
            "Ihtiyac olan kolonlari acik sec ve response yuzeyini daralt.",
        )

    if normalized.startswith("select") and " limit " not in normalized:
        _add_db_finding(
            findings,
            "medium",
            "query-scope",
            "SELECT sorgusunda LIMIT yok",
            "Sinirsiz select sorgusu buyuk tablolarda yuksek maliyet ve UI tarafinda asiri veri tasima riski olusturur.",
            query,
            "Listeleme ve inceleme sorgularina LIMIT veya pagination ekle.",
        )

    if normalized.count(" join ") >= 3:
        _add_db_finding(
            findings,
            "medium",
            "query-complexity",
            "Query icinde yuksek join yogunlugu var",
            "Coklu join yapisi performans ve okunabilirlik maliyetini arttirabilir.",
            query,
            "Execution plan ile join siralarini, gerekli indexleri ve materialization ihtiyacini incele.",
        )

    risky_patterns = {
        "delete from": ("high", "dangerous-mutation", "DELETE sorgusu tespit edildi"),
        "update ": ("medium", "mutation-query", "UPDATE sorgusu tespit edildi"),
        "drop table": ("high", "ddl-risk", "DROP TABLE ifadesi tespit edildi"),
        "truncate": ("high", "ddl-risk", "TRUNCATE ifadesi tespit edildi"),
        "alter table": ("medium", "ddl-risk", "ALTER TABLE ifadesi tespit edildi"),
    }
    for pattern, (severity, category, title) in risky_patterns.items():
        if pattern in normalized:
            desc = "Bu sorgu veri degistiren veya sema degistiren bir islem oldugu icin kontrollu ortam disinda risklidir."
            rec = "Bu sorguyu read-only akistan ayir ve onay/guardrail ekle."
            if pattern in {"delete from", "update "} and " where " not in normalized:
                severity = "high"
                desc = "Veri degistiren sorguda WHERE kosulu gorunmuyor; bu genis capli veri etkisine yol acabilir."
                rec = "Write sorgularinda WHERE kosulunu zorunlu kil ve once etkilenebilecek satir sayisini dogrula."
            _add_db_finding(findings, severity, category, title, desc, query, rec)


def _looks_like_hash(value: str) -> bool:
    return bool(
        re.match(r"^\$2[aby]\$.{20,}$", value)
        or re.match(r"^[a-f0-9]{32,128}$", value.lower())
    )


def _analyze_sample_rows(sample_rows: List[Dict[str, Any]], findings: List[DbQualityFinding]) -> None:
    if not sample_rows:
        return

    row_count = len(sample_rows)
    columns = list(sample_rows[0].keys())
    for column in columns:
        values = [row.get(column) for row in sample_rows]
        null_count = sum(value is None for value in values)
        if null_count / row_count >= 0.4:
            _add_db_finding(
                findings,
                "medium",
                "null-density",
                f"{column} kolonunda yuksek bos deger orani var",
                "Orneklemde bu kolon icin null oraninin yuksek olmasi veri kalitesi veya eksik doldurma sorunu sinyali olabilir.",
                f"{null_count}/{row_count} satir null",
                "Bu kolon icin doldurma kurallarini, default degerleri veya ETL validation adimlarini incele.",
            )

        string_values = [str(value).strip() for value in values if isinstance(value, str) and str(value).strip()]
        lowered_unique = {value.lower() for value in string_values}
        if len(lowered_unique) > 1 and any(value != value.lower() for value in string_values):
            _add_db_finding(
                findings,
                "low",
                "format-consistency",
                f"{column} kolonunda format tutarsizligi sinyali var",
                "Ayni kolon icinde farkli buyuk-kucuk harf veya format kullanimi veri standardizasyonunu zayiflatabilir.",
                f"Sample values: {', '.join(string_values[:4])}",
                "Bu kolon icin canonical format ve normalize etme kurali tanimla.",
            )

        if "password" in column.lower():
            weak_password_samples = [value for value in string_values[:5] if not _looks_like_hash(value)]
            if weak_password_samples:
                _add_db_finding(
                    findings,
                    "high",
                    "security-storage",
                    f"{column} kolonunda duz metin veya zayif hash sinyali var",
                    "Password benzeri kolon degerleri hash'lenmemis veya zayif formatta gorunuyor olabilir.",
                    f"Sample: {weak_password_samples[0][:40]}",
                    "Parola saklama icin bcrypt/argon2 gibi guclu hash stratejisine gec.",
                )

        if any(token in column.lower() for token in ("token", "secret", "api_key")):
            _add_db_finding(
                findings,
                "medium",
                "security-storage",
                f"{column} hassas veri kolonu gibi gorunuyor",
                "Token/secret benzeri alanlar icin encryption, rotation ve audit beklentisi olusur.",
                f"Detected sensitive-like column: {column}",
                "Bu kolonun encryption ve erisim politikasini dogrula; gerekirse key rotation stratejisi ekle.",
            )

    id_like_columns = [column for column in columns if column.lower() in {"id", "uuid", "user_id", "project_id"}]
    for column in id_like_columns:
        values = [row.get(column) for row in sample_rows if row.get(column) is not None]
        if len(values) != len(set(values)):
            _add_db_finding(
                findings,
                "high",
                "duplicate-identifier",
                f"{column} kolonunda tekrar eden degerler gorundu",
                "Orneklem icinde benzersiz olmasi beklenen identifier degerleri tekrar ediyor.",
                f"Duplicate values detected in {column}",
                "Primary key/unique constraint tanimlarini ve veri uretim akisini kontrol et.",
            )

    for row in sample_rows:
        normalized = {str(key).lower(): value for key, value in row.items()}
        status_value = str(normalized.get("status", "")).lower()
        payment_state = str(normalized.get("payment_status", "")).lower()
        if status_value in {"completed", "delivered"} and payment_state in {"", "pending", "failed", "none"}:
            _add_db_finding(
                findings,
                "high",
                "business-rule",
                "Is kurali ihlali sinyali tespit edildi",
                "Kayit tamamlanmis/delivered gorunurken odeme durumu uyumsuz. Bu durum business rule ihlali olabilir.",
                f"status={status_value}, payment_status={payment_state or 'empty'}",
                "Siparis/odeme state machine kurallarini ve event sirasini dogrula.",
            )
            break


def _inspect_constraints(executor: DatabaseExecutor, table_name: str) -> DbConstraintSummary:
    inspector = inspect(executor.engine)
    pk = inspector.get_pk_constraint(table_name) or {}
    foreign_keys = inspector.get_foreign_keys(table_name) or []
    unique_constraints = inspector.get_unique_constraints(table_name) or []
    columns = inspector.get_columns(table_name) or []

    unique_columns: List[str] = []
    for item in unique_constraints:
        unique_columns.extend(item.get("column_names") or [])

    return DbConstraintSummary(
        primary_keys=pk.get("constrained_columns") or [],
        foreign_keys=[",".join((fk.get("constrained_columns") or [])) for fk in foreign_keys if fk.get("constrained_columns")],
        unique_columns=sorted(set(unique_columns)),
        nullable_columns=[column["name"] for column in columns if column.get("nullable")],
    )


def _schema_smells(table_name: Optional[str], detected_columns: List[str], nullable_columns: List[str]) -> List[DbSchemaSmell]:
    smells: List[DbSchemaSmell] = []
    if len(detected_columns) >= 18:
        smells.append(DbSchemaSmell(id=len(smells) + 1, title="Genis tablo kokusu", summary="Tabloda cok fazla kolon var; normalizasyon veya bounded context ayrimi gerekebilir.", severity="medium"))
    if detected_columns and len(nullable_columns) / max(1, len(detected_columns)) >= 0.55:
        smells.append(DbSchemaSmell(id=len(smells) + 1, title="Nullable yogunlugu yuksek", summary="Kolonlarin buyuk bolumu nullable; bu durum semantik olarak zayif schema sinyali olabilir.", severity="medium"))
    repeated_prefixes = {}
    for column in detected_columns:
        prefix = column.split("_")[0]
        repeated_prefixes[prefix] = repeated_prefixes.get(prefix, 0) + 1
    if any(count >= 4 for count in repeated_prefixes.values()):
        smells.append(DbSchemaSmell(id=len(smells) + 1, title="Tekrarlayan kolon gruplari var", summary="Ayni on eke sahip cok sayida kolon bulunuyor; text tabanli de-normalized yapi buyumus olabilir.", severity="low"))
    if table_name and table_name.endswith("data"):
        smells.append(DbSchemaSmell(id=len(smells) + 1, title="Tablo ismi zayif semantik tasiyor", summary="Genel/torba tablo isimleri bakim ve sorumluluk sinirlarini zayiflatabilir.", severity="low"))
    return smells


def _score_breakdown(findings: List[DbQualityFinding]) -> DbScoreBreakdown:
    integrity = 100
    completeness = 100
    consistency = 100
    performance = 100
    security = 100
    for finding in findings:
        penalty = {"high": 28, "medium": 14, "low": 6}.get(finding.severity, 8)
        if finding.category in {"duplicate-identifier", "schema-mismatch", "business-rule"}:
            integrity -= penalty
        if finding.category in {"null-density", "empty-table"}:
            completeness -= penalty
        if finding.category in {"format-consistency", "business-rule"}:
            consistency -= penalty
        if finding.category in {"slow-query", "query-shape", "query-scope", "query-complexity", "table-scan"}:
            performance -= penalty
        if finding.category in {"security-storage", "dangerous-mutation", "ddl-risk"}:
            security -= penalty
    return DbScoreBreakdown(
        integrity=max(0, min(100, integrity)),
        completeness=max(0, min(100, completeness)),
        consistency=max(0, min(100, consistency)),
        performance=max(0, min(100, performance)),
        security=max(0, min(100, security)),
    )


def _ai_interpretation(findings: List[DbQualityFinding], table_name: Optional[str]) -> str:
    if not findings:
        return "Bu kosumda tablo ve query duzeyi temel kalite sinyalleri temiz gorunuyor; bir sonraki adim iliski ve constraint derinligi olabilir."
    if any(f.category == "business-rule" for f in findings):
        return "Veri sadece teknik olarak degil, is anlami acisindan da sapma gosteriyor. Bu durum uygulama akislarinda sessiz bozulmalara yol acabilir."
    if any(f.category == "security-storage" for f in findings):
        return "Tabloda hassas veri saklama sinyalleri var. Bu bulgular sadece kalite degil, guvenlik ve uyumluluk riski de olusturur."
    if any(f.category in {"null-density", "empty-table"} for f in findings):
        return f"{table_name or 'Secilen veri yuzeyi'} icinde completeness zayif gorunuyor; upstream veri toplama veya ETL adimlarinda kopma olabilir."
    return "Bulgular schema, veri standardi ve performans eksenlerinde birikiyor; tablo tasarimi ile veri uretim akisi birlikte ele alinmali."


def _root_cause_summary(findings: List[DbQualityFinding], smells: List[DbSchemaSmell]) -> str:
    categories = {finding.category for finding in findings}
    if "business-rule" in categories:
        return "En baskin kok neden adayi uygulama event/state machine kurallarinin DB seviyesinde garanti altina alinmamasi."
    if "security-storage" in categories:
        return "En baskin kok neden adayi hassas veri siniflandirma ve saklama politikasinin semaya yansimamis olmasi."
    if smells:
        return "En baskin kok neden adayi yillar icinde buyuyen schema tasariminin normalizasyon ve constraint acisindan zayif kalmasi."
    if "slow-query" in categories or "table-scan" in categories:
        return "En baskin kok neden adayi index kapsami ve query seklinin hedef yuk profilini karsilamiyor olmasi."
    return "Belirgin kok neden sinyali daginik; constraint ve veri standardizasyon katmanlari birlikte gozden gecirilmeli."


def _build_db_quality_response(
    findings: List[DbQualityFinding],
    schema_smells: List[DbSchemaSmell],
    constraint_summary: Optional[DbConstraintSummary],
    table_name: Optional[str],
    duration_ms: float,
    query_result: Optional[Dict[str, Any]],
    schema_validation: Optional[Dict[str, Any]],
    detected_columns: List[str],
    sample_rows: List[Dict[str, Any]],
) -> DbQualityResponse:
    penalties = {"high": 25, "medium": 12, "low": 5}
    score = 100
    for finding in findings:
        score -= penalties.get(finding.severity, 8)
    score -= len(schema_smells) * 4
    score = max(0, min(100, score))
    breakdown = _score_breakdown(findings)
    table_quality_score = round((breakdown.integrity + breakdown.completeness + breakdown.consistency + breakdown.performance + breakdown.security) / 5)
    summary = (
        f"DB kalite analizi {len(findings)} bulgu ve {len(schema_smells)} schema smell uretti. "
        f"{'Secilen tablo' if table_name else 'Calisan sorgu'} icin performans, constraint, veri butunlugu ve security sinyalleri kontrol edildi."
    )
    success = not any(finding.severity == "high" for finding in findings)

    return DbQualityResponse(
        success=success,
        overall_score=score,
        table_quality_score=table_quality_score,
        summary=summary,
        ai_interpretation=_ai_interpretation(findings, table_name),
        root_cause_summary=_root_cause_summary(findings, schema_smells),
        table_name=table_name,
        duration_ms=round(duration_ms, 2),
        score_breakdown=breakdown,
        findings=findings,
        schema_smells=schema_smells,
        constraint_summary=constraint_summary,
        query_result=query_result,
        schema_validation=schema_validation,
        detected_columns=detected_columns,
        sample_rows=sample_rows,
    )


@router.post("/query")
def run_db_query(data: DBQuerySchema):
    executor = DatabaseExecutor(data.connection_string)
    return executor.execute_query(data.query, data.params)


@router.post("/quality-audit", response_model=DbQualityResponse)
def run_db_quality_audit(data: DbQualityRequest):
    start_time = time.time()
    executor = DatabaseExecutor(data.connection_string)
    findings: List[DbQualityFinding] = []
    query_result: Optional[Dict[str, Any]] = None
    schema_validation: Optional[Dict[str, Any]] = None
    detected_columns: List[str] = []
    sample_rows: List[Dict[str, Any]] = []
    constraint_summary: Optional[DbConstraintSummary] = None

    if data.query:
        query_result = executor.execute_query(data.query)
        _analyze_query_text(data.query, findings)
        if query_result.get("success"):
            if query_result.get("duration_ms", 0) >= 300:
                _add_db_finding(
                    findings,
                    "high",
                    "slow-query",
                    "Sorgu belirgin sekilde yavas calisti",
                    "Calisan sorgu hedefin ustunde sure aldi ve optimize edilmeye aday.",
                    f"Duration: {query_result.get('duration_ms')} ms",
                    "Execution plan incele, index ve sorgu seklini optimize et.",
                )
            elif query_result.get("duration_ms", 0) >= 120:
                _add_db_finding(
                    findings,
                    "medium",
                    "slow-query",
                    "Sorgu suresi izlenmeli",
                    "Calisan sorgu yerel esiklerin ustune cikiyor.",
                    f"Duration: {query_result.get('duration_ms')} ms",
                    "p95/p99 hedefleri belirle ve query pattern'ini izle.",
                )
            sample_rows = (query_result.get("data") or [])[: data.sample_limit]
            if sample_rows:
                detected_columns = list(sample_rows[0].keys())
                _analyze_sample_rows(sample_rows, findings)
        else:
            _add_db_finding(
                findings,
                "high",
                "query-error",
                "DB sorgusu hata verdi",
                "Sorgu execute edilirken hata olustu; bu durum query kalitesi veya environment sorunu olabilir.",
                query_result.get("error", "Unknown query error"),
                "SQL syntax, baglanti bilgisi ve yetki seviyesini dogrula.",
            )

    if data.table_name:
        inspector = inspect(executor.engine)
        columns = inspector.get_columns(data.table_name)
        detected_columns = [column["name"] for column in columns]
        schema_validation = executor.validate_schema(data.table_name, data.expected_columns)
        count_result = executor.check_table_count(data.table_name)
        sample_query = executor.execute_query(f"SELECT * FROM {data.table_name} LIMIT {max(1, data.sample_limit)}")
        sample_rows = sample_query.get("data", []) if sample_query.get("success") else []
        constraint_summary = _inspect_constraints(executor, data.table_name)

        if schema_validation.get("missing_columns"):
            _add_db_finding(
                findings,
                "high",
                "schema-mismatch",
                "Beklenen kolonlar eksik",
                "Tablo semasi beklenen kolon seti ile uyusmuyor.",
                f"Missing columns: {', '.join(schema_validation.get('missing_columns', []))}",
                "Migration, ORM modeli ve target schema contract'ini hizala.",
            )

        if data.api_expected_fields:
            missing_api_fields = [field for field in data.api_expected_fields if field not in detected_columns]
            if missing_api_fields:
                _add_db_finding(
                    findings,
                    "medium",
                    "api-db-consistency",
                    "API beklentisi ile DB kolonlari ayrisiyor",
                    "API tarafindan beklenen alanlardan bazilari DB tablosunda gorunmedi.",
                    f"Missing API fields: {', '.join(missing_api_fields)}",
                    "API response modeli ile tablo kolonlarini hizala veya mapping katmanini netlestir.",
                )

        if not constraint_summary.primary_keys:
            _add_db_finding(
                findings,
                "high",
                "constraint",
                "Primary key sinyali bulunamadi",
                "Tabloda belirgin bir primary key tanimi gorunmuyor.",
                data.table_name,
                "Bu tablo icin primary key veya surrogate key yapisini netlestir.",
            )

        if count_result.get("success") and count_result.get("count", 0) == 0:
            _add_db_finding(
                findings,
                "medium",
                "empty-table",
                "Tablo bos gorunuyor",
                "Secilen tabloda hic kayit yok; bu durum seed, ETL veya veri akisi sorunu olabilir.",
                f"Row count: {count_result.get('count', 0)}",
                "Bu tablonun beklenen veri kaynagini ve populate akisini kontrol et.",
            )

        if sample_query.get("success") and sample_query.get("duration_ms", 0) >= 150:
            _add_db_finding(
                findings,
                "medium",
                "table-scan",
                "Tablo orneklemesi beklenenden yavas",
                "Basit bir ornekleme sorgusu bile yavas calisiyor; tablo boyutu veya index durumu incelenmeli.",
                f"Duration: {sample_query.get('duration_ms')} ms",
                "Index kapsami, row estimate ve storage durumunu gozden gecir.",
            )

        _analyze_sample_rows(sample_rows, findings)

    schema_smells = _schema_smells(
        table_name=data.table_name,
        detected_columns=detected_columns,
        nullable_columns=constraint_summary.nullable_columns if constraint_summary else [],
    )

    return _build_db_quality_response(
        findings=findings,
        schema_smells=schema_smells,
        constraint_summary=constraint_summary,
        table_name=data.table_name,
        duration_ms=(time.time() - start_time) * 1000,
        query_result=query_result,
        schema_validation=schema_validation,
        detected_columns=detected_columns,
        sample_rows=sample_rows[: min(len(sample_rows), 10)],
    )


@router.post("/validate-schema")
def validate_db_schema(data: DBSchemaValidationSchema):
    executor = DatabaseExecutor(data.connection_string)
    return executor.validate_schema(data.table_name, data.expected_columns)


@router.get("/tables")
def get_db_tables(connection_string: str):
    from sqlalchemy import create_engine

    engine = create_engine(connection_string)
    inspector = inspect(engine)
    return inspector.get_table_names()
