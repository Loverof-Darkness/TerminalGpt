from __future__ import annotations

import subprocess
import sys
import threading
import time

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


def _approve_pending(token: str, session_id: str) -> None:
    """Poll the local control plane and resolve command approvals in the terminal."""
    seen: set[str] = set()
    url = server_url()
    with httpx.Client(timeout=10) as client:
        while True:
            try:
                response = client.get(
                    f"{url}/api/state",
                    params={"token": token, "session_id": session_id},
                    timeout=2,
                )
                response.raise_for_status()
                pending = response.json().get("pending_approvals", [])
            except Exception:
                return

            for approval in pending:
                approval_id = approval.get("id")
                if not approval_id or approval_id in seen:
                    continue
                seen.add(approval_id)
                command = approval.get("command", "")
                console.print(Panel(command, title="Command approval", border_style="yellow"))
                answer = Prompt.ask("Approve this command?", choices=["y", "n"], default="n")
                try:
                    client.post(
                        f"{url}/api/approve",
                        json={
                            "token": token,
                            "session_id": session_id,
                            "approval_id": approval_id,
                            "approved": answer.lower() == "y",
                        },
                        timeout=5,
                    )
                except Exception:
                    return
            time.sleep(0.15)


@app.command()
def start():
    """Start the TerminalGPT local control plane."""
    run_server()


@app.command()
def pair():
    """Create an optional browser pairing page for the local control plane."""
    ensure_server()
    with httpx.Client() as client:
        response = client.post(f"{server_url()}/api/session", timeout=10)
        response.raise_for_status()
        data = response.json()
    console.print(Panel.fit("Browser pairing is optional. Use `terminalgpt chat` for terminal-only mode."))
    console.print(f"Session created: {data['session_id']}")


@app.command()
def chat():
    """Run an interactive terminal-only session using the stored OpenAI API key."""
    server_process = ensure_server()
    try:
        with httpx.Client() as client:
            response = client.post(f"{server_url()}/api/session", timeout=10)
            response.raise_for_status()
            data = response.json()
        token, session_id = data["token"], data["session_id"]

        console.print(Panel.fit("TerminalGPT is ready. Browser authentication is disabled.\nCommand approvals will appear here in the terminal."))
        console.print("Type /exit to quit.")

        with httpx.Client(timeout=None) as client:
            while True:
                message = Prompt.ask("[bold cyan]you[/bold cyan]")
                if message.strip().lower() in {"/exit", "/quit"}:
                    break

                result: dict[str, str] = {}
                error: list[Exception] = []

                def submit_prompt() -> None:
                    try:
                        r = client.post(
                            f"{server_url()}/api/prompt",
                            json={"token": token, "session_id": session_id, "message": message},
                        )
                        r.raise_for_status()
                        result["output"] = r.json()["output"]
                    except Exception as exc:
                        error.append(exc)

                worker = threading.Thread(target=submit_prompt, daemon=True)
                worker.start()
                _approve_pending(token, session_id)
                worker.join()

                if error:
                    console.print(f"[red]Error:[/red] {error[0]}")
                elif "output" in result:
                    console.print(Panel(result["output"], title="TerminalGPT"))
    finally:
        if server_process is not None:
            server_process.terminate()
            try:
                server_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                server_process.kill()


if __name__ == "__main__":
    app()
