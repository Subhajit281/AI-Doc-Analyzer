from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ToolExecution:

    tool_name: str

    input: dict[str, Any] = field(
        default_factory=dict
    )

    output: Any = None

    success: bool = True

    error: str | None = None

    duration_ms: float | None = None


@dataclass(slots=True)
class AgentResponse:

    answer: str

    document_id: str | None = None

    conversation_id: str | None = None

    sources: list[dict[str, Any]] = field(
        default_factory=list
    )

    tools_used: list[str] = field(
        default_factory=list
    )

    reasoning_used: bool = False

    metadata: dict[str, Any] = field(
        default_factory=dict
    )