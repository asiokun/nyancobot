"""Multi-channel adapter package for nyancobot.

Provides a unified ChannelAdapter interface for integrating multiple
messaging platforms (Slack, Discord, LINE, WhatsApp, etc.).
Each adapter converts platform-specific events into a common
MessageContext and dispatches them to the agent loop.
"""

from nyancobot.channels.base import ChannelAdapter, MessageContext

__all__ = ["ChannelAdapter", "MessageContext"]

# Platform adapters are optional dependencies.
# Each import is wrapped in try/except so the package works
# even when specific platform SDKs are not installed.

try:
    from nyancobot.channels.slack_adapter import SlackAdapter

    __all__.append("SlackAdapter")
except ImportError:
    pass

try:
    from nyancobot.channels.discord_adapter import DiscordAdapter

    __all__.append("DiscordAdapter")
except ImportError:
    pass

try:
    from nyancobot.channels.line_adapter import LineAdapter  # type: ignore[import-not-found]

    __all__.append("LineAdapter")
except ImportError:
    pass

try:
    from nyancobot.channels.whatsapp_adapter import WhatsAppAdapter  # type: ignore[import-not-found]

    __all__.append("WhatsAppAdapter")
except ImportError:
    pass
