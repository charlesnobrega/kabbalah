#!/usr/bin/env bash
set -euo pipefail

# Kabbalah - GitHub publication preflight
#
# This script intentionally DOES NOT push.
# Publishing is a manual decision by Charles after reviewing the current branch,
# secret-scan evidence, tests, and target remote.

echo "Kabbalah GitHub publication preflight"
echo "====================================="

if [ ! -d .git ]; then
  echo "ERROR: run this from the repository root." >&2
  exit 1
fi

echo
echo "Current branch:"
git branch --show-current

echo
echo "Current HEAD:"
git --no-pager log -1 --oneline

echo
echo "Working tree status:"
git status --short

if [ -n "$(git status --short)" ]; then
  echo
  echo "ERROR: working tree is not clean. Commit or discard intentional changes before publication." >&2
  exit 1
fi

echo
echo "Tracked sensitive-file check:"
if git ls-files | grep -iE '\.env$|sqlite|secret|credential|apikey'; then
  echo "ERROR: suspicious tracked sensitive path found. Review before publishing." >&2
  exit 1
fi
echo "OK"

if command -v gitleaks >/dev/null 2>&1; then
  echo
  echo "History secret scan:"
  gitleaks detect --source . --log-opts="--all" --redact=100
else
  echo
  echo "WARN: gitleaks not found in PATH. Run an equivalent full-history scan before pushing." >&2
fi

echo
echo "Recommended validation:"
echo "  python -m pytest tests -q"
echo "  python -m pip install -e ."
echo "  python -m kabbalah.cli --help"

echo
echo "Manual publication only after approval:"
echo "  git push origin <branch>"
echo
echo "Important docs:"
echo "  README.md"
echo "  docs/ARCHITECTURE.md"
echo "  docs/roadmap/handoff-execution-plan.md"
echo "  docs/roadmap/cleanup-execution-plan.md"
