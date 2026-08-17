#!/usr/bin/env bash
set -euo pipefail

REPO="https://github.com/Loverof-Darkness/TerminalGpt.git"
INSTALL_ROOT="${TERMINALGPT_HOME:-$HOME/.local/share/terminalgpt}"
BIN_DIR="${TERMINALGPT_BIN_DIR:-$HOME/.local/bin}"
VENV="$INSTALL_ROOT/venv"
TMP_DIR="$(mktemp -d)"

cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

show_loading() {
  local cyan='\033[1;36m' reset='\033[0m'
  local frames=('|' '/' '-' '\\')
  local i
  printf '\n'
  for i in {1..16}; do
    printf '\r%b  Initializing TerminalGPT %s%b' "$cyan" "${frames[$((i % 4))]}" "$reset"
    sleep 0.06
  done
  printf '\r%b  Initializing TerminalGPT [OK]%b\n' "$cyan" "$reset"
  printf '  Preparing installer...\n\n'
}

show_welcome() {
  local border='\033[1;36m'
  local terminal_color='\033[1;35m'
  local gpt_color='\033[1;31m'
  local white='\033[1;97m'
  local gray='\033[0;37m'
  local reset='\033[0m'
  local width=73
  local horizontal
  horizontal=$(printf '%*s' "$width" '' | tr ' ' '-')

  printf '%b\n' "${border}+${horizontal}+${reset}"

  printf '%b' "${border}|  ${reset}"
  printf '%b' "${terminal_color}█████ █████ ████  ██ ██ █████ ██ ██  ███  ██    ${reset}"
  printf '%b' "${gpt_color}  ████ ████  █████${reset}"
  printf '%b\n' "  ${border}|${reset}"

  printf '%b' "${border}|  ${reset}"
  printf '%b' "${terminal_color}  █   ██    ██ ██ █████   █   █████ ██ ██ ██    ${reset}"
  printf '%b' "${gpt_color} ██    ██ ██   █${reset}"
  printf '%b\n' "  ${border}|${reset}"

  printf '%b' "${border}|  ${reset}"
  printf '%b' "${terminal_color}  █   ██    ██ ██ ██ ██   █   █████ ██ ██ ██    ${reset}"
  printf '%b' "${gpt_color} ██    ██ ██   █${reset}"
  printf '%b\n' "  ${border}|${reset}"

  printf '%b' "${border}|  ${reset}"
  printf '%b' "${terminal_color}  █   ████  ████  ██ ██   █   ██ ██ █████ ██    ${reset}"
  printf '%b' "${gpt_color} ██ ██ ████    █${reset}"
  printf '%b\n' "  ${border}|${reset}"

  printf '%b' "${border}|  ${reset}"
  printf '%b' "${terminal_color}  █   ██    ██ ██ ██ ██   █   ██ ██ ██ ██ ██    ${reset}"
  printf '%b' "${gpt_color} ██ ██ ██      █${reset}"
  printf '%b\n' "  ${border}|${reset}"

  printf '%b' "${border}|  ${reset}"
  printf '%b' "${terminal_color}  █   ██    ██ ██ ██ ██   █   ██ ██ ██ ██ ██    ${reset}"
  printf '%b' "${gpt_color} ██ ██ ██      █${reset}"
  printf '%b\n' "  ${border}|${reset}"

  printf '%b' "${border}|  ${reset}"
  printf '%b' "${terminal_color}  █   █████ ██  ██ ██ ██ █████ ██ ██ ██ ██ █████ ${reset}"
  printf '%b' "${gpt_color}  ████ ██      █${reset}"
  printf '%b\n' "  ${border}|${reset}"

  printf '%b\n' "${border}+${horizontal}+${reset}"
  printf '%b' "${border}|${reset}"
  local tagline='TERMINAL-FIRST AI AGENT FOR YOUR SYSTEM'
  local left=$(( (width - ${#tagline}) / 2 ))
  local right=$(( width - left - ${#tagline} ))
  printf '%*s%b%*s' "$left" '' "${white}${tagline}${reset}" "$right" ''
  printf '%b\n' "${border}|${reset}"
  printf '%b\n' "${border}+${horizontal}+${reset}"
  printf '\n'

  printf '%b\n' "${white}TerminalGPT${reset} is a terminal-first AI agent that can reason about your machine,"
  printf '%b\n' "inspect files and system state, run approved shell commands, and use browser-based"
  printf '%b\n' "human approval before performing sensitive actions."
  printf '\n'
  printf '%b\n' "${gray}This installer will download the latest TerminalGPT source from GitHub,"
  printf '%b\n' "create an isolated Python environment, install dependencies, and install"
  printf '%b\n' "the terminalgpt command under $BIN_DIR."
  printf '\n'

  if [[ "${TERMINALGPT_ASSUME_YES:-0}" == "1" ]]; then
    return 0
  fi

  if [[ ! -r /dev/tty ]]; then
    printf '%b\n' "Unable to read confirmation from the terminal."
    exit 1
  fi

  local answer
  while true; do
    printf '%b' "${border}Continue with installation? [Y/n]: ${reset}"
    IFS= read -r answer < /dev/tty || exit 1
    answer="${answer:-Y}"
    case "$answer" in
      Y|y|yes|YES|Yes) printf '\n'; return 0 ;;
      N|n|no|NO|No) printf 'Installation cancelled.\n'; exit 0 ;;
      *) printf 'Please answer Y or N.\n' ;;
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
