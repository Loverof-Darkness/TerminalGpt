from __future__ import annotations

from agents import Agent, Runner

from .config import settings
from .state import SessionState
from .tools import CommandRunner, build_tools, load_tools_from_github


SYSTEM_INSTRUCTIONS = """
You are TerminalGPT, a terminal-first computer agent.

Work iteratively. Inspect the environment before making changes. Explain the plan briefly.
Use execute_command when local inspection or a change is required. Every command is shown to
and approved by the human through the browser control plane before execution. Never attempt to
bypass approval. Prefer safe, reversible commands. For destructive operations, clearly explain
what will happen and ask for approval through the normal tool flow.
""".strip()


def build_agent(state: SessionState, request_approval):
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
    state.emit("agent_started", message=message)
    result = await Runner.run(agent, message)
    state.emit("agent_finished", output=result.final_output)
    return result.final_output
