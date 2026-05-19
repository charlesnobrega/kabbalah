# No Mock Runtime Policy

Kabbalah runtime code must not fabricate provider, tool, memory, or orchestration results and present them as real execution.

## Rules

- Runtime provider paths must call a real configured provider or fail explicitly.
- Runtime tool paths must execute the requested tool or return a real execution error.
- Runtime memory paths must store/query a real backend or return a real backend failure.
- Test fakes are allowed only inside the automated test suite and only when explicitly enabled.
- Fake/test-only results must never be used as evidence that a real provider or integration works.

## Current Enforcement

- `MockProvider` is blocked unless `KABBALAH_ALLOW_TEST_FAKE_PROVIDER=1` is set.
- Live provider tests are skipped by default and require `KABBALAH_RUN_LIVE_PROVIDER_TESTS=1`.

## Operational Guidance

Use deterministic test fakes only to test local control flow, validation, and error handling. Use live provider tests for integration evidence, with real credentials supplied intentionally by the operator.
