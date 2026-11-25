#!/usr/bin/env bash
# Copies the handoff into a tellolink clone on Ubuntu and installs the Claude Code memory.
# Usage (from the root of the cloned repo):   bash /path/to/claude_devir/kur.sh
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
REPO="$(pwd)"

if [ ! -f "$REPO/tello.py" ] || [ ! -d "$REPO/.git" ]; then
    echo "Run this from the root of the cloned tellolink repo (tello.py and .git must be here)." >&2
    exit 1
fi

# 1) Handoff note + reference docs into the repo (kept out of git via .git/info/exclude)
cp "$SRC/CLAUDE.md" "$REPO/CLAUDE.md"
mkdir -p "$REPO/claude_devir_notes"
cp "$SRC/claude_devir_notes/"*.md "$REPO/claude_devir_notes/"
for p in CLAUDE.md claude_devir_notes/; do
    grep -qxF "$p" "$REPO/.git/info/exclude" 2>/dev/null || echo "$p" >> "$REPO/.git/info/exclude"
done

# 2) Memory: Claude Code keeps it in ~/.claude/projects/<project path with non-alphanumerics as "-">/memory
KEY="$(printf '%s' "$REPO" | sed 's/[^a-zA-Z0-9]/-/g')"
MEM="$HOME/.claude/projects/$KEY/memory"
mkdir -p "$MEM"
cp "$SRC/memory/"*.md "$MEM/"

echo "Handoff copied to:   $REPO/CLAUDE.md and $REPO/claude_devir_notes/ (excluded from git)"
echo "Memory installed to: $MEM"
echo "Now run 'claude' in $REPO."
