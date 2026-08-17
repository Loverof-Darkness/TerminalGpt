from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from .agent import run_agent
from .config import settings
from .memory import MemoryStore
from .state import SessionState

app = typer.Typer(add_completion=False)
console = Console()

NVIDIA_MODELS = [
    ("gpt-oss-20b", "Fast general reasoning"),
    ("gpt-oss-120b", "Stronger reasoning / agents"),
    ("deepseek-v4-flash", "Fast coding / agents"),
    ("deepseek-v4-pro", "Advanced reasoning / coding"),
    ("nemotron-3-nano-30b-a3b", "Fast NVIDIA Nemotron"),
    ("nemotron-3-super-120b-a12b", "Strong NVIDIA Nemotron"),
    ("minimax-m3", "Reasoning / coding"),
    ("glm-5.2", "Reasoning / coding"),
]


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


def choose_model(current_model: str) -> str:
    if settings.provider != "nvidia":
        console.print(f"[yellow]Runtime model switching list is currently available for NVIDIA only.[/yellow]\nCurrent model: {current_model}")
        return current_model

    console.print("[bold cyan]Available NVIDIA models:[/bold cyan]")
    for index, (model, description) in enumerate(NVIDIA_MODELS, start=1):
        marker = " [green](current)[/green]" if model == current_model else ""
        console.print(f"  [{index}] {model}{marker} — {description}")
    console.print("  [0] Cancel")

    while True:
        choice = Prompt.ask("Select model", default="0").strip()
        if choice == "0":
            return current_model
        if choice.isdigit() and 1 <= int(choice) <= len(NVIDIA_MODELS):
            selected = NVIDIA_MODELS[int(choice) - 1][0]
            console.print(f"[green]✓ Model changed to {selected}[/green]")
            return selected
        console.print("[yellow]Please choose a valid model number.[/yellow]")


async def interactive_chat() -> None:
    state = SessionState()
    thinking = ThinkingIndicator()
    current_model = settings.model

    console.print(
        Panel.fit(
            "[bold green]TerminalGPT is ready.[/bold green]\n"
            f"Provider: {settings.provider} | Model: {current_model}\n"
            "Persistent local memory: enabled\n"
            "Command approvals: terminal Y/N",
            title="TerminalGPT",
        )
    )
    console.print(
        "Type /exit to quit. Type /model to change model. "
        "Type /memory clear to erase saved conversation memory."
    )

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
        if command == "/model":
            thinking.stop()
            current_model = choose_model(current_model)
            console.print(f"[cyan]Current model:[/cyan] {current_model}")
            continue
        if not message:
            continue

        try:
            thinking.start("Thinking")
            approval = lambda cmd: terminal_approval(cmd, thinking)
            output = await run_agent(message, state, approval, model=current_model)
            thinking.stop()
            console.print(Panel(output, title=f"TerminalGPT · {current_model}"))
        except Exception as exc:
            thinking.stop()
            console.print(f"[red]Error:[/red] {type(exc).__name__}: {exc}")


@app.command()
def chat():
    """Run TerminalGPT directly in the terminal without browser pairing."""
    asyncio.run(interactive_chat())


if __name__ == "__main__":
    app()
