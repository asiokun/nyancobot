"""WhatsApp channel adapter for nyancobot.

Webhook-based adapter using Meta Cloud API.
Receives messages from WhatsApp Business Platform and sends replies.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any, Dict, Optional

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from .base import ChannelAdapter, MessageContext

logger = logging.getLogger(__name__)


class WhatsAppAdapter(ChannelAdapter):
    """WhatsApp Business API adapter using Webhook."""

    GRAPH_API_URL = "https://graph.facebook.com/v18.0"

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize WhatsApp adapter.

        Args:
            config: Configuration dict with 'channels.whatsapp' section.
                    Expected keys: token, phone_number_id, verify_token, app_secret
        """
        super().__init__(config)
        if not HTTPX_AVAILABLE:
            raise ImportError(
                "httpx is not installed. Install with: pip install httpx"
            )

        whatsapp_config = config.get("channels", {}).get("whatsapp", {})
        self._token: str = whatsapp_config.get("token", "")
        self._phone_number_id: str = whatsapp_config.get("phone_number_id", "")
        self._verify_token: str = whatsapp_config.get("verify_token", "")
        self._app_secret: str = whatsapp_config.get("app_secret", "")

        if not self._token or not self._phone_number_id:
            raise ValueError("WhatsApp token and phone_number_id are required")

        # HTTP client for API calls
        self.client: Optional[httpx.AsyncClient] = None

        logger.info("WhatsApp adapter initialized")

    async def start(self) -> None:
        """Start WhatsApp adapter.

        Initializes HTTP client for Graph API calls.
        Actual webhook server is managed by webhook_server.py.
        """
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        logger.info("WhatsApp adapter started")

    async def stop(self) -> None:
        """Stop WhatsApp adapter and cleanup resources."""
        if self.client:
            await self.client.aclose()
        logger.info("WhatsApp adapter stopped")

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verify webhook payload using HMAC-SHA256 signature.

        Compares the X-Hub-Signature-256 header against a computed HMAC
        of the raw request body using the configured app_secret.

        Args:
            payload: Raw request body as bytes.
            signature: X-Hub-Signature-256 header value (format: "sha256=<hex>").

        Returns:
            True if the signature is valid, False otherwise.
        """
        if not self._app_secret:
            logger.warning(
                "app_secret not configured; skipping signature verification"
            )
            return True

        if not signature or not signature.startswith("sha256="):
            return False

        expected = hmac.new(
            self._app_secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(f"sha256={expected}", signature)

    async def handle_webhook(self, payload: Dict[str, Any]) -> None:
        """Handle incoming webhook from WhatsApp.

        Args:
            payload: Webhook payload (JSON dict).
        """
        try:
            entry = payload.get("entry", [])
            if not entry:
                return

            for item in entry:
                changes = item.get("changes", [])
                for change in changes:
                    value = change.get("value", {})
                    messages = value.get("messages", [])

                    for msg in messages:
                        await self._process_message(msg, value)
        except Exception:
            logger.error("Error handling WhatsApp webhook")

    async def _process_message(
        self, message: Dict[str, Any], value: Dict[str, Any]
    ) -> None:
        """Process a single WhatsApp message.

        Args:
            message: Message object from webhook.
            value: Value object containing metadata.
        """
        msg_type = message.get("type")
        if msg_type != "text":
            logger.debug("Ignoring non-text message type: %s", msg_type)
            return

        # Extract message details
        sender = message.get("from", "")
        msg_id = message.get("id", "")
        text_content = message.get("text", {}).get("body", "")

        # Build reply function
        async def reply(response_text: str) -> None:
            await self.send(sender, response_text)

        # Build MessageContext with base.py-compliant field names
        context = MessageContext(
            platform="whatsapp",
            user_id=sender,
            user_name=sender,
            text=text_content,
            channel_id=sender,
            thread_id=msg_id,
            reply_func=reply,
            raw_event={"message": message, "value": value},
        )

        # Dispatch to registered message handler
        if self._on_message:
            try:
                await self._on_message(context)
            except Exception:
                logger.error("An error occurred while processing your message.")

    async def send(self, user_id: str, text: str) -> None:
        """Send a text message to a WhatsApp user.

        Args:
            user_id: WhatsApp user phone number.
            text: The message text to send.
        """
        if not self.client:
            logger.error("HTTP client not initialized")
            return

        url = f"{self.GRAPH_API_URL}/{self._phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": user_id,
            "type": "text",
            "text": {"body": text},
        }

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            logger.info("Sent WhatsApp message to %s", user_id)
        except Exception:
            logger.error("Failed to send WhatsApp message")

    @property
    def platform_name(self) -> str:
        """Return the platform identifier."""
        return "whatsapp"

    def verify_webhook(
        self, mode: str, token: str, challenge: str
    ) -> Optional[str]:
        """Verify webhook subscription request from Meta.

        Args:
            mode: Verification mode (should be "subscribe").
            token: Verify token from request.
            challenge: Challenge string to echo back.

        Returns:
            Challenge string if verification succeeds, None otherwise.
        """
        if mode == "subscribe" and token == self._verify_token:
            logger.info("WhatsApp webhook verification succeeded")
            return challenge

        logger.warning("WhatsApp webhook verification failed")
        return None
