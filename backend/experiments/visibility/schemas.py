"""影子实验的稳定数据结构。"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class RenderedQuestion:
    id: str
    intent_type: str
    branded: bool
    text: str
    purpose: str


@dataclass
class ShadowObservation:
    experiment_id: str
    question_id: str
    intent_type: str
    branded: bool
    question_text: str
    purpose: str
    provider: str
    configured_model: str
    response_model: str | None
    mode: str
    sample_index: int
    status: str
    answer: str = ""
    sources: list[dict[str, Any]] = field(default_factory=list)
    request_id: str | None = None
    latency_ms: int | None = None
    usage: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None
    collected_at: str | None = None
    current_analyzer: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
