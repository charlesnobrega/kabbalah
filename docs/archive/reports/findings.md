# Kabbalah Inspection Findings

## Initial Observations

- Repository root: `E:\projetos\kabbalah`.
- Git branch: `main`.
- Worktree is dirty with many modified tracked files and many untracked status/report/provider files.
- Project appears to be a Python package under `src/kabbalah` with tests under `tests`.
- Root contains many phase/status markdown reports, suggesting prior generated planning/status artifacts may need cleanup or consolidation.

## Structure And Hygiene

- Python package configured with `setup.py`, `requirements.txt`, and `pytest.ini`.
- README describes a large multi-agent orchestration platform with providers, memory, observability, tools, and Day 2 governance.
- Source and test trees contain many `__pycache__/*.pyc` files. They are ignored by `.gitignore`, but present locally and should not be part of a clean repository state.
- Existing audit documentation already flags placeholder/mock behavior in root orchestration, Cognee memory, and MCP tool execution.
- `requirements.txt` pins several old provider SDK versions and includes heavyweight optional systems like `cognee` as a core dependency.

## Validation Results

- `python -m compileall -q src`: passed.
- `python setup.py check`: passed.
- `python -m pip check`: passed.
- Plain `python -m pytest`: failed during collection with 23 import errors for `kabbalah`.
- `$env:PYTHONPATH='src'; python -m pytest`: collected 890 tests; 872 passed, 13 failed, 5 skipped.
- `flake8`, `black`, and `mypy` are declared as dev dependencies but are not installed in the current environment.

## Remediation Baseline 2026-04-23

- Plain `python -m pytest`: passed with 805 passed, 86 skipped, 1 warning.
- `python -m compileall -q src`: passed.
- `python setup.py check`: passed.
- `python -m pip check`: passed.
- Strong key-pattern scan across text files returned no matches after redaction.
- Live provider tests are now opt-in with `KABBALAH_RUN_LIVE_PROVIDER_TESTS=1`.
- Test-only fake provider use is guarded by `KABBALAH_ALLOW_TEST_FAKE_PROVIDER=1`.

## Major Findings

- Import/package setup is inconsistent. Tests and source mix `kabbalah.*` and `src.kabbalah.*` imports; the CLI works as `python -m kabbalah.cli` only when `PYTHONPATH=src`, while direct script execution fails.
- Core orchestration is still mostly scaffold behavior. `RootOrchestrator` emits static domain tasks, `DomainOrchestrator` returns successful empty artifacts without provider/tool execution, and `Synthesizer` consistency checks are placeholders.
- Tool execution claims sandboxing but runs shell commands with `shell=True`, path authorization uses string-prefix checks, web access defaults to all domains, and MCP execution is only a placeholder.
- Memory Cognee integration is placeholder-only. On Windows, JSONL is primary and unavailable Cognee becomes fallback, so fallback semantics are incoherent.
- Trace ID generation can create IDs that fail its own validators: domain names are not sanitized before embedding in branch/leaf IDs, and `TraceIDGenerator.generate_run_id` can exceed the 3-digit counter format.
- Day2 timestamp property fails because tests use `time.time()` while implementation uses `datetime.now().timestamp()`, producing sub-microsecond ordering drift.
- Test suite is not hermetic: provider tests load `.env` and call live APIs when credentials exist.
- Security scan found live API credentials in local `.env` and credential material embedded in generated report/status documentation. Do not commit these; rotate exposed keys.
- Documentation/status files are not reliable. Some audits call the project not production-ready, while other summaries claim zero findings or completed tasks.

## Remaining Risks

- The main orchestration path is still not real execution; it remains scaffolded even though the test baseline now passes.
- The tool execution engine still needs a real security redesign before it can be called sandboxed.
- Live provider integration evidence now requires explicit opt-in and should be run separately before claiming provider readiness.
- The local `.env` still contains working credentials; keys that appeared in reports should be rotated outside this repository.
