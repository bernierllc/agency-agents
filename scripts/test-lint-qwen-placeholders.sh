#!/usr/bin/env bash
# Qwen Code fills three ${name} placeholders into a SubAgent's prompt at launch
# (#1081). The linter must reject those three in an agent body and keep
# accepting every other ${name}, which Qwen 0.25.1+ leaves as written.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT
write_agent() {
  printf '%s\n' '---' 'name: Example Agent' 'description: Checks placeholder handling' 'color: blue' '---' \
    '## Identity' '## Core Mission' '## Critical Rules' '```bash' "echo \"$1\"" '```' > "$scratch/agent.md"
}
for key in task_prompt hook_context external_inputs_override; do
  write_agent "\${$key}"
  if bash "$SCRIPT_DIR/lint-agents.sh" "$scratch/agent.md" > "$scratch/result.log" 2>&1; then
    echo "FAIL: linter accepted the Qwen launch placeholder \${$key}" >&2; exit 1
  fi
  grep -q 'placeholder Qwen Code fills at launch' "$scratch/result.log"
done
for text in '${name}' '${BACKUP_DIR}' '${task_prompt_suffix}' '$task_prompt'; do
  write_agent "$text"
  bash "$SCRIPT_DIR/lint-agents.sh" "$scratch/agent.md" > "$scratch/result.log" 2>&1 \
    || { cat "$scratch/result.log" >&2; echo "FAIL: linter rejected ordinary text $text" >&2; exit 1; }
done
echo 'PASS: Qwen launch placeholders are rejected while other ${name} placeholders pass'
