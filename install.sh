#!/usr/bin/env bash
set -euo pipefail

REPO="https://github.com/Loverof-Darkness/TerminalGpt.git"
INSTALL_ROOT="${TERMINALGPT_HOME:-$HOME/.local/share/terminalgpt}"
BIN_DIR="${TERMINALGPT_BIN_DIR:-$HOME/.local/bin}"
VENV="$INSTALL_ROOT/venv"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

show_loading() {
  local frames=('|' '/' '-' '\\')
  local i
  printf '\n'
  for i in {1..16}; do
    printf '\r\033[1;36m  Initializing TerminalGPT %s\033[0m' "${frames[$((i % 4))]}"
    sleep 0.06
  done
  printf '\r\033[1;36m  Initializing TerminalGPT [OK]\033[0m\n'
  printf '  Preparing installer...\n\n'
}

show_welcome() {
  # Fixed 7-row block wordmark. No dynamic ANSI variables are used in the logo;
  # printf interprets the escape sequences directly, preventing literal \033 text.
  printf '\033[1;36m+-------------------------------------------------------------------------+\033[0m\n'
  printf '\033[1;36m|\033[0m                                                                         \033[1;36m|\033[0m\n'
  printf '\033[1;36m|  \033[1;35m##### ##### ####  #   # ##### #   #  ###  #     ##   ##### #####\033[1;31m  #### ##### ####\033[1;36m  |\033[0m\n'
  printf '\033[1;36m|  \033[1;35m  #   #     #   # #  ##   #   ##  # #   # #     ##   #   # #    \033[1;31m #   # #   # #\033[1;36m  |\033[0m\n'
  printf '\033[1;36m|  \033[1;35m  #   #     #   # # # #   #   ##  # #   # #     ##   #   # #    \033[1;31m #   # #   # #\033[1;36m  |\033[0m\n'
  printf '\033[1;36m|  \033[1;35m  #   ####  ####  #   #   #   # # # ##### #     ##   #   # #### \033[1;31m #   # ####  #\033[1;36m  |\033[0m\n'
  printf '\033[1;36m|  \033[1;35m  #   #     # #   #   #   #   #  ## #   # #     ##   #   # #    \033[1;31m #   # #  #  #\033[1;36m  |\033[0m\n'
  printf '\033[1;36m|  \033[1;35m  #   #     #  #  #   #   #   #  ## #   # #     ##   #   # #    \033[1;31m #   # #   # #\033[1;36m  |\033[0m\n'
  printf '\033[1;36m|  \033[1;35m  #   ##### #   # ##### ##### #   # #   # ##### ##   ##### #    \033[1;31m ####  #   # #\033[1;36m  |\033[0m\n'
  printf '\033[1;36m|\033[0m                                                                         \033[1;36m|\033[0m\n'
  printf '\033[1;36m|                    \033[1;97mTERMINAL-FIRST AI AGENT\033[0m                    \033[1;36m|\033[0m\n'
  printf '\033[1;36m|                         \033[1;97mFOR YOUR SYSTEM\033[0m                         \033[1;36m|\033[0m\n'
  printf '\033[1;36m+-------------------------------------------------------------------------+\033[0m\n'
  printf '\n'

  printf '\033[1;97mTerminalGPT\033[0m is a terminal-first AI agent that can reason about your machine,\n'
  printf 'inspect files and system state, run approved shell commands, and use browser-based\n'
  printf 'human approval before performing sensitive actions.\n\n'
  printf '\033[0;37mThis installer will download the latest TerminalGPT source from GitHub,\033[0m\n'
  printf 'create an isolated Python environment, install dependencies, and install\n'
  printf 'the \033[1;97mterminalgpt\033[0m command under \033[1;97m%s\033[0m.\n\n' "$BIN_DIR"

  if [[ "${TERMINALGPT_ASSUME_YES:-0}" == "1" ]]; then
    return 0
  fi

  if [[ ! -r /dev/tty ]]; then
    printf '\033[1;31mUnable to read confirmation from the terminal.\033[0m\n'
    exit 1
  fi

  local answer
  while true; do
    printf '\033[1;36mContinue with installation? [Y/n]: \033[0m'
    IFS= read -r answer < /dev/tty || exit 1
    answer="${answer:-Y}"
    case "$answer" in
      Y|y|yes|YES|Yes)
        printf '\n'
        return 0
        ;;
      N|n|no|NO|No)
        printf 'Installation cancelled.\n'
        exit 0
        ;;
      *)
        printf '\033[1;31mPlease answer Y or N.\033[0m\n'
        ;;
    esac
  done
}

show_loading
show_welcome

command -v python3 >/dev/null 2>&1 || {
  echo "TerminalGPT requires Python 3.11+. Install python3 and run this command again." >&2
  exit 1
}

PYTHON=python3
if ! "$PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)'; then
  echo "TerminalGPT requires Python 3.11+." >&2
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

case "${SHELL:-}" in
  */fish)
    FISH_CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/fish/config.fish"
    mkdir -p "$(dirname "$FISH_CONFIG")"
    touch "$FISH_CONFIG"
    grep -Fqx "fish_add_path $BIN_DIR" "$FISH_CONFIG" 2>/dev/null || echo "fish_add_path $BIN_DIR" >> "$FISH_CONFIG"
    fish -c 'fish_add_path "$HOME/.local/bin"' 2>/dev/null || true
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
  echo "For the current shell: fish_add_path $BIN_DIR"
fi
echo "Run: terminalgpt chat"

if [[ $# -gt 0 ]]; then
  exec "$BIN_DIR/terminalgpt" "$@"
fi
