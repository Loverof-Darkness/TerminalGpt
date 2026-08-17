from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from .agent import run_agent
from .state import SessionState

app = typer.Typer(add_completion=False)
console = Console()


@app.command()
def start():
    """Start the legacy local control plane."""
    from .config import settings
    import uvicorn
    from .server import app as fastapi_app

    uvicorn.run(fastapi_app, host=settings.server_host, port=settings.server_port)


async def terminal_approval(command: str) -> bool:
    console.print(Panel(command, title="TerminalGPT command approval", border_style="yellow"))
    answer = Prompt.ask("Approve this command? [y/N]", default="N")
    return answer.strip().lower() in {"y", "yes"}


async def interactive_chat() -> None:
    state = SessionState()
    console.print(
        Panel.fit(
            "[bold green]TerminalGPT is ready.[/bold green]\n"
            "API key authorization is already configured.\n"
            "Browser authentication is disabled.\n"
            "Command approvals will appear here in the terminal.",
            title="TerminalGPT",
        )
    )
    console.print("Type /exit to quit.")

    while True:
        message = Prompt.ask("[bold cyan]you[/bold cyan]")
        if message.strip().lower() in {"/exit", "/quit"}:
            break
        if not message.strip():
            continue

        try:
            output = await run_agent(message, state, terminal_approval)
            console.print(Panel(output, title="TerminalGPT"))
        except Exception as exc:
            console.print(f"[red]Error:[/red] {type(exc).__name__}: {exc}")


@app.command()
def chat():
    """Run TerminalGPT directly in the terminal without browser pairing."""
    asyncio.run(interactive_chat())


if __name__ == "__main__":
    app()
