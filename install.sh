#!/usr/bin/env bash
set -euo pipefail

REPO="https://github.com/Loverof-Darkness/TerminalGpt.git"
INSTALL_ROOT="${TERMINALGPT_HOME:-$HOME/.local/share/terminalgpt}"
BIN_DIR="${TERMINALGPT_BIN_DIR:-$HOME/.local/bin}"
VENV="$INSTALL_ROOT/venv"
TMP_DIR="$(mktemp -d)"

cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

show_welcome() {
  local reset='\033[0m' border='\033[1;36m' terminal_color='\033[1;35m' gpt_color='\033[1;36m' white='\033[1;97m' gray='\033[0;37m' red='\033[1;31m'
  local width=69
  local line
  line=$(printf '%*s' "$width" '' | tr ' ' '─')

  printf '\n'
  printf '%b\n' "${border}╭${line}╮${reset}"
  printf '%b' "${border}│${reset}  ${terminal_color}█████ █████ ████  █████ ██  █ █████ ${reset}"
  printf '%b\n' " ${border}│${reset}"
  printf '%b' "${border}│${reset}  ${terminal_color}  █   ██    ██  ██ ██    ██ ████  ${reset}"
  printf '%b\n' " ${border}│${reset}"
  printf '%b' "${border}│${reset}  ${terminal_color}  █   ████  ████  ████    █████  ${reset}"
  printf '%b\n' " ${border}│${reset}"
  printf '%b' "${border}│${reset}  ${terminal_color}  █   ██    ██    ██ ██   ██ ██  ${reset}"
  printf '%b\n' " ${border}│${reset}"
  printf '%b' "${border}│${reset}  ${terminal_color}  █   █████ ██    ██  ██ █████ █████ ${reset}"
  printf '%b' "${gpt_color} GPT${reset}"
  printf '%b\n' " ${border}│${reset}"
  printf '%b\n' "${border}├${line}┤${reset}"
  printf '%b' "${border}│${reset}"
  local tagline='Terminal-first AI agent for your system'
  local left=$(( (width - ${#tagline}) / 2 ))
  printf '%*s%b%*s' "$left" '' "${white}${tagline}${reset}" "$(( width-left-${#tagline} ))" ''
  printf '%b\n' "${border}│${reset}"
  printf '%b\n' "${border}╰${line}╯${reset}"
  printf '\n'

  printf '%b\n' "${white}TerminalGPT${reset} is a terminal-first AI agent that can reason about your machine,"
  printf '%b\n' "inspect files and system state, run approved shell commands, and use browser-based"
  printf '%b\n' "human approval before performing sensitive actions."
  printf '\n'
  printf '%b\n' "${gray}This installer will download the latest TerminalGPT source from GitHub,"
  printf '%b\n' "create an isolated Python environment, install dependencies, and install"
  printf '%b\n' "the ${white}terminalgpt${reset}${gray} command under ${white}$BIN_DIR${reset}${gray}."
  printf '\n'

  if [[ "${TERMINALGPT_ASSUME_YES:-0}" == "1" ]]; then return 0; fi
  local answer
  if [[ ! -r /dev/tty ]]; then
    printf '%b\n' "${red}Unable to read confirmation from the terminal.${reset}"
    exit 1
  fi
  while true; do
    printf '%b' "${border}Continue with installation? [Y/n]: ${reset}"
    IFS= read -r answer < /dev/tty || exit 1
    answer="${answer:-Y}"
    case "$answer" in
      Y|y|yes|YES|Yes) printf '\n'; return 0 ;;
      N|n|no|NO|No) printf '%b\n' "${gray}Installation cancelled.${reset}"; exit 0 ;;
      *) printf '%b\n' "${red}Please answer Y or N.${reset}" ;;
    esac
  done
}

show_welcome

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

case "${SHELL:-}" in
  */fish)
    FISH_CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/fish/config.fish"
    mkdir -p "$(dirname "$FISH_CONFIG")"
    touch "$FISH_CONFIG"
    grep -Fqx "fish_add_path $BIN_DIR" "$FISH_CONFIG" 2>/dev/null || echo "fish_add_path $BIN_DIR" >> "$FISH_CONFIG"
    if command -v fish >/dev/null 2>&1; then fish -c 'fish_add_path "$HOME/.local/bin"' 2>/dev/null || true; fi
    ;;
  */zsh)
    ZSH_CONFIG="$HOME/.zshrc"; touch "$ZSH_CONFIG"
    grep -Fqx "export PATH=\"$BIN_DIR:\$PATH\"" "$ZSH_CONFIG" 2>/dev/null || echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$ZSH_CONFIG"
    ;;
  */bash)
    BASH_CONFIG="$HOME/.bashrc"; touch "$BASH_CONFIG"
    grep -Fqx "export PATH=\"$BIN_DIR:\$PATH\"" "$BASH_CONFIG" 2>/dev/null || echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$BASH_CONFIG"
    ;;
esac

echo "TerminalGPT installed to $BIN_DIR/terminalgpt"
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
  echo "PATH configured for future shells. For the current shell, run: fish_add_path $BIN_DIR"
fi
echo "Run: terminalgpt chat"

if [[ $# -gt 0 ]]; then
  exec "$BIN_DIR/terminalgpt" "$@"
fi
