"""Discord channel adapter using Gateway WebSocket.

Uses discord.py with Gateway connection so no public URL is required.
The bot listens for direct messages and @mentions, converting them
into a unified MessageContext for the agent loop.
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

try:
    import discord
    from discord import Intents

    _HAS_DISCORD = True
except ImportError:
    _HAS_DISCORD = False

try:
    from loguru import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)  # type: ignore[assignment]

from nyancobot.channels.base import ChannelAdapter, MessageContext

# Discord enforces a 2000-character message limit
_DISCORD_MAX_MESSAGE_LENGTH = 2000


class DiscordAdapter(ChannelAdapter):
    """Discord adapter using Gateway WebSocket for real-time messaging.

    Configuration keys (under ``config['channels']['discord']``):
        - token: Discord bot token.

    Events handled:
        - Direct messages (DMs) to the bot.
        - Messages that @mention the bot in a guild channel.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the Discord adapter.

        Args:
            config: Full application config dict.

        Raises:
            ImportError: If discord.py is not installed.
        """
        super().__init__(config)
        if not _HAS_DISCORD:
            raise ImportError(
                "discord.py is required for DiscordAdapter. "
                "Install with: pip install discord.py"
            )

        discord_config = config.get("channels", {}).get("discord", {})
        self._token: str = discord_config.get("token", "")

        intents = Intents.default()
        intents.message_content = True
        intents.dm_messages = True

        self._bot = discord.Client(intents=intents)
        self._ready = asyncio.Event()
        self._setup_events()

    def _setup_events(self) -> None:
        """Register Discord event handlers."""

        @self._bot.event
        async def on_ready() -> None:
            """Log connection and signal readiness."""
            logger.info(f"Discord adapter connected as {self._bot.user}")
            self._ready.set()

        @self._bot.event
        async def on_message(message: "discord.Message") -> None:
            """Handle incoming Discord messages."""
            # Ignore messages from the bot itself
            if message.author == self._bot.user:
                return

            is_dm = isinstance(message.channel, discord.DMChannel)
            is_mentioned = (
                self._bot.user in message.mentions if self._bot.user else False
            )

            if not (is_dm or is_mentioned):
                return

            # Strip the bot mention from the message text
            text = message.content
            if is_mentioned and self._bot.user:
                text = text.replace(f"<@{self._bot.user.id}>", "").strip()

            await self._process_message(message, text)

    async def _process_message(
        self, message: "discord.Message", text: str
    ) -> None:
        """Convert a Discord message into a MessageContext and dispatch.

        Args:
            message: The discord.py Message object.
            text: Pre-processed message text (mention stripped).
        """
        if not self._on_message:
            return

        # Build reply function with automatic chunking
        async def reply(response_text: str) -> None:
            chunks = _split_message(response_text)
            for chunk in chunks:
                await message.reply(chunk)

        # Collect attachment metadata
        attachments = [
            {
                "url": a.url,
                "filename": a.filename,
                "size": a.size,
                "content_type": a.content_type,
            }
            for a in message.attachments
        ]

        ctx = MessageContext(
            platform="discord",
            user_id=str(message.author.id),
            user_name=str(message.author),
            text=text,
            channel_id=str(message.channel.id),
            thread_id="",
            attachments=attachments,
            reply_func=reply,
            raw_event=message,
        )

        try:
            await self._on_message(ctx)
        except Exception as exc:
            logger.error(f"Error processing Discord message: {exc}")
            try:
                await message.reply("An error occurred while processing your message.")
            except Exception:
                pass

    # ------------------------------------------------------------------
    # ChannelAdapter interface
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the Discord bot via Gateway WebSocket.

        Raises:
            ValueError: If the bot token is not configured.
        """
        if not self._token:
            raise ValueError(
                "Discord bot token is required. "
                "Set config.channels.discord.token"
            )

        logger.info("Starting Discord adapter")
        await self._bot.start(self._token)

    async def stop(self) -> None:
        """Stop the Discord bot and close the connection."""
        if not self._bot.is_closed():
            logger.info("Stopping Discord adapter")
            await self._bot.close()

    async def send(self, user_id: str, text: str) -> None:
        """Send a direct message to a Discord user.

        Args:
            user_id: Discord user ID (numeric string).
            text: The message text to send.
        """
        await self._ready.wait()
        user = await self._bot.fetch_user(int(user_id))
        if user:
            dm_channel = await user.create_dm()
            chunks = _split_message(text)
            for chunk in chunks:
                await dm_channel.send(chunk)

    @property
    def platform_name(self) -> str:
        """Return the platform identifier."""
        return "discord"


def _split_message(text: str) -> list[str]:
    """Split a message into chunks that fit Discord's character limit.

    Args:
        text: The full message text.

    Returns:
        List of text chunks, each at most 2000 characters.
    """
    if len(text) <= _DISCORD_MAX_MESSAGE_LENGTH:
        return [text]
    return [
        text[i : i + _DISCORD_MAX_MESSAGE_LENGTH]
        for i in range(0, len(text), _DISCORD_MAX_MESSAGE_LENGTH)
    ]
