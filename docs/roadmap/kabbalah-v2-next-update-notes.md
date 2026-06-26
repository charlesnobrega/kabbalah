# Kabbalah v2 - Notes for the Next Update

Date: 2026-06-26

## Scope

These notes capture implementation findings that should be reviewed after the
current "implement as documented" pass. They are not blockers for the current
implementation.

## Security clarification received: `qlipot`

The source document describes the module as a fallback for false refusals and
legitimate requests that were poorly phrased by non-technical users. That goal
is valid and was implemented as safe intent recovery:

- receive a request that was refused by the LLM;
- analyze whether the refusal is a false positive;
- if false positive, reformulate the request technically and retry with the same LLM;
- route uncertain requests to dialogue/HITL;
- block real critical-risk requests (`risk > 0.95`) without retrying;
- keep an audit log of recovery decisions.

The original document used wording around guardrail contour/bypass. That wording
was confirmed as unfortunate wording for AI interpretation. The intended meaning
is not evasion; it is correction of LLM misinterpretation when the local/system
risk layer has already classified the request as legitimate.

Follow-up questions for cybersecurity/product hardening:

1. Which false-positive scenarios should become regression tests?
2. What audit evidence must be captured before retrying a refused request?
3. Which risk signals should force dialogue/HITL instead of retry?
4. Which categories should remain hard-stop, with no recovery attempt?

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
recovery for LLM false positives and blocks high-risk requests.
