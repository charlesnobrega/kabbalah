# Kabbalah Inspection Progress

## 2026-04-23

- Started broad project inspection requested by user.
- Checked root directory, Git status, and repository file list.
- Created `task_plan.md`, `findings.md`, and `progress.md` to track the audit.
- Read README, setup, requirements, pytest config, config example, `.gitignore`, source/test file inventory, TODO/placeholder scan, and Git diff stat.
- Read core orchestrator, domain orchestrator, intake, synthesizer, providers, configuration, memory, observability, CLI, and tool execution modules.
- Ran validation commands: pytest without overrides, pytest with `PYTHONPATH=src`, targeted failing tests, compileall, setup check, pip check, CLI smoke checks, and security/hygiene scans.
- Confirmed current project assessment: not production-ready; closer to an expanded prototype/scaffold with useful tests but severe packaging, security, and runtime-realism gaps.
- Completed inspection and prepared final user-facing assessment.

## Remediation Milestone 1

- Redacted detected API keys from generated report/status docs.
- Added no-mock-runtime policy at `docs/specs/NO_MOCK_RUNTIME_POLICY.md`.
- Added runtime guard to `MockProvider`; it now requires `KABBALAH_ALLOW_TEST_FAKE_PROVIDER=1`.
- Added provider test collection control; live provider tests require `KABBALAH_RUN_LIVE_PROVIDER_TESTS=1`.
- Removed `.env` loading from provider config/factory tests and replaced real-key usage with explicit test keys where no network call is made.
- Fixed `pytest.ini` pythonpath syntax and changed runtime imports from `src.kabbalah` to `kabbalah`.
- Fixed FSM timestamp tests by using the same clock source as implementation.
- Fixed trace ID validation/generation for sanitized domains and counters greater than 999.
- Fixed memory fallback semantics and property tests to respect update-by-`knowledge_id` behavior.
- Validation: `python -m pytest` passed with 805 passed, 86 skipped, 1 warning.
- Validation: `python -m compileall -q src`, `python setup.py check`, and `python -m pip check` passed.
- Security scan: strong API-key pattern scan returned no matches after redaction.
- Updated README setup instructions to install the package editable and use `kabbalah config --show`.
