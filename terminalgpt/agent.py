from __future__ import annotations

from agents import Agent, Runner, set_default_openai_api, set_default_openai_client, set_tracing_disabled
from openai import AsyncOpenAI

from .config import settings
from .state import SessionState
from .tools import CommandRunner, build_tools, load_tools_from_github


SYSTEM_INSTRUCTIONS = """
You are TerminalGPT, a terminal-first computer agent.

You are an online AI agent. Never assume a local model is being used.
Work iteratively. Inspect the environment before making changes. Explain the plan briefly.
Use execute_command when local inspection or a change is required. Every command is shown to
and approved by the human in the terminal before execution. Never bypass command approval.
Prefer safe, reversible commands. For destructive commands, clearly explain what will happen
and wait for the normal terminal approval flow.
""".strip()


def _configure_provider() -> None:
    if not settings.api_key:
        raise RuntimeError(
            f"No API key configured for provider '{settings.provider}'. "
            f"Set {settings.api_key_env} before starting TerminalGPT."
        )

    client = AsyncOpenAI(api_key=settings.api_key, base_url=settings.base_url)
    set_default_openai_client(client, use_for_tracing=False)
    set_default_openai_api("chat_completions")
    set_tracing_disabled(True)


def build_agent(state: SessionState, request_approval):
    _configure_provider()
    runner = CommandRunner(state, settings.workspace, request_approval)
    tools = build_tools(runner)
    external = load_tools_from_github(settings.github_tools_url)
    if external:
        state.emit("external_tools_loaded", manifest=external)
    return Agent(
        name="TerminalGPT",
        instructions=SYSTEM_INSTRUCTIONS,
        model=settings.model,
        tools=tools,
    )


async def run_agent(message: str, state: SessionState, request_approval):
    agent = build_agent(state, request_approval)
    state.emit("agent_started", message=message, provider=settings.provider, model=settings.model)
    result = await Runner.run(agent, message)
    state.emit("agent_finished", output=result.final_output)
    return result.final_output
