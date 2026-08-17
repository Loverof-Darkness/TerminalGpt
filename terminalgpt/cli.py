from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.panel import Panel

from .agent import run_agent
from .config import settings
from .memory import MemoryStore
from .state import SessionState

app = typer.Typer(add_completion=False)
console = Console()


@app.command()
def start():
    """Start the legacy local control plane."""
    from .config import settings as cfg
    import uvicorn
    from .server import app as fastapi_app

    uvicorn.run(fastapi_app, host=cfg.server_host, port=cfg.server_port)


class ThinkingIndicator:
    def __init__(self) -> None:
        self._status = None

    def start(self, text: str = "Thinking") -> None:
        if self._status is None:
            self._status = console.status(f"[cyan]{text}...[/cyan]", spinner="dots")
            self._status.start()

    def stop(self) -> None:
        if self._status is not None:
            self._status.stop()
            self._status = None


async def terminal_approval(command: str, thinking: ThinkingIndicator) -> bool:
    thinking.stop()
    console.print(
        Panel(
            f"[bold white]{command}[/bold white]",
            title="TerminalGPT command approval",
            border_style="yellow",
        )
    )
    while True:
        answer = console.input("[bold yellow]Approve this command? [Y/N]: [/bold yellow]").strip().lower()
        if answer in {"y", "yes"}:
            thinking.start("Running command")
            return True
        if answer in {"n", "no", ""}:
            return False
        console.print("[yellow]Please enter Y or N.[/yellow]")


async def interactive_chat() -> None:
    state = SessionState()
    thinking = ThinkingIndicator()
    console.print(
        Panel.fit(
            "[bold green]TerminalGPT is ready.[/bold green]\n"
            f"Provider: {settings.provider} | Model: {settings.model}\n"
            "Persistent local memory: enabled\n"
            "Command approvals: terminal Y/N",
            title="TerminalGPT",
        )
    )
    console.print("Type /exit to quit. Type /memory clear to erase saved conversation memory.")

    while True:
        message = console.input("[bold cyan]you[/bold cyan]: ").strip()
        command = message.lower()
        if command in {"/exit", "/quit"}:
            thinking.stop()
            break
        if command == "/memory clear":
            thinking.stop()
            MemoryStore(settings.memory_path).clear()
            console.print("[green]✓ Persistent memory cleared.[/green]")
            continue
        if not message:
            continue

        try:
            thinking.start("Thinking")
            approval = lambda cmd: terminal_approval(cmd, thinking)
            output = await run_agent(message, state, approval)
            thinking.stop()
            console.print(Panel(output, title="TerminalGPT"))
        except Exception as exc:
            thinking.stop()
            console.print(f"[red]Error:[/red] {type(exc).__name__}: {exc}")


@app.command()
def chat():
    """Run TerminalGPT directly in the terminal without browser pairing."""
    asyncio.run(interactive_chat())


if __name__ == "__main__":
    app()
