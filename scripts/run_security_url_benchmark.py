import json
import time
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_FILE = ROOT / "benchmarks" / "security_urls.json"
RESULTS_DIR = ROOT / "benchmark_results"
DEFAULT_BASE_URL = "http://127.0.0.1:8000"


def _load_cases():
    return json.loads(BENCHMARK_FILE.read_text(encoding="utf-8"))


def _analyze_case(base_url: str, case: dict) -> dict:
    started = time.perf_counter()
    response = requests.post(
        f"{base_url}/security/analyze-url",
        json={
            "url": case["url"],
            "platform": "web",
            "headless": True,
            "full_page": True,
        },
        timeout=180,
    )
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    response.raise_for_status()
    payload = response.json()
    categories = sorted({item["category"] for item in payload.get("findings", [])})
    predicted_has_issue = len(categories) > 0
    expected_has_issue = bool(case["expected_has_issue"])
    expected_primary_signal = case["expected_primary_signal"]
    category_match = expected_primary_signal == "none" or expected_primary_signal in categories

    return {
        "id": case["id"],
        "name": case["name"],
        "url": case["url"],
        "elapsed_ms": elapsed_ms,
        "expected_has_issue": expected_has_issue,
        "predicted_has_issue": predicted_has_issue,
        "expected_primary_signal": expected_primary_signal,
        "detected_categories": categories,
        "category_match": category_match,
        "overall_score": payload.get("overall_score"),
        "overview": payload.get("overview", ""),
        "findings_count": len(payload.get("findings", [])),
    }


def _compute_metrics(results: list[dict]) -> dict:
    tp = fp = fn = tn = 0
    signal_matches = 0
    for item in results:
        expected = item["expected_has_issue"]
        predicted = item["predicted_has_issue"]
        if expected and predicted:
            tp += 1
        elif not expected and predicted:
            fp += 1
        elif expected and not predicted:
            fn += 1
        else:
            tn += 1
        if item["category_match"]:
            signal_matches += 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    accuracy = (tp + tn) / max(1, len(results))
    category_match_rate = signal_matches / max(1, len(results))

    return {
        "total_cases": len(results),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "accuracy": round(accuracy, 4),
        "category_match_rate": round(category_match_rate, 4),
        "avg_time_ms": round(sum(item["elapsed_ms"] for item in results) / max(1, len(results)), 2),
    }


def _render_markdown(summary: dict, results: list[dict]) -> str:
    lines = [
        "# Security URL Benchmark",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Total cases | {summary['total_cases']} |",
        f"| TP | {summary['tp']} |",
        f"| FP | {summary['fp']} |",
        f"| FN | {summary['fn']} |",
        f"| TN | {summary['tn']} |",
        f"| Precision | {summary['precision']} |",
        f"| Recall | {summary['recall']} |",
        f"| Accuracy | {summary['accuracy']} |",
        f"| Category match rate | {summary['category_match_rate']} |",
        f"| Avg time (ms) | {summary['avg_time_ms']} |",
        "",
        "## Case Results",
        "",
        "| Case | Expected Issue | Predicted Issue | Expected Signal | Detected Categories | Time (ms) |",
        "|---|---:|---:|---|---|---:|",
    ]
    for item in results:
        detected = ", ".join(item["detected_categories"]) if item["detected_categories"] else "none"
        lines.append(
            f"| {item['name']} | {str(item['expected_has_issue']).lower()} | {str(item['predicted_has_issue']).lower()} | "
            f"{item['expected_primary_signal']} | {detected} | {item['elapsed_ms']} |"
        )
    return "\n".join(lines) + "\n"


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    base_url = DEFAULT_BASE_URL
    cases = _load_cases()
    results = []

    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case['name']} -> {case['url']}")
        try:
            result = _analyze_case(base_url, case)
            result["status"] = "ok"
        except Exception as exc:
            result = {
                "id": case["id"],
                "name": case["name"],
                "url": case["url"],
                "status": "failed",
                "error": str(exc),
                "expected_has_issue": case["expected_has_issue"],
                "expected_primary_signal": case["expected_primary_signal"],
                "predicted_has_issue": False,
                "detected_categories": [],
                "category_match": False,
                "elapsed_ms": 0,
                "overall_score": None,
                "overview": "",
                "findings_count": 0,
            }
        results.append(result)

    successful = [item for item in results if item["status"] == "ok"]
    summary = _compute_metrics(successful)
    summary["failed_cases"] = len(results) - len(successful)

    payload = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "base_url": base_url,
        "summary": summary,
        "results": results,
    }

    json_path = RESULTS_DIR / "security_url_benchmark.json"
    md_path = RESULTS_DIR / "security_url_benchmark.md"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown(summary, results), encoding="utf-8")

    print(f"\nJSON report: {json_path}")
    print(f"Markdown report: {md_path}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
