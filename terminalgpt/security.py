from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field


@dataclass
class PairingStore:
    ttl_seconds: int = 600
    _tokens: dict[str, tuple[float, bool]] = field(default_factory=dict)

    def create(self) -> str:
        token = secrets.token_urlsafe(32)
        self._tokens[token] = (time.time() + self.ttl_seconds, False)
        return token

    def approve(self, token: str) -> bool:
        row = self._tokens.get(token)
        if not row:
            return False
        expires_at, used = row
        if used or time.time() > expires_at:
            return False
        self._tokens[token] = (expires_at, True)
        return True

    def valid(self, token: str) -> bool:
        row = self._tokens.get(token)
        if not row:
            return False
        expires_at, used = row
        return used and time.time() <= expires_at
