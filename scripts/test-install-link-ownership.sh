#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT
mkdir -p "$scratch/repo/scripts" "$scratch/repo/engineering" "$scratch/repo/integrations" "$scratch/home"
cp "$SCRIPT_DIR/install.sh" "$SCRIPT_DIR/lib.sh" "$scratch/repo/scripts/"
cp "$SCRIPT_DIR/../divisions.json" "$scratch/repo/"
export HOME="$scratch/home"
for agent in first second; do
  printf '%s\n' '---' "name: $agent" 'description: Example agent' 'color: blue' '---' '# Example agent' > "$scratch/repo/engineering/$agent.md"
done
run_install() {
  bash "$scratch/repo/scripts/install.sh" --tool claude-code --division engineering \
    --no-convert --link --path "$scratch/dest" > "$scratch/result.log" 2>&1
}
mkdir -p "$scratch/dest"
printf 'user content\n' > "$scratch/dest/first.md"
run_install
[[ ! -L "$scratch/dest/first.md" ]] && grep -qx 'user content' "$scratch/dest/first.md" || {
  echo 'FAIL: --link replaced a user-owned regular file' >&2; exit 1;
}
[[ -L "$scratch/dest/second.md" ]]
grep -q 'Not installed: 1 file' "$scratch/result.log"
for kind in foreign dangling directory; do
  rm -f "$scratch/dest/first.md" "$scratch/dest/second.md"
  target="$scratch/$kind"
  [[ "$kind" == foreign ]] && printf 'outside content\n' > "$target"
  [[ "$kind" == directory ]] && mkdir -p "$target"
  ln -s "$target" "$scratch/dest/first.md"
  run_install
  [[ "$(readlink "$scratch/dest/first.md")" == "$target" ]]
  [[ -L "$scratch/dest/second.md" ]]
  grep -q 'Not installed: 1 file' "$scratch/result.log"
  [[ "$kind" != foreign ]] || grep -qx 'outside content' "$target"
  [[ "$kind" != dangling ]] || [[ ! -e "$target" ]]
  [[ "$kind" != directory ]] || [[ ! -e "$target/first.md" ]]
done
rm -f "$scratch/dest/first.md"
ln -s "$scratch/repo/engineering/old.md" "$scratch/dest/first.md"
run_install
[[ "$(readlink "$scratch/dest/first.md")" == "$scratch/repo/engineering/first.md" ]]
run_install
[[ "$(readlink "$scratch/dest/first.md")" == "$scratch/repo/engineering/first.md" ]]
# A config directory itself may be a user's dotfiles link; protect leaf files.
mv "$scratch/dest" "$scratch/dotfiles"
ln -s "$scratch/dotfiles" "$scratch/dest"
run_install
[[ -L "$scratch/dest" && -L "$scratch/dest/second.md" ]]
echo 'PASS: --link skips user files and foreign links, replaces its own links, and continues'
