import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = ROOT / "benchmark_cases"
RESULTS_DIR = ROOT / "benchmark_results"

REQUIRED_FIELDS = {"id", "module", "feature", "input", "expected", "metrics", "screenshot"}


def _load_cases() -> list[dict]:
    cases: list[dict] = []
    for path in sorted(CASES_DIR.glob("*_cases.json")):
        items = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(items, list):
            raise ValueError(f"{path.name} must contain a JSON array")
        for item in items:
            missing = REQUIRED_FIELDS - set(item)
            if missing:
                raise ValueError(f"{path.name}:{item.get('id', '<missing-id>')} missing fields: {sorted(missing)}")
            if not item["screenshot"].get("required"):
                raise ValueError(f"{path.name}:{item['id']} must require a result screenshot")
            cases.append({**item, "_source_file": path.name})
    return cases


def _write_plan_csv(cases: list[dict]) -> None:
    path = RESULTS_DIR / "benchmark_plan.csv"
    rows = []
    for case in cases:
        screenshot = case["screenshot"]
        rows.append(
            {
                "case_id": case["id"],
                "module": case["module"],
                "feature": case["feature"],
                "metrics": ";".join(case["metrics"]),
                "screenshot_route": screenshot.get("route", ""),
                "screenshot_file": screenshot.get("filename", ""),
                "source_file": case["_source_file"],
            }
        )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_plan_json(cases: list[dict]) -> None:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for case in cases:
        grouped[case["module"]].append(
            {
                "case_id": case["id"],
                "feature": case["feature"],
                "metrics": case["metrics"],
                "screenshot": case["screenshot"],
                "source_file": case["_source_file"],
            }
        )
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_modules": len(grouped),
        "total_cases": len(cases),
        "modules": {
            module: {
                "case_count": len(items),
                "features": [item["feature"] for item in items],
                "cases": items,
            }
            for module, items in sorted(grouped.items())
        },
    }
    (RESULTS_DIR / "benchmark_plan.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    cases = _load_cases()
    if not cases:
        raise SystemExit("No benchmark cases found.")
    _write_plan_csv(cases)
    _write_plan_json(cases)
    print(f"Benchmark plan ready: {len(cases)} cases across {len({case['module'] for case in cases})} modules")
    print(f"- {RESULTS_DIR / 'benchmark_plan.csv'}")
    print(f"- {RESULTS_DIR / 'benchmark_plan.json'}")


if __name__ == "__main__":
    main()
