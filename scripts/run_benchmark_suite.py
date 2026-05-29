import argparse
import base64
import csv
import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES_DIR = ROOT / "benchmark_cases"
DEFAULT_RESULTS_DIR = ROOT / "benchmark_results"
FIXTURES_DIR = DEFAULT_CASES_DIR / "fixtures"

JOB_TIMEOUT_SECONDS = 180
POLL_INTERVAL_SECONDS = 2


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_cases(cases_dir: Path, selected_modules: set[str] | None) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for path in sorted(cases_dir.glob("*_cases.json")):
        items = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(items, list):
            raise ValueError(f"{path.name} must contain a JSON array")
        for item in items:
            module = str(item.get("module") or "").strip()
            if selected_modules and module not in selected_modules:
                continue
            cases.append({**item, "_source_file": path.name})
    return cases


def _json_request(base_url: str, method: str, path: str, payload: dict[str, Any] | None = None, timeout: int = 60) -> Any:
    url = f"{base_url.rstrip('/')}{path}"
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {exc.code} for {method} {path}: {detail[:500]}") from exc
    except URLError as exc:
        raise RuntimeError(f"Cannot reach backend at {url}: {exc.reason}") from exc


def _poll_job(base_url: str, status_path: str, job_id: int) -> dict[str, Any]:
    deadline = time.time() + JOB_TIMEOUT_SECONDS
    path = status_path.format(job_id=job_id)
    last_payload: dict[str, Any] = {}
    while time.time() < deadline:
        payload = _json_request(base_url, "GET", path, timeout=20)
        last_payload = payload if isinstance(payload, dict) else {}
        status = str(last_payload.get("status") or "").lower()
        if status in {"completed", "failed"}:
            return last_payload
        time.sleep(POLL_INTERVAL_SECONDS)
    raise RuntimeError(f"Job {job_id} timed out. Last status: {last_payload.get('status')}")


def _start_job(base_url: str, start_path: str, status_path: str, payload: dict[str, Any]) -> dict[str, Any]:
    started = _json_request(base_url, "POST", start_path, payload, timeout=60)
    job_id = started.get("job_id") if isinstance(started, dict) else None
    if not job_id:
        raise RuntimeError(f"Job endpoint did not return job_id: {started}")
    completed = _poll_job(base_url, status_path, int(job_id))
    if str(completed.get("status") or "").lower() == "failed":
        raise RuntimeError(completed.get("error_message") or f"Job {job_id} failed")
    result = completed.get("result")
    if not isinstance(result, dict):
        raise RuntimeError(f"Job {job_id} completed without result payload")
    return {"job": completed, "result": result}


def _fixture_base64(case: dict[str, Any]) -> tuple[str | None, str | None]:
    fixture = (case.get("input") or {}).get("fixture")
    if not fixture:
        return None, None
    path = FIXTURES_DIR / str(fixture)
    if not path.exists():
        return None, f"Missing fixture: {path}"
    return base64.b64encode(path.read_bytes()).decode("utf-8"), None


def _local_fixture_url(base_url: str, url: str | None) -> str | None:
    if not url:
        return url
    mapping = {
        "https://jsonplaceholder.typicode.com/todos/1": "/benchmark-fixtures/api/todos/1",
        "https://httpbin.org/get": "/benchmark-fixtures/api/todos/1",
        "https://httpbin.org/delay/2": "/benchmark-fixtures/api/delay/2",
        "https://demoqa.com/": "/benchmark-fixtures/pages/demoqa",
        "https://demoqa.com/text-box": "/benchmark-fixtures/pages/text-box",
        "https://www.saucedemo.com/": "/benchmark-fixtures/pages/saucedemo-login",
        "https://the-internet.herokuapp.com/": "/benchmark-fixtures/pages/the-internet",
    }
    path = mapping.get(url.rstrip("/") + "/" if url.rstrip("/") in {"https://demoqa.com", "https://www.saucedemo.com", "https://the-internet.herokuapp.com"} else url)
    if not path:
        path = mapping.get(url)
    return f"{base_url.rstrip('/')}{path}" if path else url


def _with_local_fixture_urls(base_url: str, data: dict[str, Any]) -> dict[str, Any]:
    mapped = dict(data)
    for key in ("url", "web_url", "api_url"):
        if key in mapped:
            mapped[key] = _local_fixture_url(base_url, mapped.get(key))
    return mapped


def _normalize_case_payload(
    case: dict[str, Any],
    project_id: int | None,
    base_url: str,
    local_fixtures: bool,
) -> tuple[str, str, dict[str, Any] | None, str | None]:
    module = case["module"]
    data = dict(case.get("input") or {})
    if local_fixtures:
        data = _with_local_fixture_urls(base_url, data)

    if module == "api":
        payload = {
            "method": data.get("method", "GET"),
            "url": data.get("url"),
            "project_id": project_id,
            "headers": data.get("headers"),
            "body": data.get("body"),
            "params": data.get("params"),
            "expected_status": data.get("expected_status"),
            "expected_fields": data.get("expected_fields") or [],
            "expected_response_type": data.get("expected_response_type"),
            "run_negative_checks": bool(data.get("run_negative_checks", True)),
        }
        return "POST", "/api-test/analyze", payload, None

    if module == "security":
        if data.get("hypotheses"):
            payload = {"url": data.get("url"), "platform": data.get("platform", "web"), "hypotheses": data.get("hypotheses") or []}
            return "POST", "/security/simulate-url", payload, None
        payload = {
            "url": data.get("url"),
            "platform": data.get("platform", "web"),
            "headless": bool(data.get("headless", True)),
            "full_page": bool(data.get("full_page", True)),
        }
        return "POST_JOB", "/security/analyze-url-job", payload, "/security/jobs/{job_id}"

    if module == "autonomous":
        payload = {
            "url": data.get("url"),
            "platform": data.get("platform", "web"),
            "project_id": project_id,
            "use_screenshot": bool(data.get("use_screenshot", True)),
            "strict_visual": bool(data.get("strict_visual", False)),
            "require_live_show": False,
        }
        return "POST", "/cases/generate", payload, None

    if module == "dataset":
        return "POST_JOB", "/dataset/analyze-job", data, "/dataset/jobs/{job_id}"

    if module == "database":
        payload = {
            "connection_string": data.get("connection_string"),
            "query": data.get("query"),
            "table_name": data.get("table_name"),
            "expected_columns": data.get("expected_columns") or [],
            "api_expected_fields": data.get("api_expected_fields") or [],
            "sample_limit": data.get("sample_limit", 50),
        }
        return "POST_JOB", "/db-test/quality-audit-job", payload, "/db-test/jobs/{job_id}"

    if module == "performance":
        payload = {
            "project_id": project_id if data.get("project_id") is None else data.get("project_id"),
            "url": data.get("web_url") or data.get("url"),
            "api_method": data.get("api_method", "GET"),
            "api_url": data.get("api_url"),
            "db_connection_string": data.get("db_connection_string"),
            "db_query": data.get("db_query"),
            "sample_api_runs": data.get("sample_count", data.get("sample_api_runs", 5)),
            "platform": data.get("platform", "web"),
        }
        return "POST_JOB", "/performance/analyze-job", payload, "/performance/jobs/{job_id}"

    if module == "accessibility":
        if data.get("source_type") == "screenshot":
            image_base64, error = _fixture_base64(case)
            if error:
                return "SKIP", "", None, error
            return "POST_JOB", "/accessibility/analyze-image-job", {"platform": data.get("platform", "web"), "image_base64": image_base64}, "/accessibility/jobs/{job_id}"
        payload = {
            "url": data.get("url"),
            "platform": data.get("platform", "web"),
            "headless": bool(data.get("headless", True)),
            "full_page": bool(data.get("full_page", True)),
        }
        return "POST_JOB", "/accessibility/analyze-url-job", payload, "/accessibility/jobs/{job_id}"

    if module == "uiux":
        image_base64, error = _fixture_base64(case)
        if error:
            return "SKIP", "", None, error
        return "POST_JOB", "/uiux/analyze-image-job", {"platform": data.get("platform", "web"), "project_id": project_id, "image_base64": image_base64}, "/uiux/jobs/{job_id}"

    if module == "mobile":
        payload = {
            "platform": data.get("platform", "android"),
            "project_id": project_id,
            "screen_name": data.get("screen_name"),
            "element_metadata": data.get("metadata") or data.get("element_metadata") or [],
        }
        return "POST_JOB", "/mobile/analyze-job", payload, "/mobile/jobs/{job_id}"

    if module == "final_report":
        if not project_id:
            return "SKIP", "", None, "Final report benchmark requires --project-id"
        return "GET", f"/reports/project/{project_id}/summary", None, None

    return "SKIP", "", None, f"No runner mapping for module: {module}"


def _flatten_values(payload: Any) -> list[Any]:
    values: list[Any] = []
    if isinstance(payload, dict):
        for value in payload.values():
            values.extend(_flatten_values(value))
    elif isinstance(payload, list):
        for value in payload:
            values.extend(_flatten_values(value))
    else:
        values.append(payload)
    return values


def _payload_text(payload: Any) -> str:
    return json.dumps(_json_safe(payload), ensure_ascii=False, sort_keys=True).lower()


def _categories(payload: Any) -> set[str]:
    found: set[str] = set()

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key in ("category", "type", "probe_type", "error_type"):
                item = value.get(key)
                if isinstance(item, str) and item.strip():
                    found.add(item.strip())
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(payload)
    return found


def _score(payload: dict[str, Any]) -> int | None:
    for key in ("overall_score", "ux_score", "table_quality_score"):
        value = payload.get(key)
        if isinstance(value, (int, float)):
            return int(value)
    summary = payload.get("summary")
    if isinstance(summary, dict):
        value = summary.get("overall_score")
        if isinstance(value, (int, float)):
            return int(value)
    return None


def _findings_count(payload: Any) -> int:
    if not isinstance(payload, dict):
        return 0
    count = 0
    for key in ("findings", "detail_errors", "schema_smells", "probes", "priority_actions"):
        value = payload.get(key)
        if isinstance(value, list):
            count += len(value)
    if isinstance(payload.get("cases"), list):
        return len(payload.get("cases") or [])
    if isinstance(payload.get("saved_cases"), list):
        return len(payload.get("saved_cases") or [])
    return count


def _case_count(payload: dict[str, Any]) -> int:
    if isinstance(payload.get("total_cases"), int):
        return int(payload["total_cases"])
    for key in ("cases", "saved_cases"):
        if isinstance(payload.get(key), list):
            return len(payload[key])
    return 0


def _step_actions(payload: Any) -> set[str]:
    actions: set[str] = set()

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key in ("action", "type", "step_type"):
                item = value.get(key)
                if isinstance(item, str):
                    actions.add(item.lower())
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(payload)
    return actions


def _evaluate_expected(expected: dict[str, Any], payload: dict[str, Any]) -> tuple[bool, list[str]]:
    checks: list[tuple[bool, str]] = []
    text = _payload_text(payload)
    categories = _categories(payload)

    if "status_code" in expected:
        checks.append((payload.get("status_code") == expected["status_code"], f"status_code={payload.get('status_code')} expected={expected['status_code']}"))
    if "minimum_findings" in expected:
        count = _findings_count(payload)
        checks.append((count >= int(expected["minimum_findings"]), f"findings={count} minimum={expected['minimum_findings']}"))
    if "maximum_findings" in expected:
        count = _findings_count(payload)
        checks.append((count <= int(expected["maximum_findings"]), f"findings={count} maximum={expected['maximum_findings']}"))
    if "minimum_score" in expected:
        score = _score(payload)
        checks.append((score is not None and score >= int(expected["minimum_score"]), f"score={score} minimum={expected['minimum_score']}"))
    if "minimum_cases" in expected:
        count = _case_count(payload)
        checks.append((count >= int(expected["minimum_cases"]), f"cases={count} minimum={expected['minimum_cases']}"))
    if "must_include_categories" in expected:
        required = set(expected["must_include_categories"])
        checks.append((required.issubset(categories), f"categories={sorted(categories)} required={sorted(required)}"))
    if "must_include_categories_any" in expected:
        required = set(expected["must_include_categories_any"])
        checks.append((bool(required.intersection(categories)), f"categories={sorted(categories)} any={sorted(required)}"))
    if "must_not_include_categories" in expected:
        forbidden = set(expected["must_not_include_categories"])
        checks.append((not forbidden.intersection(categories), f"categories={sorted(categories)} forbidden={sorted(forbidden)}"))
    if "must_include_terms" in expected:
        missing = [term for term in expected["must_include_terms"] if str(term).lower() not in text]
        checks.append((not missing, f"missing_terms={missing}"))
    if "must_not_include_terms" in expected:
        present = [term for term in expected["must_not_include_terms"] if str(term).lower() in text]
        checks.append((not present, f"forbidden_terms_present={present}"))
    if "must_include_step_actions" in expected:
        actions = _step_actions(payload)
        required = {str(item).lower() for item in expected["must_include_step_actions"]}
        checks.append((required.issubset(actions), f"actions={sorted(actions)} required={sorted(required)}"))
    if "minimum_probes" in expected:
        probes = payload.get("probes") if isinstance(payload.get("probes"), list) else []
        checks.append((len(probes) >= int(expected["minimum_probes"]), f"probes={len(probes)} minimum={expected['minimum_probes']}"))
    if "must_include_probe_types" in expected:
        probes = {str(item.get("probe_type")) for item in payload.get("probes", []) if isinstance(item, dict)}
        required = set(expected["must_include_probe_types"])
        checks.append((required.issubset(probes), f"probe_types={sorted(probes)} required={sorted(required)}"))
    if "must_include_top_level_keys" in expected:
        required = set(expected["must_include_top_level_keys"])
        checks.append((required.issubset(payload.keys()), f"top_keys={sorted(payload.keys())} required={sorted(required)}"))

    if not checks:
        return True, ["No executable expected checks were defined for this case."]
    return all(item[0] for item in checks), [message for _, message in checks]


def _metric_value(metric: str, payload: dict[str, Any]) -> Any:
    direct = payload.get(metric)
    if direct is not None:
        return direct
    aliases = {
        "case_count": _case_count(payload),
        "findings_count": _findings_count(payload),
        "overall_score": _score(payload),
        "api_actions": len(payload.get("api_actions") or []),
        "performance_actions": len(payload.get("performance_actions") or []),
        "db_actions": len(payload.get("db_actions") or []),
        "risk_summary": payload.get("risk_summary"),
        "grade": payload.get("performance_grade") or payload.get("quality_grade"),
    }
    return aliases.get(metric)


def _json_safe(value: Any, seen: set[int] | None = None) -> Any:
    if seen is None:
        seen = set()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    marker = id(value)
    if marker in seen:
        return "<circular-reference>"
    seen.add(marker)
    try:
        if isinstance(value, dict):
            return {str(key): _json_safe(child, seen) for key, child in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [_json_safe(child, seen) for child in value]
        if hasattr(value, "isoformat"):
            try:
                return value.isoformat()
            except Exception:
                pass
        return str(value)
    finally:
        seen.discard(marker)


def _run_case(base_url: str, case: dict[str, Any], project_id: int | None, dry_run: bool, local_fixtures: bool) -> dict[str, Any]:
    started = time.perf_counter()
    method, path, payload, extra = _normalize_case_payload(case, project_id, base_url, local_fixtures)
    screenshot = case.get("screenshot") or {}
    result: dict[str, Any] = {}
    status = "passed"
    error = ""
    checks: list[str] = []

    if method == "SKIP":
        status = "skipped"
        error = str(extra or "Skipped")
    elif dry_run:
        status = "skipped"
        error = "dry-run"
    else:
        try:
            if method == "POST":
                result = _json_request(base_url, "POST", path, payload, timeout=90)
            elif method == "GET":
                result = _json_request(base_url, "GET", path, timeout=60)
            elif method == "POST_JOB":
                if not extra:
                    raise RuntimeError(f"Missing job status path for {path}")
                job_payload = _start_job(base_url, path, extra, payload or {})
                result = job_payload["result"]
                job_meta = dict(job_payload["job"])
                job_meta.pop("result", None)
                result["_benchmark_job"] = job_meta
            else:
                raise RuntimeError(f"Unsupported method: {method}")
            passed, checks = _evaluate_expected(case.get("expected") or {}, result)
            status = "passed" if passed else "failed"
        except Exception as exc:
            status = "error"
            error = str(exc)

    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    metrics = {metric: _metric_value(metric, result) for metric in case.get("metrics") or []}
    return {
        "case_id": case.get("id"),
        "module": case.get("module"),
        "feature": case.get("feature"),
        "status": status,
        "duration_ms": duration_ms,
        "error": error,
        "checks": checks,
        "metrics": metrics,
        "screenshot_route": screenshot.get("route"),
        "screenshot_file": screenshot.get("filename"),
        "result": result,
    }


def _write_module_outputs(results_dir: Path, module: str, rows: list[dict[str, Any]]) -> None:
    module_dir = results_dir / module
    module_dir.mkdir(parents=True, exist_ok=True)
    csv_rows = []
    for row in rows:
        csv_rows.append(
            {
                "case_id": row["case_id"],
                "feature": row["feature"],
                "status": row["status"],
                "duration_ms": row["duration_ms"],
                "error": row["error"],
                "metrics": json.dumps(_json_safe(row["metrics"]), ensure_ascii=False),
                "checks": " | ".join(row["checks"]),
                "screenshot_route": row["screenshot_route"],
                "screenshot_file": row["screenshot_file"],
            }
        )
    with (module_dir / "results.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0].keys()))
        writer.writeheader()
        writer.writerows(csv_rows)
    (module_dir / "evidence.json").write_text(
        json.dumps(_json_safe(rows), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_summary(results_dir: Path, results: list[dict[str, Any]]) -> None:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        grouped[row["module"]].append(row)

    summary_rows = []
    for module, rows in sorted(grouped.items()):
        total = len(rows)
        passed = sum(1 for row in rows if row["status"] == "passed")
        failed = sum(1 for row in rows if row["status"] == "failed")
        errored = sum(1 for row in rows if row["status"] == "error")
        skipped = sum(1 for row in rows if row["status"] == "skipped")
        summary_rows.append(
            {
                "module": module,
                "total_cases": total,
                "passed": passed,
                "failed": failed,
                "error": errored,
                "skipped": skipped,
                "pass_rate": round((passed / total) * 100, 2) if total else 0,
                "screenshot_targets": sum(1 for row in rows if row.get("screenshot_file")),
            }
        )

    with (results_dir / "paper_summary_table.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    payload = {
        "generated_at": _utc_now(),
        "total_cases": len(results),
        "modules": summary_rows,
        "notes": [
            "UI result screenshots are tracked as screenshot targets and should be captured by the Playwright benchmark screenshot runner.",
            "Skipped cases usually mean a required screenshot fixture or project id was not provided.",
        ],
    }
    (results_dir / "paper_summary_table.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run VisionQA benchmark cases and write paper-ready result tables.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Backend API base URL.")
    parser.add_argument("--cases-dir", type=Path, default=DEFAULT_CASES_DIR)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--module", action="append", help="Run one module. Can be passed multiple times.")
    parser.add_argument("--project-id", type=int, default=None, help="Project id for project-bound modules and final report.")
    parser.add_argument("--local-fixtures", action="store_true", help="Map public demo URLs to local deterministic benchmark fixtures.")
    parser.add_argument("--dry-run", action="store_true", help="Do not call backend; only emit skipped rows and table structure.")
    args = parser.parse_args()

    modules = None
    if args.module:
        modules = {item.strip() for raw in args.module for item in raw.split(",") if item.strip()}

    args.results_dir.mkdir(parents=True, exist_ok=True)
    cases = _load_cases(args.cases_dir, modules)
    if not cases:
        raise SystemExit("No benchmark cases found.")

    results = []
    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case['module']}::{case['id']}")
        results.append(_run_case(args.base_url, case, args.project_id, args.dry_run, args.local_fixtures))

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        grouped[row["module"]].append(row)
    for module, rows in grouped.items():
        _write_module_outputs(args.results_dir, module, rows)
    _write_summary(args.results_dir, results)

    print(f"Benchmark results written to: {args.results_dir}")
    print(f"- {args.results_dir / 'paper_summary_table.csv'}")
    print(f"- {args.results_dir / 'paper_summary_table.json'}")


if __name__ == "__main__":
    main()
