#!/usr/bin/env bash
# Sync selected ~/.config directories between this repo and the live system.
#
# Usage:
#   scripts/sync-dotfiles.sh push [--dry-run]   # ~/.config -> repo (default)
#   scripts/sync-dotfiles.sh pull [--dry-run]   # repo -> ~/.config (bootstrap a new machine)
#
# Only directories/files listed in TARGETS are touched. Everything else in
# ~/.config is left alone. Add new entries to TARGETS as you adopt new configs.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$HOME/.config"
DEST="$REPO_DIR/.config"

MODE="${1:-push}"
DRY_RUN="${2:-}"

# Whitelist of subpaths (relative to .config) to keep in sync.
# Keep this scoped to real, hand-edited config -- not caches, app state,
# or machine-specific secrets.
TARGETS=(
  dunst
  eww
  my_eww
  rofi
  hypr
  waybar
  kitty
  nvim
  cava
  swaylock
  nwg-look
  Kvantum
  fontconfig
  xsettingsd
  hyprdynamicmonitors
  htop/htoprc
)

# Never sync these, even inside a whitelisted directory: local Claude
# settings, editor/WM backup files, and personal wallpapers.
EXCLUDES=(
  --exclude='.claude/'
  --exclude='*.bak-*'
  --exclude='*.save'
  --exclude='wallpapers/'
  --exclude='*.tmp*'
)

RSYNC_OPTS=(-av --delete)
if [ "$DRY_RUN" = "--dry-run" ]; then
  RSYNC_OPTS+=(--dry-run)
fi

sync_one() {
  local from="$1" to="$2"
  [ -e "$from" ] || { echo "skip (missing): $from"; return; }
  mkdir -p "$(dirname "$to")"
  if [ -d "$from" ]; then
    mkdir -p "$to"
    rsync "${RSYNC_OPTS[@]}" "${EXCLUDES[@]}" "$from/" "$to/"
  else
    rsync "${RSYNC_OPTS[@]}" "$from" "$to"
  fi
}

case "$MODE" in
  push)
    for t in "${TARGETS[@]}"; do
      sync_one "$SRC/$t" "$DEST/$t"
    done
    ;;
  pull)
    for t in "${TARGETS[@]}"; do
      sync_one "$DEST/$t" "$SRC/$t"
    done
    ;;
  *)
    echo "usage: $0 [push|pull] [--dry-run]" >&2
    exit 1
    ;;
esac

echo
echo "Done ($MODE${DRY_RUN:+, $DRY_RUN})."
if [ "$MODE" = "push" ]; then
  echo "Next: cd '$REPO_DIR' && git status && git diff -- .config"
fi
