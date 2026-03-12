"""Unified webhook server for LINE and WhatsApp channels.

FastAPI-based server that receives webhooks from messaging platforms
and routes them to appropriate channel adapters.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

try:
    from fastapi import FastAPI, Request, Response, status
    from fastapi.responses import JSONResponse, PlainTextResponse
    import uvicorn

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

logger = logging.getLogger(__name__)


class WebhookServer:
    """Unified webhook server for messaging platforms."""

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize webhook server.

        Args:
            config: Configuration dict with 'gateway.port' setting.
        """
        if not FASTAPI_AVAILABLE:
            raise ImportError(
                "FastAPI and uvicorn are not installed. "
                "Install with: pip install fastapi uvicorn"
            )

        self.port = config.get("gateway", {}).get("port", 8080)
        self.app = FastAPI(title="nyancobot Webhook Gateway")
        self.server: Optional[uvicorn.Server] = None
        self.server_task: Optional[asyncio.Task] = None

        # Adapter references (set by agent loop)
        self.line_adapter = None
        self.whatsapp_adapter = None

        self._setup_routes()
        logger.info(f"Webhook server initialized on port {self.port}")

    def _setup_routes(self) -> None:
        """Setup FastAPI routes for webhooks."""

        @self.app.get("/health")
        async def health_check() -> JSONResponse:
            """Health check endpoint."""
            return JSONResponse(
                {
                    "status": "ok",
                    "service": "nyancobot-webhook-gateway",
                    "channels": {
                        "line": self.line_adapter is not None,
                        "whatsapp": self.whatsapp_adapter is not None,
                    },
                }
            )

        @self.app.post("/webhook/line")
        async def line_webhook(request: Request) -> Response:
            """LINE webhook endpoint.

            Receives webhook from LINE Messaging API and forwards to LineAdapter.
            """
            if not self.line_adapter:
                return Response(
                    content="LINE adapter not configured",
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            try:
                # Get request body and signature
                body = await request.body()
                signature = request.headers.get("X-Line-Signature", "")

                # Validate and handle webhook
                self.line_adapter.handle_webhook(body.decode("utf-8"), signature)

                return Response(status_code=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"LINE webhook error: {e}")
                return Response(
                    content="Internal server error",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        @self.app.get("/webhook/whatsapp")
        async def whatsapp_webhook_verify(
            mode: str = "", token: str = "", challenge: str = ""
        ) -> Response:
            """WhatsApp webhook verification endpoint.

            Meta sends GET request to verify webhook subscription.
            """
            if not self.whatsapp_adapter:
                return Response(
                    content="WhatsApp adapter not configured",
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            # Verify webhook subscription
            result = self.whatsapp_adapter.verify_webhook(mode, token, challenge)
            if result:
                return PlainTextResponse(content=result, status_code=200)

            return Response(
                content="Verification failed",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        @self.app.post("/webhook/whatsapp")
        async def whatsapp_webhook(request: Request) -> Response:
            """WhatsApp webhook endpoint.

            Receives webhook from Meta Cloud API and forwards to WhatsAppAdapter.
            """
            if not self.whatsapp_adapter:
                return Response(
                    content="WhatsApp adapter not configured",
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            try:
                # Get JSON payload
                payload = await request.json()

                # Handle webhook asynchronously
                asyncio.create_task(self.whatsapp_adapter.handle_webhook(payload))

                return Response(status_code=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"WhatsApp webhook error: {e}")
                return Response(
                    content="Internal server error",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

    async def start(self) -> None:
        """Start webhook server.

        Runs uvicorn server in background asyncio task.
        """
        config = uvicorn.Config(
            self.app,
            host="0.0.0.0",
            port=self.port,
            log_level="info",
        )
        self.server = uvicorn.Server(config)

        # Run server in background task
        self.server_task = asyncio.create_task(self.server.serve())
        logger.info(f"Webhook server started on port {self.port}")

    async def stop(self) -> None:
        """Stop webhook server gracefully."""
        if self.server:
            self.server.should_exit = True

        if self.server_task:
            try:
                await asyncio.wait_for(self.server_task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Webhook server shutdown timeout")
                if self.server_task:
                    self.server_task.cancel()

        logger.info("Webhook server stopped")

    def register_adapter(self, channel: str, adapter: Any) -> None:
        """Register channel adapter with webhook server.

        Args:
            channel: Channel name ("line" or "whatsapp").
            adapter: Channel adapter instance.
        """
        if channel == "line":
            self.line_adapter = adapter
            logger.info("LINE adapter registered with webhook server")
        elif channel == "whatsapp":
            self.whatsapp_adapter = adapter
            logger.info("WhatsApp adapter registered with webhook server")
        else:
            logger.warning(f"Unknown channel: {channel}")
