#!/usr/bin/env bash
# One tool failing in a sequential install must not cost the tools after it,
# and the install must still exit non-zero and name the tool that failed.
#
# Before: install_tool ran bare under set -e, so the first tool whose output
# was missing exited the script. With gemini-cli, cursor and qwen selected and
# no integrations/cursor, gemini-cli installed, cursor printed its [ERR], and
# qwen was never attempted and never mentioned.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
tmp="$(mktemp -d "${TMPDIR:-/tmp}/agency-continue.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT

fail() { echo "FAIL: $*" >&2; sed 's/^/    /' "$tmp/output" >&2; exit 1; }

mkdir -p "$tmp/repo/scripts" "$tmp/repo/engineering" \
  "$tmp/repo/integrations/gemini-cli/agents" "$tmp/repo/integrations/qwen/agents" \
  "$tmp/home/project"
cp "$SCRIPT_DIR/install.sh" "$SCRIPT_DIR/lib.sh" "$tmp/repo/scripts/"
cat > "$tmp/repo/divisions.json" <<'EOF'
{
  "divisions": {
    "engineering": {}
  }
}
EOF
cat > "$tmp/repo/engineering/agent.md" <<'EOF'
---
name: Sample Agent
description: Example agent
---
Instructions.
EOF
printf 'Gemini output\n' > "$tmp/repo/integrations/gemini-cli/agents/sample-agent.md"
printf 'Qwen output\n'   > "$tmp/repo/integrations/qwen/agents/sample-agent.md"
# integrations/cursor is deliberately absent: cursor is the tool that fails.

status=0
(cd "$tmp/home/project" && HOME="$tmp/home" PATH=/usr/bin:/bin \
  bash "$tmp/repo/scripts/install.sh" --no-interactive --no-convert \
    --tool gemini-cli,cursor,qwen > "$tmp/output" 2>&1) || status=$?

[[ "$status" -ne 0 ]] || fail "install exited 0 although cursor failed"
[[ -f "$tmp/home/.gemini/agents/sample-agent.md" ]] || fail "gemini-cli, before the failure, did not install"
[[ -f "$tmp/home/project/.qwen/agents/sample-agent.md" ]] \
  || fail "qwen, after the failing cursor, was never installed"
grep -q 'integrations/cursor missing' "$tmp/output" || fail "cursor's own error was not shown"
grep -q 'Failed: cursor' "$tmp/output"             || fail "the summary does not name the failed tool"
grep -q 'Installed 2 of 3 tool(s)' "$tmp/output"    || fail "the summary does not count the tools that installed"
echo "PASS: a failing tool is reported and the tools after it still install"

# The clean path is unchanged: every tool installs and the install exits 0.
mkdir -p "$tmp/repo/integrations/cursor/rules" "$tmp/home2/project"
printf -- '---\ndescription: x\n---\nCursor output\n' > "$tmp/repo/integrations/cursor/rules/sample-agent.mdc"
(cd "$tmp/home2/project" && HOME="$tmp/home2" PATH=/usr/bin:/bin \
  bash "$tmp/repo/scripts/install.sh" --no-interactive --no-convert \
    --tool gemini-cli,cursor,qwen > "$tmp/output" 2>&1) || fail "a clean install exited non-zero"
grep -q 'Done!  Installed 3 tool(s)' "$tmp/output" || fail "a clean install did not report all three tools"
echo "PASS: a clean multi-tool install still exits 0"
