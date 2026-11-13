#!/usr/bin/env bash
#
# test-convert-fence-model.sh — the converted-outputs eval must parse source
# code fences the way lib.sh and GitHub do.
#
# The eval's Python model read fences only at column 0, while CommonMark (and
# lib.sh's fence_open_p / fence_closes_p, aligned to it in #855 and #1028)
# allows up to three spaces of indentation and does not constrain a closer by
# the opener's indent. With an indented opening fence and a column-0 closer,
# the model missed the opener and treated the closer as its own opener, so it
# reported the following lines as a torn fenced block across SOUL.md/AGENTS.md
# — a hard failure in the Check Tools workflow for an agent file that lint,
# GitHub and convert_openclaw all handle correctly.
#
# Builds a throwaway repo around the real eval and one such fixture, then
# requires the eval to validate it cleanly. `--update` keeps the check on a
# fresh repo without a committed manifest.
#
# Usage: ./scripts/test-convert-fence-model.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
scratch="$(mktemp -d "${TMPDIR:-/tmp}/agency-fence-model.XXXXXX")"
trap 'rm -rf "$scratch"' EXIT

mkdir -p "$scratch/repo/scripts" "$scratch/repo/engineering"
cp "$SCRIPT_DIR/convert.sh" "$SCRIPT_DIR/lib.sh" "$SCRIPT_DIR/build-hermes-plugin.py" \
   "$SCRIPT_DIR/test-convert-outputs.sh" "$scratch/repo/scripts/"

cat > "$scratch/repo/divisions.json" <<'EOF'
{
  "divisions": {
    "engineering": {"label": "Engineering", "icon": "Code", "color": "#3B82F6"}
  }
}
EOF

cat > "$scratch/repo/engineering/fence-fixture.md" <<'EOF'
---
name: Fence Model Fixture
description: Fixture agent with an indented opening code fence
color: blue
---
## Identity
  ```text
  code sample
```
## Core Mission
mission text
EOF

cd "$scratch/repo"
if ! bash scripts/test-convert-outputs.sh --update > "$scratch/eval.log" 2>&1; then
  cat "$scratch/eval.log" >&2
  echo "FAIL: the outputs eval rejected a GitHub-valid indented opening fence" >&2
  exit 1
fi
if grep -q 'torn across' "$scratch/eval.log"; then
  echo "FAIL: the outputs eval reported a torn fence for correctly split output" >&2
  exit 1
fi
echo "PASS: the outputs eval parses indented code fences like lib.sh and GitHub"
