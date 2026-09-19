from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


MessageRole = Literal[
    "system",
    "user",
    "assistant",
    "tool"
]


@dataclass(slots=True)
class ConversationMessage:

    role: MessageRole

    content: str

    message_id: str | None = None

    timestamp: datetime | None = None

    tool_name: str | None = None

    metadata: dict = field(
        default_factory=dict
    )


@dataclass(slots=True)
class Conversation:

    conversation_id: str

    document_id: str

    messages: list[ConversationMessage] = field(
        default_factory=list
    )

    max_memory_messages: int = 15

    created_at: datetime | None = None

    updated_at: datetime | None = None

    def add_message(
        self,
        message: ConversationMessage
    ) -> None:

        self.messages.append(message)

        if (
            len(self.messages)
            > self.max_memory_messages
        ):
            self.messages = self.messages[
                -self.max_memory_messages:
            ]

    def recent_messages(
        self,
        limit: int | None = None
    ) -> list[ConversationMessage]:

        limit = (
            limit
            if limit is not None
            else self.max_memory_messages
        )

        return self.messages[-limit:]