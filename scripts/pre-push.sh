#!/usr/bin/env bash
# Pre-push safety check: run tests before push.
# Usage: ./scripts/pre-push.sh
# Exits 0 if all good, 1 if tests fail (push will be rejected).

set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> Running tests before push..."
source venv/bin/activate
python -m pytest tests/ -v
echo "==> All tests passed. Push safely."
