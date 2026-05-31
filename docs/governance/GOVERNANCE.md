# Governance

## Execution Policies

- Runtime actions must be traceable to a `run_id`, `branch_id`, or `leaf_id` when they occur inside orchestration.
- Leaf execution must not silently simulate success. Missing provider/tool capability must fail explicitly.
- Production execution must pass FSM, role, contract, and Day 2 checks.
- Test-only fakes require explicit test gates such as `KABBALAH_ALLOW_TEST_FAKE_PROVIDER=1`.

## Tool Access Policies

- Shell commands require explicit allow-listing in production profiles.
- File operations must be constrained to approved workspace paths.
- File deletion must require an approval model and audit record.
- Network access must use explicit domain allow-lists; wildcard access is development-only.
- MCP tools must not execute until a configured client, policy checks, and audit logging exist.

## Security Model

- Secrets must not be committed.
- Provider keys should be read from a secrets vault or environment variables, never from source files.
- Security-sensitive skills must be registered as disabled by default.
- Tool execution must record command, arguments, actor, trace id, result, and rollback metadata where applicable.

## Rollback Model

- Every production-affecting action must have a documented rollback path.
- Changes should be small enough to revert with a single commit when possible.
- Destructive operations must include a backup or snapshot strategy before execution.

## Approval Model

- Documentation-only changes can use standard PR review.
- Runtime behavior changes require tests and owner review.
- Provider/tool/security changes require explicit security review.
- External skill integration requires approval for registry entry, sandbox limits, and execution scope.

## Audit Requirements

- PRs must describe implementation status honestly: implemented, partial, prototype, documentation only, or abandoned.
- PRs that add execution capability must include tests and policy impact notes.
- Release candidates must include a current recovery/status report.
