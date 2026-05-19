# Kabbalah Forensic Audit

Date: 2026-04-11  
Workspace audited: `e:\projetos\kabbalah`  
Method: read-only audit of the current worktree, with real test/provider execution where credentials and endpoints were already present.

## Executive Summary

This worktree is not production-ready.

The current repository state contradicts the strongest claims in `README.md` and `docs/specs/AUDIT_REPORT.md`. The main blockers are:

1. plain `pytest -q` does not even collect safely;
2. the published CLI entrypoint is broken;
3. the core orchestration path is not executable end-to-end;
4. the tool execution layer does not satisfy the roadmap/requirements for human authorization and true sandboxing;
5. the repository contains stale completion/approval documents that are observably false in the current tree.

Current measured baseline on 2026-04-11:

- `pytest -q` -> `24 errors during collection`, `40 warnings`
- `$env:PYTHONPATH='.;src'; pytest tests -q --tb=no -ra` -> `812 passed / 74 failed / 4 skipped`
- `python -m compileall src` -> passed
- `$env:PYTHONPATH='.;src'; pytest tests/providers -q` -> `132 passed / 7 failed / 2 skipped`
- `$env:PYTHONPATH='.;src'; pytest tests/integration -q` -> `36 passed`
- `$env:PYTHONPATH='.;src'; pytest tests/tools/test_execution_engine.py -q` -> `33 passed`
- `$env:PYTHONPATH='.;src'; pytest tests/observability/test_observability_module.py -q` -> `17 passed`
- `$env:PYTHONPATH='.;src'; pytest tests/test_contract_enforcement.py tests/test_contract_enforcement_properties.py -q` -> `40 passed`
- `$env:PYTHONPATH='.;src'; pytest tests/test_configuration_manager.py tests/test_day2_operations.py tests/test_memory_governance.py tests/test_memory_governance_properties.py tests/test_specification_parser.py tests/test_specification_pretty_printer.py tests/test_transition_validation.py tests/test_transition_validation_properties.py -q` -> `196 passed / 2 skipped`

The plan handed to this audit referenced an older baseline of `814 passed / 72 failed / 4 skipped`. That is not the current truth of this worktree anymore. The rerun on 2026-04-11 produced `812 / 74 / 4`, so this report treats the rerun as authoritative.

## Scope and Method

- Audited `src/`, `tests/`, `docs/specs/`, `config/`, root scripts, status artifacts, and untracked working-tree content.
- Treated `openclaude/` as a boundary/dependency audit only. No evidence was found that the Kabbalah runtime imports or executes it.
- Did not mock provider results. Real provider checks were executed only where credentials were already present.
- Did not modify runtime code. The only new artifact from this audit is this report file.

## Findings

### Blocker 1: The repository is not safely collectible or hermetic under plain pytest

Severity: `blocker`

Evidence:

- `test_gemini_debug.py:11-23` prints part of the live `GOOGLE_API_KEY` and performs a real Gemini request at import time.
- `pytest -q` fails during collection with `google.api_core.exceptions.ResourceExhausted: 429 ... quota exceeded` from `test_gemini_debug.py`.
- The same `pytest -q` run also fails with `ModuleNotFoundError: No module named 'kabbalah'` across multiple test files because the suite mixes `from kabbalah...` and `from src.kabbalah...` import styles without a working packaging/test configuration.
- No `pytest.ini`, `pyproject.toml`, or `setup.cfg` exists at the repo root, and `src/kabbalah/cli.py` is missing.
- `workspace/phase_2/*` and `workspace/phase_4/*` are also collected by plain pytest and emit unrelated collection warnings.

Expected:

- A clean `pytest -q` should collect deterministically without hitting external APIs or requiring ad hoc `PYTHONPATH` patching.

Observed:

- Collection executes live API traffic, leaks a key prefix to stdout, and fails on packaging/import drift.

Impact:

- CI, local verification, and release gating are unreliable.
- A supposedly read-only test collection can consume quota and expose credential material in logs.

Primary evidence:

- [test_gemini_debug.py](/e:/projetos/kabbalah/test_gemini_debug.py:11)
- [setup.py](/e:/projetos/kabbalah/setup.py:46)

### Blocker 2: Published production/completion claims are false in the current worktree

Severity: `blocker`

Evidence:

- `docs/specs/AUDIT_REPORT.md:5` says all `200+` tasks are completed.
- `docs/specs/AUDIT_REPORT.md:638-673` says all properties/integration/security/performance checks passed and the system is `APPROVED FOR PRODUCTION`.
- `README.md:7` describes the system as having `complete observability`.
- `README.md:51` claims support for `12+ LLM providers`.
- Current measured state on 2026-04-11 is `812 passed / 74 failed / 4 skipped` in the main `tests/` suite, and plain `pytest -q` does not collect.

Expected:

- Status reports and README claims should match the current tree.

Observed:

- Release/completion documents materially overstate the state of the codebase.

Impact:

- Any operator or reviewer relying on repository docs would be misled about safety, completeness, and releasability.

Primary evidence:

- [docs/specs/AUDIT_REPORT.md](/e:/projetos/kabbalah/docs/specs/AUDIT_REPORT.md:5)
- [docs/specs/AUDIT_REPORT.md](/e:/projetos/kabbalah/docs/specs/AUDIT_REPORT.md:638)
- [README.md](/e:/projetos/kabbalah/README.md:7)

### Blocker 3: The published CLI entrypoint is broken

Severity: `blocker`

Evidence:

- `setup.py:46-49` publishes `kabbalah=kabbalah.cli:main`.
- `src/kabbalah/cli.py` does not exist in the worktree.

Expected:

- A published console script must resolve to a real module/function.

Observed:

- The package advertises a CLI that is absent.

Impact:

- Installation exposes a dead entrypoint.
- Documentation around CLI/configuration cannot be trusted as an operable interface.

Primary evidence:

- [setup.py](/e:/projetos/kabbalah/setup.py:46)

### Blocker 4: The orchestration core is not executable end-to-end

Severity: `blocker`

Evidence:

- `src/kabbalah/root_orchestrator.py:145-155` checks dependencies using `dep in executed`, but `executed` stores `branch_id` while branch dependencies are domain names such as `backend` and `frontend`. This produces false circular dependency detection.
- `src/kabbalah/root_orchestrator.py:194-205` still returns a placeholder static task list.
- `src/kabbalah/root_orchestrator.py:274-279` raises `NotImplementedError` for actual branch execution.
- The following test groups fail as a direct consequence:
  - `tests/test_root_orchestrator.py` -> 10 failures
  - `tests/test_e2e_orchestration.py` -> 6 failures
  - `tests/test_synthesizer.py` -> 4 failures rooted in orchestration before synthesis

Expected:

- Branch execution should respect dependency semantics and perform real branch execution.

Observed:

- Dependency resolution is wrong and actual execution is explicitly unimplemented.

Impact:

- The central runtime path advertised by the project cannot be executed correctly.

Primary evidence:

- [src/kabbalah/root_orchestrator.py](/e:/projetos/kabbalah/src/kabbalah/root_orchestrator.py:145)
- [src/kabbalah/root_orchestrator.py](/e:/projetos/kabbalah/src/kabbalah/root_orchestrator.py:194)
- [src/kabbalah/root_orchestrator.py](/e:/projetos/kabbalah/src/kabbalah/root_orchestrator.py:274)

### Blocker 5: Tool execution violates the roadmap rule for human approval and does not deliver true sandboxing

Severity: `blocker`

Evidence:

- `docs/specs/NEXT_GEN_ROADMAP.md:11-12` explicitly forbids mock execution and requires express human authorization for any filesystem, infrastructure, code-generation, or external API action.
- `docs/specs/NEXT_GEN_ROADMAP.md:37` explicitly says terminal operations must pause and request approval before execution.
- `docs/specs/requirements.md:214-216` requires tool execution in a sandboxed environment with restricted permissions and violation logging.
- `src/kabbalah/tools/execution_engine.py:477-483` executes shell commands with `subprocess.run(..., shell=True, ...)`.
- `src/kabbalah/tools/execution_engine.py:606-617` performs direct file writes and deletes.
- `src/kabbalah/tools/execution_engine.py:781-787` performs direct outbound HTTP requests.
- `src/kabbalah/tools/execution_engine.py:830-842` leaves MCP execution as a placeholder.
- No approval/authorization gate was found in `src/kabbalah` for mutable or external tool actions.

Expected:

- Mutating/external actions should require explicit human approval and run inside an actually restricted sandbox boundary.

Observed:

- The engine enforces some allowlists and tests pass for those local rules, but it still runs direct shell/file/network operations without human gating or OS-level sandbox evidence.

Impact:

- The implementation does not meet the roadmap/requirements for safe execution.

Primary evidence:

- [docs/specs/NEXT_GEN_ROADMAP.md](/e:/projetos/kabbalah/docs/specs/NEXT_GEN_ROADMAP.md:11)
- [docs/specs/requirements.md](/e:/projetos/kabbalah/docs/specs/requirements.md:214)
- [src/kabbalah/tools/execution_engine.py](/e:/projetos/kabbalah/src/kabbalah/tools/execution_engine.py:477)

### High 6: IntakeNode violates caller intent and fails common property cases

Severity: `high`

Evidence:

- `src/kabbalah/intake_node.py:126-132` uses `or` when handling `scope`, `constraints`, and `resources`.
- Empty-but-valid values such as `constraints=[]` and `resources={}` are replaced by defaults, breaking preservation semantics.
- `_infer_scope()` can return an empty string for minimal descriptions such as `"."`, and `_validate_specification()` then rejects the spec at `src/kabbalah/intake_node.py:276-277`.
- `created_at` uses `datetime.utcnow().timestamp()` at `src/kabbalah/intake_node.py:150`, which caused precision/timing assertions to fail in property tests on this environment.
- Failures caused or amplified by this defect appear in:
  - `tests/test_intake_node.py` -> 6 failures
  - `tests/test_specification_properties.py` -> 10 failures
  - `tests/test_domain_orchestrator.py::test_leaf_ids_are_unique` -> falsifies on empty inferred scope
  - part of `tests/test_e2e_orchestration.py`

Expected:

- Explicit empty values should be preserved when semantically valid, and scope inference should not collapse to invalid empty strings.

Observed:

- Minimal-but-valid inputs are coerced or rejected incorrectly.

Primary evidence:

- [src/kabbalah/intake_node.py](/e:/projetos/kabbalah/src/kabbalah/intake_node.py:126)
- [src/kabbalah/intake_node.py](/e:/projetos/kabbalah/src/kabbalah/intake_node.py:150)
- [src/kabbalah/intake_node.py](/e:/projetos/kabbalah/src/kabbalah/intake_node.py:276)

### High 7: Trace/run ID contracts drift from their own tests and can overflow the documented format

Severity: `high`

Evidence:

- `src/kabbalah/trace_id_tracking.py:77-81` uses `zfill(3)` but does not cap width, so daily run IDs become `run_YYYY_MM_DD_1000+`, which violates the validator regex.
- `src/kabbalah/trace_id_tracking.py:211-223` validates a fixed `..._NNN` pattern for run and branch IDs.
- `src/kabbalah/trace_id_tracking.py:20-33` makes `ExecutionLogEntry.duration` mandatory, while tests expect default derivation from `start_time` and `end_time`.
- Current failing suites:
  - `tests/test_trace_id_tracking.py` -> 2 failures
  - `tests/test_trace_id_tracking_properties.py` -> 8 failures

Important nuance:

- Not every failure here is a runtime bug. At least one test is wrong: `tests/test_trace_id_tracking.py::test_generate_run_id_format` asserts `len(parts) == 4` after splitting a valid `run_YYYY_MM_DD_NNN`, which actually has 5 underscore-separated parts.
- The runtime still has real contract drift: overflow past `999`, strict regex mismatch, and `ExecutionLogEntry` constructor mismatch.

Primary evidence:

- [src/kabbalah/trace_id_tracking.py](/e:/projetos/kabbalah/src/kabbalah/trace_id_tracking.py:20)
- [src/kabbalah/trace_id_tracking.py](/e:/projetos/kabbalah/src/kabbalah/trace_id_tracking.py:77)
- [src/kabbalah/trace_id_tracking.py](/e:/projetos/kabbalah/src/kabbalah/trace_id_tracking.py:211)

### High 8: Memory fallback behavior is not coherent and Cognee integration is still a placeholder

Severity: `high`

Evidence:

- `src/kabbalah/memory_subsystem.py:73-75` explicitly marks Cognee initialization as placeholder.
- `src/kabbalah/memory_subsystem.py:92-109` leaves Cognee store/query as placeholder and returns an empty result set on query.
- `src/kabbalah/memory_subsystem.py:257-258` always creates both backends.
- `src/kabbalah/memory_subsystem.py:375-384` requires both primary and fallback backends to be consistent.
- On this Windows environment where Cognee is unavailable, `ensure_consistency()` fails even when JSONL is healthy.
- Current failing suites:
  - `tests/test_memory_subsystem.py` -> 2 failures
  - `tests/test_memory_subsystem_properties.py` -> 5 failures

Expected:

- When Cognee is unavailable, JSONL fallback should remain available and sufficient, per `docs/specs/requirements.md:282`.

Observed:

- Fallback availability and consistency semantics are inverted or over-constrained.

Primary evidence:

- [src/kabbalah/memory_subsystem.py](/e:/projetos/kabbalah/src/kabbalah/memory_subsystem.py:73)
- [src/kabbalah/memory_subsystem.py](/e:/projetos/kabbalah/src/kabbalah/memory_subsystem.py:100)
- [src/kabbalah/memory_subsystem.py](/e:/projetos/kabbalah/src/kabbalah/memory_subsystem.py:375)

### High 9: RoleTraceValidation denies trace propagation for Intake even though the suite/spec expect universal propagation

Severity: `high`

Evidence:

- `src/kabbalah/role_trace_validation.py:72-77` does not grant `PROPAGATE_TRACE` to `CanonicalRole.INTAKE_CLARIFIER`.
- `src/kabbalah/role_trace_validation.py:260-269` raises `ValueError` when propagation is not permitted.
- Current failing suites:
  - `tests/test_role_trace_validation.py` -> 1 failure
  - `tests/test_role_trace_validation_properties.py` -> 7 failures

Expected:

- Either the implementation or the public contract must be authoritative. Right now they disagree.

Observed:

- Intake propagation is blocked in code while tests/documented intent treat propagation as universally allowed.

Primary evidence:

- [src/kabbalah/role_trace_validation.py](/e:/projetos/kabbalah/src/kabbalah/role_trace_validation.py:72)
- [src/kabbalah/role_trace_validation.py](/e:/projetos/kabbalah/src/kabbalah/role_trace_validation.py:260)

### High 10: Google Gemini integration is degraded in both implementation and live validation

Severity: `high`

Evidence:

- `src/kabbalah/providers/google_gemini_provider.py:10` still imports deprecated `google.generativeai`.
- Live execution produced real `429 quota exceeded` responses on 2026-04-11.
- `tests/providers/test_google_gemini_provider.py` -> 7 failures / 8 passes.
- `tests/providers/test_google_gemini_provider.py::test_execute_request_records_stats` failed because provider stats were not incremented after an error response.
- `src/kabbalah/providers/factory.py:101-103` derives API keys as `{PROVIDER_NAME}_API_KEY`, which implies `GOOGLE_GEMINI_API_KEY` for the Gemini provider, but `src/kabbalah/providers/google_gemini_provider.py:57-61` actually expects `GOOGLE_API_KEY`.
- `tests/providers/test_openai_provider.py -q` passed `15/15`, so this is not a generalized provider harness failure.

Expected:

- Provider env var contracts, dependency stack, and stats behavior should be internally consistent.

Observed:

- Gemini is using deprecated SDKs, hits real quota failure, and loses accounting information on error paths.

Primary evidence:

- [src/kabbalah/providers/google_gemini_provider.py](/e:/projetos/kabbalah/src/kabbalah/providers/google_gemini_provider.py:10)
- [src/kabbalah/providers/google_gemini_provider.py](/e:/projetos/kabbalah/src/kabbalah/providers/google_gemini_provider.py:57)
- [src/kabbalah/providers/factory.py](/e:/projetos/kabbalah/src/kabbalah/providers/factory.py:101)

### Medium 11: Synthesizer rejects successful executions with zero artifacts

Severity: `medium`

Evidence:

- `src/kabbalah/synthesizer.py:147-148` rejects empty artifact collections outright.
- `src/kabbalah/synthesizer.py:225-248` wraps that failure inside `generate_delivery_package()`.
- `tests/test_synthesizer.py` shows two independent issue classes:
  - 2 failures are true synthesizer contract failures when successful `BranchResult` objects contain `artifacts=[]`;
  - 4 failures are inherited from `RootOrchestrator.execute_branches()`.

Expected:

- A delivery package generator should be able to produce reports/trace metadata for successful branches even when the artifact set is empty.

Observed:

- Synthesis fails on an empty artifact map even for otherwise valid success results.

Primary evidence:

- [src/kabbalah/synthesizer.py](/e:/projetos/kabbalah/src/kabbalah/synthesizer.py:147)
- [src/kabbalah/synthesizer.py](/e:/projetos/kabbalah/src/kabbalah/synthesizer.py:225)

### Medium 12: FSM/DAY2 enforcement has an API/behavior split and a timestamp precision edge

Severity: `medium`

Evidence:

- `docs/specs/requirements.md:76-84` requires blocked DAY2 bootstrap operations to be logged with immutable audit records.
- `src/kabbalah/fsm_enforcement.py:156-172` makes `check_operation_allowed()` return a boolean without logging.
- Logging only happens in `check_operation_allowed_with_logging()`.
- `tests/test_day2_enforcement_properties.py` shows:
  - 1 failure because blocked operations are not logged when callers use `check_operation_allowed()`;
  - 1 failure because timestamp precision is marginally outside the measured `[before, after]` window.
- `src/kabbalah/day2_operations.py:294-304` also exposes `clear_audit_log()`, explicitly noting it `breaks immutability`.

Expected:

- The public enforcement path should not silently skip required logging, and immutable audit guarantees should not include a public log-clear primitive in normal runtime code.

Observed:

- Required logging depends on which method the caller chooses, and audit immutability is not absolute.

Primary evidence:

- [docs/specs/requirements.md](/e:/projetos/kabbalah/docs/specs/requirements.md:76)
- [src/kabbalah/fsm_enforcement.py](/e:/projetos/kabbalah/src/kabbalah/fsm_enforcement.py:156)
- [src/kabbalah/day2_operations.py](/e:/projetos/kabbalah/src/kabbalah/day2_operations.py:294)

### Medium 13: Public configuration surface is fragmented and misleading

Severity: `medium`

Evidence:

- `README.md:119-127` documents `KABBALAH_PROVIDER`, `KABBALAH_MODEL`, and `KABBALAH_INTAKE_PROVIDER`.
- `src/kabbalah/configuration_manager.py:134-150` loads `KABBALAH_MODE`, `KABBALAH_ENV`, `KABBALAH_LOG_LEVEL`, and `KABBALAH_DEFAULT_PROVIDER`.
- `src/kabbalah/providers/config.py:57-71` loads `KABBALAH_PROVIDER_MODE`, `KABBALAH_DEFAULT_PROVIDER`, and role vars for `orchestrator/analyzer/executor/validator/synthesizer`.
- This role naming does not match the README examples (`INTAKE`, `LEAF_VERIFIER`, etc.).
- `src/kabbalah/configuration_manager.py:82-85` claims CLI argument support, but the implementation only exposes `set_config()` marking values as `ConfigurationSource.CLI`; no actual CLI parser or entrypoint exists.

Expected:

- One documented, executable configuration contract.

Observed:

- Docs, provider config, and general config disagree on variable names, roles, and entry surfaces.

Impact:

- Operators can configure the system “correctly” according to docs and still hit the wrong code path.

Primary evidence:

- [README.md](/e:/projetos/kabbalah/README.md:119)
- [src/kabbalah/configuration_manager.py](/e:/projetos/kabbalah/src/kabbalah/configuration_manager.py:134)
- [src/kabbalah/providers/config.py](/e:/projetos/kabbalah/src/kabbalah/providers/config.py:57)

### Medium 14: `openclaude/` is not part of the runtime, but the embedded boundary is high-risk clutter

Severity: `medium`

Evidence:

- `openclaude/` contains git internals such as `HEAD`, `FETCH_HEAD`, `index`, `packed-refs`, `objects/`, `refs/`, plus its own project files.
- Search across `src/`, `tests/`, `README.md`, and `setup.py` found no runtime import/execution path for `openclaude`.

Expected:

- Embedded external code should either be clearly vendored and wired into runtime, or excluded from operational workspaces.

Observed:

- The directory behaves like bundled upstream state rather than an integrated dependency.

Impact:

- Increases audit surface, repository weight, and accidental leakage/supply-chain ambiguity.

### Low 15: Documentation hygiene is poor and contains obviously placeholder content

Severity: `low`

Evidence:

- `README.md:348` points support to `support@example.com`.
- `README.md` still advertises Anthropic in examples, but the provider package exports only six real providers plus `MockProvider`.
- `docs/specs/AUDIT_REPORT.md` continues to describe a fully complete provider matrix that does not exist in `src/kabbalah/providers/__init__.py` or `src/kabbalah/providers/factory.py`.

Primary evidence:

- [README.md](/e:/projetos/kabbalah/README.md:348)
- [src/kabbalah/providers/__init__.py](/e:/projetos/kabbalah/src/kabbalah/providers/__init__.py:18)
- [src/kabbalah/providers/factory.py](/e:/projetos/kabbalah/src/kabbalah/providers/factory.py:49)

### Low 16: Mock provider is still part of the public provider surface

Severity: `low`

Evidence:

- `src/kabbalah/providers/__init__.py:14-31` exports `MockProvider`.
- `docs/specs/NEXT_GEN_ROADMAP.md:11` prohibits mocked runtime behavior.

Assessment:

- This is not a blocker by itself because current `root_orchestrator.py` now fails fast instead of silently simulating execution.
- It is still a governance mismatch: a public mock provider remains in the primary abstraction layer of a project whose roadmap now forbids mock runtime behavior.

### Low 17: Part of the failing suite is a test defect, not a runtime defect

Severity: `low`

Evidence:

- `tests/test_trace_id_tracking.py::test_generate_run_id_format` asserts `len(parts) == 4` after splitting `run_YYYY_MM_DD_NNN`, but that string has 5 underscore-separated parts.
- Some property strategies in trace/branch tests generate identifiers that violate the runtime's own validator regex, so a subset of failures are suite-side contract drift.
- This does not cancel the runtime defects already documented above; it means the suite itself also needs maintenance.

## Dynamic Verification Log

Commands executed during this audit:

```powershell
pytest -q
$env:PYTHONPATH='.;src'; pytest tests -q --tb=no -ra
python -m compileall src
$env:PYTHONPATH='.;src'; pytest tests/providers -q
$env:PYTHONPATH='.;src'; pytest tests/providers/test_openai_provider.py -q
$env:PYTHONPATH='.;src'; pytest tests/providers/test_google_gemini_provider.py -q
$env:PYTHONPATH='.;src'; pytest tests/integration -q
$env:PYTHONPATH='.;src'; pytest tests/tools/test_execution_engine.py -q
$env:PYTHONPATH='.;src'; pytest tests/observability/test_observability_module.py -q
$env:PYTHONPATH='.;src'; pytest tests/test_contract_enforcement.py tests/test_contract_enforcement_properties.py -q
$env:PYTHONPATH='.;src'; pytest tests/test_configuration_manager.py tests/test_day2_operations.py tests/test_memory_governance.py tests/test_memory_governance_properties.py tests/test_specification_parser.py tests/test_specification_pretty_printer.py tests/test_transition_validation.py tests/test_transition_validation_properties.py -q
```

Live provider/environment observations:

- API keys detected as present: `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `GROQ_API_KEY`, `TOGETHER_API_KEY`, `DEEPSEEK_API_KEY`, `MISTRAL_API_KEY`
- API keys detected as absent: `ANTHROPIC_API_KEY`
- Base URL detected as absent: `OLLAMA_BASE_URL`
- OpenAI targeted provider tests passed.
- Gemini targeted provider tests hit real quota exhaustion and also exposed an implementation-side stats bug.

## Failure Buckets

This is the 2026-04-11 mapping of the current `74` failures in `$env:PYTHONPATH='.;src'; pytest tests -q --tb=no -ra`:

| Bucket | Affected tests/files | Notes |
| --- | --- | --- |
| Intake/spec generation contract drift | `tests/test_intake_node.py`, `tests/test_specification_properties.py`, part of `tests/test_domain_orchestrator.py`, part of `tests/test_e2e_orchestration.py` | Empty values overwritten, empty inferred scope, timestamp sensitivity |
| Root orchestration defects | `tests/test_root_orchestrator.py`, part of `tests/test_e2e_orchestration.py`, part of `tests/test_synthesizer.py` | Dependency comparison bug plus explicit `NotImplementedError` path |
| Memory fallback / placeholder integration | `tests/test_memory_subsystem.py`, `tests/test_memory_subsystem_properties.py` | Cognee placeholder and incorrect consistency/fallback semantics |
| Role permission mismatch | `tests/test_role_trace_validation.py`, `tests/test_role_trace_validation_properties.py` | Intake cannot propagate traces in code |
| Trace/log contract drift | `tests/test_trace_id_tracking.py`, `tests/test_trace_id_tracking_properties.py` | Mix of real runtime defects and test defects |
| Live Gemini dependency + provider bug | `tests/providers/test_google_gemini_provider.py` | Real 429 quota plus stats/accounting bug |
| DAY2 enforcement behavior drift | `tests/test_day2_enforcement_properties.py` | Missing logging on one public path and timestamp precision edge |
| Synthesizer contract drift | subset of `tests/test_synthesizer.py` | Empty artifact collections incorrectly rejected |

## Modules That Held Up Under Targeted Verification

The audit was not uniformly negative. These modules/suites were stable under targeted execution:

- `contract_enforcement` -> `40 passed`
- `observability` -> `17 passed`
- `configuration_manager`, `day2_operations`, `memory_governance`, `specification_parser`, `specification_pretty_printer`, `transition_validation` -> `196 passed / 2 skipped`
- `tools/execution_engine` -> `33 passed`
- `tests/integration` -> `36 passed` when `PYTHONPATH` is manually fixed
- OpenAI provider targeted suite -> `15 passed`

Important caution:

- Passing local tests for `execution_engine` do not prove compliance with the roadmap requirement for human approval and hard sandboxing. They prove only the narrower behavior currently encoded by the suite.

## Spec / Docs / Tests / Code Matrix

| Area | Spec / docs claim | Code / runtime reality | Status |
| --- | --- | --- | --- |
| CLI | Package advertises CLI entrypoint | `kabbalah.cli` is missing | False |
| `run_id` format | `run_YYYY_MM_DD_NNN` | Generated in that shape initially, but not bounded past `999`; tests and validators drift | Partially confirmed |
| `branch_id` / `leaf_id` / `trace_id` | Hierarchical IDs throughout orchestration | Generators exist, but orchestration path fails before end-to-end guarantees hold | Partially confirmed |
| Provider matrix | README/specs claim `12+` providers | Runtime exports 6 real providers plus `MockProvider` | False |
| Provider config | README examples show `KABBALAH_PROVIDER`, `KABBALAH_MODEL`, per-role envs like `KABBALAH_INTAKE_PROVIDER` | Actual code expects different env names and role labels | False |
| Memory fallback | Requirements say automatic fallback when Cognee unavailable | Current consistency/fallback semantics fail on unavailable Cognee | False |
| Tool sandboxing | Requirements/roadmap require sandbox + approval | Current engine runs direct shell/file/network operations without human approval gate | False |
| Observability | README claims complete observability | Observability module itself tested well, but global release claim is overstated | Partially confirmed |
| Audit immutability | Requirements say immutable DAY2 audit log | `clear_audit_log()` exists and explicitly breaks immutability | False |
| No mocks in runtime | Roadmap forbids runtime mocking | Root orchestrator now fails fast instead of silently mocking, but `MockProvider` remains public | Partially confirmed |

## Claim Matrix

| Claim | Evidence | Status |
| --- | --- | --- |
| "All 200+ tasks complete" | `docs/specs/AUDIT_REPORT.md:5`, current suite still `74` failing tests and broken collection | False |
| "APPROVED FOR PRODUCTION" | `docs/specs/AUDIT_REPORT.md:671-673`, broken CLI, broken orchestration, unsafe test collection | False |
| "Support for 12+ LLM providers" | README/docs vs `src/kabbalah/providers/factory.py:49-55` and `__init__.py:18-31` | False |
| "CLI available" | `setup.py:48` vs missing `src/kabbalah/cli.py` | False |
| "Sandboxing" | Requirements/roadmap vs `execution_engine.py` direct shell/file/network calls | False |
| "Complete observability" | Observability tests pass, but system-level release claim is still overstated | Partially confirmed |
| "All tests passing" | Measured results contradict this | False |
| "Integration tests all passing" | `tests/integration -q` passes with manual `PYTHONPATH`, but plain pytest collection is broken | Partially confirmed |

## Recommended Remediation Backlog

Fix order matters. The current dependency chain should be treated as:

1. Stop unsafe collection.
   - Remove or rename root debug scripts like `test_gemini_debug.py` so they are not collected by pytest.
   - Add a real project test config (`pyproject.toml` or `pytest.ini`) and limit discovery to supported test roots.
   - Unify import style to either installed package imports or `src`-layout config, not both.

2. Repair published packaging surface.
   - Either implement `src/kabbalah/cli.py` with a real `main()` or remove the console script from `setup.py`.

3. Fix `IntakeNode` contract handling.
   - Preserve explicit empty lists/dicts.
   - Make scope inference non-empty or fail earlier with a clearer contract.
   - Normalize timestamp semantics used by properties.

4. Make `RootOrchestrator` executable.
   - Resolve dependencies against the right identifier domain.
   - Replace placeholder task extraction.
   - Replace `NotImplementedError` branch execution with actual provider-backed logic.

5. Enforce the roadmap on mutable/external operations.
   - Add human approval gates before shell/file/network/infra actions.
   - Replace "sandbox" claims with enforceable isolation or downgrade the documentation immediately.

6. Repair trace/logging contracts.
   - Decide whether IDs are fixed-width forever or variable-width after overflow.
   - Align validators, generators, and test expectations.
   - Decide whether `ExecutionLogEntry.duration` is explicit or derived, then enforce one contract.

7. Repair memory fallback semantics.
   - Make JSONL fallback truly available when Cognee is absent.
   - Remove placeholder success semantics from unavailable backends.
   - Rework consistency checks so a missing optional backend does not poison healthy storage.

8. Align role permissions with the intended trace contract.
   - Either allow Intake trace propagation or rewrite specs/tests/docs to the stricter model.

9. Repair Gemini integration.
   - Migrate from deprecated `google.generativeai`.
   - Align env var naming between provider factory and provider implementation.
   - Record provider stats on error paths as well as success paths.

10. Delete or rewrite stale status reports.
    - `docs/specs/AUDIT_REPORT.md` and all "final/complete/approved" reports should be treated as untrusted until regenerated from actual verification.

## Final Assessment

The codebase contains real working islands: observability, contract enforcement, parts of configuration, transition validation, and several provider integrations are materially implemented and testable. But the repository, as a whole, is currently in a contradictory state: some subsystems are solid, while the top-level operational story presented by the docs is false.

The most dangerous gap is governance drift: the codebase claims completion, safety, sandboxing, and production readiness while the current tree still contains unsafe test collection, a broken CLI, unimplemented orchestration paths, and no enforceable human-approval gate for mutable/external execution.
