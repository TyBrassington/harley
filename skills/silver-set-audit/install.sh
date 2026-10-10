#!/usr/bin/env bash
# Install the audit-contrast-set skill for Claude Code and/or Codex CLI.
#   ./install.sh            # both
#   ./install.sh claude     # ~/.claude/skills/audit-contrast-set
#   ./install.sh codex      # ~/.codex/skills/audit-contrast-set
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
targets="${*:-claude codex}"
for t in $targets; do
  case "$t" in
    claude) dest="$HOME/.claude/skills/audit-contrast-set" ;;
    codex)  dest="$HOME/.codex/skills/audit-contrast-set" ;;
    *) echo "unknown target: $t (use claude or codex)" >&2; exit 1 ;;
  esac
  mkdir -p "$(dirname "$dest")"
  rm -rf "$dest"
  cp -r "$here/$t/audit-contrast-set" "$dest"
  echo "installed $t -> $dest"
done
