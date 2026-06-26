# ADR-002: Provider Abstraction

## Context

The provider package defines `BaseProvider`, `ProviderResponse`, provider adapters, `ProviderFactory`, and configuration modes. The README advertises more providers than the factory currently supports.

## Decision

Treat `BaseProvider` and `ProviderFactory` as the canonical provider abstraction. Documentation must state the implemented provider set accurately.

## Rationale

The abstraction is already tested and supports multiple providers. Correcting claims is safer than introducing a new abstraction or pretending unimplemented providers exist.

## Consequences

- Current provider support is `openai`, `google_gemini`, `groq`, `mistral`, `together`, and `deepseek`.
- Additional providers require explicit adapter implementation, tests, configuration, and cost accounting.
- Mock provider usage remains test-only and gated.

## Alternatives Considered

- Direct SDK calls from orchestrators: rejected because it bypasses provider governance.
- Plugin-based provider loading now: useful later, but unnecessary before the current provider factory is wired into orchestration.
