
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from database import get_db
from database.models import (
    AccessibilityAnalysisRecord,
    ApiAnalysisRecord,
    DbAnalysisRecord,
    DatasetAnalysisRecord,
    JiraTicketDraft,
    MobileAnalysisRecord,
    PerformanceAnalysisRecord,
    Project,
    SecurityAnalysisRecord,
    TestRun,
    UiuxAnalysisRecord,
)
from core.bug_analysis import build_bug_analysis
import json

router = APIRouter(prefix="/reports", tags=["reports"])


class JiraDraftRequest(BaseModel):
    source_module: str = Field(..., min_length=1, max_length=100)
    source_type: str = Field(default="final_report_action", max_length=100)
    source_ref: str | None = Field(default=None, max_length=255)
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    priority: str = Field(default="medium", max_length=50)
    evidence: str | None = None
    recommendation: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class JiraDraftChecklistUpdate(BaseModel):
    acceptance_criteria: list[dict[str, Any]] = Field(default_factory=list)


def _enum_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    return value


def _datetime_value(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _parse_logs(raw_logs: str | None) -> Any:
    if not raw_logs:
        return None

    try:
        return json.loads(raw_logs)
    except json.JSONDecodeError:
        return {
            "raw": raw_logs,
            "parse_error": "Run logları JSON formatında değil; ham metin olarak dışa aktarıldı.",
        }


def _logs_as_dict(raw_logs: str | None) -> dict[str, Any]:
    if not raw_logs:
        return {"summary": "", "steps": [], "integrations": []}

    try:
        parsed = json.loads(raw_logs)
    except json.JSONDecodeError:
        return {"summary": "", "steps": [], "integrations": [], "raw": raw_logs}

    if isinstance(parsed, dict):
        parsed.setdefault("steps", [])
        parsed.setdefault("integrations", [])
        return parsed

    if isinstance(parsed, list):
        return {"summary": "", "steps": parsed, "integrations": []}

    return {"summary": "", "steps": [], "integrations": [], "raw": parsed}


def _ticket_priority(run: TestRun, failed_steps: list[dict[str, Any]]) -> str:
    if _enum_value(run.status) in {"failed", "crashed"} or failed_steps:
        return "high"
    if run.findings:
        return "medium"
    return "low"


def _build_work_items(run: TestRun, logs: dict[str, Any]) -> list[str]:
    work_items: list[str] = []
    steps = logs.get("steps", [])
    failed_steps = [step for step in steps if step.get("status") == "failed"]

    for finding in run.findings:
        work_items.append(
            f"{finding.category}/{finding.severity}: {finding.title} - {finding.description}"
        )

    for step in failed_steps:
        label = step.get("action_label") or step.get("action") or "step"
        target = step.get("target") or step.get("selector_used") or "unknown target"
        reason = step.get("reason") or step.get("error") or "Hata detayı yok."
        work_items.append(f"Failed step düzelt: {label} -> {target}. Sebep: {reason}")

    return work_items


def _build_ticket_payload(run: TestRun, logs: dict[str, Any]) -> dict[str, Any]:
    steps = logs.get("steps", [])
    failed_steps = [step for step in steps if step.get("status") == "failed"]
    work_items = _build_work_items(run, logs)
    module_label = (run.module_name or "general").replace("_", " ").title()
    project_name = run.project.name if run.project else f"Project #{run.project_id}"
    if not work_items:
        raise HTTPException(
            status_code=422,
            detail=(
                "Bu run için gerçek finding veya failed step bulunamadı. "
                "Demo ticket üretilmedi; önce gerçek analiz/koşu çıktısı oluşmalı."
            ),
        )

    title = f"{module_label}: {project_name} için {len(work_items)} gerçek bulgu/adım"

    return {
        "provider": "jira",
        "ticket_key": f"JIRA-RUN-{run.id}",
        "title": title,
        "description": (
            f"Run #{run.id} ({project_name}) sonucuna göre {module_label} modülünde "
            "tespit edilen gerçek bulgu/adım kayıtları ticket içeriğine aktarıldı."
        ),
        "priority": _ticket_priority(run, failed_steps),
        "status": "created",
        "target": run.target,
        "module": run.module_name,
        "run_status": _enum_value(run.status),
        "work_items": work_items,
        "acceptance_criteria": [],
        "created_at": datetime.utcnow().isoformat(),
    }


def _append_integration_log(run: TestRun, db: Session) -> dict[str, Any]:
    logs = _logs_as_dict(run.logs)
    event = _build_ticket_payload(run, logs)
    logs["integrations"].append(event)
    run.logs = json.dumps(logs, ensure_ascii=False)
    db.commit()
    return event


def _get_run_or_404(run_id: int, db: Session) -> TestRun:
    run = db.query(TestRun).filter(TestRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Test koşusu bulunamadı.")
    return run


def _build_run_report(run: TestRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "project_id": run.project_id,
        "project_name": run.project.name if run.project else None,
        "page_id": run.page_id,
        "page_name": run.page.name if run.page else None,
        "platform": _enum_value(run.platform),
        "module_name": run.module_name,
        "target": run.target,
        "test_case_id": run.test_case_id,
        "test_case_title": run.test_case.title if run.test_case else None,
        "status": _enum_value(run.status),
        "config": run.config,
        "logs": _parse_logs(run.logs),
        "findings": [
            {
                "id": finding.id,
                "title": finding.title,
                "description": finding.description,
                "severity": finding.severity,
                "category": finding.category,
                "screenshot_url": finding.screenshot_url,
                "extra_data": finding.extra_data,
                "created_at": _datetime_value(finding.created_at),
            }
            for finding in run.findings
        ],
        "started_at": _datetime_value(run.started_at),
        "completed_at": _datetime_value(run.completed_at),
        "created_at": _datetime_value(run.created_at),
    }


def _severity_rank(severity: str | None) -> int:
    return {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4, "none": 5}.get(str(severity or "none").lower(), 5)


def _security_record_summary(record: SecurityAnalysisRecord) -> dict[str, Any]:
    payload = record.analysis_payload or {}
    risk_summary = payload.get("risk_summary") or {}
    priority_actions = risk_summary.get("priority_actions") or []
    scan_evidence = payload.get("scan_evidence") or {}
    return {
        "id": record.id,
        "source_type": record.source_type,
        "source_label": record.source_label,
        "source_url": record.source_url,
        "overall_score": record.overall_score,
        "findings_count": record.findings_count,
        "overview": record.overview or "",
        "created_at": _datetime_value(record.created_at),
        "risk_summary": risk_summary,
        "priority_actions": priority_actions[:3],
        "scan_evidence": {
            "status_code": scan_evidence.get("status_code"),
            "final_url": scan_evidence.get("final_url"),
            "headers_observed": scan_evidence.get("headers_observed", 0),
            "checks_executed": len(scan_evidence.get("checks_executed") or []),
        },
    }


def _generic_analysis_summary(record: Any, module_key: str) -> dict[str, Any]:
    payload = record.analysis_payload or {}
    return {
        "id": record.id,
        "module": module_key,
        "source_type": getattr(record, "source_type", None),
        "source_label": getattr(record, "source_label", None),
        "source_url": getattr(record, "source_url", None),
        "overall_score": int(getattr(record, "overall_score", 0) or 0),
        "findings_count": int(getattr(record, "findings_count", 0) or 0),
        "overview": getattr(record, "overview", "") or payload.get("overview", "") or payload.get("summary", ""),
        "created_at": _datetime_value(getattr(record, "created_at", None)),
    }


def _accessibility_analysis_summary(record: AccessibilityAnalysisRecord) -> dict[str, Any]:
    payload = record.analysis_payload or {}
    findings = [
        finding
        for finding in (payload.get("findings") or [])
        if isinstance(finding, dict)
    ]
    return {
        **_generic_analysis_summary(record, "accessibility"),
        "score_breakdown": payload.get("score_breakdown") or {},
        "accessibility_summary": payload.get("accessibility_summary") or {},
        "test_suggestions": payload.get("test_suggestions") or [],
        "keyboard_profile": payload.get("keyboard_profile") or {},
        "component_summary": payload.get("component_summary") or {},
        "finding_categories": [
            finding.get("category")
            for finding in findings
            if finding.get("category")
        ],
        "findings": findings[:8],
        "high_findings": [
            finding
            for finding in findings
            if finding.get("severity") in {"critical", "high"}
        ][:4],
    }


def _uiux_analysis_summary(record: UiuxAnalysisRecord) -> dict[str, Any]:
    payload = record.analysis_payload or {}
    findings = [
        finding
        for finding in (payload.get("findings") or [])
        if isinstance(finding, dict)
    ]
    return {
        **_generic_analysis_summary(record, "uiux"),
        "detected_platform": payload.get("detected_platform") or payload.get("platform"),
        "platform_profile": payload.get("platform_profile"),
        "color_intelligence": payload.get("color_intelligence") or {},
        "design_tokens": payload.get("design_tokens") or {},
        "task_evaluation": payload.get("task_evaluation") or {},
        "persona_risk": payload.get("persona_risk") or {},
        "visual_regression": payload.get("visual_regression") or {},
        "score_breakdown": payload.get("score_breakdown") or {},
        "evidence_matrix": payload.get("evidence_matrix") or {},
        "test_suggestions": payload.get("test_suggestions") or [],
        "finding_categories": [
            finding.get("category")
            for finding in findings
            if finding.get("category")
        ],
        "findings": findings[:6],
        "high_findings": [
            finding
            for finding in findings
            if finding.get("severity") in {"critical", "high"}
        ][:3],
    }


def _mobile_analysis_summary(record: MobileAnalysisRecord) -> dict[str, Any]:
    payload = record.analysis_payload or {}
    findings = [
        finding
        for finding in (payload.get("findings") or [])
        if isinstance(finding, dict)
    ]
    context_profile = payload.get("context_profile") or {}
    return {
        **_generic_analysis_summary(record, "mobile"),
        "score_breakdown": payload.get("score_breakdown") or {},
        "context_profile": context_profile,
        "screen_type": context_profile.get("screen_type"),
        "task_completion_friction": payload.get("task_completion_friction"),
        "cross_platform_parity_summary": payload.get("cross_platform_parity_summary"),
        "thumb_zone_summary": payload.get("thumb_zone_summary"),
        "keyboard_overlap_signal": payload.get("keyboard_overlap_signal"),
        "safe_area_signal": payload.get("safe_area_signal"),
        "finding_categories": [
            finding.get("category")
            for finding in findings
            if finding.get("category")
        ],
        "findings": findings[:8],
        "high_findings": [
            finding
            for finding in findings
            if finding.get("severity") in {"critical", "high"}
        ][:4],
    }


def _api_analysis_summary(record: ApiAnalysisRecord) -> dict[str, Any]:
    payload = record.analysis_payload or {}
    findings = payload.get("findings") or []
    evidence_summary = payload.get("evidence_summary") or {}
    return {
        **_generic_analysis_summary(record, "api"),
        "method": payload.get("method"),
        "status_code": payload.get("status_code"),
        "duration_ms": payload.get("duration_ms"),
        "endpoint_context": payload.get("endpoint_context"),
        "endpoint_risk_score": payload.get("endpoint_risk_score"),
        "score_breakdown": payload.get("score_breakdown") or {},
        "evidence_summary": evidence_summary,
        "finding_categories": [
            finding.get("category")
            for finding in findings
            if isinstance(finding, dict) and finding.get("category")
        ],
        "findings": [
            finding
            for finding in findings
            if isinstance(finding, dict)
        ][:6],
        "high_findings": [
            finding
            for finding in findings
            if isinstance(finding, dict) and finding.get("severity") == "high"
        ][:3],
    }


def _api_priority_actions(api_summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    merged: dict[tuple[str, str, str], dict[str, Any]] = {}
    for record in api_summaries:
        findings = (record.get("high_findings") or record.get("findings") or [])

        # high_findings is intentionally short. Fall back to categories so older
        # records still produce a useful report signal.
        if not findings and record.get("finding_categories"):
            findings = [
                {
                    "title": f"API {category} sinyali",
                    "severity": "medium",
                    "category": category,
                    "description": record.get("overview") or "API endpoint bulgusu incelenmeli.",
                    "evidence": record.get("source_url") or record.get("source_label") or "API record",
                    "recommendation": "Endpoint response contract, status ve hata semasini dogrula.",
                }
                for category in record.get("finding_categories", [])[:3]
            ]

        for finding in findings[:3]:
            if not isinstance(finding, dict):
                continue
            endpoint = record.get("source_url") or ""
            category = finding.get("category") or "api"
            evidence = finding.get("evidence") or record.get("overview") or ""
            key = (endpoint, category, evidence)
            action = {
                "title": finding.get("title") or "API endpoint finding",
                "severity": finding.get("severity") or "medium",
                "category": category,
                "source": "api",
                "api_record_id": record.get("id"),
                "api_record_ids": [record.get("id")] if record.get("id") else [],
                "duplicate_count": 1,
                "endpoint": endpoint,
                "method": record.get("method"),
                "status_code": record.get("status_code"),
                "duration_ms": record.get("duration_ms"),
                "summary": finding.get("description") or record.get("overview") or "API endpoint bulgusu incelenmeli.",
                "evidence": evidence,
                "recommendation": finding.get("recommendation") or "Endpoint sozlesmesini, response tipini ve hata standardini kontrol et.",
                "score_breakdown": record.get("score_breakdown") or {},
                "evidence_summary": record.get("evidence_summary") or {},
            }
            existing = merged.get(key)
            if existing:
                existing["duplicate_count"] = int(existing.get("duplicate_count", 1) or 1) + 1
                if record.get("id") and record.get("id") not in existing["api_record_ids"]:
                    existing["api_record_ids"].append(record.get("id"))
                existing["api_record_id"] = max(existing["api_record_ids"])
                existing["duration_ms"] = max(float(existing.get("duration_ms") or 0), float(action.get("duration_ms") or 0))
                existing["severity"] = min(
                    [existing.get("severity"), action.get("severity")],
                    key=lambda value: _severity_rank(str(value)),
                )
                existing_summary = existing.get("evidence_summary") or {}
                incoming_summary = action.get("evidence_summary") or {}
                for signal_key in (
                    "contract_signals",
                    "security_signals",
                    "performance_signals",
                    "validation_signals",
                    "availability_signals",
                    "negative_probe_signals",
                ):
                    existing_summary[signal_key] = max(
                        int(existing_summary.get(signal_key, 0) or 0),
                        int(incoming_summary.get(signal_key, 0) or 0),
                    )
                existing["evidence_summary"] = existing_summary
            else:
                merged[key] = action

    actions = list(merged.values())
    actions.sort(key=lambda item: (_severity_rank(item.get("severity")), item.get("api_record_id") or 0))
    return actions[:8]


def _db_analysis_summary(record: DbAnalysisRecord) -> dict[str, Any]:
    payload = record.analysis_payload or {}
    findings = [
        finding
        for finding in (payload.get("findings") or [])
        if isinstance(finding, dict)
    ]
    schema_smells = [
        smell
        for smell in (payload.get("schema_smells") or [])
        if isinstance(smell, dict)
    ]
    return {
        **_generic_analysis_summary(record, "database"),
        "table_name": payload.get("table_name"),
        "table_quality_score": payload.get("table_quality_score"),
        "detected_columns": payload.get("detected_columns") or [],
        "query": payload.get("query") or payload.get("source_query"),
        "findings": findings[:6],
        "schema_smells": schema_smells[:6],
        "finding_categories": [
            item.get("category")
            for item in findings + schema_smells
            if item.get("category")
        ],
        "high_findings": [
            item
            for item in findings + schema_smells
            if item.get("severity") == "high"
        ][:3],
    }


def _performance_analysis_summary(record: PerformanceAnalysisRecord) -> dict[str, Any]:
    payload = record.analysis_payload or {}
    findings = [
        finding
        for finding in (payload.get("findings") or [])
        if isinstance(finding, dict)
    ]
    return {
        **_generic_analysis_summary(record, "performance"),
        "performance_grade": payload.get("performance_grade"),
        "technical_score": payload.get("technical_score"),
        "perceived_score": payload.get("perceived_score"),
        "api_duration_ms": payload.get("api_duration_ms") or payload.get("duration_ms"),
        "sample_api_runs": payload.get("sample_api_runs"),
        "finding_categories": [
            finding.get("category")
            for finding in findings
            if finding.get("category")
        ],
        "findings": findings[:6],
        "high_findings": [
            finding
            for finding in findings
            if finding.get("severity") == "high"
        ][:3],
    }


def _db_priority_actions(db_summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    merged: dict[tuple[str, str, str], dict[str, Any]] = {}
    for record in db_summaries:
        findings = (record.get("high_findings") or record.get("findings") or record.get("schema_smells") or [])
        if not findings and record.get("finding_categories"):
            findings = [
                {
                    "title": f"DB {category} sinyali",
                    "severity": "medium",
                    "category": category,
                    "description": record.get("overview") or "DB kalite bulgusu incelenmeli.",
                    "evidence": record.get("query") or record.get("source_label") or "DB record",
                    "recommendation": "Schema, query ve API field beklentilerini birlikte dogrula.",
                }
                for category in record.get("finding_categories", [])[:3]
            ]

        for finding in findings[:3]:
            if not isinstance(finding, dict):
                continue
            category = finding.get("category") or "database"
            evidence = finding.get("evidence") or record.get("query") or record.get("source_label") or ""
            key = (str(record.get("table_name") or record.get("source_label") or ""), category, evidence)
            action = {
                "title": finding.get("title") or "Database quality finding",
                "severity": finding.get("severity") or "medium",
                "category": category,
                "source": "database",
                "db_record_id": record.get("id"),
                "db_record_ids": [record.get("id")] if record.get("id") else [],
                "duplicate_count": 1,
                "table_name": record.get("table_name"),
                "query": record.get("query"),
                "summary": finding.get("description") or record.get("overview") or "DB kalite bulgusu incelenmeli.",
                "evidence": evidence,
                "recommendation": finding.get("recommendation") or "DB schema, query shape ve API field beklentilerini birlikte hizala.",
                "score": record.get("overall_score"),
                "detected_columns": record.get("detected_columns") or [],
            }
            existing = merged.get(key)
            if existing:
                existing["duplicate_count"] = int(existing.get("duplicate_count", 1) or 1) + 1
                if record.get("id") and record.get("id") not in existing["db_record_ids"]:
                    existing["db_record_ids"].append(record.get("id"))
                existing["db_record_id"] = max(existing["db_record_ids"])
                existing["severity"] = min(
                    [existing.get("severity"), action.get("severity")],
                    key=lambda value: _severity_rank(str(value)),
                )
            else:
                merged[key] = action

    actions = list(merged.values())
    actions.sort(key=lambda item: (_severity_rank(item.get("severity")), item.get("db_record_id") or 0))
    return actions[:8]


def _performance_priority_actions(performance_summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    merged: dict[tuple[str, str, str], dict[str, Any]] = {}
    for record in performance_summaries:
        findings = (record.get("high_findings") or record.get("findings") or [])
        if not findings and record.get("findings_count", 0) > 0:
            findings = [
                {
                    "title": "Performance attention signal",
                    "severity": "medium",
                    "category": "performance",
                    "description": record.get("overview") or "Performance kaydi bulgu uretti.",
                    "evidence": record.get("source_url") or record.get("source_label") or "Performance record",
                    "recommendation": "Latency, asset, DB query ve downstream servis etkisini birlikte incele.",
                }
            ]

        for finding in findings[:3]:
            if not isinstance(finding, dict):
                continue
            category = finding.get("category") or "performance"
            target = record.get("source_url") or record.get("source_label") or ""
            evidence = finding.get("evidence") or record.get("overview") or target
            key = (target, category, evidence)
            action = {
                "title": finding.get("title") or "Performance finding",
                "severity": finding.get("severity") or "medium",
                "category": category,
                "source": "performance",
                "performance_record_id": record.get("id"),
                "performance_record_ids": [record.get("id")] if record.get("id") else [],
                "duplicate_count": 1,
                "target": target,
                "summary": finding.get("description") or record.get("overview") or "Performans bulgusu incelenmeli.",
                "evidence": evidence,
                "recommendation": finding.get("recommendation") or "p95 hedefi, cache, query ve network davranisini birlikte profille.",
                "score": record.get("overall_score"),
                "grade": record.get("performance_grade"),
                "technical_score": record.get("technical_score"),
                "perceived_score": record.get("perceived_score"),
                "api_duration_ms": record.get("api_duration_ms"),
            }
            existing = merged.get(key)
            if existing:
                existing["duplicate_count"] = int(existing.get("duplicate_count", 1) or 1) + 1
                if record.get("id") and record.get("id") not in existing["performance_record_ids"]:
                    existing["performance_record_ids"].append(record.get("id"))
                existing["performance_record_id"] = max(existing["performance_record_ids"])
                existing["severity"] = min(
                    [existing.get("severity"), action.get("severity")],
                    key=lambda value: _severity_rank(str(value)),
                )
            else:
                merged[key] = action

    actions = list(merged.values())
    actions.sort(key=lambda item: (_severity_rank(item.get("severity")), item.get("performance_record_id") or 0))
    return actions[:8]


def _uiux_priority_actions(uiux_summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for record in uiux_summaries:
        findings = record.get("findings") or []
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            severity = str(finding.get("severity") or "medium")
            if severity not in {"critical", "high", "medium"}:
                continue
            category = str(finding.get("category") or "uiux")
            title = str(finding.get("title") or "UI/UX bulgusu incelenmeli")
            evidence = finding.get("numeric_evidence") or {}
            metric = evidence.get("metric") or category
            key = (title, category)
            action = {
                "title": title,
                "severity": severity,
                "category": category,
                "source": "uiux",
                "platform": record.get("platform"),
                "detected_platform": record.get("detected_platform"),
                "uiux_record_id": record.get("id"),
                "uiux_record_ids": [record.get("id")] if record.get("id") else [],
                "duplicate_count": 1,
                "summary": finding.get("description") or record.get("overview") or "UI/UX bulgusu incelenmeli.",
                "evidence": f"{metric}: {evidence.get('value', 'n/a')}",
                "recommendation": finding.get("recommendation") or "İlgili UI/UX metriğini tasarım ve screenshot regresyon testiyle doğrula.",
                "score": record.get("overall_score"),
                "metric": metric,
                "metric_value": evidence.get("value"),
                "test_suggestion": finding.get("test_suggestion"),
                "color_intelligence": record.get("color_intelligence") or {},
                "design_tokens": record.get("design_tokens") or {},
                "task_evaluation": record.get("task_evaluation") or {},
            }
            existing = merged.get(key)
            if existing:
                existing["duplicate_count"] = int(existing.get("duplicate_count", 1) or 1) + 1
                if record.get("id") and record.get("id") not in existing["uiux_record_ids"]:
                    existing["uiux_record_ids"].append(record.get("id"))
                existing["uiux_record_id"] = max(existing["uiux_record_ids"]) if existing["uiux_record_ids"] else existing.get("uiux_record_id")
                existing["severity"] = min([existing.get("severity"), severity], key=lambda value: _severity_rank(str(value)))
            else:
                merged[key] = action
        design_tokens = record.get("design_tokens") or {}
        try:
            token_score = int(design_tokens.get("design_token_score") or 100)
        except (TypeError, ValueError):
            token_score = 100
        if design_tokens and token_score < 82:
            title = "Design token consistency should be reviewed"
            category = "design-token"
            key = (title, category)
            action = {
                "title": title,
                "severity": "medium" if token_score >= 65 else "high",
                "category": category,
                "source": "uiux",
                "platform": record.get("platform"),
                "detected_platform": record.get("detected_platform"),
                "uiux_record_id": record.get("id"),
                "uiux_record_ids": [record.get("id")] if record.get("id") else [],
                "duplicate_count": 1,
                "summary": "Spacing, font scale, radius veya button token tutarliligi zayif gorunuyor.",
                "evidence": f"design_token_score: {token_score}",
                "recommendation": design_tokens.get("recommendation")
                or "Spacing, font, radius ve button standardini tasarim sistemi tokenlariyla hizala.",
                "score": record.get("overall_score"),
                "metric": "design_token_score",
                "metric_value": token_score,
                "test_suggestion": "Ayni ekran icin tasarim token regresyon kontrolu yap.",
                "color_intelligence": record.get("color_intelligence") or {},
                "design_tokens": design_tokens,
                "task_evaluation": record.get("task_evaluation") or {},
            }
            existing = merged.get(key)
            if existing:
                existing["duplicate_count"] = int(existing.get("duplicate_count", 1) or 1) + 1
                if record.get("id") and record.get("id") not in existing["uiux_record_ids"]:
                    existing["uiux_record_ids"].append(record.get("id"))
                existing["uiux_record_id"] = max(existing["uiux_record_ids"]) if existing["uiux_record_ids"] else existing.get("uiux_record_id")
                existing["severity"] = min([existing.get("severity"), action["severity"]], key=lambda value: _severity_rank(str(value)))
            else:
                merged[key] = action

        task_evaluation = record.get("task_evaluation") or {}
        try:
            task_score = int(task_evaluation.get("task_score") or 100)
            friction_score = int(task_evaluation.get("friction_score") or 0)
        except (TypeError, ValueError):
            task_score = 100
            friction_score = 0
        if task_evaluation and str(task_evaluation.get("task_type") or "generic") != "generic" and (task_score < 82 or friction_score >= 40):
            task_label = str(task_evaluation.get("task_label") or "Task flow")
            title = f"{task_label} akisi iyilestirilmeli"
            category = "task-flow"
            key = (title, category)
            action = {
                "title": title,
                "severity": "high" if task_score < 58 or friction_score >= 62 else "medium",
                "category": category,
                "source": "uiux",
                "platform": record.get("platform"),
                "detected_platform": record.get("detected_platform"),
                "uiux_record_id": record.get("id"),
                "uiux_record_ids": [record.get("id")] if record.get("id") else [],
                "duplicate_count": 1,
                "summary": task_evaluation.get("summary") or "Gorev akisi ekran uzerinde surtunme uretiyor.",
                "evidence": f"task_score: {task_score}, friction_score: {friction_score}",
                "recommendation": task_evaluation.get("recommendation") or "Ana gorev yolunu daha net hale getir.",
                "score": record.get("overall_score"),
                "metric": "task_completion_score",
                "metric_value": task_score,
                "test_suggestion": "Ayni gorev tipi icin primary action, input ve sonraki adim yolunu tekrar dogrula.",
                "color_intelligence": record.get("color_intelligence") or {},
                "design_tokens": record.get("design_tokens") or {},
                "task_evaluation": task_evaluation,
            }
            existing = merged.get(key)
            if existing:
                existing["duplicate_count"] = int(existing.get("duplicate_count", 1) or 1) + 1
                if record.get("id") and record.get("id") not in existing["uiux_record_ids"]:
                    existing["uiux_record_ids"].append(record.get("id"))
                existing["uiux_record_id"] = max(existing["uiux_record_ids"]) if existing["uiux_record_ids"] else existing.get("uiux_record_id")
                existing["severity"] = min([existing.get("severity"), action["severity"]], key=lambda value: _severity_rank(str(value)))
            else:
                merged[key] = action

        visual_regression = record.get("visual_regression") or {}
        if visual_regression.get("status") == "regressed":
            regressions = [
                item
                for item in (visual_regression.get("regressions") or [])
                if isinstance(item, dict)
            ]
            title = "UI/UX visual regression detected"
            category = "visual-regression"
            score_delta = visual_regression.get("score_delta")
            key = (title, category)
            action = {
                "title": title,
                "severity": "high" if isinstance(score_delta, int) and score_delta <= -15 else "medium",
                "category": category,
                "source": "uiux",
                "platform": record.get("platform"),
                "detected_platform": record.get("detected_platform"),
                "uiux_record_id": record.get("id"),
                "uiux_record_ids": [record.get("id")] if record.get("id") else [],
                "duplicate_count": 1,
                "summary": visual_regression.get("summary") or "Onceki UI/UX kaydina gore metrik gerilemesi bulundu.",
                "evidence": (
                    f"baseline #{visual_regression.get('baseline_record_id')}, "
                    f"score_delta: {score_delta}, "
                    f"pixel_change: {visual_regression.get('pixel_change_percent')}"
                ),
                "recommendation": visual_regression.get("recommendation")
                or "Onceki screenshot ile yeni ekran arasindaki UX metrik farklarini incele.",
                "score": record.get("overall_score"),
                "metric": regressions[0].get("metric") if regressions else "visual_regression",
                "metric_value": score_delta,
                "test_suggestion": "Ayni ekran icin baseline screenshot ile yeni screenshot UX metriklerini karsilastir.",
                "visual_regression": visual_regression,
                "color_intelligence": record.get("color_intelligence") or {},
                "design_tokens": record.get("design_tokens") or {},
                "task_evaluation": record.get("task_evaluation") or {},
            }
            existing = merged.get(key)
            if existing:
                existing["duplicate_count"] = int(existing.get("duplicate_count", 1) or 1) + 1
                if record.get("id") and record.get("id") not in existing["uiux_record_ids"]:
                    existing["uiux_record_ids"].append(record.get("id"))
                existing["uiux_record_id"] = max(existing["uiux_record_ids"]) if existing["uiux_record_ids"] else existing.get("uiux_record_id")
                existing["severity"] = min([existing.get("severity"), action["severity"]], key=lambda value: _severity_rank(str(value)))
            else:
                merged[key] = action

    actions = list(merged.values())
    actions.sort(key=lambda item: (_severity_rank(item.get("severity")), item.get("uiux_record_id") or 0))
    return actions[:8]


def _accessibility_priority_actions(accessibility_summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for record in accessibility_summaries:
        findings = record.get("findings") or []
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            severity = str(finding.get("severity") or "medium").lower()
            if severity not in {"critical", "high", "medium"}:
                continue
            category = str(finding.get("category") or "accessibility")
            title = str(finding.get("title") or finding.get("summary") or "Accessibility issue")
            key = (title, category)
            evidence = finding.get("evidence") if isinstance(finding.get("evidence"), dict) else {}
            action = {
                "title": title,
                "severity": severity,
                "category": category,
                "source": "accessibility",
                "accessibility_record_id": record.get("id"),
                "accessibility_record_ids": [record.get("id")] if record.get("id") else [],
                "duplicate_count": 1,
                "summary": str(
                    finding.get("description")
                    or finding.get("why_flagged")
                    or record.get("overview")
                    or "Accessibility finding requires review."
                ),
                "evidence": str(
                    evidence.get("why_flagged")
                    or evidence.get("selector")
                    or finding.get("evidence_text")
                    or finding.get("category")
                    or category
                ),
                "recommendation": str(
                    finding.get("recommendation")
                    or "Label, focus, contrast ve semantic accessibility davranisini dogrula."
                ),
                "wcag_refs": finding.get("wcag_refs") or [],
                "impact_score": finding.get("impact_score"),
                "selector": evidence.get("selector"),
                "component": finding.get("component") or evidence.get("element"),
            }
            if key in merged:
                existing = merged[key]
                existing["duplicate_count"] += 1
                if record.get("id") and record.get("id") not in existing["accessibility_record_ids"]:
                    existing["accessibility_record_ids"].append(record.get("id"))
                existing["accessibility_record_id"] = max(existing["accessibility_record_ids"]) if existing["accessibility_record_ids"] else existing.get("accessibility_record_id")
                if _severity_rank(severity) < _severity_rank(existing.get("severity")):
                    existing["severity"] = severity
            else:
                merged[key] = action

    actions = list(merged.values())
    actions.sort(key=lambda item: (_severity_rank(item.get("severity")), item.get("accessibility_record_id") or 0))
    return actions[:8]


def _mobile_priority_actions(mobile_summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for record in mobile_summaries:
        findings = record.get("findings") or []
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            severity = str(finding.get("severity") or "medium").lower()
            if severity not in {"critical", "high", "medium"}:
                continue
            category = str(finding.get("category") or "mobile")
            title = str(finding.get("title") or "Mobile UX bulgusu incelenmeli")
            key = (title, category)
            action = {
                "title": title,
                "severity": severity,
                "category": category,
                "source": "mobile",
                "mobile_record_id": record.get("id"),
                "mobile_record_ids": [record.get("id")] if record.get("id") else [],
                "duplicate_count": 1,
                "platform": record.get("platform"),
                "screen_type": record.get("screen_type"),
                "summary": finding.get("description") or record.get("overview") or "Mobile bulgusu incelenmeli.",
                "evidence": finding.get("evidence") or record.get("source_label") or category,
                "recommendation": finding.get("recommendation") or "Touch target, responsive davranis ve mobil akisi cihaz bazli dogrula.",
                "score": record.get("overall_score"),
                "task_completion_friction": record.get("task_completion_friction"),
                "cross_platform_parity_summary": record.get("cross_platform_parity_summary"),
            }
            if key in merged:
                existing = merged[key]
                existing["duplicate_count"] += 1
                if record.get("id") and record.get("id") not in existing["mobile_record_ids"]:
                    existing["mobile_record_ids"].append(record.get("id"))
                existing["mobile_record_id"] = max(existing["mobile_record_ids"]) if existing["mobile_record_ids"] else existing.get("mobile_record_id")
                if _severity_rank(severity) < _severity_rank(existing.get("severity")):
                    existing["severity"] = severity
            else:
                merged[key] = action

    actions = list(merged.values())
    actions.sort(key=lambda item: (_severity_rank(item.get("severity")), item.get("mobile_record_id") or 0))
    return actions[:8]


def _module_status(score: int | None, issues: int = 0, present: bool = True) -> str:
    if not present:
        return "not_connected"
    if issues > 0 or (score is not None and score < 70):
        return "attention"
    if score is not None and score >= 85:
        return "healthy"
    return "observed"


def _module_guidance(module: str, status: str, findings: int, records: int) -> dict[str, str]:
    if status == "not_connected":
        return {
            "interpretation": "Bu modülden henüz projeye bağlı kayıt yok.",
            "recommended_action": "Modülü aynı proje seçimiyle çalıştır; çıktı Full Report içinde otomatik birleşir.",
            "evidence_level": "none",
        }

    guidance = {
        "autonomous": {
            "interpretation": "URL ve test run çıktıları otonom test üretimiyle ilişkilendirildi.",
            "recommended_action": "Failed run varsa ilgili case protokolünü ve Bug Analysis kanıtını birlikte incele.",
        },
        "bug_analysis": {
            "interpretation": "Failed step logları yapılandırılmış bug raporuna dönüştürüldü.",
            "recommended_action": "Kategori, hedef selector ve önerilen aksiyonu ticket veya backlog maddesine çevir.",
        },
        "security": {
            "interpretation": "Security taramaları yüzey, header ve saldırı hipotezi sinyali üretiyor.",
            "recommended_action": "High/medium aksiyonları önceliklendir; correlation varsa aynı hedefteki test ve API bulgularıyla birlikte doğrula.",
        },
        "accessibility": {
            "interpretation": "Erişilebilirlik sinyalleri görsel/URL analizi üzerinden rapora bağlanır.",
            "recommended_action": "Label, focus, kontrast ve bileşen semantiği bulgularını UI/UX çıktılarıyla birlikte değerlendir.",
        },
        "uiux": {
            "interpretation": "UI/UX görsel kalite ve kullanılabilirlik sinyalleri rapora taşındı.",
            "recommended_action": "Yoğunluk, kontrast, hizalama ve okunabilirlik bulgularını accessibility ile eşleştir.",
        },
        "dataset": {
            "interpretation": "Dataset kalite bulguları model güvenilirliği ve annotation sağlığı için özetlendi.",
            "recommended_action": "Eksik etiket, duplicate, label consistency ve split dağılımı bulgularını veri hazırlama backlog'una ekle.",
        },
        "api": {
            "interpretation": "Endpoint contract, status, latency ve negatif kontrol sinyalleri rapora bağlandı.",
            "recommended_action": "Schema mismatch, status mismatch ve yavaş response bulgularını serializer, gateway ve servis katmanıyla doğrula.",
        },
        "database": {
            "interpretation": "DB query/schema kalite bulguları API contract ve veri tutarlılığı açısından özetlendi.",
            "recommended_action": "Query shape, constraint, null density ve API-DB consistency bulgularını migration/model değişiklikleriyle hizala.",
        },
        "performance": {
            "interpretation": "Web/API/DB performans sinyalleri proje seviyesinde raporlandı.",
            "recommended_action": "Yavaş endpoint veya sayfa varsa p95 hedefi, cache, query ve asset yükleme davranışını birlikte incele.",
        },
        "mobile": {
            "interpretation": "Mobil screenshot ve element metadata sinyalleri touch target, responsive risk ve platform uyumluluğu açısından rapora taşındı.",
            "recommended_action": "Küçük dokunma hedefleri, input erişilebilirliği, ekran taşması ve mobil yoğunluk bulgularını cihaz bazlı regresyonla doğrula.",
        },
    }
    default = guidance.get(module, {
        "interpretation": "Modül çıktısı proje raporuna bağlandı.",
        "recommended_action": "Bulguları ilgili modül ekranında detaylandır.",
    })
    if findings > 0:
        evidence_level = "actionable"
    elif records > 0:
        evidence_level = "observed"
    else:
        evidence_level = "none"
    return {**default, "evidence_level": evidence_level}


def _average_score(items: list[dict[str, Any]], default: int | None = None) -> int | None:
    scores = [int(item.get("overall_score") or 0) for item in items if item.get("overall_score") is not None]
    scores = [score for score in scores if score > 0]
    if not scores:
        return default
    return round(sum(scores) / len(scores))


def _analysis_project_id(record: Any) -> int | None:
    payload = getattr(record, "analysis_payload", None) or {}
    try:
        value = payload.get("project_id")
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _build_module_breakdown(
    *,
    runs: list[TestRun],
    security_summaries: list[dict[str, Any]],
    accessibility_summaries: list[dict[str, Any]],
    uiux_summaries: list[dict[str, Any]],
    dataset_summaries: list[dict[str, Any]],
    api_summaries: list[dict[str, Any]],
    db_summaries: list[dict[str, Any]],
    performance_summaries: list[dict[str, Any]],
    mobile_summaries: list[dict[str, Any]],
    bug_reports: list[dict[str, Any]],
    total_cases: int,
) -> list[dict[str, Any]]:
    failed_runs = sum(1 for run in runs if _enum_value(run.status) == "failed")
    completed_runs = sum(1 for run in runs if _enum_value(run.status) == "completed")
    high_security = sum(
        (record.get("risk_summary") or {}).get("critical", 0) + (record.get("risk_summary") or {}).get("high", 0)
        for record in security_summaries
    )
    medium_security = sum((record.get("risk_summary") or {}).get("medium", 0) for record in security_summaries)
    accessibility_findings = sum(item.get("findings_count", 0) for item in accessibility_summaries)
    uiux_findings = sum(item.get("findings_count", 0) for item in uiux_summaries)
    dataset_findings = sum(item.get("findings_count", 0) for item in dataset_summaries)
    api_findings = sum(item.get("findings_count", 0) for item in api_summaries)
    db_findings = sum(item.get("findings_count", 0) for item in db_summaries)
    performance_findings = sum(item.get("findings_count", 0) for item in performance_summaries)
    mobile_findings = sum(item.get("findings_count", 0) for item in mobile_summaries)
    module_counts: dict[str, int] = {}
    for run in runs:
        module_name = str(run.module_name or "unknown").lower()
        module_counts[module_name] = module_counts.get(module_name, 0) + 1

    items = [
        {
            "module": "autonomous",
            "label": "Autonomous Testing",
            "status": _module_status(None, failed_runs, bool(runs) or total_cases > 0),
            "score": None,
            "records": len(runs),
            "findings": failed_runs,
            "summary": f"{total_cases} case, {completed_runs} successful run ve {failed_runs} failed run sinyali var.",
            "latest": [],
        },
        {
            "module": "bug_analysis",
            "label": "Bug Analysis",
            "status": _module_status(None, len(bug_reports), bool(bug_reports)),
            "score": None,
            "records": len(bug_reports),
            "findings": len(bug_reports),
            "summary": f"{len(bug_reports)} structured bug report uretildi.",
            "latest": bug_reports[:3],
        },
        {
            "module": "security",
            "label": "Security",
            "status": _module_status(_average_score(security_summaries), high_security + medium_security, bool(security_summaries)),
            "score": _average_score(security_summaries),
            "records": len(security_summaries),
            "findings": high_security + medium_security,
            "summary": f"{high_security} high/critical ve {medium_security} medium security sinyali var.",
            "latest": security_summaries[:3],
        },
        {
            "module": "accessibility",
            "label": "Accessibility",
            "status": _module_status(_average_score(accessibility_summaries), accessibility_findings, bool(accessibility_summaries)),
            "score": _average_score(accessibility_summaries),
            "records": len(accessibility_summaries),
            "findings": accessibility_findings,
            "summary": f"{len(accessibility_summaries)} accessibility kaydi ve {accessibility_findings} bulgu var.",
            "latest": accessibility_summaries[:3],
        },
        {
            "module": "uiux",
            "label": "UI/UX",
            "status": _module_status(_average_score(uiux_summaries), uiux_findings, bool(uiux_summaries)),
            "score": _average_score(uiux_summaries),
            "records": len(uiux_summaries),
            "findings": uiux_findings,
            "summary": f"{len(uiux_summaries)} UI/UX kaydi ve {uiux_findings} bulgu var.",
            "latest": uiux_summaries[:3],
        },
        {
            "module": "dataset",
            "label": "Dataset",
            "status": _module_status(_average_score(dataset_summaries), dataset_findings, bool(dataset_summaries)),
            "score": _average_score(dataset_summaries),
            "records": len(dataset_summaries),
            "findings": dataset_findings,
            "summary": f"{len(dataset_summaries)} dataset analizi ve {dataset_findings} kalite bulgusu var.",
            "latest": dataset_summaries[:3],
        },
        {
            "module": "api",
            "label": "API",
            "status": _module_status(_average_score(api_summaries), api_findings, bool(api_summaries)),
            "score": _average_score(api_summaries),
            "records": len(api_summaries),
            "findings": api_findings,
            "summary": f"{len(api_summaries)} API analizi ve {api_findings} endpoint bulgusu var.",
            "latest": api_summaries[:3],
        },
        {
            "module": "database",
            "label": "Database",
            "status": _module_status(_average_score(db_summaries), db_findings, bool(db_summaries)),
            "score": _average_score(db_summaries),
            "records": len(db_summaries),
            "findings": db_findings,
            "summary": f"{len(db_summaries)} DB kalite analizi ve {db_findings} schema/query bulgusu var.",
            "latest": db_summaries[:3],
        },
        {
            "module": "performance",
            "label": "Performance",
            "status": _module_status(_average_score(performance_summaries), performance_findings, bool(performance_summaries)),
            "score": _average_score(performance_summaries),
            "records": len(performance_summaries),
            "findings": performance_findings,
            "summary": f"{len(performance_summaries)} performance analizi ve {performance_findings} performans bulgusu var.",
            "latest": performance_summaries[:3],
        },
        {
            "module": "mobile",
            "label": "Mobile",
            "status": _module_status(_average_score(mobile_summaries), mobile_findings, bool(mobile_summaries)),
            "score": _average_score(mobile_summaries),
            "records": len(mobile_summaries),
            "findings": mobile_findings,
            "summary": f"{len(mobile_summaries)} mobil analiz ve {mobile_findings} mobil bulgu var.",
            "latest": mobile_summaries[:3],
        },
    ]
    for item in items:
        item.update(
            _module_guidance(
                str(item.get("module") or ""),
                str(item.get("status") or ""),
                int(item.get("findings") or 0),
                int(item.get("records") or 0),
            )
        )
    return items


def _run_summary(run: TestRun) -> dict[str, Any]:
    logs = _logs_as_dict(run.logs)
    steps = logs.get("steps", [])
    failed_steps = [step for step in steps if step.get("status") == "failed"]
    bug_reports = _bug_reports_for_run(run, logs)
    return {
        "id": run.id,
        "module_name": run.module_name,
        "target": run.target,
        "status": _enum_value(run.status),
        "page_id": run.page_id,
        "page_name": run.page.name if run.page else None,
        "test_case_id": run.test_case_id,
        "test_case_title": run.test_case.title if run.test_case else None,
        "findings_count": len(run.findings),
        "failed_steps_count": len(failed_steps),
        "bug_reports_count": len(bug_reports),
        "created_at": _datetime_value(run.created_at),
        "completed_at": _datetime_value(run.completed_at),
    }


def _bug_reports_for_run(run: TestRun, logs: dict[str, Any]) -> list[dict[str, Any]]:
    existing = logs.get("bug_analysis") or []
    if isinstance(existing, list) and existing:
        return existing

    steps = logs.get("steps", [])
    if not isinstance(steps, list):
        return []

    return build_bug_analysis(
        {"steps": steps},
        run_target=run.target,
        case_title=run.test_case.title if run.test_case else "Exploratory run",
    )


def _test_priority_actions(runs: list[TestRun]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for run in runs:
        logs = _logs_as_dict(run.logs)
        steps = logs.get("steps", [])
        failed_steps = [step for step in steps if step.get("status") == "failed"]
        bug_reports = _bug_reports_for_run(run, logs)
        run_status = _enum_value(run.status)
        case_title = run.test_case.title if run.test_case else "Exploratory run"
        page_name = run.page.name if run.page else None

        if bug_reports:
            for bug in bug_reports[:2]:
                actions.append(
                    {
                        "title": f"{case_title}: {bug.get('title', 'Bug report')}",
                        "severity": bug.get("severity", "high"),
                        "source": "test-run",
                        "module": run.module_name,
                        "run_id": run.id,
                        "test_case_id": run.test_case_id,
                        "page_id": run.page_id,
                        "target": bug.get("target") or run.target,
                        "run_target": run.target,
                        "summary": f"{page_name or run.target} uzerinde {bug.get('category', 'bug')} sinyali olustu.",
                        "recommendation": bug.get("recommendation", "Failed step evidence incelenmeli."),
                        "bug_report": bug,
                    }
                )
        elif failed_steps:
            for step in failed_steps[:2]:
                label = step.get("action_label") or step.get("action") or "step"
                target = step.get("target") or step.get("selector_used") or run.target
                reason = step.get("reason") or step.get("error") or "Failed step needs review."
                actions.append(
                    {
                        "title": f"{case_title}: {label} failed",
                        "severity": "high",
                        "source": "test-run",
                        "module": run.module_name,
                        "run_id": run.id,
                        "test_case_id": run.test_case_id,
                        "page_id": run.page_id,
                        "target": target,
                        "run_target": run.target,
                        "summary": f"{page_name or run.target} uzerindeki failed step incelenmeli.",
                        "recommendation": f"Selector/hedef davranisini kontrol et: {target}. Sebep: {reason}",
                    }
                )
        elif run_status == "failed":
            actions.append(
                {
                    "title": f"{case_title}: run failed",
                    "severity": "high",
                    "source": "test-run",
                    "module": run.module_name,
                    "run_id": run.id,
                    "test_case_id": run.test_case_id,
                    "page_id": run.page_id,
                    "target": run.target,
                    "run_target": run.target,
                    "summary": "Run failed oldu ancak failed step detayi bulunamadi.",
                    "recommendation": "Run loglarini ve screenshot kanitlarini kontrol et; protokol adimlarini yeniden dogrula.",
                }
            )

    actions.sort(key=lambda item: (_severity_rank(item.get("severity")), item.get("run_id") or 0))
    return actions[:5]


def _correlate_project_findings(
    security_summaries: list[dict[str, Any]],
    test_actions: list[dict[str, Any]],
    page_url_by_id: dict[int, str],
    api_summaries: list[dict[str, Any]] | None = None,
    db_summaries: list[dict[str, Any]] | None = None,
    performance_summaries: list[dict[str, Any]] | None = None,
    accessibility_summaries: list[dict[str, Any]] | None = None,
    uiux_summaries: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    correlations: list[dict[str, Any]] = []
    api_summaries = api_summaries or []
    db_summaries = db_summaries or []
    performance_summaries = performance_summaries or []
    accessibility_summaries = accessibility_summaries or []
    uiux_summaries = uiux_summaries or []

    def _bug_categories(actions: list[dict[str, Any]]) -> list[str]:
        categories: list[str] = []
        for action in actions:
            bug = action.get("bug_report") or {}
            category = str(bug.get("category") or "").strip()
            if category and category not in categories:
                categories.append(category)
        return categories

    def _correlation_title(categories: list[str]) -> str:
        if "timing_issue" in categories:
            return "Ayni hedefte timing kaynakli test kirilmasi ve security riski var"
        if "selector_issue" in categories:
            return "Ayni hedefte selector kirilmasi ve security riski var"
        if "browser_context_closed" in categories:
            return "Ayni hedefte tarayici akisi kirilmasi ve security riski var"
        if "assertion_mismatch" in categories:
            return "Ayni hedefte beklenen durum uyusmazligi ve security riski var"
        if "test_case_generation_issue" in categories:
            return "Ayni hedefte test protokol riski ve security riski var"
        return "Ayni hedefte security riski ve failed test var"

    def _correlation_recommendation(categories: list[str], source_url: str) -> str:
        if "timing_issue" in categories:
            return f"{source_url} icin failed step timing kaynakli gorunuyor. Security hardening ile birlikte performans/load state ve async render davranisini kontrol et."
        if "selector_issue" in categories:
            return f"{source_url} icin selector kirilmasi var. Security bulgularini incelerken DOM semantigi, data-test/role kullanimi ve element stabilitesini birlikte duzelt."
        if "browser_context_closed" in categories:
            return f"{source_url} icin tarayici akisi kapanmis. Redirect, popup, frame, auth guard ve security header davranislarini birlikte kontrol et."
        if "assertion_mismatch" in categories:
            return f"{source_url} icin beklenen durum gorunmedi. Security bulgulariyla birlikte UI state, hata mesaji ve yetki/guard davranisini dogrula."
        if "test_case_generation_issue" in categories:
            return f"{source_url} icin test protokolu eksik hedef uretmis. Once visual/DOM envanteriyle case'i yenile, sonra security aksiyonlarini dogrula."
        return "Bu URL icin once security hardening bulgularini ve failed test step'lerini birlikte incele; selector/akis hatasi gercek bir yetki, header veya form davranisi problemiyle iliskili olabilir."

    for security in security_summaries:
        source_url = security.get("source_url") or (security.get("scan_evidence") or {}).get("final_url")
        if not source_url:
            continue

        risk_summary = security.get("risk_summary") or {}
        high_count = int(risk_summary.get("critical", 0) or 0) + int(risk_summary.get("high", 0) or 0)
        medium_count = int(risk_summary.get("medium", 0) or 0)
        if high_count + medium_count <= 0:
            continue

        related_tests = [
            action for action in test_actions
            if (
                action.get("target") == source_url
                or action.get("run_target") == source_url
                or page_url_by_id.get(action.get("page_id")) == source_url
            )
        ]
        if not related_tests:
            continue

        categories = _bug_categories(related_tests)
        severity = "high" if high_count else "medium"
        test_titles = [action.get("title", "Failed test step") for action in related_tests[:2]]
        security_titles = [
            action.get("title", "Security risk")
            for action in (security.get("priority_actions") or [])[:2]
        ]
        correlations.append(
            {
                "title": _correlation_title(categories),
                "severity": severity,
                "target": source_url,
                "related_modules": ["security", "test-execution", "bug-analysis"],
                "signal_count": high_count + medium_count + len(related_tests) + len(categories),
                "security_record_id": security.get("id"),
                "run_ids": [action.get("run_id") for action in related_tests if action.get("run_id")],
                "evidence": {
                    "security": security_titles,
                    "tests": test_titles,
                    "bug_categories": categories,
                },
                "recommendation": _correlation_recommendation(categories, source_url),
            }
        )

    security_by_url = {
        (security.get("source_url") or (security.get("scan_evidence") or {}).get("final_url")): security
        for security in security_summaries
        if security.get("source_url") or (security.get("scan_evidence") or {}).get("final_url")
    }
    performance_by_url = {
        performance.get("source_url"): performance
        for performance in performance_summaries
        if performance.get("source_url")
    }

    for api_record in api_summaries:
        source_url = api_record.get("source_url")
        if not source_url:
            continue

        evidence = api_record.get("evidence_summary") or {}
        categories = api_record.get("finding_categories") or evidence.get("primary_categories") or []
        api_has_security = int(evidence.get("security_signals", 0) or 0) > 0
        api_has_contract = int(evidence.get("contract_signals", 0) or 0) > 0
        api_has_performance = int(evidence.get("performance_signals", 0) or 0) > 0
        api_has_availability = int(evidence.get("availability_signals", 0) or 0) > 0
        related_security = security_by_url.get(source_url)
        related_performance = performance_by_url.get(source_url)

        related_tests = [
            action for action in test_actions
            if (
                action.get("target") == source_url
                or action.get("run_target") == source_url
                or page_url_by_id.get(action.get("page_id")) == source_url
            )
        ]

        if api_has_security and related_security:
            correlations.append(
                {
                    "title": "Ayni endpointte API security sinyali ve security bulgusu var",
                    "severity": "high" if any(category in categories for category in ("auth-signal", "error-leakage")) else "medium",
                    "target": source_url,
                    "related_modules": ["api", "security"],
                    "signal_count": int(evidence.get("security_signals", 0) or 0) + int((related_security.get("risk_summary") or {}).get("total", 0) or 0),
                    "security_record_id": related_security.get("id"),
                    "run_ids": [],
                    "evidence": {
                        "security": [action.get("title", "Security risk") for action in (related_security.get("priority_actions") or [])[:2]],
                        "tests": [],
                        "bug_categories": categories,
                    },
                    "recommendation": "API auth, error response ve security header bulgularini birlikte incele; endpoint sozlesmesi ile security hardening aksiyonlarini ayni degisiklikte dogrula.",
                }
            )

        if (api_has_contract or api_has_availability) and related_tests:
            correlations.append(
                {
                    "title": "API contract/availability sinyali failed test ile eslesti",
                    "severity": "high" if api_has_availability else "medium",
                    "target": source_url,
                    "related_modules": ["api", "test-execution", "bug-analysis"],
                    "signal_count": len(categories) + len(related_tests),
                    "security_record_id": None,
                    "run_ids": [action.get("run_id") for action in related_tests if action.get("run_id")],
                    "evidence": {
                        "security": [],
                        "tests": [action.get("title", "Failed test step") for action in related_tests[:2]],
                        "bug_categories": categories,
                    },
                    "recommendation": "Failed test hedefi ile API response contract'ini birlikte kontrol et; status, schema ve hata cevabi degisiklikleri test protokolunu kirmis olabilir.",
                }
            )

        if api_has_performance and related_performance:
            correlations.append(
                {
                    "title": "API latency sinyali performance modulu ile eslesti",
                    "severity": "medium",
                    "target": source_url,
                    "related_modules": ["api", "performance"],
                    "signal_count": int(evidence.get("performance_signals", 0) or 0) + int(related_performance.get("findings_count", 0) or 0),
                    "security_record_id": None,
                    "run_ids": [],
                    "evidence": {
                        "security": [],
                        "tests": [api_record.get("overview", "API latency finding")],
                        "bug_categories": categories,
                    },
                    "recommendation": "Endpoint latency ve sayfa performans bulgularini birlikte profille; p95/p99, cache, DB sorgusu ve downstream bagimliliklari ayni raporda takip et.",
                }
            )

        if api_has_contract and db_summaries:
            db_contract_records = [
                db_record for db_record in db_summaries
                if (
                    db_record.get("findings_count", 0) > 0
                    and any(
                        category in {
                            "schema-mismatch",
                            "api-db-consistency",
                            "query-shape",
                            "query-scope",
                            "constraint",
                            "null-density",
                        }
                        for category in (db_record.get("finding_categories") or [])
                    )
                )
            ]
            if db_contract_records:
                related_db = db_contract_records[0]
                db_categories = related_db.get("finding_categories") or []
                correlations.append(
                    {
                        "title": "API contract drift ile DB schema sinyali eslesti",
                        "severity": "high" if any(category in db_categories for category in ("schema-mismatch", "api-db-consistency", "constraint")) else "medium",
                        "target": source_url,
                        "related_modules": ["api", "database"],
                        "signal_count": int(evidence.get("contract_signals", 0) or 0) + int(related_db.get("findings_count", 0) or 0),
                        "security_record_id": None,
                        "run_ids": [],
                        "evidence": {
                            "security": [],
                            "tests": [
                                f"API: {', '.join(categories[:3]) or 'contract signal'}",
                                f"DB: {', '.join(db_categories[:3]) or related_db.get('overview', 'database signal')}",
                            ],
                            "bug_categories": list(dict.fromkeys([*categories, *db_categories]))[:6],
                        },
                        "recommendation": "API response contract, serializer/DTO modeli ve DB kolon/constraint yapisini birlikte hizala; missing field bulgulari icin mapping veya migration gerekip gerekmedigini kontrol et.",
                    }
                )

    accessibility_signal_count = sum(int(item.get("findings_count", 0) or 0) for item in accessibility_summaries)
    uiux_signal_count = sum(int(item.get("findings_count", 0) or 0) for item in uiux_summaries)
    if accessibility_signal_count > 0 and uiux_signal_count > 0:
        uiux_categories = list(
            dict.fromkeys(
                category
                for record in uiux_summaries
                for category in (record.get("finding_categories") or [])
                if category
            )
        )
        accessibility_urls = [
            record.get("source_url")
            for record in accessibility_summaries
            if record.get("source_url")
        ]
        target = accessibility_urls[0] if accessibility_urls else "project-level-ui-accessibility"
        has_readability = any(category in {"readability-flow", "visual-clutter", "hierarchy"} for category in uiux_categories)
        correlations.append(
            {
                "title": "UI okunabilirlik sinyali accessibility bulgulari ile eslesti",
                "severity": "high" if has_readability and accessibility_signal_count >= 3 else "medium",
                "target": target,
                "related_modules": ["uiux", "accessibility"],
                "signal_count": accessibility_signal_count + uiux_signal_count,
                "security_record_id": None,
                "run_ids": [],
                "evidence": {
                    "security": [],
                    "tests": [
                        f"Accessibility: {accessibility_signal_count} bulgu",
                        f"UI/UX: {uiux_signal_count} bulgu",
                    ],
                    "bug_categories": uiux_categories[:6],
                },
                "recommendation": "Okunabilirlik, kontrast, label/focus ve görsel hiyerarşi bulgularını aynı ekran tasarım düzeltmesinde birlikte doğrula.",
            }
        )

    merged_correlations: dict[tuple[str, str, tuple[str, ...]], dict[str, Any]] = {}
    for item in correlations:
        key = (
            str(item.get("title") or ""),
            str(item.get("target") or ""),
            tuple(item.get("related_modules") or []),
        )
        existing = merged_correlations.get(key)
        if not existing:
            item["duplicate_count"] = 1
            merged_correlations[key] = item
            continue

        existing["duplicate_count"] = int(existing.get("duplicate_count", 1) or 1) + 1
        existing["signal_count"] = int(existing.get("signal_count", 0) or 0) + int(item.get("signal_count", 0) or 0)
        existing["severity"] = min(
            [existing.get("severity"), item.get("severity")],
            key=lambda value: _severity_rank(str(value)),
        )
        existing["run_ids"] = list(dict.fromkeys([*(existing.get("run_ids") or []), *(item.get("run_ids") or [])]))
        existing_evidence = existing.get("evidence") or {}
        item_evidence = item.get("evidence") or {}
        for evidence_key in ("security", "tests", "bug_categories"):
            existing_evidence[evidence_key] = list(
                dict.fromkeys([
                    *(existing_evidence.get(evidence_key) or []),
                    *(item_evidence.get(evidence_key) or []),
                ])
            )
        existing["evidence"] = existing_evidence

    correlations = list(merged_correlations.values())
    correlations.sort(key=lambda item: (_severity_rank(item.get("severity")), -(item.get("signal_count") or 0)))
    return correlations[:6]


def _risk_level(overall_score: int, failed_runs: int, high_security: int, correlations: int) -> str:
    if high_security > 0 or failed_runs >= 3 or overall_score < 55:
        return "high"
    if failed_runs > 0 or correlations > 0 or overall_score < 80:
        return "medium"
    return "low"


def _build_executive_summary(
    *,
    project: Project,
    overall_score: int,
    total_runs: int,
    failed_runs: int,
    high_security: int,
    medium_security: int,
    correlations: list[dict[str, Any]],
    module_breakdown: list[dict[str, Any]],
    api_actions: list[dict[str, Any]],
    bug_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    risk_level = _risk_level(overall_score, failed_runs, high_security, len(correlations))
    connected_modules = [item for item in module_breakdown if item.get("status") != "not_connected"]
    attention_modules = [
        item.get("label")
        for item in module_breakdown
        if item.get("status") == "attention"
    ]
    healthy_modules = [
        item.get("label")
        for item in module_breakdown
        if item.get("status") == "healthy"
    ]

    top_risks: list[str] = []
    if failed_runs:
        top_risks.append(f"{failed_runs} failed run yapılandırılmış bug/test aksiyonu üretti.")
    if high_security + medium_security:
        top_risks.append(f"{high_security} high/critical ve {medium_security} medium security sinyali var.")
    if api_actions:
        top_risks.append(f"{len(api_actions)} API endpoint aksiyonu contract, latency veya availability açısından izlenmeli.")
    if correlations:
        top_risks.append(f"{len(correlations)} cross-module correlation aynı hedefte birden fazla modül sinyali gösteriyor.")
    if not top_risks:
        top_risks.append("Bu raporda öncelikli kırılım sinyali oluşmadı.")

    next_actions: list[str] = []
    if correlations:
        next_actions.append("Önce correlation kartlarındaki aynı hedefli modül sinyallerini doğrula.")
    if bug_reports:
        next_actions.append("Failed step için Bug Analysis önerisini case/protokol düzeltmesine çevir.")
    if high_security + medium_security:
        next_actions.append("Security priority actions listesindeki header, auth ve surface hardening maddelerini uygula.")
    if api_actions:
        next_actions.append("API endpoint aksiyonlarında schema/status/latency bulgularını servis contract testlerine bağla.")
    if not next_actions:
        next_actions.append("Yeni modül çalıştırmalarıyla rapor kanıt kapsamını genişlet.")

    return {
        "title": f"{project.name} project quality executive summary",
        "risk_level": risk_level,
        "readiness_score": overall_score,
        "narrative": (
            f"{project.name} için {len(connected_modules)} modülden kanıt toplandı. "
            f"{total_runs} run içinde {failed_runs} failed run, "
            f"{high_security + medium_security} security sinyali ve {len(correlations)} correlation bulundu."
        ),
        "attention_modules": attention_modules,
        "healthy_modules": healthy_modules,
        "top_risks": top_risks[:4],
        "next_actions": next_actions[:4],
    }


def _build_evidence_matrix(
    *,
    module_breakdown: list[dict[str, Any]],
    runs: list[TestRun],
    security_summaries: list[dict[str, Any]],
    accessibility_summaries: list[dict[str, Any]],
    uiux_summaries: list[dict[str, Any]],
    dataset_summaries: list[dict[str, Any]],
    api_summaries: list[dict[str, Any]],
    db_summaries: list[dict[str, Any]],
    performance_summaries: list[dict[str, Any]],
    mobile_summaries: list[dict[str, Any]],
    correlations: list[dict[str, Any]],
    jira_drafts: list[JiraTicketDraft],
) -> dict[str, Any]:
    connected = [item for item in module_breakdown if item.get("status") != "not_connected"]
    actionable = [item for item in module_breakdown if item.get("evidence_level") == "actionable"]
    return {
        "coverage": {
            "connected_modules": len(connected),
            "total_modules": len(module_breakdown),
            "actionable_modules": len(actionable),
            "evidence_coverage_percent": round((len(connected) / len(module_breakdown)) * 100) if module_breakdown else 0,
        },
        "artifacts": {
            "test_runs": len(runs),
            "security_records": len(security_summaries),
            "accessibility_records": len(accessibility_summaries),
            "uiux_records": len(uiux_summaries),
            "dataset_records": len(dataset_summaries),
            "api_records": len(api_summaries),
            "database_records": len(db_summaries),
            "performance_records": len(performance_summaries),
            "mobile_records": len(mobile_summaries),
            "correlation_items": len(correlations),
            "jira_drafts": len(jira_drafts),
        },
        "paper_evidence": [
            "module_breakdown",
            "priority_security_actions",
            "api_endpoint_actions",
            "database_quality_actions",
            "performance_actions",
            "accessibility_actions",
            "uiux_actions",
            "mobile_actions",
            "jira_drafts",
            "failed_test_actions",
            "cross_module_correlation",
            "run_history",
        ],
        "limitations": [
            "Benchmark metrikleri ayrı deney dosyalarıyla tamamlanmalıdır.",
            "Gerçek üretim sitelerinde credential, captcha ve rate-limit kısıtları test kapsamını etkileyebilir.",
        ],
    }


def _build_paper_alignment(
    *,
    module_breakdown: list[dict[str, Any]],
    evidence_matrix: dict[str, Any],
    correlations: list[dict[str, Any]],
    bug_reports: list[dict[str, Any]],
    accessibility_actions: list[dict[str, Any]],
    api_actions: list[dict[str, Any]],
    db_actions: list[dict[str, Any]],
    performance_actions: list[dict[str, Any]],
    uiux_actions: list[dict[str, Any]],
    mobile_actions: list[dict[str, Any]],
    jira_drafts: list[JiraTicketDraft],
) -> dict[str, Any]:
    modules = {item.get("module"): item for item in module_breakdown}

    def _module_status(module_key: str) -> str:
        item = modules.get(module_key) or {}
        if item.get("status") == "not_connected":
            return "pending"
        if item.get("evidence_level") == "actionable":
            return "supported"
        return "observed"

    claims = [
        {
            "claim": "Unified multi-module QA framework",
            "status": "supported" if evidence_matrix.get("coverage", {}).get("connected_modules", 0) >= 4 else "observed",
            "evidence": "Final Report module breakdown, action cards and shared project summary combine module outputs.",
        },
        {
            "claim": "Autonomous test generation and failed-step evidence",
            "status": _module_status("autonomous"),
            "evidence": "Test runs, failed test actions and structured Bug Analysis records are linked in one report.",
        },
        {
            "claim": "Visual security intelligence",
            "status": _module_status("security"),
            "evidence": "Security records expose risk summary, priority actions, surface/header findings and scan evidence.",
        },
        {
            "claim": "Dataset quality validation",
            "status": _module_status("dataset"),
            "evidence": "Dataset records report quality findings and model-impact oriented remediation signals.",
        },
        {
            "claim": "Image-processing based UI/UX analysis",
            "status": _module_status("uiux"),
            "evidence": "UI/UX actions include screenshot metrics, numeric evidence and regression suggestions.",
        },
        {
            "claim": "Accessibility evidence and WCAG-oriented remediation",
            "status": _module_status("accessibility"),
            "evidence": "Accessibility actions expose contrast, label, focus, keyboard and component-level remediation evidence.",
        },
        {
            "claim": "Mobile UX and responsive risk analysis",
            "status": _module_status("mobile"),
            "evidence": "Mobile records expose touch target, safe-area, keyboard overlap, density and platform-parity actions.",
        },
        {
            "claim": "Cross-module correlation",
            "status": "supported" if correlations else "observed",
            "evidence": "Correlation cards merge signals from test, security, API, DB, performance, accessibility, UI/UX and mobile modules.",
        },
        {
            "claim": "API, DB and performance evidence integration",
            "status": "supported" if (api_actions or db_actions or performance_actions) else "pending",
            "evidence": "Endpoint, database and performance action cards are surfaced in Full Report and project export.",
        },
    ]

    return {
        "status": "implementation_evidence_ready",
        "benchmark_status": "deferred_final_phase",
        "claims": claims,
        "evidence_counts": {
            "correlations": len(correlations),
            "bug_reports": len(bug_reports),
            "accessibility_actions": len(accessibility_actions),
            "api_actions": len(api_actions),
            "db_actions": len(db_actions),
            "performance_actions": len(performance_actions),
            "uiux_actions": len(uiux_actions),
            "mobile_actions": len(mobile_actions),
            "jira_drafts": len(jira_drafts),
        },
        "next_research_steps": [
            "Benchmark/metrics deney dosyalarını son fazda üret.",
            "Makale tablolarını Final Report export çıktılarıyla eşleştir.",
            "Kalan modül kanıtlarını aynı project_id altında yeniden çalıştırarak rapor kapsamını kapat.",
        ],
    }


def _ticket_draft_schema(draft: JiraTicketDraft) -> dict[str, Any]:
    return {
        "id": draft.id,
        "project_id": draft.project_id,
        "provider": draft.provider,
        "ticket_key": draft.ticket_key,
        "source_module": draft.source_module,
        "source_type": draft.source_type,
        "source_ref": draft.source_ref,
        "title": draft.title,
        "description": draft.description,
        "priority": draft.priority,
        "status": draft.status,
        "payload": draft.payload or {},
        "created_at": _datetime_value(draft.created_at),
        "updated_at": _datetime_value(draft.updated_at),
    }


@router.get("/project/{project_id}/summary")
def export_project_summary(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    jira_drafts = (
        db.query(JiraTicketDraft)
        .filter(JiraTicketDraft.project_id == project_id)
        .order_by(JiraTicketDraft.created_at.desc(), JiraTicketDraft.id.desc())
        .limit(20)
        .all()
    )
    runs = (
        db.query(TestRun)
        .filter(TestRun.project_id == project_id)
        .order_by(TestRun.created_at.desc(), TestRun.id.desc())
        .limit(20)
        .all()
    )
    project_urls = {page.url for page in project.pages}
    page_url_by_id = {page.id: page.url for page in project.pages}
    security_query = db.query(SecurityAnalysisRecord).order_by(SecurityAnalysisRecord.created_at.desc(), SecurityAnalysisRecord.id.desc())
    if project_urls:
        security_query = security_query.filter(SecurityAnalysisRecord.source_url.in_(project_urls))
    security_records = security_query.limit(8).all()

    accessibility_query = db.query(AccessibilityAnalysisRecord).order_by(AccessibilityAnalysisRecord.created_at.desc(), AccessibilityAnalysisRecord.id.desc())
    if project_urls:
        accessibility_query = accessibility_query.filter(AccessibilityAnalysisRecord.source_url.in_(project_urls))
    accessibility_records = accessibility_query.limit(8).all()

    uiux_candidates = (
        db.query(UiuxAnalysisRecord)
        .order_by(UiuxAnalysisRecord.created_at.desc(), UiuxAnalysisRecord.id.desc())
        .limit(80)
        .all()
    )
    uiux_records = [
        record
        for record in uiux_candidates
        if _analysis_project_id(record) == project.id
    ][:8]
    dataset_records = (
        db.query(DatasetAnalysisRecord)
        .order_by(DatasetAnalysisRecord.created_at.desc(), DatasetAnalysisRecord.id.desc())
        .limit(5)
        .all()
    )
    api_candidates = (
        db.query(ApiAnalysisRecord)
        .order_by(ApiAnalysisRecord.created_at.desc(), ApiAnalysisRecord.id.desc())
        .limit(80)
        .all()
    )
    api_records = [
        record
        for record in api_candidates
        if _analysis_project_id(record) == project.id or (project_urls and record.source_url in project_urls)
    ][:8]

    db_records = (
        db.query(DbAnalysisRecord)
        .order_by(DbAnalysisRecord.created_at.desc(), DbAnalysisRecord.id.desc())
        .limit(8)
        .all()
    )

    performance_candidates = (
        db.query(PerformanceAnalysisRecord)
        .order_by(PerformanceAnalysisRecord.created_at.desc(), PerformanceAnalysisRecord.id.desc())
        .limit(80)
        .all()
    )
    performance_records = [
        record
        for record in performance_candidates
        if _analysis_project_id(record) == project.id or (project_urls and record.source_url in project_urls)
    ][:8]
    mobile_candidates = (
        db.query(MobileAnalysisRecord)
        .order_by(MobileAnalysisRecord.created_at.desc(), MobileAnalysisRecord.id.desc())
        .limit(80)
        .all()
    )
    mobile_records = [
        record
        for record in mobile_candidates
        if _analysis_project_id(record) == project.id
    ][:8]

    security_summaries = [_security_record_summary(record) for record in security_records]
    accessibility_summaries = [_accessibility_analysis_summary(record) for record in accessibility_records]
    uiux_summaries = [_uiux_analysis_summary(record) for record in uiux_records]
    dataset_summaries = [_generic_analysis_summary(record, "dataset") for record in dataset_records]
    api_summaries = [_api_analysis_summary(record) for record in api_records]
    db_summaries = [_db_analysis_summary(record) for record in db_records]
    performance_summaries = [_performance_analysis_summary(record) for record in performance_records]
    mobile_summaries = [_mobile_analysis_summary(record) for record in mobile_records]
    total_runs = len(runs)
    failed_runs = sum(1 for run in runs if _enum_value(run.status) == "failed")
    passed_runs = sum(1 for run in runs if _enum_value(run.status) == "completed")
    test_actions = _test_priority_actions(runs)
    bug_reports = [
        bug
        for run in runs
        for bug in _bug_reports_for_run(run, _logs_as_dict(run.logs))
    ]
    security_actions = [
        action
        for record in security_summaries
        for action in record.get("priority_actions", [])
    ]
    security_actions.sort(key=lambda item: _severity_rank(item.get("severity")))
    accessibility_actions = _accessibility_priority_actions(accessibility_summaries)
    api_actions = _api_priority_actions(api_summaries)
    db_actions = _db_priority_actions(db_summaries)
    performance_actions = _performance_priority_actions(performance_summaries)
    uiux_actions = _uiux_priority_actions(uiux_summaries)
    mobile_actions = _mobile_priority_actions(mobile_summaries)
    correlations = _correlate_project_findings(
        security_summaries,
        test_actions,
        page_url_by_id,
        api_summaries=api_summaries,
        db_summaries=db_summaries,
        performance_summaries=performance_summaries,
        accessibility_summaries=accessibility_summaries,
        uiux_summaries=uiux_summaries,
    )
    high_security = sum(
        (record.get("risk_summary") or {}).get("critical", 0) + (record.get("risk_summary") or {}).get("high", 0)
        for record in security_summaries
    )
    medium_security = sum((record.get("risk_summary") or {}).get("medium", 0) for record in security_summaries)
    run_penalty = failed_runs * 12
    security_penalty = high_security * 10 + medium_security * 5
    overall_score = max(0, min(100, 100 - run_penalty - security_penalty))
    total_cases = len(project.test_cases)
    module_breakdown = _build_module_breakdown(
        runs=runs,
        security_summaries=security_summaries,
        accessibility_summaries=accessibility_summaries,
        uiux_summaries=uiux_summaries,
        dataset_summaries=dataset_summaries,
        api_summaries=api_summaries,
        db_summaries=db_summaries,
        performance_summaries=performance_summaries,
        mobile_summaries=mobile_summaries,
        bug_reports=bug_reports,
        total_cases=total_cases,
    )
    executive_summary = _build_executive_summary(
        project=project,
        overall_score=overall_score,
        total_runs=total_runs,
        failed_runs=failed_runs,
        high_security=high_security,
        medium_security=medium_security,
        correlations=correlations,
        module_breakdown=module_breakdown,
        api_actions=api_actions,
        bug_reports=bug_reports,
    )
    evidence_matrix = _build_evidence_matrix(
        module_breakdown=module_breakdown,
        runs=runs,
        security_summaries=security_summaries,
        accessibility_summaries=accessibility_summaries,
        uiux_summaries=uiux_summaries,
        dataset_summaries=dataset_summaries,
        api_summaries=api_summaries,
        db_summaries=db_summaries,
        performance_summaries=performance_summaries,
        mobile_summaries=mobile_summaries,
        correlations=correlations,
        jira_drafts=jira_drafts,
    )
    paper_alignment = _build_paper_alignment(
        module_breakdown=module_breakdown,
        evidence_matrix=evidence_matrix,
        correlations=correlations,
        bug_reports=bug_reports,
        accessibility_actions=accessibility_actions,
        api_actions=api_actions,
        db_actions=db_actions,
        performance_actions=performance_actions,
        uiux_actions=uiux_actions,
        mobile_actions=mobile_actions,
        jira_drafts=jira_drafts,
    )

    return {
        "project": {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "platforms": project.platforms,
            "pages_count": len(project.pages),
        },
        "generated_at": datetime.utcnow().isoformat(),
        "overall_score": overall_score,
        "executive_summary": executive_summary,
        "summary": {
            "total_runs": total_runs,
            "passed_runs": passed_runs,
            "failed_runs": failed_runs,
            "security_records": len(security_summaries),
            "high_security_risks": high_security,
            "medium_security_risks": medium_security,
            "test_actions": len(test_actions),
            "correlations": len(correlations),
            "bug_reports": len(bug_reports),
            "api_actions": len(api_actions),
            "db_actions": len(db_actions),
            "performance_actions": len(performance_actions),
            "uiux_actions": len(uiux_actions),
            "accessibility_actions": len(accessibility_actions),
            "mobile_actions": len(mobile_actions),
            "jira_drafts": len(jira_drafts),
        },
        "security": {
            "records": security_summaries,
            "priority_actions": security_actions[:5],
        },
        "tests": {
            "priority_actions": test_actions,
            "bug_reports": bug_reports[:10],
        },
        "accessibility": {
            "records": accessibility_summaries,
            "priority_actions": accessibility_actions,
        },
        "api": {
            "records": api_summaries,
            "priority_actions": api_actions,
        },
        "database": {
            "records": db_summaries,
            "priority_actions": db_actions,
        },
        "performance": {
            "records": performance_summaries,
            "priority_actions": performance_actions,
        },
        "uiux": {
            "records": uiux_summaries,
            "priority_actions": uiux_actions,
        },
        "mobile": {
            "records": mobile_summaries,
            "priority_actions": mobile_actions,
        },
        "correlation": {
            "items": correlations,
        },
        "module_breakdown": {
            "items": module_breakdown,
        },
        "evidence_matrix": evidence_matrix,
        "paper_alignment": paper_alignment,
        "jira_drafts": {
            "summary": {
                "total": len(jira_drafts),
                "completed_checklist_items": sum(
                    1
                    for draft in jira_drafts
                    for item in ((draft.payload or {}).get("acceptance_criteria") or [])
                    if item.get("done")
                ),
                "total_checklist_items": sum(
                    len((draft.payload or {}).get("acceptance_criteria") or [])
                    for draft in jira_drafts
                ),
                "modules": sorted({draft.source_module for draft in jira_drafts}),
            },
            "items": [_ticket_draft_schema(draft) for draft in jira_drafts],
        },
        "runs": [_run_summary(run) for run in runs],
    }


def _jira_acceptance_criteria_for_action(source_module: str, payload: dict[str, Any], recommendation: str | None) -> list[dict[str, Any]]:
    module = str(source_module or "general").lower()
    category = str(payload.get("category") or payload.get("module") or "").lower()
    criteria_by_module: dict[str, list[str]] = {
        "api": [
            "Endpoint ayni request ile tekrar calistirildiginda beklenen status ve response contract saglanmali.",
            "Schema/content-type/required field kontrolleri icin negatif ve pozitif API testleri guncellenmeli.",
            "Final Report API aksiyon karti ayni endpoint icin tekrar uretildiginde yeni bulgu vermemeli.",
        ],
        "database": [
            "Ilgili SQL/query veya schema kontrolu tekrar calistirildiginda ayni DB kalite bulgusu gorulmemeli.",
            "Gerekiyorsa migration/model/constraint degisikligi uygulanip veri tutarliligi dogrulanmali.",
            "API-DB etkisi varsa ilgili endpoint veya serializer testiyle regresyon kontrolu yapilmali.",
        ],
        "performance": [
            "Ayni hedef icin performans analizi tekrarlandiginda sure/p95/LCP sinyali kabul edilebilir esige dusmeli.",
            "Yavas kaynak, query, cache veya asset iyilestirmesi kanit metrikleriyle dogrulanmali.",
            "Full Report performans aksiyon karti resolved/observed seviyesine inmeli.",
        ],
        "uiux": [
            "Ayni screenshot veya ekran akisi tekrar analiz edildiginde ilgili UI/UX metriği kabul edilebilir seviyeye gelmeli.",
            "Gorsel hiyerarsi, spacing, okunabilirlik veya renk tutarliligi screenshot regresyonuyla dogrulanmali.",
            "Ilgili ekran icin yeni UI/UX aksiyon karti ayni bulguyu tekrar uretmemeli.",
        ],
        "accessibility": [
            "Ilgili bilesen WCAG/focus/label/contrast kontrolunden gecmeli.",
            "Keyboard navigation ve screen reader icin manuel veya otomatik accessibility kontrolu tekrar edilmeli.",
            "Accessibility aksiyon karti ayni selector/bilesen icin tekrar uretildiginde bulgu vermemeli.",
        ],
        "mobile": [
            "Ayni mobil ekran Android/iOS veya hedef cihaz viewport'unda tekrar analiz edildiginde bulgu azalmalı.",
            "Touch target, input erisilebilirligi, tasma veya yogunluk problemi cihaz bazli kontrolle dogrulanmali.",
            "Mobile action karti ayni ekran icin tekrar uretildiginde ilgili kategori resolved/observed seviyesine dusmeli.",
        ],
        "security": [
            "Ilgili security kontrolu tekrarlandiginda ayni header/surface/hypothesis bulgusu gorulmemeli.",
            "Gerekli hardening veya guard davranisi test ortamina uygulanip kanitlanmali.",
            "Security aksiyon karti ayni hedef icin high/medium sinyal uretmemeli.",
        ],
        "correlation": [
            "Iliskili modullerdeki kaynak bulgular birlikte incelenip ortak kok neden notu eklenmeli.",
            "En az iki ilgili modul tekrar calistirilip correlation sinyalinin azaldigi dogrulanmali.",
            "Final Report correlation karti ayni hedef icin tekrar uretildiginde risk seviyesi dusmeli.",
        ],
        "test-run": [
            "Failed step yeniden calistirildiginda ayni selector/akis hatasi gorulmemeli.",
            "Test protokolu veya locator stratejisi guncellenip run completed sonucuyla dogrulanmali.",
            "Bug Analysis kaydi ayni run/case icin tekrar high severity uretmemeli.",
        ],
    }
    criteria = criteria_by_module.get(module, [
        "Ilgili modul analizi tekrar calistirildiginda ayni bulgu gorulmemeli.",
        "Onerilen aksiyon uygulanip kanit metrikleriyle dogrulanmali.",
        "Final Report aksiyon karti resolved/observed seviyesine dusmeli.",
    ])
    if module == "api" and category == "slow-response":
        criteria[0] = "Endpoint tekrar calistirildiginda response suresi hedef esigin altinda kalmali."
    if module == "mobile" and category == "touch-target":
        criteria[1] = "Etkilesimli hedefler en az 44x44 px civarina getirilmeli ve cihazda dokunma testiyle dogrulanmali."
    if module == "uiux" and category in {"hierarchy", "readability-flow"}:
        criteria[1] = "Ana aksiyon, baslik ve destek metni gorsel hiyerarsi/regresyon screenshot'i ile dogrulanmali."
    if module == "uiux" and category in {"contrast-risk", "cta-visibility", "palette-consistency", "color-harmony"}:
        criteria[0] = "Ayni ekran tekrar analiz edildiginde renk/kontrast metriği kabul edilebilir esige cikmali."
        criteria[1] = "CTA, metin ve zemin renkleri screenshot uzerinden ayrisma kontrolunden gecmeli."
        criteria[2] = "Onerilen accent, text veya palette duzenlemesi tasarim tokenlariyla uyumlu uygulanmali."
    if module == "uiux" and category in {"design-token", "spacing-token", "font-scale", "radius-consistency", "button-consistency"}:
        criteria[0] = "Ayni ekran tekrar analiz edildiginde ilgili design token metriği kabul edilebilir esige cikmali."
        criteria[1] = "Spacing, font scale, radius veya button standardi tasarim sistemi tokenlariyla hizalanmali."
        criteria[2] = "screenshot regresyonunda ayni token tutarsizligi tekrar uretilmemeli."
    if module == "uiux" and category == "task-flow":
        criteria[0] = "Ayni gorev tipi tekrar analiz edildiginde task completion score kabul edilebilir seviyeye cikmali."
        criteria[1] = "Primary action, gerekli inputlar ve sonraki adim yolu ayni screenshot uzerinde net gorunmeli."
        criteria[2] = "Login/search/form/checkout akisi manuel veya otomatik regresyon testiyle tamamlanmali."
    if module == "uiux" and category == "persona-risk":
        criteria[0] = "Ayni ekran tekrar analiz edildiginde en yuksek persona risk skoru dusmeli."
        criteria[1] = "Low vision, mobile one-hand, novice veya screen reader profilindeki ana risk icin UI duzenlemesi uygulanmali."
        criteria[2] = "Ilgili persona akisi manuel kontrol veya screenshot regresyonuyla tekrar dogrulanmali."
    if module == "uiux" and category == "visual-regression":
        criteria[0] = "Ayni ekran baseline screenshot ile tekrar karsilastirildiginda regression status regressed olmamali."
        criteria[1] = "Gerileyen UX metrikleri onceki kayit seviyesine yaklasmali veya iyilesmeli."
        criteria[2] = "Pixel degisimi ve score delta tasarim degisikligi notuyla birlikte dogrulanmali."
    if recommendation:
        criteria.append(f"Onerilen aksiyon uygulanmali: {recommendation}")
    return [{"text": item, "done": False} for item in criteria[:4]]


@router.post("/project/{project_id}/jira-drafts")
def create_project_jira_draft(project_id: int, request: JiraDraftRequest, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    description = request.description or (
        f"{project.name} Final Report aksiyonundan Jira ticket taslagi olusturuldu."
    )
    payload = {
        **(request.payload or {}),
        "evidence": request.evidence,
        "recommendation": request.recommendation,
        "acceptance_criteria": (request.payload or {}).get("acceptance_criteria")
        or _jira_acceptance_criteria_for_action(request.source_module, request.payload or {}, request.recommendation),
        "project": {"id": project.id, "name": project.name},
    }

    existing_draft = (
        db.query(JiraTicketDraft)
        .filter(
            JiraTicketDraft.project_id == project.id,
            JiraTicketDraft.source_module == request.source_module,
            JiraTicketDraft.source_type == request.source_type,
            JiraTicketDraft.source_ref == request.source_ref,
            JiraTicketDraft.title == request.title,
        )
        .order_by(JiraTicketDraft.created_at.desc(), JiraTicketDraft.id.desc())
        .first()
    )
    if existing_draft:
        return _ticket_draft_schema(existing_draft)

    draft = JiraTicketDraft(
        project_id=project.id,
        provider="jira",
        ticket_key="JIRA-DRAFT-PENDING",
        source_module=request.source_module,
        source_type=request.source_type,
        source_ref=request.source_ref,
        title=request.title,
        description=description,
        priority=request.priority,
        status="draft",
        payload=payload,
    )
    db.add(draft)
    db.flush()
    draft.ticket_key = f"JIRA-DRAFT-{draft.id}"
    db.commit()
    db.refresh(draft)
    return _ticket_draft_schema(draft)


@router.get("/project/{project_id}/jira-drafts")
def list_project_jira_drafts(project_id: int, limit: int = 20, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    limit = max(1, min(limit, 100))
    drafts = (
        db.query(JiraTicketDraft)
        .filter(JiraTicketDraft.project_id == project_id)
        .order_by(JiraTicketDraft.created_at.desc(), JiraTicketDraft.id.desc())
        .limit(limit)
        .all()
    )
    return [_ticket_draft_schema(draft) for draft in drafts]


@router.patch("/jira-drafts/{draft_id}/checklist")
def update_jira_draft_checklist(draft_id: int, request: JiraDraftChecklistUpdate, db: Session = Depends(get_db)):
    draft = db.query(JiraTicketDraft).filter(JiraTicketDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Jira draft not found.")

    normalized: list[dict[str, Any]] = []
    for item in request.acceptance_criteria[:10]:
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        normalized.append({"text": text, "done": bool(item.get("done"))})

    payload = dict(draft.payload or {})
    payload["acceptance_criteria"] = normalized
    draft.payload = payload
    db.commit()
    db.refresh(draft)
    return _ticket_draft_schema(draft)


@router.get("/{run_id}/json")
def export_run_json(run_id: int, db: Session = Depends(get_db)):
    """Test koşusunu JSON olarak dışa aktarır."""
    run = _get_run_or_404(run_id, db)
    data = _build_run_report(run)

    return JSONResponse(content=data, headers={"Content-Disposition": f"attachment; filename=report_{run_id}.json"})

@router.post("/{run_id}/send-to-jira")
async def send_to_jira(run_id: int, db: Session = Depends(get_db)):
    """Bulunan hatayı Jira'ya ticket olarak açar."""
    run = _get_run_or_404(run_id, db)
    ticket = _append_integration_log(run, db)
    return {
        "success": True,
        "provider": "jira",
        "configured": False,
        "run_id": run_id,
        "ticket": ticket,
        "message": f"{ticket['ticket_key']} loglara eklendi.",
    }

@router.get("/{run_id}/pdf-placeholder")
def export_run_pdf_placeholder(run_id: int, db: Session = Depends(get_db)):
    """PDF export için placeholder (Kütüphane kurulumu gerektiği için)."""
    _get_run_or_404(run_id, db)
    return {"message": "PDF oluşturma özelliği için fpdf2 kütüphanesi kurulmalıdır. Şimdilik JSON export kullanabilirsiniz."}
