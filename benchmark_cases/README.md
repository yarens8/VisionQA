# VisionQA Benchmark Cases

This folder defines feature-level benchmark inputs for each VisionQA module.
Each JSON file is intentionally small, readable, and suitable for both paper
tables and UI screenshot evidence.

Common case shape:

```json
{
  "id": "module_feature_case",
  "module": "api",
  "feature": "Schema mismatch detection",
  "input": {},
  "expected": {},
  "metrics": ["passed", "findings_count", "score"],
  "screenshot": {
    "required": true,
    "route": "/test-lab",
    "filename": "api_schema_mismatch_result.png"
  }
}
```

Output target:

```text
benchmark_results/
  paper_summary_table.csv
  paper_summary_table.json
  <module>/
    results.csv
    evidence.json
    screenshots/
```

Useful commands:

```powershell
# Only validate the benchmark plan and output structure.
python scripts\prepare_benchmark_plan.py
python scripts\run_benchmark_suite.py --dry-run

# Run one module against the local backend.
python scripts\run_benchmark_suite.py --module api

# Run project-bound cases, including final report checks.
python scripts\run_benchmark_suite.py --project-id 113

# Run selected modules only.
python scripts\run_benchmark_suite.py --module api,database,performance --project-id 113

# Run with deterministic local fixtures instead of public demo URLs.
python scripts\run_benchmark_suite.py --local-fixtures --project-id 113

# Capture UI screenshots for paper evidence after running the analyses.
python scripts\capture_benchmark_screenshots.py --project-id 113

# Capture screenshots only for selected modules.
python scripts\capture_benchmark_screenshots.py --module api,database,performance --project-id 113
```

Notes:

- Start the backend first: `cd backend; python run_server.py`.
- Start the frontend too: `cd frontend; npm run dev`.
- Screenshot-based cases need PNG fixtures in `benchmark_cases/fixtures`.
- UI result screenshots are saved under
  `benchmark_results/<module>/screenshots/`.
