"""Provider-neutral structured analysis adapter.

The MVP uses DemoLLMAdapter so local development never requires a provider key.
Production adapters can implement the same protocol and return validated dicts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class LLMAdapter(Protocol):
    name: str
    version: str

    def analyze(self, *, task: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Return structured analysis without performing file operations."""


@dataclass(frozen=True)
class DemoLLMAdapter:
    name: str = "demo"
    version: str = "0.1"

    def analyze(self, *, task: str, payload: dict[str, Any]) -> dict[str, Any]:
        slide_count = len(payload.get("slides", []))
        if task == "storyline":
            return {
                "audience": "科技商业比赛评委",
                "thesis": "用可验证的技术方案解决真实场景中的高价值问题",
                "stages": ["问题与机会", "技术方案", "验证与壁垒", "商业化与团队"],
                "slide_count": slide_count,
            }
        return {"task": task, "slide_count": slide_count, "suggestions": []}
