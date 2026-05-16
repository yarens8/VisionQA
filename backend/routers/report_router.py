
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from database import get_db
from database.models import (
    AccessibilityAnalysisRecord,
    ApiAnalysisRecord,
    DbAnalysisRecord,
    DatasetAnalysisRecord,
    PerformanceAnalysisRecord,
    Project,
    SecurityAnalysisRecord,
    TestRun,
    UiuxAnalysisRecord,
)
from core.bug_analysis import build_bug_analysis
import json

router = APIRouter(prefix="/reports", tags=["reports"])


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


def _module_status(score: int | None, issues: int = 0, present: bool = True) -> str:
    if not present:
        return "not_connected"
    if issues > 0 or (score is not None and score < 70):
        return "attention"
    if score is not None and score >= 85:
        return "healthy"
    return "observed"


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
    module_counts: dict[str, int] = {}
    for run in runs:
        module_name = str(run.module_name or "unknown").lower()
        module_counts[module_name] = module_counts.get(module_name, 0) + 1

    return [
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
    ]


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
) -> list[dict[str, Any]]:
    correlations: list[dict[str, Any]] = []
    api_summaries = api_summaries or []
    db_summaries = db_summaries or []
    performance_summaries = performance_summaries or []

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


@router.get("/project/{project_id}/summary")
def export_project_summary(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

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

    uiux_records = (
        db.query(UiuxAnalysisRecord)
        .order_by(UiuxAnalysisRecord.created_at.desc(), UiuxAnalysisRecord.id.desc())
        .limit(5)
        .all()
    )
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

    security_summaries = [_security_record_summary(record) for record in security_records]
    accessibility_summaries = [_generic_analysis_summary(record, "accessibility") for record in accessibility_records]
    uiux_summaries = [_generic_analysis_summary(record, "uiux") for record in uiux_records]
    dataset_summaries = [_generic_analysis_summary(record, "dataset") for record in dataset_records]
    api_summaries = [_api_analysis_summary(record) for record in api_records]
    db_summaries = [_db_analysis_summary(record) for record in db_records]
    performance_summaries = [_generic_analysis_summary(record, "performance") for record in performance_records]
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
    api_actions = _api_priority_actions(api_summaries)
    correlations = _correlate_project_findings(
        security_summaries,
        test_actions,
        page_url_by_id,
        api_summaries=api_summaries,
        db_summaries=db_summaries,
        performance_summaries=performance_summaries,
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
        bug_reports=bug_reports,
        total_cases=total_cases,
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
        },
        "security": {
            "records": security_summaries,
            "priority_actions": security_actions[:5],
        },
        "tests": {
            "priority_actions": test_actions,
            "bug_reports": bug_reports[:10],
        },
        "api": {
            "records": api_summaries,
            "priority_actions": api_actions,
        },
        "correlation": {
            "items": correlations,
        },
        "module_breakdown": {
            "items": module_breakdown,
        },
        "runs": [_run_summary(run) for run in runs],
    }


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
