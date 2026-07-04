# Security Skill Registry Analysis

Target repository: `https://github.com/charlesnobrega/Anthropic-Cybersecurity-Skills`

This document analyzes compatibility only. No integration was performed.

## Architectural Fit

Cybersecurity skills could fit as external skill definitions invoked by future leaf nodes. The current repository does not yet have a runtime skill registry, central policy engine, or safe MCP execution path, so direct integration would be premature.

Potential fit points:

- `DomainOrchestrator` could select a skill-backed leaf task in the future.
- `ToolExecutionEngine` could provide controlled execution once MCP and command policies are complete.
- `MemoryGovernanceModule` could restrict what findings and sensitive artifacts are stored.
- Observability could attach skill execution to trace ids.

## Risks

- Security tools can be dual-use and must not run without strict scope.
- Skills may request network, filesystem, shell, or scanner access.
- External skill content introduces supply-chain risk.
- Findings may contain secrets or sensitive infrastructure details.
- Unbounded execution can create legal, operational, or availability risk.

## Required Safeguards

- Disabled-by-default registry entries.
- Explicit target scope per run.
- Allowed tool list per skill.
- Network and filesystem allow-lists.
- No destructive actions unless separately approved.
- Complete audit logging of inputs, commands, outputs, and artifacts.
- Redaction rules for secrets in logs and memory.
- Human approval for active scanning, exploitation, credential testing, or persistence checks.

## Policy Requirements

Each registered skill should declare:

- `skill_id`
- source repository and commit hash
- owner
- category
- allowed operations
- denied operations
- required approvals
- network scope
- filesystem scope
- timeout and resource limits
- artifact retention policy
- rollback notes

## Execution Restrictions

Until a policy engine and registry exist, cybersecurity skills should be documentation-only. They must not be imported or executed automatically by orchestrators.

Future execution should be limited to:

- passive analysis by default
- read-only filesystem access unless approved
- no credential harvesting
- no persistence
- no exploitation outside explicitly authorized lab targets
- no external network targets without written scope

## Proposed Registry Design

```yaml
skills:
  - skill_id: cybersecurity.passive-audit
    source:
      repository: https://github.com/charlesnobrega/Anthropic-Cybersecurity-Skills
      commit: pinned-commit-required
    status: disabled
    allowed_tools:
      - file.read
      - grep
    denied_tools:
      - shell
      - web
      - file.delete
    approvals:
      required: true
      approver_role: owner
    audit:
      log_inputs: true
      log_outputs: true
      redact_secrets: true
```

## Conclusion

The external cybersecurity skills repository is conceptually compatible with Kabbalah's planned skill registry, but the current codebase is not ready for safe integration. The immediate work should be registry design, policy engine integration, and passive read-only execution constraints before any skill import or runtime invocation.
