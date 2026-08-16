from __future__ import annotations

import subprocess
import sys
import time
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
    host = "127.0.0.1" if settings.server_host in {"0.0.0.0", "::"} else settings.server_host
    return f"http://{host}:{settings.server_port}"


def ensure_server() -> subprocess.Popen | None:
    """Start the local control plane if it is not already running."""
    url = server_url()
    try:
        with httpx.Client() as client:
            client.get(f"{url}/health", timeout=1)
        return None
    except Exception:
        pass

    process = subprocess.Popen(
        [sys.executable, "-m", "terminalgpt.cli", "start"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for _ in range(50):
        time.sleep(0.1)
        try:
            with httpx.Client() as client:
                client.get(f"{url}/health", timeout=0.5)
            return process
        except Exception:
            if process.poll() is not None:
                raise RuntimeError("TerminalGPT control server exited during startup")

    process.terminate()
    raise RuntimeError(f"TerminalGPT control server did not start at {url}")


@app.command()
def start():
    """Start the TerminalGPT browser control plane."""
    run_server()


@app.command()
def pair():
    """Create a one-time browser pairing approval page."""
    ensure_server()
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
    """Run an interactive terminal session and automatically start the local control plane."""
    server_process = ensure_server()
    try:
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
                    r = client.post(
                        f"{server_url()}/api/prompt",
                        json={"token": token, "session_id": session_id, "message": message},
                    )
                    r.raise_for_status()
                    console.print(Panel(r.json()["output"], title="TerminalGPT"))
                except Exception as exc:
                    console.print(f"[red]Error:[/red] {exc}")
    finally:
        if server_process is not None:
            server_process.terminate()
            try:
                server_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                server_process.kill()


if __name__ == "__main__":
    app()
