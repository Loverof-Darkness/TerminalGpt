from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    model: str = os.getenv("TERMINALGPT_MODEL", "gpt-5.6")
    server_host: str = os.getenv("TERMINALGPT_HOST", "127.0.0.1")
    server_port: int = int(os.getenv("TERMINALGPT_PORT", "8765"))
    approval_base_url: str = os.getenv("TERMINALGPT_APPROVAL_URL", "http://127.0.0.1:8765")
    github_tools_url: str = os.getenv("TERMINALGPT_TOOLS_URL", "")
    workspace: str = os.path.expanduser(os.getenv("TERMINALGPT_WORKSPACE", "~"))


settings = Settings()
