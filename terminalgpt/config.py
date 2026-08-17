from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    provider: str = os.getenv("TERMINALGPT_PROVIDER", "nvidia").lower()
    model: str = os.getenv("TERMINALGPT_MODEL", "openai/gpt-oss-120b")
    base_url: str = os.getenv("TERMINALGPT_BASE_URL", "https://integrate.api.nvidia.com/v1")
    api_key_env: str = os.getenv("TERMINALGPT_API_KEY_ENV", "NVIDIA_API_KEY")
    github_tools_url: str = os.getenv("TERMINALGPT_TOOLS_URL", "")
    workspace: str = os.path.expanduser(os.getenv("TERMINALGPT_WORKSPACE", "~"))

    @property
    def api_key(self) -> str:
        value = os.getenv(self.api_key_env, "").strip()
        if value:
            return value
        if self.provider == "openai":
            return os.getenv("OPENAI_API_KEY", "").strip()
        return ""


settings = Settings()
