"""Base channel adapter for multi-platform messaging.

Provides the abstract ChannelAdapter class and MessageContext dataclass
that all platform-specific adapters must implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Optional


@dataclass
class MessageContext:
    """Unified message context from any messaging platform.

    Attributes:
        platform: Platform identifier (e.g., 'slack', 'discord', 'line').
        user_id: Platform-specific user identifier.
        user_name: Human-readable display name of the sender.
        text: The message text content.
        channel_id: Platform-specific channel/conversation identifier.
        thread_id: Thread or reply-chain identifier (if applicable).
        attachments: List of attachment metadata dicts.
        reply_func: Async callable to reply in the same context (thread/channel).
        raw_event: The original platform-specific event object for advanced use.
    """

    platform: str
    user_id: str
    user_name: str
    text: str
    channel_id: str = ""
    thread_id: str = ""
    attachments: list[dict[str, Any]] = field(default_factory=list)
    reply_func: Optional[Callable[[str], Coroutine[Any, Any, None]]] = None
    raw_event: Any = None


# Type alias for the message handler callback
MessageHandler = Callable[[MessageContext], Coroutine[Any, Any, None]]


class ChannelAdapter(ABC):
    """Abstract base class for channel adapters.

    Each adapter bridges a messaging platform (Slack, Discord, LINE, etc.)
    to the agent loop via a unified MessageContext interface.

    Subclasses must implement:
        - start(): Connect to the platform and begin listening.
        - stop(): Disconnect and clean up resources.
        - send(user_id, text): Send a message to a specific user or channel.
        - platform_name: Return the platform identifier string.

    Usage::

        adapter = SlackAdapter(config)
        adapter.on_message(my_handler)
        await adapter.start()
        # ... process messages ...
        await adapter.stop()
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the adapter with platform configuration.

        Args:
            config: Full application config dict. Each adapter extracts
                    its own section (e.g., config['channels']['slack']).
        """
        self._config = config
        self._on_message: Optional[MessageHandler] = None

    def on_message(self, callback: MessageHandler) -> None:
        """Register a callback for incoming messages.

        Args:
            callback: Async function that receives a MessageContext.
        """
        self._on_message = callback

    @abstractmethod
    async def start(self) -> None:
        """Start the adapter and connect to the messaging platform.

        This method should block (or run in background) until stop() is called.
        """
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop the adapter and disconnect from the platform.

        Should clean up all resources (connections, tasks, etc.).
        """
        ...

    @abstractmethod
    async def send(self, user_id: str, text: str) -> None:
        """Send a message to a specific user or channel.

        Args:
            user_id: Platform-specific user or channel identifier.
            text: The message text to send.
        """
        ...

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform name identifier (e.g., 'slack', 'discord')."""
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} platform={self.platform_name}>"
