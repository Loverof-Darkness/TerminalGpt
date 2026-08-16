#!/usr/bin/env bash
set -euo pipefail

REPO="https://github.com/Loverof-Darkness/TerminalGpt.git"
INSTALL_ROOT="${TERMINALGPT_HOME:-$HOME/.local/share/terminalgpt}"
BIN_DIR="${TERMINALGPT_BIN_DIR:-$HOME/.local/bin}"
VENV="$INSTALL_ROOT/venv"
TMP_DIR="$(mktemp -d)"

cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

command -v python3 >/dev/null 2>&1 || {
  echo "TerminalGPT requires Python 3.11+. Install python3 and run this command again." >&2
  exit 1
}

PYTHON="python3"
PY_VERSION="$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if ! "$PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'; then
  echo "TerminalGPT requires Python 3.11+; found Python $PY_VERSION." >&2
  exit 1
fi

mkdir -p "$INSTALL_ROOT" "$BIN_DIR"

if command -v git >/dev/null 2>&1; then
  git clone --depth 1 --filter=blob:none "$REPO" "$TMP_DIR/src" >/dev/null 2>&1
else
  command -v curl >/dev/null 2>&1 || { echo "Install git or curl first." >&2; exit 1; }
  curl -fsSL "https://github.com/Loverof-Darkness/TerminalGpt/archive/refs/heads/main.tar.gz" -o "$TMP_DIR/repo.tar.gz"
  mkdir -p "$TMP_DIR/src"
  tar -xzf "$TMP_DIR/repo.tar.gz" --strip-components=1 -C "$TMP_DIR/src"
fi

rm -rf "$VENV"
"$PYTHON" -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip >/dev/null
"$VENV/bin/python" -m pip install "$TMP_DIR/src" >/dev/null

cat > "$BIN_DIR/terminalgpt" <<EOF
#!/usr/bin/env bash
exec "$VENV/bin/terminalgpt" "\$@"
EOF
chmod +x "$BIN_DIR/terminalgpt"

# Make the command available in common interactive shells after installation.
case "${SHELL:-}" in
  */fish)
    FISH_CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/fish/config.fish"
    mkdir -p "$(dirname "$FISH_CONFIG")"
    touch "$FISH_CONFIG"
    grep -Fqx "fish_add_path $BIN_DIR" "$FISH_CONFIG" 2>/dev/null || echo "fish_add_path $BIN_DIR" >> "$FISH_CONFIG"
    ;;
  */zsh)
    ZSH_CONFIG="$HOME/.zshrc"
    touch "$ZSH_CONFIG"
    grep -Fqx "export PATH=\"$BIN_DIR:\$PATH\"" "$ZSH_CONFIG" 2>/dev/null || echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$ZSH_CONFIG"
    ;;
  */bash)
    BASH_CONFIG="$HOME/.bashrc"
    touch "$BASH_CONFIG"
    grep -Fqx "export PATH=\"$BIN_DIR:\$PATH\"" "$BASH_CONFIG" 2>/dev/null || echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$BASH_CONFIG"
    ;;
esac

echo "TerminalGPT installed to $BIN_DIR/terminalgpt"
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
  echo "Current shell: run 'source ~/.config/fish/config.fish' (fish) or start a new shell."
fi
echo "Run: terminalgpt chat"

if [[ $# -gt 0 ]]; then
  exec "$BIN_DIR/terminalgpt" "$@"
fi
