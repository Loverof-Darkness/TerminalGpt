from __future__ import annotations

import asyncio
import os
from typing import Any, Awaitable, Callable

from agents import function_tool

from .state import SessionState


async def _exec_command(command: str, cwd: str, timeout: int = 120) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_shell(
        command,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        executable=os.environ.get("SHELL", "/bin/sh"),
    )
    try:
        output, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        output, _ = await proc.communicate()
        return 124, (output or b"").decode(errors="replace") + "\n[command timed out]"
    return proc.returncode or 0, output.decode(errors="replace")


class CommandRunner:
    def __init__(self, state: SessionState, workspace: str, request_approval: Callable[[str], Awaitable[bool]]):
        self.state = state
        self.workspace = os.path.abspath(os.path.expanduser(workspace))
        self.request_approval = request_approval

    async def run(self, command: str) -> str:
        approved = await self.request_approval(command)
        if not approved:
            return "Command rejected by the user."
        self.state.emit("command_started", command=command)
        code, output = await _exec_command(command, self.workspace)
        self.state.last_output = output
        self.state.emit("command_finished", command=command, returncode=code, output=output)
        return f"exit_code={code}\n{output}"


def build_tools(runner: CommandRunner):
    # Browser approval is implemented by CommandRunner/request_approval. Do not also
    # request an Agents SDK interruption here, otherwise Runner.run would return an
    # interruption object that this server does not resume.
    @function_tool
    async def execute_command(command: str) -> str:
        """Execute a shell command after browser approval."""
        return await runner.run(command)

    @function_tool
    async def read_terminal_output() -> str:
        """Return the latest terminal command output."""
        return runner.state.last_output or "No terminal output yet."

    return [execute_command, read_terminal_output]


def load_tools_from_github(reference: str) -> list[dict[str, Any]]:
    """Return a manifest describing externally loaded tools.

    Tool code is deliberately not executed directly from an arbitrary URL. A future
    signed-package implementation can use this manifest as the trust boundary.
    """
    if not reference:
        return []
    return [{"source": reference, "status": "manifest-only"}]
