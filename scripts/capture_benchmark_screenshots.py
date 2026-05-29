import argparse
import asyncio
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES_DIR = ROOT / "benchmark_cases"
DEFAULT_RESULTS_DIR = ROOT / "benchmark_results"


def _load_targets(cases_dir: Path, selected_modules: set[str] | None, project_id: int | None) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for path in sorted(cases_dir.glob("*_cases.json")):
        items = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(items, list):
            continue
        for item in items:
            module = item.get("module")
            if selected_modules and module not in selected_modules:
                continue
            screenshot = item.get("screenshot") or {}
            if not screenshot.get("required") or not screenshot.get("filename"):
                continue
            route = screenshot.get("route") or "/"
            if module == "final_report" and project_id:
                route = f"/projects/{project_id}/report"
            targets.append(
                {
                    "case_id": item.get("id"),
                    "module": module,
                    "route": route,
                    "filename": screenshot.get("filename"),
                    "source_file": path.name,
                }
            )
    return targets


def _write_manifest(results_dir: Path, rows: list[dict[str, Any]]) -> None:
    (results_dir / "screenshot_manifest.json").write_text(
        json.dumps({"screenshots": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


async def _capture_targets(
    *,
    targets: list[dict[str, Any]],
    frontend_url: str,
    results_dir: Path,
    width: int,
    height: int,
    wait_ms: int,
    dry_run: bool,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if dry_run:
        for target in targets:
            output = results_dir / target["module"] / "screenshots" / target["filename"]
            rows.append({**target, "status": "skipped", "output": str(output), "error": "dry-run"})
        return rows

    from playwright.async_api import async_playwright

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": width, "height": height})
        for target in targets:
            module_dir = results_dir / target["module"] / "screenshots"
            module_dir.mkdir(parents=True, exist_ok=True)
            output = module_dir / target["filename"]
            url = f"{frontend_url.rstrip('/')}{target['route']}"
            row = {**target, "status": "captured", "url": url, "output": str(output), "error": ""}
            try:
                await page.goto(url, wait_until="networkidle", timeout=45_000)
                await page.wait_for_timeout(wait_ms)
                await page.screenshot(path=str(output), full_page=True)
            except Exception as exc:
                row["status"] = "error"
                row["error"] = str(exc)
            rows.append(row)
        await browser.close()
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture paper-ready UI screenshots for benchmark cases.")
    parser.add_argument("--frontend-url", default="http://127.0.0.1:3000", help="Frontend base URL.")
    parser.add_argument("--cases-dir", type=Path, default=DEFAULT_CASES_DIR)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--module", action="append", help="Capture one module. Can be passed multiple times or comma separated.")
    parser.add_argument("--project-id", type=int, default=None, help="Project id for final report screenshots.")
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=1000)
    parser.add_argument("--wait-ms", type=int, default=1200)
    parser.add_argument("--dry-run", action="store_true", help="Only write manifest; do not open browser.")
    args = parser.parse_args()

    modules = None
    if args.module:
        modules = {item.strip() for raw in args.module for item in raw.split(",") if item.strip()}

    args.results_dir.mkdir(parents=True, exist_ok=True)
    targets = _load_targets(args.cases_dir, modules, args.project_id)
    if not targets:
        raise SystemExit("No screenshot targets found.")

    rows = asyncio.run(
        _capture_targets(
            targets=targets,
            frontend_url=args.frontend_url,
            results_dir=args.results_dir,
            width=args.width,
            height=args.height,
            wait_ms=args.wait_ms,
            dry_run=args.dry_run,
        )
    )
    _write_manifest(args.results_dir, rows)
    captured = sum(1 for row in rows if row["status"] == "captured")
    errors = sum(1 for row in rows if row["status"] == "error")
    skipped = sum(1 for row in rows if row["status"] == "skipped")
    print(f"Screenshot targets processed: {len(rows)}")
    print(f"- captured: {captured}")
    print(f"- skipped: {skipped}")
    print(f"- errors: {errors}")
    print(f"- manifest: {args.results_dir / 'screenshot_manifest.json'}")


if __name__ == "__main__":
    main()
