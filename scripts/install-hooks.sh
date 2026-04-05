#!/bin/sh
#
# Install git hooks from scripts/hooks/ into .git/hooks/
#
REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_SRC="$REPO_ROOT/scripts/hooks"
HOOKS_DST="$REPO_ROOT/.git/hooks"

if [ ! -d "$HOOKS_SRC" ]; then
    echo "No hooks to install (scripts/hooks/ not found)."
    exit 0
fi

for hook in "$HOOKS_SRC"/*; do
    name="$(basename "$hook")"
    cp "$hook" "$HOOKS_DST/$name"
    chmod +x "$HOOKS_DST/$name"
    echo "Installed: $name"
done

echo "Done."
