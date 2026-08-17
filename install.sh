#!/usr/bin/env bash
set -euo pipefail

REPO="https://github.com/Loverof-Darkness/TerminalGpt.git"
INSTALL_ROOT="${TERMINALGPT_HOME:-$HOME/.local/share/terminalgpt}"
BIN_DIR="${TERMINALGPT_BIN_DIR:-$HOME/.local/bin}"
VENV="$INSTALL_ROOT/venv"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

show_loading() {
  local i
  printf '\n'
  for i in {1..18}; do
    case $((i % 4)) in
      0) printf '\r\033[1;36m  Initializing TerminalGPT |\033[0m' ;;
      1) printf '\r\033[1;36m  Initializing TerminalGPT /\033[0m' ;;
      2) printf '\r\033[1;36m  Initializing TerminalGPT -\033[0m' ;;
      3) printf '\r\033[1;36m  Initializing TerminalGPT \\\033[0m' ;;
    esac
    sleep 0.055
  done
  printf '\r\033[1;36m  Initializing TerminalGPT [OK]\033[0m\n'
  printf '  Preparing installer...\n\n'
}

show_welcome() {
  # Real ANSI Shadow-style wordmark, rendered directly so figlet is not required.
  # TERMINAL = bright magenta, GPT = bright red.
  local magenta=$'\033[1;35m'
  local red=$'\033[1;31m'
  local cyan=$'\033[1;36m'
  local white=$'\033[1;97m'
  local gray=$'\033[0;37m'
  local reset=$'\033[0m'

  # ANSI Shadow glyphs for TERMINAL.
  local T1='████████╗' T2='╚══██╔══╝' T3='   ██║   ' T4='   ██║   ' T5='   ██║   ' T6='   ╚═╝   '
  local E1='███████╗' E2='██╔════╝' E3='█████╗  ' E4='██╔══╝  ' E5='███████╗' E6='╚══════╝'
  local R1='██████╗ ' R2='██╔══██╗' R3='██████╔╝' R4='██╔══██╗' R5='██║  ██║' R6='╚═╝  ╚═╝'
  local M1='███╗   ███╗' M2='████╗ ████║' M3='██╔████╔██║' M4='██║╚██╔╝██║' M5='██║ ╚═╝ ██║' M6='╚═╝     ╚═╝'
  local I1='██╗' I2='██║' I3='██║' I4='██║' I5='██║' I6='╚═╝'
  local N1='███╗   ██╗' N2='████╗  ██║' N3='██╔██╗ ██║' N4='██║╚██╗██║' N5='██║ ╚████║' N6='╚═╝  ╚═══╝'
  local A1=' █████╗ ' A2='██╔══██╗' A3='███████║' A4='██╔══██║' A5='██║  ██║' A6='╚═╝  ╚═╝'
  local L1='██╗     ' L2='██║     ' L3='██║     ' L4='██║     ' L5='███████╗' L6='╚══════╝'

  # ANSI Shadow glyphs for GPT.
  local G1=' ██████╗ ' G2='██╔════╝ ' G3='██║  ███╗' G4='██║   ██║' G5='╚██████╔╝' G6=' ╚═════╝ '
  local P1='██████╗ ' P2='██╔══██╗' P3='██████╔╝' P4='██╔═══╝ ' P5='██║     ' P6='╚═╝     '
  local GT1='████████╗' GT2='╚══██╔══╝' GT3='   ██║   ' GT4='   ██║   ' GT5='   ██║   ' GT6='   ╚═╝   '

  printf '%s%s %s %s %s %s %s %s %s  %s' "$magenta" "$T1" "$E1" "$R1" "$M1" "$I1" "$N1" "$A1" "$L1" "$reset"
  printf '%s%s %s %s%s\n' "$red" "$G1" "$P1" "$GT1" "$reset"

  printf '%s%s %s %s %s %s %s %s %s  %s' "$magenta" "$T2" "$E2" "$R2" "$M2" "$I2" "$N2" "$A2" "$L2" "$reset"
  printf '%s%s %s %s%s\n' "$red" "$G2" "$P2" "$GT2" "$reset"

  printf '%s%s %s %s %s %s %s %s %s  %s' "$magenta" "$T3" "$E3" "$R3" "$M3" "$I3" "$N3" "$A3" "$L3" "$reset"
  printf '%s%s %s %s%s\n' "$red" "$G3" "$P3" "$GT3" "$reset"

  printf '%s%s %s %s %s %s %s %s %s  %s' "$magenta" "$T4" "$E4" "$R4" "$M4" "$I4" "$N4" "$A4" "$L4" "$reset"
  printf '%s%s %s %s%s\n' "$red" "$G4" "$P4" "$GT4" "$reset"

  printf '%s%s %s %s %s %s %s %s %s  %s' "$magenta" "$T5" "$E5" "$R5" "$M5" "$I5" "$N5" "$A5" "$L5" "$reset"
  printf '%s%s %s %s%s\n' "$red" "$G5" "$P5" "$GT5" "$reset"

  printf '%s%s %s %s %s %s %s %s %s  %s' "$magenta" "$T6" "$E6" "$R6" "$M6" "$I6" "$N6" "$A6" "$L6" "$reset"
  printf '%s%s %s %s%s\n' "$red" "$G6" "$P6" "$GT6" "$reset"

  printf '%s  ░▒▓%sTERMINAL%s▓▒░     ░▒▓%sGPT%s▓▒░%s\n' "$cyan" "$magenta" "$reset" "$red" "$reset" "$cyan"
  printf '%s────────────────────────────────────────────────────────────────────────────────────────────%s\n' "$cyan" "$reset"
  printf '%s                 %sTERMINAL-FIRST AI AGENT FOR YOUR SYSTEM%s                 %s\n' "$cyan" "$white" "$reset" "$cyan"
  printf '%s────────────────────────────────────────────────────────────────────────────────────────────%s\n\n' "$cyan" "$reset"

  printf '%sTerminalGPT%s is a terminal-first AI agent that can reason about your machine,\n' "$white" "$reset"
  printf 'inspect files and system state, run approved shell commands, and use browser-based\n'
  printf 'human approval before performing sensitive actions.\n\n'
  printf '%sThis installer will download the latest TerminalGPT source from GitHub,%s\n' "$gray" "$reset"
  printf 'create an isolated Python environment, install dependencies, and install\n'
  printf 'the %sterminalgpt%s command under %s%s%s.\n\n' "$white" "$reset" "$white" "$BIN_DIR" "$reset"

  if [[ "${TERMINALGPT_ASSUME_YES:-0}" == "1" ]]; then
    return 0
  fi

  if [[ ! -r /dev/tty ]]; then
    printf '%sUnable to read confirmation from the terminal.%s\n' "$red" "$reset"
    exit 1
  fi

  local answer
  while true; do
    printf '%sContinue with installation? [Y/n]: %s' "$cyan" "$reset"
    IFS= read -r answer < /dev/tty || exit 1
    answer="${answer:-Y}"
    case "$answer" in
      Y|y|yes|YES|Yes) printf '\n'; return 0 ;;
      N|n|no|NO|No) printf 'Installation cancelled.\n'; exit 0 ;;
      *) printf '%sPlease answer Y or N.%s\n' "$red" "$reset" ;;
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
