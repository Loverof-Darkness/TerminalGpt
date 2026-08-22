from __future__ import annotations

import json
import re
from typing import Any

from openai import APIStatusError, AsyncOpenAI

from .config import settings
from .memory import MemoryStore
from .state import SessionState
from .tools import CommandRunner, load_tools_from_github


SYSTEM_INSTRUCTIONS = """
You are TerminalGPT, an online terminal-first computer agent.

The model runs in the cloud. The user's machine is used only for local inspection and for commands explicitly approved by the user in the terminal.

You have access to persistent local conversation memory. Use prior context when relevant and do not ask the user to repeat information already available. You may record useful stable facts about the user/environment when they are explicitly stated or verified. Never invent facts.

Be concise and action-oriented. Work iteratively: inspect only what is needed, execute the minimum safe command needed, then report the result.

Before EVERY tool call, determine what NEW information the tool call will provide. Do not execute a command merely because it is syntactically different from a command already executed if it is semantically equivalent.

Never repeatedly modify a diagnostic command with grep, awk, head, sed, pipes, or similar wrappers when the underlying command has already failed to provide the requested information. Change diagnostic strategy instead.

Track the user's exact request. Pay attention to time scope such as current boot versus previous/last boot. Do not use a current-boot diagnostic as if it were historical data.

If a command fails, inspect its result and either choose a materially different approach or explain the limitation. Do not blindly retry equivalent commands.

Stop using tools as soon as the task is solved. If the requested information cannot be reliably obtained, give the user a useful final response explaining what was checked and what cannot be established.

Every shell command must be shown to and approved by the human in the terminal before execution. Never bypass approval. Prefer safe, reversible commands.
""".strip()


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "Execute a shell command on the user's machine after terminal approval.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_terminal_output",
            "description": "Read the most recent command output from the user's machine.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
]


FALLBACK_MODELS = (
    "deepseek-ai/deepseek-v4-flash-0731",
    "openai/gpt-oss-20b",
)


def _client() -> AsyncOpenAI:
    api_key = settings.api_key
    if not api_key:
        raise RuntimeError(
            f"No API key configured for provider '{settings.provider}'. "
            f"Set {settings.api_key_env} before starting TerminalGPT."
        )
    return AsyncOpenAI(api_key=api_key, base_url=settings.base_url)


def _learn_explicit_facts(memory: MemoryStore, text: str) -> None:
    patterns = {
        "distribution": r"\b(?:i am|i'm|im) using\s+(Garuda Linux)\b",
        "shell": r"\b(?:i use|i'm using)\s+(fish|zsh|bash)\s*(?:shell)?\b",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            memory.set_fact(key, match.group(1).strip())


def _command_fingerprint(command: str) -> str:
    """Conservatively fingerprint commands to catch repeated diagnostics."""
    normalized = re.sub(r"\s+", " ", command.strip().lower())
    normalized = re.sub(r"2>/dev/null", "", normalized)
    base = normalized.split("|", 1)[0].strip()
    return re.sub(r"\s+", " ", base)


def _is_model_gone(exc: Exception) -> bool:
    if isinstance(exc, APIStatusError):
        return exc.status_code in {404, 410}
    text = str(exc).lower()
    return "410" in text or "404" in text or "end of life" in text or "no longer available" in text


async def _completion_with_fallback(client: AsyncOpenAI, selected_model: str, messages: list[dict[str, Any]]) -> tuple[Any, str]:
    candidates = [selected_model, *FALLBACK_MODELS]
    tried: set[str] = set()
    last_error: Exception | None = None

    for candidate in candidates:
        if candidate in tried:
            continue
        tried.add(candidate)
        try:
            response = await client.chat.completions.create(
                model=candidate,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                max_tokens=2048,
                temperature=0.2,
            )
            return response, candidate
        except Exception as exc:
            last_error = exc
            if not _is_model_gone(exc):
                raise

    raise RuntimeError(
        f"The selected model '{selected_model}' is unavailable and all configured fallback models failed."
    ) from last_error


async def run_agent(
    message: str,
    state: SessionState,
    request_approval,
    model: str | None = None,
) -> str:
    client = _client()
    selected_model = model or settings.model
    runner = CommandRunner(state, settings.workspace, request_approval)
    memory = MemoryStore(settings.memory_path)

    _learn_explicit_facts(memory, message)

    external = load_tools_from_github(settings.github_tools_url)
    if external:
        state.emit("external_tools_loaded", manifest=external)

    messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_INSTRUCTIONS}]
    messages.extend(memory.prompt_context(settings.memory_messages))
    messages.append({"role": "user", "content": message})

    memory.add_message("user", message)
    state.emit("agent_started", message=message, provider=settings.provider, model=selected_model)

    max_iterations = 12
    last_fingerprints: list[str] = []

    for iteration in range(max_iterations):
        response, active_model = await _completion_with_fallback(client, selected_model, messages)
        if active_model != selected_model:
            state.emit("model_fallback", from_model=selected_model, to_model=active_model)
            selected_model = active_model

        assistant = response.choices[0].message
        tool_calls = assistant.tool_calls or []
        messages.append(
            {
                "role": "assistant",
                "content": assistant.content or "",
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in tool_calls
                ],
            }
        )

        if assistant.content:
            memory.add_message("assistant", assistant.content)

        if not tool_calls:
            output = assistant.content or "I completed the available checks but there is no additional result to report."
            state.emit("agent_finished", output=output, model=selected_model, iterations=iteration + 1)
            return output

        made_progress = False

        for call in tool_calls:
            name = call.function.name
            try:
                arguments = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError as exc:
                result = f"Invalid tool arguments: {exc}"
            else:
                if name == "execute_command":
                    command = str(arguments.get("command", "")).strip()
                    fingerprint = _command_fingerprint(command)

                    if not command:
                        result = "No command was supplied. Choose a valid command or provide a final answer."
                    elif state.has_recent_command(fingerprint):
                        state.strategy_repeats += 1
                        result = (
                            "DUPLICATE DIAGNOSTIC BLOCKED: an equivalent command was already executed. "
                            "Do not repeat it with only grep/awk/head/sed/pipe changes. "
                            "Choose a materially different diagnostic strategy or provide the final answer."
                        )
                        state.emit("duplicate_command_blocked", command=command, fingerprint=fingerprint)
                    else:
                        result = await runner.run(command)
                        state.record_command(fingerprint, result)
                        last_fingerprints.append(fingerprint)
                        last_fingerprints = last_fingerprints[-6:]
                        made_progress = True
                elif name == "read_terminal_output":
                    result = state.last_output or "No terminal output yet."
                    made_progress = bool(state.last_output)
                else:
                    result = f"Unknown tool: {name}"

            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

        if state.strategy_repeats >= 3 or (len(last_fingerprints) >= 4 and len(set(last_fingerprints[-4:])) <= 1):
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "STOP REPEATING THE SAME DIAGNOSTIC STRATEGY. You have made no meaningful progress. "
                        "Do not issue another equivalent command. Choose a genuinely different diagnostic strategy "
                        "or provide the best final answer with an explicit limitation."
                    ),
                }
            )
            state.emit("agent_stagnation_detected", iteration=iteration + 1)
            state.strategy_repeats = 0

        if not made_progress and iteration >= 2:
            messages.append(
                {
                    "role": "user",
                    "content": "No new information was obtained in this step. Prefer a final answer unless a materially different action is necessary.",
                }
            )

    # Never leak a raw iteration RuntimeError to the interactive CLI. Add a final user
    # instruction so the message ordering remains valid for OpenAI-compatible APIs.
    final_messages = messages + [
        {
            "role": "user",
            "content": (
                "The tool-call budget is exhausted. Do not call any more tools. Give the user the best concise "
                "final answer using only the information already gathered, including any limitation."
            ),
        }
    ]
    final_response, active_model = await _completion_with_fallback(client, selected_model, final_messages)
    output = final_response.choices[0].message.content or "I could not complete the task within the available tool-call budget."
    state.emit("agent_finished", output=output, model=active_model, iterations=max_iterations, budget_exhausted=True)
    memory.add_message("assistant", output)
    return output
