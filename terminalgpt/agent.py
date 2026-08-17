from __future__ import annotations

import json
import re
from typing import Any

from openai import AsyncOpenAI

from .config import settings
from .memory import MemoryStore
from .state import SessionState
from .tools import CommandRunner, load_tools_from_github


SYSTEM_INSTRUCTIONS = """
You are TerminalGPT, an online terminal-first computer agent.

The model runs in the cloud. The user's machine is used only for local inspection and
for commands explicitly approved by the user in the terminal.

You have access to persistent local conversation memory. Use prior context when relevant and do
not ask the user to repeat information already available. You may record useful stable facts
about the user/environment when they are explicitly stated or verified. Never invent facts.

Be concise and action-oriented. Work iteratively: inspect only what is needed, execute the
minimum safe command needed, then report the result. Do not suggest extra commands after a
task is complete unless necessary. Every shell command must be shown to and approved by the
human in the terminal before execution. Never bypass approval. Prefer safe, reversible commands.
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


async def run_agent(message: str, state: SessionState, request_approval) -> str:
    client = _client()
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
    state.emit("agent_started", message=message, provider=settings.provider, model=settings.model)

    for _ in range(6):
        response = await client.chat.completions.create(
            model=settings.model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            max_tokens=1024,
            temperature=0.2,
        )

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
            output = assistant.content or ""
            state.emit("agent_finished", output=output)
            return output

        for call in tool_calls:
            name = call.function.name
            try:
                arguments = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError as exc:
                result = f"Invalid tool arguments: {exc}"
            else:
                if name == "execute_command":
                    result = await runner.run(str(arguments.get("command", "")))
                elif name == "read_terminal_output":
                    result = state.last_output or "No terminal output yet."
                else:
                    result = f"Unknown tool: {name}"

            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

    raise RuntimeError("Agent reached the maximum tool-call iterations without a final response.")
