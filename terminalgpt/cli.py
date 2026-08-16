from __future__ import annotations

import asyncio
import secrets
import sys
import webbrowser

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from .config import settings

app = typer.Typer(add_completion=False)
console = Console()


def run_server() -> None:
    import uvicorn
    from .server import app as fastapi_app
    uvicorn.run(fastapi_app, host=settings.server_host, port=settings.server_port)


def server_url() -> str:
    return f"http://{settings.server_host}:{settings.server_port}"


@app.command()
def start():
    """Start the TerminalGPT browser control plane."""
    run_server()


@app.command()
def pair():
    """Create a one-time browser pairing approval page."""
    with httpx.Client() as client:
        response = client.post(f"{server_url()}/api/session", timeout=10)
        response.raise_for_status()
        data = response.json()
    url = server_url() + data["pair_url"]
    console.print(Panel.fit(f"Open once to approve this terminal session:\n{url}"))
    try:
        webbrowser.open(url)
    except Exception:
        pass
    console.print("Pairing token is single-use and expires automatically.")


@app.command()
def chat():
    """Run an interactive terminal session."""
    with httpx.Client() as client:
        response = client.post(f"{server_url()}/api/session", timeout=10)
        response.raise_for_status()
        data = response.json()
    token, session_id = data["token"], data["session_id"]
    url = server_url() + data["pair_url"]
    console.print(Panel.fit(f"Approve this session in a browser:\n{url}"))
    try:
        webbrowser.open(url)
    except Exception:
        pass
    console.print("Type /exit to quit.")
    with httpx.Client(timeout=None) as client:
        while True:
            message = Prompt.ask("[bold cyan]you[/bold cyan]")
            if message.strip().lower() in {"/exit", "/quit"}:
                break
            try:
                r = client.post(f"{server_url()}/api/prompt", json={"token": token, "session_id": session_id, "message": message})
                r.raise_for_status()
                console.print(Panel(r.json()["output"], title="TerminalGPT"))
            except Exception as exc:
                console.print(f"[red]Error:[/red] {exc}")


if __name__ == "__main__":
    app()
