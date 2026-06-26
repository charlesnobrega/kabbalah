# Repository Structure

This document defines the intended documentation layout for the repository.

## Code

- `src/kabbalah/`: canonical Python package.
- `tests/`: canonical test suite.
- `config/`: example configuration.

The legacy top-level `kabbalah/` directory should be treated as historical until explicitly reconciled. Do not delete it without a dedicated migration PR.

## Documentation

- `docs/specs/`: audits, recovery reports, implementation status, and detailed technical specifications.
- `docs/adr/`: Architecture Decision Records.
- `docs/architecture/`: stable architecture maps and structure guides.
- `docs/governance/`: execution, security, approval, rollback, and audit policy.
- `docs/development/`: local development and git workflow.
- `docs/roadmap/`: forward-looking plans that do not claim implementation.
- `docs/audit/`: historical and forensic audits.
- `docs/updates/`: historical update logs.

## Root Documents

Root-level markdown files should be minimized over time. Keep only documents that help a new contributor immediately:

- `README.md`
- `CONTRIBUTING.md`
- `LICENSE`
- setup and packaging files

Historical phase reports should be moved or indexed in a future documentation cleanup PR, not deleted in this branch.
