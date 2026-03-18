"""Skill-layer contracts bridging subagents and low-level tools."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass(slots=True)
class SkillContract:
    """Capability contract describing one reusable domain skill."""

    name: str
    description: str
    tool_names: list[str] = field(default_factory=list)
    allowed_subagents: list[str] = field(default_factory=list)
    freshness_policy: str = "best_effort"
    fallback_policy: str = "graceful_degrade"
    output_artifact: Optional[str] = None
    evidence_required: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary for diagnostics and docs."""
        return asdict(self)
