# Kabbalah Project Inspection Plan

Goal: inspect and evaluate the whole project with emphasis on structure, correctness, tests, security, maintainability, and readiness.

## Phases

1. Complete - Map repository structure, stack, dependencies, and current Git state.
2. Complete - Inspect core source modules, tests, documentation, and configuration.
3. Complete - Run validation commands available in the project.
4. Complete - Record findings, risks, and project assessment.

## Remediation Milestone 1

Goal: establish a safer, repeatable baseline without mocked runtime evidence.

1. Complete - Redact detected API keys from report/status documentation.
2. Complete - Add explicit no-mock-runtime policy.
3. Complete - Guard `MockProvider` behind `KABBALAH_ALLOW_TEST_FAKE_PROVIDER=1`.
4. Complete - Skip live provider tests by default unless `KABBALAH_RUN_LIVE_PROVIDER_TESTS=1`.
5. Complete - Fix pytest import path configuration and package imports in runtime modules.
6. Complete - Fix remaining property-test failures in FSM timestamps, memory fallback semantics, and trace ID validation.
7. Complete - Re-run validation baseline.

## Errors Encountered

| Error | Attempt | Resolution |
|---|---|---|
| Plain `python -m pytest` failed collection with `ModuleNotFoundError: No module named 'kabbalah'` | Ran suite without environment overrides | Reproduced; confirmed `PYTHONPATH=src` allows collection and execution. Root cause is import/path packaging configuration. |
| Full test suite with `PYTHONPATH=src` failed | Ran `$env:PYTHONPATH='src'; python -m pytest` | Captured current baseline: 872 passed, 13 failed, 5 skipped. |
| Quality tools unavailable | Checked `flake8`, `black`, and `mypy` packages | Tools declared in project metadata are not installed in current Python environment. |
| Full suite failed after initial remediation with one FSM timestamp assertion | Ran plain `python -m pytest` | Aligned test clock with implementation clock; suite now passes. |
