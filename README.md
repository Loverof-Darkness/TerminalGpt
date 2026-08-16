# TerminalGPT

A terminal-first OpenAI agent with a one-time browser approval/control plane.

The repository is intentionally small and uses the OpenAI Agents SDK. The agent can reason about the local machine, request shell-command execution, keep command output in session state, and pause until a human approves the requested command in the browser. The approval model follows the Agents SDK human-in-the-loop pattern: sensitive tool execution must be approved before the side effect happens. See: https://openai.github.io/openai-agents-python/human_in_the_loop/

## Architecture

```text
Terminal CLI
   |
   | local HTTP
   v
FastAPI control plane <---- browser approval console
   |
   +---- one-time pairing token
   +---- session/event state
   |
   v
OpenAI Agents SDK
   |
   +---- execute_command (approval required)
   +---- read_terminal_output
   |
   v
Local shell
```

The browser is a control/approval surface, not an unauthenticated remote shell. Commands are never executed merely because an HTTP endpoint is reachable; a terminal session must first be paired and shell tool calls enter an approval gate.

## Requirements

- Python 3.11+
- An OpenAI API key in `OPENAI_API_KEY`
- `uv` recommended

Install:

```bash
uv sync
```

Start the control server:

```bash
uv run terminalgpt start
```

Start an interactive terminal client:

```bash
uv run terminalgpt chat
```

The client generates a one-time browser URL. Approve the session in the browser, then continue from the terminal.

## Configuration

```bash
export OPENAI_API_KEY="..."
export TERMINALGPT_MODEL="gpt-5.6"
export TERMINALGPT_HOST="127.0.0.1"
export TERMINALGPT_PORT="8765"
export TERMINALGPT_WORKSPACE="$HOME"
```

## GitHub tool loading

The design reserves `TERMINALGPT_TOOLS_URL` for a GitHub-hosted signed tool manifest. Remote Python is **not** executed directly from an arbitrary URL. A production package loader should verify repository identity, commit/tag pinning, file hashes/signatures, declared permissions, and user approval before enabling a tool.

A convenient future single-line interface is intended to look like:

```bash
terminalgpt tools add github:Loverof-Darkness/SomeTool@v1.0.0
```

This preserves the requested one-line GitHub installation model without the unsafe pattern of executing untrusted source fetched from a URL.

## Security notes

- Keep the control server bound to `127.0.0.1` unless you explicitly add TLS/authentication.
- Do not expose the pairing endpoint to the public internet.
- Use a dedicated non-root user/workspace for agent execution.
- Keep destructive commands behind approval.
- For remote browser control, add real authentication, TLS, CSRF protection, rate limiting, and signed session claims before deployment.
