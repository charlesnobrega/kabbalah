# Kabbalah v2 - Notes for the Next Update

Date: 2026-06-26

## Scope

These notes capture implementation findings that should be reviewed after the
current "implement as documented" pass. They are not blockers for the current
implementation.

## Security clarification required: `qlipot`

The source document describes the module as a fallback for false refusals and
legitimate requests that were poorly phrased by non-technical users. That goal
is valid and was implemented as safe intent recovery:

- recover legitimate low-risk intent;
- route uncertain requests to dialogue/HITL;
- block critical-risk requests;
- keep an audit log of recovery decisions.

The document also uses wording around guardrail contour/bypass. That wording
needs explicit clarification from the responsible cybersecurity team before
any provider-routing or refusal-recovery logic is expanded beyond safe intent
recovery.

Questions for cybersecurity:

1. What specific false-positive scenarios motivated the guardrail-contour wording?
2. Which requests are considered legal/legitimate but commonly blocked by upstream models?
3. What audit evidence must be captured before retrying a refused request?
4. Should recovery be limited to rephrasing into technical language, or may it choose a different approved provider?
5. What are the hard-stop categories where recovery must never be attempted?

## Implementation improvements to evaluate

- Replace keyword-based risk scoring in `TradutorLocal` and `FirewallMCP` with a policy-backed classifier.
- Persist HITL and firewall audit decisions in the existing trace execution log.
- Add typed adapters for real MCP clients instead of only authorizing requests.
- Define a formal schema for `translation_info` in `Specification`.
- Add operational UI or ticket workflow for HITL instead of injected callback only.
- Add Bitwarden item/field naming conventions for `CofreBitwarden`.
- Add provider health checks and live capability discovery to `LLMGateway`.
- Define federation conflict-resolution rules for `SyncHub`.

## Current intentional constraint

`Qlipot` does not implement guardrail evasion. It implements audited safe intent
recovery and blocks high-risk requests while the cybersecurity clarification is
pending.
