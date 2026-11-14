#!/usr/bin/env bash
# A filter that was asked for but selects nothing must fail, never fall back to
# "no filter" and install the whole roster (--division ' , ', --agent ',', a
# comment-only --agents-file). The wizard path is covered by
# test-install-wizard-empty-teams.sh.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT
mkdir -p "$scratch/repo/scripts" "$scratch/repo/engineering" "$scratch/repo/integrations" "$scratch/home"
cp "$SCRIPT_DIR/install.sh" "$SCRIPT_DIR/lib.sh" "$scratch/repo/scripts/"
cp "$SCRIPT_DIR/../divisions.json" "$scratch/repo/"
export HOME="$scratch/home" CLAUDE_CONFIG_DIR="$scratch/home/.claude"
printf '%s\n' '---' 'name: first' 'description: Example agent' 'color: blue' '---' '# Example agent' > "$scratch/repo/engineering/first.md"
printf '# nothing selected yet\n\n' > "$scratch/empty.txt"
expect_refused() {
  local status=0
  bash "$scratch/repo/scripts/install.sh" --tool claude-code --no-convert "$@" > "$scratch/out.log" 2>&1 || status=$?
  [[ "$status" != 0 ]] || { cat "$scratch/out.log"; echo "FAIL: '$*' exited 0"; exit 1; }
  [[ ! -e "$HOME/.claude/agents/first.md" ]] || { echo "FAIL: '$*' installed agents"; exit 1; }
}
expect_refused --division ' , '
expect_refused --agent ','
expect_refused --agents-file "$scratch/empty.txt"
# Control: a real selection still installs.
bash "$scratch/repo/scripts/install.sh" --tool claude-code --no-convert --division engineering > "$scratch/ok.log" 2>&1
[[ -f "$HOME/.claude/agents/first.md" ]] || { cat "$scratch/ok.log"; echo 'FAIL: control install did not run'; exit 1; }
echo 'PASS: explicit filters that select nothing are refused'
