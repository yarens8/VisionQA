import os
import sys
from datetime import datetime

from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import main
import database.models as db_models
from database import SessionLocal


def _create_run(logs: str | None = '{"result": "ok"}') -> int:
    db = SessionLocal()
    try:
        project = db_models.Project(
            name="Report Router Test",
            description="Report export test project",
            platforms=["web"],
        )
        db.add(project)
        db.flush()

        run = db_models.TestRun(
            project_id=project.id,
            platform=db_models.PlatformType.WEB,
            module_name="security",
            target="https://example.test",
            status=db_models.TestStatus.COMPLETED,
            logs=logs,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        db.add(run)
        db.flush()

        finding = db_models.Finding(
            test_run_id=run.id,
            title="Sample finding",
            description="Sample description",
            severity="medium",
            category="security",
        )
        db.add(finding)
        db.commit()
        return run.id
    finally:
        db.close()


def test_report_json_export_returns_structured_run_report():
    client = TestClient(main.app)
    run_id = _create_run()

    response = client.get(f"/reports/{run_id}/json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == run_id
    assert payload["platform"] == "web"
    assert payload["status"] == "completed"
    assert payload["logs"] == {"result": "ok"}
    assert payload["findings"][0]["title"] == "Sample finding"


def test_report_json_export_handles_malformed_logs():
    client = TestClient(main.app)
    run_id = _create_run(logs="{broken json")

    response = client.get(f"/reports/{run_id}/json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["logs"]["raw"] == "{broken json"
    assert "parse_error" in payload["logs"]


def test_report_jira_action_creates_ticket_from_real_evidence():
    client = TestClient(main.app)
    run_id = _create_run()

    jira_response = client.post(f"/reports/{run_id}/send-to-jira")

    assert jira_response.status_code == 200
    assert jira_response.json()["success"] is True
    assert jira_response.json()["provider"] == "jira"
    jira_ticket = jira_response.json()["ticket"]
    assert jira_ticket["ticket_key"] == f"JIRA-RUN-{run_id}"
    assert jira_ticket["work_items"] == ["security/medium: Sample finding - Sample description"]
    assert jira_ticket["acceptance_criteria"] == []

    export_response = client.get(f"/reports/{run_id}/json")
    integrations = export_response.json()["logs"]["integrations"]
    assert {item["provider"] for item in integrations} == {"jira"}
    assert all(item["work_items"] for item in integrations)


def test_report_slack_endpoint_is_not_exposed():
    client = TestClient(main.app)
    run_id = _create_run()

    response = client.post(f"/reports/{run_id}/notify-slack")

    assert response.status_code == 404


def test_report_actions_do_not_create_demo_ticket_without_real_evidence():
    client = TestClient(main.app)
    db = SessionLocal()
    try:
        project = db_models.Project(
            name="No Evidence Report Test",
            description="No findings or failed steps",
            platforms=["web"],
        )
        db.add(project)
        db.flush()
        run = db_models.TestRun(
            project_id=project.id,
            platform=db_models.PlatformType.WEB,
            module_name="security",
            target="https://example.test",
            status=db_models.TestStatus.COMPLETED,
            logs='{"summary": "All good", "steps": [{"order": 1, "action": "verify", "target": "home", "status": "passed"}]}',
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        db.add(run)
        db.commit()
        run_id = run.id
    finally:
        db.close()

    response = client.post(f"/reports/{run_id}/send-to-jira")

    assert response.status_code == 422
    assert "gerçek finding veya failed step bulunamadı" in response.json()["detail"]


def test_report_actions_return_404_for_missing_run():
    client = TestClient(main.app)

    response = client.post("/reports/999999999/send-to-jira")

    assert response.status_code == 404


def test_project_summary_report_includes_security_records_for_project_pages():
    client = TestClient(main.app)
    db = SessionLocal()
    try:
        project = db_models.Project(
            name="Project Summary Security",
            description="Project level summary",
            platforms=["web"],
        )
        db.add(project)
        db.flush()
        unique_url = f"https://security-summary-{project.id}.test/login"

        page = db_models.Page(
            project_id=project.id,
            name="Login",
            url=unique_url,
        )
        db.add(page)
        run = db_models.TestRun(
            project_id=project.id,
            page_id=page.id,
            platform=db_models.PlatformType.WEB,
            module_name="autonomous",
            target=page.url,
            status=db_models.TestStatus.FAILED,
            logs='{"steps": [{"status": "failed", "action": "click", "target": "#login"}]}',
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        db.add(run)
        security = db_models.SecurityAnalysisRecord(
            platform="web",
            source_type="url",
            source_label="Login security",
            source_url=page.url,
            overall_score=72,
            findings_count=2,
            overview="Security summary test",
            analysis_payload={
                "risk_summary": {
                    "critical": 0,
                    "high": 1,
                    "medium": 1,
                    "low": 0,
                    "total": 2,
                    "highest_severity": "high",
                    "priority_actions": [
                        {
                            "title": "Missing CSP",
                            "severity": "high",
                            "category": "header-hardening",
                            "source": "surface",
                            "evidence": "content-security-policy",
                            "recommendation": "Add CSP.",
                        }
                    ],
                },
                "scan_evidence": {"status_code": 200, "final_url": page.url, "headers_observed": 8, "checks_executed": ["headers"]},
            },
        )
        db.add(security)
        accessibility = db_models.AccessibilityAnalysisRecord(
            platform="web",
            source_type="url",
            source_label="Accessibility check",
            source_url=page.url,
            overall_score=84,
            findings_count=2,
            overview="Accessibility summary test",
            analysis_payload={
                "overall_score": 84,
                "findings": [
                    {
                        "title": "Form alaninda label eksik",
                        "severity": "medium",
                        "category": "form-label",
                        "description": "Email input alaninda iliskili label yok.",
                        "recommendation": "Input alanini label veya aria-label ile eslestir.",
                        "wcag_refs": ["1.3.1", "3.3.2"],
                        "impact_score": 70,
                        "evidence": {
                            "selector": "input#email",
                            "why_flagged": "Label veya accessible name bulunamadi.",
                        },
                    },
                    {"severity": "low", "category": "contrast"},
                ],
                "score_breakdown": {"form_accessibility": 70},
                "accessibility_summary": {"risk_level": "medium"},
            },
        )
        db.add(accessibility)
        uiux = db_models.UiuxAnalysisRecord(
            platform="web",
            source_type="upload",
            source_label="UIUX check",
            overall_score=91,
            findings_count=1,
            overview="UIUX summary test",
            analysis_payload={
                "project_id": project.id,
                "overall_score": 91,
                "findings": [
                    {
                        "title": "Metin okunabilirligi riskli",
                        "severity": "medium",
                        "category": "readability-flow",
                        "description": "Kucuk metin bolgesi algilandi.",
                        "recommendation": "Metin boyutunu ve satir uzunlugunu kontrol et.",
                        "numeric_evidence": {
                            "metric": "readability_risk_score",
                            "value": 52,
                            "source": "image-processing",
                        },
                        "test_suggestion": "Okunabilirlik metriğini screenshot regresyon testine ekle.",
                    }
                ],
                "evidence_matrix": {"readability_risk_score": 52},
                "score_breakdown": {"readability_flow": 68},
            },
        )
        db.add(uiux)
        api_record = db_models.ApiAnalysisRecord(
            platform="api",
            source_type="endpoint",
            source_label=f"GET {page.url}",
            source_url=page.url,
            overall_score=82,
            findings_count=1,
            overview="API summary test",
            analysis_payload={"overall_score": 82, "findings": [{"severity": "medium"}]},
        )
        db.add(api_record)
        db_record = db_models.DbAnalysisRecord(
            platform="database",
            source_type="query",
            source_label="SELECT * FROM users",
            overall_score=76,
            findings_count=2,
            overview="DB summary test",
            analysis_payload={"overall_score": 76, "findings": [{"severity": "medium"}], "schema_smells": [{"severity": "low"}]},
        )
        db.add(db_record)
        performance_record = db_models.PerformanceAnalysisRecord(
            platform="web",
            source_type="web",
            source_label=page.url,
            source_url=page.url,
            overall_score=68,
            findings_count=3,
            overview="Performance summary test",
            analysis_payload={"overall_score": 68, "findings": [{"severity": "high"}]},
        )
        db.add(performance_record)
        mobile_record = db_models.MobileAnalysisRecord(
            platform="android",
            source_type="metadata",
            source_label="Login mobile",
            overall_score=74,
            findings_count=2,
            overview="Mobile summary test",
            analysis_payload={
                "project_id": project.id,
                "overall_score": 74,
                "task_completion_friction": 62,
                "cross_platform_parity_summary": "Android/iOS parity kontrol edilmeli.",
                "context_profile": {"screen_type": "auth", "detected_patterns": ["form"], "cross_platform_consistency_signal": "Review parity."},
                "score_breakdown": {"mobile_ux": 74, "touch_target": 60, "readability": 80, "layout": 76, "interaction_readiness": 70},
                "findings": [
                    {
                        "title": "Kucuk touch target",
                        "severity": "high",
                        "category": "touch-target",
                        "description": "Buton dokunma hedefi cok kucuk.",
                        "evidence": "38x36 px",
                        "recommendation": "Dokunma hedefini 44px uzerine cikar.",
                    },
                    {"severity": "low", "category": "density"},
                ],
            },
        )
        db.add(mobile_record)
        db.commit()
        project_id = project.id
    finally:
        db.close()

    response = client.get(f"/reports/project/{project_id}/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["project"]["id"] == project_id
    assert payload["summary"]["failed_runs"] == 1
    assert payload["summary"]["security_records"] == 1
    assert payload["summary"]["high_security_risks"] == 1
    assert payload["summary"]["test_actions"] == 1
    assert payload["summary"]["correlations"] >= 1
    assert payload["summary"]["bug_reports"] == 1
    assert payload["summary"]["api_actions"] == 1
    assert payload["summary"]["db_actions"] >= 1
    assert payload["summary"]["performance_actions"] >= 1
    assert payload["summary"]["uiux_actions"] >= 1
    assert payload["summary"]["accessibility_actions"] >= 1
    assert payload["summary"]["mobile_actions"] >= 1
    assert payload["executive_summary"]["readiness_score"] == payload["overall_score"]
    assert payload["executive_summary"]["risk_level"] in {"medium", "high"}
    assert payload["executive_summary"]["top_risks"]
    assert payload["evidence_matrix"]["coverage"]["connected_modules"] >= 6
    assert "module_breakdown" in payload["evidence_matrix"]["paper_evidence"]
    assert payload["paper_alignment"]["benchmark_status"] == "deferred_final_phase"
    claim_statuses = {claim["claim"]: claim["status"] for claim in payload["paper_alignment"]["claims"]}
    assert claim_statuses["Unified multi-module QA framework"] == "supported"
    assert claim_statuses["Cross-module correlation"] == "supported"
    assert payload["paper_alignment"]["evidence_counts"]["bug_reports"] == 1
    modules = {item["module"]: item for item in payload["module_breakdown"]["items"]}
    assert modules["security"]["records"] == 1
    assert modules["security"]["interpretation"]
    assert modules["security"]["recommended_action"]
    assert modules["security"]["evidence_level"] == "actionable"
    assert modules["accessibility"]["records"] == 1
    assert modules["accessibility"]["findings"] == 2
    assert modules["uiux"]["records"] >= 1
    assert modules["bug_analysis"]["records"] == 1
    assert modules["api"]["records"] == 1
    assert modules["database"]["findings"] >= 2
    assert modules["performance"]["score"] == 68
    assert modules["mobile"]["records"] == 1
    assert modules["mobile"]["findings"] == 2

    assert payload["security"]["priority_actions"][0]["title"] == "Missing CSP"
    assert payload["api"]["priority_actions"][0]["source"] == "api"
    assert payload["api"]["priority_actions"][0]["api_record_id"]
    assert payload["database"]["priority_actions"][0]["source"] == "database"
    assert payload["performance"]["priority_actions"][0]["source"] == "performance"
    assert payload["accessibility"]["records"][0]["module"] == "accessibility"
    assert payload["accessibility"]["priority_actions"][0]["source"] == "accessibility"
    assert payload["accessibility"]["priority_actions"][0]["selector"] == "input#email"
    assert payload["uiux"]["priority_actions"][0]["source"] == "uiux"
    assert any(action["metric"] == "readability_risk_score" for action in payload["uiux"]["priority_actions"])
    assert payload["mobile"]["priority_actions"][0]["source"] == "mobile"
    assert payload["mobile"]["priority_actions"][0]["category"] == "touch-target"
    assert payload["tests"]["priority_actions"][0]["source"] == "test-run"
    assert payload["tests"]["priority_actions"][0]["bug_report"]["category"] == "selector_issue"
    assert payload["tests"]["bug_reports"][0]["target"] == "#login"
    assert "#login" in payload["tests"]["priority_actions"][0]["recommendation"]
    test_security_correlation = next(
        item for item in payload["correlation"]["items"]
        if item["related_modules"] == ["security", "test-execution", "bug-analysis"]
    )
    assert test_security_correlation["target"] == unique_url
    assert test_security_correlation["evidence"]["bug_categories"] == ["selector_issue"]
    assert "selector" in test_security_correlation["title"].lower()
    uiux_accessibility_correlation = next(
        item for item in payload["correlation"]["items"]
        if item["related_modules"] == ["uiux", "accessibility"]
    )
    assert "UI" in uiux_accessibility_correlation["title"]


def test_project_jira_draft_is_saved_for_final_report_action():
    client = TestClient(main.app)
    db = SessionLocal()
    try:
        project = db_models.Project(
            name="Jira Draft Project",
            description="Ticket draft test",
            platforms=["web"],
        )
        db.add(project)
        db.commit()
        project_id = project.id
    finally:
        db.close()

    response = client.post(
        f"/reports/project/{project_id}/jira-drafts",
        json={
            "source_module": "api",
            "source_type": "final_report_action",
            "source_ref": "api-1",
            "title": "API contract drift",
            "description": "Response schema mismatch should become a ticket.",
            "priority": "high",
            "evidence": "Missing field: status",
            "recommendation": "Serializer contract testlerini guncelle.",
            "payload": {"category": "schema-mismatch"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == project_id
    assert payload["ticket_key"] == f"JIRA-DRAFT-{payload['id']}"
    assert payload["status"] == "draft"
    assert payload["payload"]["evidence"] == "Missing field: status"
    assert payload["payload"]["acceptance_criteria"][0]["done"] is False
    assert "Endpoint" in payload["payload"]["acceptance_criteria"][0]["text"]
    assert "API" in payload["payload"]["acceptance_criteria"][1]["text"]

    update_response = client.patch(
        f"/reports/jira-drafts/{payload['id']}/checklist",
        json={
            "acceptance_criteria": [
                {"text": payload["payload"]["acceptance_criteria"][0]["text"], "done": True},
                {"text": payload["payload"]["acceptance_criteria"][1]["text"], "done": False},
            ]
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["payload"]["acceptance_criteria"][0]["done"] is True

    duplicate_response = client.post(
        f"/reports/project/{project_id}/jira-drafts",
        json={
            "source_module": "api",
            "source_type": "final_report_action",
            "source_ref": "api-1",
            "title": "API contract drift",
            "description": "Response schema mismatch should become a ticket.",
            "priority": "high",
            "evidence": "Missing field: status",
            "recommendation": "Serializer contract testlerini guncelle.",
            "payload": {"category": "schema-mismatch"},
        },
    )
    assert duplicate_response.status_code == 200
    duplicate = duplicate_response.json()
    assert duplicate["id"] == payload["id"]
    assert duplicate["payload"]["acceptance_criteria"][0]["done"] is True

    list_response = client.get(f"/reports/project/{project_id}/jira-drafts")
    assert list_response.status_code == 200
    drafts = list_response.json()
    assert drafts[0]["id"] == payload["id"]
    assert drafts[0]["payload"]["acceptance_criteria"][0]["done"] is True

    summary_response = client.get(f"/reports/project/{project_id}/summary")
    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["summary"]["jira_drafts"] == 1
    assert summary["jira_drafts"]["summary"]["total"] == 1
    assert summary["jira_drafts"]["summary"]["completed_checklist_items"] == 1
    assert summary["jira_drafts"]["items"][0]["id"] == payload["id"]


def test_project_jira_draft_uses_mobile_specific_acceptance_criteria():
    client = TestClient(main.app)
    db = SessionLocal()
    try:
        project = db_models.Project(
            name="Mobile Jira Draft Project",
            description="Mobile ticket draft test",
            platforms=["mobile_android"],
        )
        db.add(project)
        db.commit()
        project_id = project.id
    finally:
        db.close()

    response = client.post(
        f"/reports/project/{project_id}/jira-drafts",
        json={
            "source_module": "mobile",
            "source_type": "final_report_action",
            "source_ref": "mobile-1",
            "title": "Dokunma alani kucuk",
            "description": "Mobil ekranda button size 40x38.",
            "priority": "high",
            "evidence": "button size=40x38",
            "recommendation": "Tap hedeflerini 44x44 px civarina yaklastir.",
            "payload": {"category": "touch-target"},
        },
    )

    assert response.status_code == 200
    criteria = response.json()["payload"]["acceptance_criteria"]
    criteria_text = " ".join(item["text"] for item in criteria)
    assert "Android/iOS" in criteria_text
    assert "44x44" in criteria_text
    assert "Tap hedeflerini" in criteria_text


def test_bug_analysis_classifies_common_failure_patterns():
    from core.bug_analysis import build_bug_analysis

    reports = build_bug_analysis(
        {
            "steps": [
                {
                    "order": 3,
                    "action": "type",
                    "target": "#user-name",
                    "status": "failed",
                    "reason": "Locator.wait_for: Timeout 2500ms exceeded",
                }
            ]
        },
        run_target="https://example.test/login",
        case_title="Login form check",
    )

    assert len(reports) == 1
    assert reports[0]["category"] == "timing_issue"
    assert reports[0]["failed_step_order"] == 3
    assert reports[0]["affected_case"] == "Login form check"
    assert "wait" in reports[0]["recommendation"].lower()


def test_project_summary_correlates_api_security_signals_with_security_record():
    client = TestClient(main.app)
    db = SessionLocal()
    try:
        project = db_models.Project(
            name="Project Summary API Correlation",
            description="API correlation test project",
            platforms=["web", "api"],
        )
        db.add(project)
        db.flush()
        unique_url = f"https://api-correlation-{project.id}.test/api/admin"
        page = db_models.Page(project_id=project.id, name="Admin API", url=unique_url)
        db.add(page)
        security = db_models.SecurityAnalysisRecord(
            platform="web",
            source_type="url",
            source_label="Admin API security",
            source_url=unique_url,
            overall_score=75,
            findings_count=1,
            overview="Security record",
            analysis_payload={
                "risk_summary": {
                    "critical": 0,
                    "high": 0,
                    "medium": 1,
                    "low": 0,
                    "total": 1,
                    "highest_severity": "medium",
                    "priority_actions": [
                        {
                            "title": "Auth hardening needed",
                            "severity": "medium",
                            "category": "auth",
                            "source": "surface",
                            "evidence": "admin endpoint",
                            "recommendation": "Check auth policy.",
                        }
                    ],
                },
                "scan_evidence": {"status_code": 200, "final_url": unique_url, "headers_observed": 6, "checks_executed": ["headers"]},
            },
        )
        db.add(security)
        api_record = db_models.ApiAnalysisRecord(
            platform="api",
            source_type="endpoint",
            source_label=f"POST {unique_url}",
            source_url=unique_url,
            overall_score=68,
            findings_count=1,
            overview="API auth signal",
            analysis_payload={
                "project_id": project.id,
                "method": "POST",
                "url": unique_url,
                "overall_score": 68,
                "findings": [{"severity": "high", "category": "auth-signal", "title": "Mutating endpoint auth signal"}],
                "evidence_summary": {
                    "contract_signals": 0,
                    "security_signals": 1,
                    "performance_signals": 0,
                    "validation_signals": 0,
                    "availability_signals": 0,
                    "negative_probe_signals": 0,
                    "primary_categories": ["auth-signal"],
                    "recommended_modules": ["4.5 Security"],
                },
            },
        )
        db.add(api_record)
        db.commit()
        project_id = project.id
    finally:
        db.close()

    response = client.get(f"/reports/project/{project_id}/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["correlations"] == 1
    assert payload["summary"]["api_actions"] == 1
    assert payload["api"]["priority_actions"][0]["category"] == "auth-signal"
    correlation = payload["correlation"]["items"][0]
    assert "API security" in correlation["title"]
    assert correlation["related_modules"] == ["api", "security"]
    assert correlation["evidence"]["bug_categories"] == ["auth-signal"]


def test_project_summary_merges_duplicate_api_actions():
    client = TestClient(main.app)
    db = SessionLocal()
    try:
        project = db_models.Project(
            name="Project Summary API Dedupe",
            description="API action dedupe test project",
            platforms=["api"],
        )
        db.add(project)
        db.flush()
        endpoint = "https://jsonplaceholder.typicode.com/todos/1"
        for index in range(2):
            db.add(
                db_models.ApiAnalysisRecord(
                    platform="api",
                    source_type="endpoint",
                    source_label=f"GET {endpoint}",
                    source_url=endpoint,
                    overall_score=76,
                    findings_count=1,
                    overview="Duplicate API schema finding",
                    analysis_payload={
                        "project_id": project.id,
                        "method": "GET",
                        "url": endpoint,
                        "overall_score": 76,
                        "duration_ms": 200 + index,
                        "findings": [
                            {
                                "severity": "medium",
                                "category": "schema-mismatch",
                                "title": "Response icinde beklenen alanlar eksik",
                                "description": "Beklenen zorunlu alanlardan bazilari response icinde bulunmuyor.",
                                "evidence": "Missing fields: notExistingField",
                                "recommendation": "API response contract'ini kontrol et.",
                            }
                        ],
                        "evidence_summary": {
                            "contract_signals": 1,
                            "security_signals": 0,
                            "performance_signals": 0,
                            "validation_signals": 0,
                            "availability_signals": 0,
                            "negative_probe_signals": 0,
                            "primary_categories": ["schema-mismatch"],
                            "recommended_modules": ["4.10 Database"],
                        },
                    },
                )
            )
        db.commit()
        project_id = project.id
    finally:
        db.close()

    response = client.get(f"/reports/project/{project_id}/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["api_actions"] == 1
    action = payload["api"]["priority_actions"][0]
    assert action["duplicate_count"] == 2
    assert len(action["api_record_ids"]) == 2


def test_project_summary_correlates_api_contract_with_database_schema():
    client = TestClient(main.app)
    db = SessionLocal()
    try:
        project = db_models.Project(
            name="Project Summary API DB Correlation",
            description="API DB correlation test project",
            platforms=["api", "database"],
        )
        db.add(project)
        db.flush()
        endpoint = f"https://api-db-correlation-{project.id}.test/users"
        db.add(
            db_models.ApiAnalysisRecord(
                platform="api",
                source_type="endpoint",
                source_label=f"GET {endpoint}",
                source_url=endpoint,
                overall_score=72,
                findings_count=1,
                overview="API contract finding",
                analysis_payload={
                    "project_id": project.id,
                    "method": "GET",
                    "url": endpoint,
                    "overall_score": 72,
                    "findings": [
                        {
                            "severity": "high",
                            "category": "schema-mismatch",
                            "title": "Response icinde beklenen alanlar eksik",
                            "description": "Beklenen zorunlu alan response icinde yok.",
                            "evidence": "Missing fields: email",
                            "recommendation": "API contract ve serializer katmanini kontrol et.",
                        }
                    ],
                    "evidence_summary": {
                        "contract_signals": 1,
                        "security_signals": 0,
                        "performance_signals": 0,
                        "validation_signals": 0,
                        "availability_signals": 0,
                        "negative_probe_signals": 0,
                        "primary_categories": ["schema-mismatch"],
                        "recommended_modules": ["4.10 Database"],
                    },
                },
            )
        )
        db.add(
            db_models.DbAnalysisRecord(
                platform="database",
                source_type="table",
                source_label="users",
                overall_score=70,
                findings_count=1,
                overview="DB schema mismatch",
                analysis_payload={
                    "overall_score": 70,
                    "table_name": "users",
                    "findings": [
                        {
                            "severity": "medium",
                            "category": "api-db-consistency",
                            "title": "API beklentisi ile DB kolonlari ayrisiyor",
                            "description": "API field DB kolon setinde gorunmedi.",
                            "evidence": "Missing API fields: email",
                            "recommendation": "API response modeli ile tablo kolonlarini hizala.",
                        }
                    ],
                    "schema_smells": [],
                },
            )
        )
        db.commit()
        project_id = project.id
    finally:
        db.close()

    response = client.get(f"/reports/project/{project_id}/summary")

    assert response.status_code == 200
    payload = response.json()
    correlation = next(
        item for item in payload["correlation"]["items"]
        if item["related_modules"] == ["api", "database"]
    )
    assert "API contract drift" in correlation["title"]
    assert "api-db-consistency" in correlation["evidence"]["bug_categories"]
    assert correlation["severity"] == "high"


def test_project_summary_correlates_api_latency_with_performance_record_by_project():
    client = TestClient(main.app)
    db = SessionLocal()
    try:
        project = db_models.Project(
            name="Project Summary API Performance Correlation",
            description="API performance correlation test project",
            platforms=["api", "web"],
        )
        db.add(project)
        db.flush()
        endpoint = "https://jsonplaceholder.typicode.com/todos/1"
        db.add(
            db_models.ApiAnalysisRecord(
                platform="api",
                source_type="endpoint",
                source_label=f"GET {endpoint}",
                source_url=endpoint,
                overall_score=70,
                findings_count=1,
                overview="API latency finding",
                analysis_payload={
                    "project_id": project.id,
                    "method": "GET",
                    "url": endpoint,
                    "overall_score": 70,
                    "findings": [
                        {
                            "severity": "medium",
                            "category": "slow-response",
                            "title": "API yaniti hedefin ustunde",
                            "description": "Response suresi kabul edilebilir seviyenin ustune cikiyor.",
                            "evidence": "Duration: 1400.00 ms",
                            "recommendation": "Endpoint icin latency butcesi belirle.",
                        }
                    ],
                    "evidence_summary": {
                        "contract_signals": 0,
                        "security_signals": 0,
                        "performance_signals": 1,
                        "validation_signals": 0,
                        "availability_signals": 0,
                        "negative_probe_signals": 0,
                        "primary_categories": ["slow-response"],
                        "recommended_modules": ["4.7 Performance"],
                    },
                },
            )
        )
        db.add(
            db_models.PerformanceAnalysisRecord(
                platform="api",
                source_type="api",
                source_label=endpoint,
                source_url=endpoint,
                overall_score=68,
                findings_count=1,
                overview="Performance API latency",
                analysis_payload={
                    "project_id": project.id,
                    "overall_score": 68,
                    "performance_grade": "C",
                    "findings": [{"severity": "medium", "category": "api-latency"}],
                },
            )
        )
        db.commit()
        project_id = project.id
    finally:
        db.close()

    response = client.get(f"/reports/project/{project_id}/summary")

    assert response.status_code == 200
    payload = response.json()
    modules = {item["module"]: item for item in payload["module_breakdown"]["items"]}
    assert modules["performance"]["records"] == 1
    correlation = next(
        item for item in payload["correlation"]["items"]
        if item["related_modules"] == ["api", "performance"]
    )
    assert "API latency" in correlation["title"]
    assert correlation["target"] == endpoint
    assert correlation["evidence"]["bug_categories"] == ["slow-response"]


def test_project_summary_merges_duplicate_correlations():
    client = TestClient(main.app)
    db = SessionLocal()
    try:
        project = db_models.Project(
            name="Project Summary Correlation Dedupe",
            description="Correlation dedupe test project",
            platforms=["api", "database"],
        )
        db.add(project)
        db.flush()
        endpoint = "https://jsonplaceholder.typicode.com/todos/1"
        for index in range(2):
            db.add(
                db_models.ApiAnalysisRecord(
                    platform="api",
                    source_type="endpoint",
                    source_label=f"GET {endpoint}",
                    source_url=endpoint,
                    overall_score=72,
                    findings_count=1,
                    overview="API contract finding",
                    analysis_payload={
                        "project_id": project.id,
                        "method": "GET",
                        "url": endpoint,
                        "overall_score": 72,
                        "findings": [
                            {
                                "severity": "medium",
                                "category": "schema-mismatch",
                                "title": "Response icinde beklenen alanlar eksik",
                                "description": "Beklenen alan response icinde yok.",
                                "evidence": "Missing fields: notExistingField",
                                "recommendation": "API contract kontrol edilmeli.",
                            }
                        ],
                        "evidence_summary": {
                            "contract_signals": 1,
                            "security_signals": 0,
                            "performance_signals": 0,
                            "validation_signals": 0,
                            "availability_signals": 0,
                            "negative_probe_signals": 0,
                            "primary_categories": ["schema-mismatch"],
                            "recommended_modules": ["4.10 Database"],
                        },
                    },
                )
            )
        db.add(
            db_models.DbAnalysisRecord(
                platform="database",
                source_type="query",
                source_label="SELECT * FROM projects",
                overall_score=76,
                findings_count=1,
                overview="DB query shape",
                analysis_payload={
                    "overall_score": 76,
                    "findings": [
                        {
                            "severity": "medium",
                            "category": "query-shape",
                            "title": "SELECT * kullanimi",
                            "description": "Query shape izlenmeli.",
                            "evidence": "SELECT * FROM projects",
                            "recommendation": "Alanlari explicit sec.",
                        }
                    ],
                    "schema_smells": [],
                },
            )
        )
        db.commit()
        project_id = project.id
    finally:
        db.close()

    response = client.get(f"/reports/project/{project_id}/summary")

    assert response.status_code == 200
    payload = response.json()
    matching = [
        item for item in payload["correlation"]["items"]
        if item["related_modules"] == ["api", "database"]
    ]
    assert len(matching) == 1
    assert matching[0]["duplicate_count"] == 2
    assert matching[0]["signal_count"] >= 4
