#!/usr/bin/env bash
set -euo pipefail

REPO="https://github.com/Loverof-Darkness/TerminalGpt.git"
INSTALL_ROOT="${TERMINALGPT_HOME:-$HOME/.local/share/terminalgpt}"
BIN_DIR="${TERMINALGPT_BIN_DIR:-$HOME/.local/bin}"
VENV="$INSTALL_ROOT/venv"
TMP_DIR="$(mktemp -d)"
AUTH_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/terminalgpt"
AUTH_FILE="$AUTH_DIR/auth.env"
trap 'rm -rf "$TMP_DIR"' EXIT

curl -fsSL "https://raw.githubusercontent.com/Loverof-Darkness/TerminalGpt/main/installer_banner.sh" -o "$TMP_DIR/banner.sh"
# shellcheck disable=SC1091
source "$TMP_DIR/banner.sh"
show_loading
show_welcome || exit 0

command -v python3 >/dev/null 2>&1 || { echo "TerminalGPT requires Python 3.11+." >&2; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "TerminalGPT requires curl." >&2; exit 1; }
python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)' || { echo "TerminalGPT requires Python 3.11+." >&2; exit 1; }

mkdir -p "$INSTALL_ROOT" "$BIN_DIR" "$AUTH_DIR"
chmod 700 "$AUTH_DIR"

printf '\033[1;36mChoose an online AI provider:\033[0m\n'
printf '  [1] NVIDIA NIM  — hosted cloud model / free endpoint\n'
printf '  [2] OpenAI API  — hosted cloud model\n\n'
printf 'Provider [1]: '
IFS= read -r provider_choice < /dev/tty
provider_choice="${provider_choice:-1}"

case "$provider_choice" in
  1)
    PROVIDER="nvidia"
    KEY_NAME="NVIDIA_API_KEY"
    MODEL="${TERMINALGPT_MODEL:-openai/gpt-oss-120b}"
    BASE_URL="https://integrate.api.nvidia.com/v1"
    VALIDATE_URL="$BASE_URL/models"
    LABEL="NVIDIA API key"
    ;;
  2)
    PROVIDER="openai"
    KEY_NAME="OPENAI_API_KEY"
    MODEL="${TERMINALGPT_MODEL:-gpt-5.5}"
    BASE_URL="https://api.openai.com/v1"
    VALIDATE_URL="$BASE_URL/models"
    LABEL="OpenAI API key"
    ;;
  *)
    echo "Invalid provider choice." >&2
    exit 1
    ;;
esac

validate_key() {
  local key="$1" code
  code=$(curl -sS -o /dev/null -w '%{http_code}' -H "Authorization: Bearer ${key}" "$VALIDATE_URL" || true)
  printf '%s' "$code"
}

load_saved_key() {
  [[ -s "$AUTH_FILE" ]] || return 1
  # shellcheck disable=SC1090
  source "$AUTH_FILE"
  local saved=""
  if [[ "$PROVIDER" == "nvidia" ]]; then saved="${NVIDIA_API_KEY:-}"; else saved="${OPENAI_API_KEY:-}"; fi
  [[ -n "$saved" ]] || return 1
  local code
  code=$(validate_key "$saved")
  if [[ "$code" == 2* ]]; then
    printf '\033[1;32m✓ Saved %s is valid.\033[0m\n' "$LABEL"
    return 0
  fi
  printf '\033[1;33mSaved %s is invalid or expired (HTTP %s).\033[0m\n' "$LABEL" "$code"
  return 1
}

if ! load_saved_key; then
  key=""
  if [[ "$PROVIDER" == "nvidia" && -n "${NVIDIA_API_KEY:-}" ]]; then key="$NVIDIA_API_KEY"; fi
  if [[ "$PROVIDER" == "openai" && -n "${OPENAI_API_KEY:-}" ]]; then key="$OPENAI_API_KEY"; fi

  while [[ -z "$key" ]]; do
    printf '\n\033[1;36m%s authorization\033[0m\n' "$PROVIDER"
    printf 'Enter %s. Input is hidden and stored locally with mode 600.\n\n' "$LABEL"
    printf '\033[1;36m%s: \033[0m' "$LABEL"
    IFS= read -r -s key < /dev/tty || exit 1
    printf '\n'
    [[ -n "$key" ]] || { printf '\033[1;31mKey cannot be empty.\033[0m\n'; key=""; }
  done

  printf '\033[1;36mAuthorizing online...\033[0m\n'
  code=$(validate_key "$key")
  if [[ "$code" != 2* ]]; then
    printf '\033[1;31m✗ %s rejected (HTTP %s).\033[0m\n' "$LABEL" "$code"
    exit 1
  fi

  {
    printf 'TERMINALGPT_PROVIDER=%q\n' "$PROVIDER"
    printf 'TERMINALGPT_MODEL=%q\n' "$MODEL"
    printf 'TERMINALGPT_BASE_URL=%q\n' "$BASE_URL"
    printf 'TERMINALGPT_API_KEY_ENV=%q\n' "$KEY_NAME"
    printf '%s=%q\n' "$KEY_NAME" "$key"
  } > "$AUTH_FILE"
  chmod 600 "$AUTH_FILE"
  unset key
  printf '\033[1;32m✓ Online AI provider authorized successfully.\033[0m\n'
fi

if command -v git >/dev/null 2>&1; then
  git clone --depth 1 --filter=blob:none "$REPO" "$TMP_DIR/src" >/dev/null 2>&1
else
  curl -fsSL "https://github.com/Loverof-Darkness/TerminalGpt/archive/refs/heads/main.tar.gz" -o "$TMP_DIR/repo.tar.gz"
  mkdir -p "$TMP_DIR/src"
  tar -xzf "$TMP_DIR/repo.tar.gz" --strip-components=1 -C "$TMP_DIR/src"
fi

rm -rf "$VENV"
python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip >/dev/null
"$VENV/bin/python" -m pip install "$TMP_DIR/src" >/dev/null

cat > "$BIN_DIR/terminalgpt" <<EOF
#!/usr/bin/env bash
set -euo pipefail
AUTH_FILE="$AUTH_FILE"
if [[ -f "\$AUTH_FILE" ]]; then
  # Export all provider configuration to the Python child process.
  set -a
  # shellcheck disable=SC1090
  source "\$AUTH_FILE"
  set +a
fi
exec "$VENV/bin/terminalgpt" "\$@"
EOF
chmod +x "$BIN_DIR/terminalgpt"

case "${SHELL:-}" in
  */fish)
    FISH_CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/fish/config.fish"
    mkdir -p "$(dirname "$FISH_CONFIG")"; touch "$FISH_CONFIG"
    grep -Fqx "fish_add_path $BIN_DIR" "$FISH_CONFIG" 2>/dev/null || echo "fish_add_path $BIN_DIR" >> "$FISH_CONFIG"
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

printf '\n\033[1;32m✓ TerminalGPT installed successfully.\033[0m\n'
printf '\033[1;36mProvider:\033[0m %s\n' "$PROVIDER"
printf '\033[1;36mModel:\033[0m %s\n' "$MODEL"
printf '\033[1;36mInference:\033[0m Online / cloud\n'
printf '\nRun: terminalgpt chat\n'
