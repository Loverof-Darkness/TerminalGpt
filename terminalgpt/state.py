from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Approval:
    id: str
    command: str
    created_at: float = field(default_factory=time.time)
    resolved: bool = False
    approved: bool = False


@dataclass
class SessionState:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    connected: bool = True
    last_output: str = ""
    approvals: dict[str, Approval] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    executed_commands: list[str] = field(default_factory=list)
    command_results: dict[str, str] = field(default_factory=dict)
    strategy_repeats: int = 0
    resume_event: asyncio.Event = field(default_factory=asyncio.Event, repr=False)

    def emit(self, event_type: str, **data: Any) -> None:
        self.events.append({"type": event_type, "ts": time.time(), **data})
        self.events = self.events[-500:]

    def record_command(self, fingerprint: str, result: str) -> None:
        self.executed_commands.append(fingerprint)
        self.executed_commands = self.executed_commands[-50:]
        self.command_results[fingerprint] = result

    def has_recent_command(self, fingerprint: str) -> bool:
        return fingerprint in self.executed_commands
