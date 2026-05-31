# Git Workflow

## Branches

- `main`: protected stable branch. No direct pushes.
- `develop`: integration branch for tested work before release hardening.
- `feature/*`: new capabilities.
- `fix/*`: defect fixes.
- `docs/*`: documentation-only work.
- `chore/*`: maintenance and repository organization.

## Pull Request Rules

- Open PRs against `develop` unless the repository owner explicitly chooses `main`.
- Keep PRs focused and reversible.
- Include a summary, risk notes, tests run, and rollback notes.
- Do not merge a PR that claims implementation without code/tests supporting the claim.

## Commit Rules

- Prefer small commits grouped by concern.
- Use clear prefixes such as `docs:`, `chore:`, `fix:`, `feat:`, and `test:`.
- Do not mix large refactors with behavior changes.
- Do not commit secrets, generated caches, virtual environments, or local logs.

## Rollback Strategy

- Documentation-only PRs should be revertible with `git revert`.
- Runtime PRs must identify stateful side effects and data migration rollback steps.
- Destructive or migration work requires a pre-change snapshot.

## Release Flow

1. Merge completed PRs into `develop`.
2. Run the test suite and update status documentation.
3. Create a release branch when needed.
4. Fix release blockers only.
5. Merge to `main` through PR.
6. Tag the release.
7. Publish release notes with known limitations.
