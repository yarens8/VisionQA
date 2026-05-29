Benchmark Screenshot Fixtures
=============================

Some benchmark cases use uploaded screenshots instead of live URLs. Put those
PNG files in this directory before running the full benchmark suite.

Expected fixture files:

- `toolsqa_home.png`
- `dense_dashboard.png`
- `saucedemo_login.png`

If a fixture is missing, `scripts/run_benchmark_suite.py` marks only that case
as `skipped` and still writes the benchmark summary tables.
