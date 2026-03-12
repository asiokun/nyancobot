"""LINE channel adapter for nyancobot.

Webhook-based adapter using line-bot-sdk v3.
Receives messages from LINE Messaging API and sends replies.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

try:
    from linebot.v3 import WebhookHandler
    from linebot.v3.messaging import (
        ApiClient,
        Configuration,
        MessagingApi,
        ReplyMessageRequest,
        TextMessage,
    )
    from linebot.v3.webhooks import MessageEvent, TextMessageContent

    LINEBOT_AVAILABLE = True
except ImportError:
    LINEBOT_AVAILABLE = False

from .base import ChannelAdapter, MessageContext

logger = logging.getLogger(__name__)


class LineAdapter(ChannelAdapter):
    """LINE Messaging API adapter using Webhook."""

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize LINE adapter.

        Args:
            config: Configuration dict with 'channels.line' section.
                    Expected keys: channel_access_token, channel_secret
        """
        super().__init__(config)
        if not LINEBOT_AVAILABLE:
            raise ImportError(
                "line-bot-sdk is not installed. "
                "Install with: pip install line-bot-sdk>=3.0.0"
            )

        line_config = config.get("channels", {}).get("line", {})
        self.channel_access_token = line_config.get("channel_access_token", "")
        self.channel_secret = line_config.get("channel_secret", "")

        if not self.channel_access_token or not self.channel_secret:
            raise ValueError(
                "LINE channel_access_token and channel_secret are required"
            )

        # Initialize LINE SDK
        self.configuration = Configuration(access_token=self.channel_access_token)
        self.handler = WebhookHandler(self.channel_secret)
        self.api_client: Optional[ApiClient] = None
        self.messaging_api: Optional[MessagingApi] = None

        logger.info("LINE adapter initialized")

    async def start(self) -> None:
        """Start LINE adapter.

        Registers webhook handler and initializes API client.
        Actual webhook server is managed by webhook_server.py.
        """
        self.api_client = ApiClient(self.configuration)
        self.messaging_api = MessagingApi(self.api_client)

        # Register webhook handler
        @self.handler.add(MessageEvent, message=TextMessageContent)
        def handle_text_message(event: MessageEvent) -> None:
            """Handle incoming text message from LINE."""
            if not isinstance(event.message, TextMessageContent):
                return

            reply_token = event.reply_token

            # Build reply function that uses the LINE Reply Message API
            async def reply(response_text: str) -> None:
                if self.messaging_api and reply_token:
                    try:
                        request = ReplyMessageRequest(
                            reply_token=reply_token,
                            messages=[TextMessage(text=response_text)],
                        )
                        await self.messaging_api.reply_message(request)
                    except Exception as exc:
                        logger.error("Failed to reply via LINE: %s", exc)

            # Build MessageContext with base.py-compliant field names
            context = MessageContext(
                platform="line",
                user_id=event.source.user_id,
                user_name=event.source.user_id,
                text=event.message.text,
                channel_id=event.source.user_id,
                thread_id="",
                reply_func=reply,
                raw_event=event,
            )

            # Dispatch to registered message handler
            if self._on_message:
                asyncio.create_task(self._dispatch_message(context))

        logger.info("LINE adapter started")

    async def _dispatch_message(self, context: MessageContext) -> None:
        """Dispatch message to the registered handler.

        Args:
            context: Unified message context.
        """
        try:
            if self._on_message:
                await self._on_message(context)
        except Exception as exc:
            logger.error("Error handling LINE message: %s", exc)

    async def stop(self) -> None:
        """Stop LINE adapter and cleanup resources."""
        if self.api_client:
            await self.api_client.close()
        logger.info("LINE adapter stopped")

    async def send(self, user_id: str, text: str) -> None:
        """Send a message to a LINE user via Push Message API.

        Args:
            user_id: LINE user ID to send to.
            text: The message text.
        """
        if not self.messaging_api:
            logger.error("MessagingApi not initialized")
            return

        try:
            await self.messaging_api.push_message(
                to=user_id,
                messages=[TextMessage(text=text)],
            )
            logger.info("Sent LINE push message to %s", user_id)
        except Exception as exc:
            logger.error("Failed to send LINE message: %s", exc)

    @property
    def platform_name(self) -> str:
        """Return the platform identifier."""
        return "line"

    def handle_webhook(self, body: str, signature: str) -> None:
        """Handle webhook request from LINE platform.

        Args:
            body: Request body (raw string).
            signature: X-Line-Signature header value.
        """
        try:
            self.handler.handle(body, signature)
        except Exception as exc:
            logger.error("Webhook handling error: %s", exc)
            raise
