from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SENSITIVE_KEYS = {
    "source",
    "source_code",
    "raw_output",
    "finding",
    "findings",
    "poc",
    "trace",
    "prompt",
    "response",
    "private_key",
    "api_key",
    "secret",
    "token",
    "signature",
}


class SensitiveScrubber:
    def scrub(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: "[REDACTED]" if self._is_sensitive_key(key) else self.scrub(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [self.scrub(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self.scrub(item) for item in value)
        return value

    def _is_sensitive_key(self, key: str) -> bool:
        key_lower = key.lower()
        return any(marker in key_lower for marker in SENSITIVE_KEYS)


@dataclass(frozen=True)
class LlmCostEvent:
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    estimated_cost_usd: float
    layer: str
    audit_id: str | None = None


@dataclass
class LlmCostLedger:
    events: list[LlmCostEvent] = field(default_factory=list)

    def record(self, event: LlmCostEvent) -> None:
        self.events.append(event)

    def total_cost_usd(self) -> float:
        return round(sum(event.estimated_cost_usd for event in self.events), 6)

    def summary(self) -> dict[str, object]:
        return {
            "event_count": len(self.events),
            "total_cost_usd": self.total_cost_usd(),
            "by_layer": self._sum_by("layer"),
            "by_provider": self._sum_by("provider"),
        }

    def _sum_by(self, field_name: str) -> dict[str, float]:
        totals: dict[str, float] = {}
        for event in self.events:
            key = str(getattr(event, field_name))
            totals[key] = round(totals.get(key, 0.0) + event.estimated_cost_usd, 6)
        return totals
