"""Slack channel adapter using Socket Mode.

Uses slack_bolt with AsyncSocketModeHandler so no public URL is required.
The bot listens for app_mention events and direct messages, converting
them into a unified MessageContext for the agent loop.
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

try:
    from slack_bolt.async_app import AsyncApp
    from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

    _HAS_SLACK_BOLT = True
except ImportError:
    _HAS_SLACK_BOLT = False

try:
    from loguru import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)  # type: ignore[assignment]

from nyancobot.channels.base import ChannelAdapter, MessageContext


class SlackAdapter(ChannelAdapter):
    """Slack adapter using Socket Mode for real-time messaging.

    Configuration keys (under ``config['channels']['slack']``):
        - token: Bot User OAuth Token (xoxb-...).
        - signing_secret: Slack app signing secret.
        - app_token: App-Level Token for Socket Mode (xapp-...).

    Events handled:
        - ``app_mention``: When the bot is @mentioned in a channel.
        - ``message`` (channel_type=im): Direct messages to the bot.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the Slack adapter.

        Args:
            config: Full application config dict.

        Raises:
            ImportError: If slack_bolt is not installed.
        """
        super().__init__(config)
        if not _HAS_SLACK_BOLT:
            raise ImportError(
                "slack_bolt is required for SlackAdapter. "
                "Install with: pip install slack-bolt"
            )

        slack_config = config.get("channels", {}).get("slack", {})
        self._token: str = slack_config.get("token", "")
        self._signing_secret: str = slack_config.get("signing_secret", "")
        self._app_token: str = slack_config.get("app_token", "")

        self._app = AsyncApp(
            token=self._token,
            signing_secret=self._signing_secret,
        )
        self._handler: Optional[AsyncSocketModeHandler] = None
        self._setup_events()

    def _setup_events(self) -> None:
        """Register Slack event listeners."""

        @self._app.event("app_mention")
        async def handle_mention(event: dict[str, Any], say: Any) -> None:
            """Handle @mention events in channels."""
            await self._process_event(event, say)

        @self._app.event("message")
        async def handle_message(event: dict[str, Any], say: Any) -> None:
            """Handle direct messages (DMs) to the bot."""
            # Skip bot messages, message edits, and other subtypes
            if event.get("subtype") or event.get("bot_id"):
                return
            # Only process DMs; channel mentions are handled by app_mention
            if event.get("channel_type") == "im":
                await self._process_event(event, say)

    async def _process_event(
        self, event: dict[str, Any], say: Any
    ) -> None:
        """Convert a Slack event into a MessageContext and dispatch.

        Args:
            event: The Slack event payload.
            say: The slack_bolt ``say`` utility for replying.
        """
        if not self._on_message:
            return

        user_id: str = event.get("user", "unknown")
        text: str = event.get("text", "")
        thread_ts: str = event.get("thread_ts") or event.get("ts", "")
        channel: str = event.get("channel", "")

        # Build a reply function that posts in the same thread
        async def reply(response_text: str) -> None:
            await say(text=response_text, thread_ts=thread_ts)

        ctx = MessageContext(
            platform="slack",
            user_id=user_id,
            user_name=user_id,  # Slack user ID; real name requires API call
            text=text,
            channel_id=channel,
            thread_id=thread_ts,
            attachments=event.get("files", []),
            reply_func=reply,
            raw_event=event,
        )

        try:
            await self._on_message(ctx)
        except Exception as exc:
            logger.error(f"Error processing Slack message: {exc}")
            try:
                await say(
                    text="An error occurred while processing your message.",
                    thread_ts=thread_ts,
                )
            except Exception:
                pass

    # ------------------------------------------------------------------
    # ChannelAdapter interface
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the Slack Socket Mode handler.

        Raises:
            ValueError: If ``app_token`` is not configured.
        """
        if not self._app_token:
            raise ValueError(
                "Slack app_token is required for Socket Mode. "
                "Set config.channels.slack.app_token (xapp-...)"
            )

        self._handler = AsyncSocketModeHandler(self._app, self._app_token)
        logger.info("Starting Slack adapter (Socket Mode)")
        await self._handler.start_async()

    async def stop(self) -> None:
        """Stop the Slack Socket Mode handler and clean up."""
        if self._handler:
            logger.info("Stopping Slack adapter")
            await self._handler.close_async()
            self._handler = None

    async def send(self, user_id: str, text: str) -> None:
        """Send a message to a Slack user or channel.

        Args:
            user_id: Slack user ID or channel ID to send to.
            text: The message text.
        """
        await self._app.client.chat_postMessage(
            channel=user_id,
            text=text,
        )

    @property
    def platform_name(self) -> str:
        """Return the platform identifier."""
        return "slack"
