#!/usr/bin/env bash
# Regression coverage for install.sh agent-selection validation.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALLER="$SCRIPT_DIR/install.sh"
AGENTS_FILE="$(mktemp "${TMPDIR:-/tmp}/agency-agent-selection.XXXXXX")"
trap 'rm -f "$AGENTS_FILE"' EXIT

set +e
output="$($INSTALLER --tool claude-code --agent definitely-not-an-agent --dry-run 2>&1)"
status=$?
set -e
[[ "$status" -ne 0 ]] || {
  printf 'Unknown --agent selection unexpectedly succeeded:\n%s\n' "$output" >&2
  exit 1
}
[[ "$output" == *"Unknown agent"* ]] || {
  printf 'Unknown --agent selection did not explain the error:\n%s\n' "$output" >&2
  exit 1
}

printf '%s\n' 'definitely-not-an-agent' > "$AGENTS_FILE"
set +e
output="$($INSTALLER --tool claude-code --agents-file "$AGENTS_FILE" --dry-run 2>&1)"
status=$?
set -e
[[ "$status" -ne 0 ]] || {
  printf 'Unknown agents-file entry unexpectedly succeeded:\n%s\n' "$output" >&2
  exit 1
}
[[ "$output" == *"in agents-file"* ]] || {
  printf 'Unknown agents-file entry did not identify its source:\n%s\n' "$output" >&2
  exit 1
}

output="$($INSTALLER --tool claude-code --agent 'Developer Tooling Engineer' --dry-run 2>&1)"
[[ "$output" == *"Agents:  1"* ]] || {
  printf 'Valid display-name selection did not resolve to one agent:\n%s\n' "$output" >&2
  exit 1
}

# The file stem is the id strategy/runbooks.json uses, and for most agents it is
# not the install slug (engineering-frontend-developer vs frontend-developer).
output="$("$INSTALLER" --tool claude-code --agent engineering-frontend-developer --dry-run 2>&1)"
[[ "$output" == *"Agents:  1"* ]] || {
  printf 'File-stem selection did not resolve to one agent:\n%s\n' "$output" >&2
  exit 1
}

# Every runbook roster, fed to --agents-file as the runbooks list it, resolves
# to exactly its own agents. On main 35 of the 36 ids were "Unknown agent".
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
while IFS=$'\t' read -r runbook count ids; do
  printf '%s\n' $ids > "$AGENTS_FILE"
  set +e
  output="$("$INSTALLER" --tool claude-code --agents-file "$AGENTS_FILE" --dry-run 2>&1)"
  status=$?
  set -e
  [[ "$status" -eq 0 && "$output" == *"Agents:  $count"* ]] || {
    printf 'Runbook %s roster (%s agents) did not resolve:\n%s\n' "$runbook" "$count" "$output" >&2
    exit 1
  }
done < <(python3 - "$REPO_ROOT/strategy/runbooks.json" <<'PY'
import json, sys
for rb in json.load(open(sys.argv[1], encoding="utf-8"))["runbooks"]:
    ids = sorted({a for group in rb["roster"] for a in group["agents"]})
    print(f'{rb["slug"]}\t{len(ids)}\t{" ".join(ids)}')
PY
)

echo "PASS: install.sh rejects unknown agent selections and accepts display names, file stems, and runbook rosters"
