#!/usr/bin/env bash
# Deselecting every team in the wizard must not install anything: an empty
# FILTER_DIVISIONS means "no filter", so confirming used to install the whole roster.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT
mkdir -p "$scratch/repo/scripts" "$scratch/repo/engineering" "$scratch/repo/integrations" "$scratch/home"
cp "$SCRIPT_DIR/install.sh" "$SCRIPT_DIR/lib.sh" "$scratch/repo/scripts/"
cp "$SCRIPT_DIR/../divisions.json" "$scratch/repo/"
export HOME="$scratch/home" CLAUDE_CONFIG_DIR="$scratch/home/.claude" AGENCY_TUI_FORCE=1
printf '%s\n' '---' 'name: first' 'description: Example agent' 'color: blue' '---' '# Example agent' > "$scratch/repo/engineering/first.md"
# Tools: none, then claude-code (first row). Teams: none. Review: Enter (must be refused), then quit.
status=0
printf 'n \nn\n\nq' | bash "$scratch/repo/scripts/install.sh" --interactive --no-convert > "$scratch/out.log" 2>&1 || status=$?
[[ "$status" == 0 ]] || { cat "$scratch/out.log"; echo "FAIL: wizard exited $status"; exit 1; }
grep -q 'No teams selected' "$scratch/out.log" || { echo 'FAIL: review screen did not warn about zero teams'; exit 1; }
[[ ! -e "$HOME/.claude/agents/first.md" ]] || { echo 'FAIL: zero-team selection installed agents'; exit 1; }
# Control: the same keys with teams left selected do install.
printf 'n \n\n\n' | bash "$scratch/repo/scripts/install.sh" --interactive --no-convert > "$scratch/ok.log" 2>&1
[[ -f "$HOME/.claude/agents/first.md" ]] || { cat "$scratch/ok.log"; echo 'FAIL: control install did not run'; exit 1; }
echo 'PASS: wizard refuses to install with zero teams selected'
