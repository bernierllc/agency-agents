#!/usr/bin/env bash
# --parallel must hand workers the same argv the parent got: an --agents-file
# path with spaces used to be word-split on its way into each worker.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT
mkdir -p "$scratch/repo/scripts" "$scratch/repo/engineering" "$scratch/repo/integrations" "$scratch/home" "$scratch/my lists"
cp "$SCRIPT_DIR/install.sh" "$SCRIPT_DIR/lib.sh" "$scratch/repo/scripts/"
cp "$SCRIPT_DIR/../divisions.json" "$scratch/repo/"
export HOME="$scratch/home"
export CLAUDE_CONFIG_DIR="$HOME/.claude" COPILOT_AGENT_DIR="$HOME/.github/agents"
for agent in first second; do
  printf '%s\n' '---' "name: $agent" 'description: Example agent' 'color: blue' '---' '# Example agent' > "$scratch/repo/engineering/$agent.md"
done
printf 'first\n' > "$scratch/my lists/agents.txt"
bash "$scratch/repo/scripts/install.sh" --tool claude-code,copilot --agents-file "$scratch/my lists/agents.txt" \
  --no-convert --parallel --jobs 2 > "$scratch/out.log" 2>&1 || { cat "$scratch/out.log"; echo 'FAIL: parallel install with spaced --agents-file path failed'; exit 1; }
for d in "$HOME/.claude/agents" "$HOME/.github/agents"; do
  [[ -f "$d/first.md" ]] || { cat "$scratch/out.log"; echo "FAIL: $d/first.md missing"; exit 1; }
  [[ ! -e "$d/second.md" ]] || { echo "FAIL: worker ignored --agents-file selection in $d"; exit 1; }
done
echo 'PASS: parallel workers receive --agents-file paths with spaces intact'
