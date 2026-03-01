"""Messenger tool for sending messages to dev team agents via tmux.

Permanent fix v3: Input line clearing + improved delivery confirmation during thinking + retry safety + log channel posting.
Messenger = input line clear + message input + Enter send + delivery confirmation + log posting.
"""

import asyncio
import os
import subprocess
import time
from typing import Any

import httpx
from loguru import logger

from nyancobot.agent.tools.base import Tool


class DenreiTool(Tool):
    """Tool to send messages (messenger) to dev team agents running in tmux."""

    # Environment variables for tmux session targets
    _LEADER_1_SESSION = os.environ.get("NYANCOBOT_LEADER_1_SESSION", "leader:0.0")
    _LEADER_2_SESSION = os.environ.get("NYANCOBOT_LEADER_2_SESSION", "leader2:0.0")

    _LEADER_TARGETS = {
        "1": _LEADER_1_SESSION,
        "2": _LEADER_2_SESSION,
        "leader": _LEADER_1_SESSION,
        "leader2": _LEADER_2_SESSION,
    }

    MAX_RETRIES = 2
    RETRY_DELAY_SEC = 3
    VERIFY_DELAY_SEC = 3
    THINKING_VERIFY_DELAY_SEC = 8

    # Slack log channel for audit trail
    _LOG_CHANNEL = os.environ.get("NYANCOBOT_LOG_CHANNEL")
    _SLACK_TOKEN = os.environ.get("NYANCOBOT_CHANNELS__SLACK__TOKEN")

    @property
    def name(self) -> str:
        return "denrei"

    @property
    def description(self) -> str:
        return (
            "Messenger tool for sending messages to development team leaders."
            "Development team leader 1 and leader 2 are running in tmux."
            "Use this tool when the user requests to send instructions or messages to dev teams."
            "Naturally align the message content with the user in conversation, then send when approved."
            "No permission confirmation needed. You can execute this tool directly."
            "Delivery confirmation is performed automatically after sending."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "enum": ["1", "2"],
                    "description": "Target development team leader number (1=leader 1, 2=leader 2)",
                },
                "message": {
                    "type": "string",
                    "description": "Message content to send to the development team leader",
                },
            },
            "required": ["target", "message"],
        }

    def _capture_pane(self, tmux_target: str, lines: int = 20) -> str:
        """Capture current display content of tmux pane."""
        try:
            result = subprocess.run(
                ["tmux", "capture-pane", "-t", tmux_target, "-p"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            output = result.stdout.strip()
            return "\n".join(output.splitlines()[-lines:])
        except Exception as e:
            logger.warning(f"Pane capture failed: {e}")
            return ""

    def _is_thinking(self, tmux_target: str) -> bool:
        """Determine if pane is thinking/processing."""
        pane_content = self._capture_pane(tmux_target, lines=5)
        thinking_indicators = [
            "thinking", "Effecting", "Boondoggling", "Puzzling",
            "Calculating", "Fermenting", "Crunching", "Running",
            "Esc to interrupt",
        ]
        lower = pane_content.lower()
        return any(ind.lower() in lower for ind in thinking_indicators)

    def _check_pane_ready(self, tmux_target: str) -> tuple[bool, str]:
        """Check if pane is ready to accept messages."""
        pane_content = self._capture_pane(tmux_target, lines=5)

        if "Compacting conversation" in pane_content:
            return False, "compacting in progress"

        if "❯" in pane_content:
            return True, "prompt displayed"

        if self._is_thinking(tmux_target):
            return True, "thinking (input will be queued)"

        return True, "status unknown, attempting to send"

    def _clear_input_line(self, tmux_target: str) -> None:
        """Clear input line (Ctrl+U). Remove residual text."""
        subprocess.run(
            ["tmux", "send-keys", "-t", tmux_target, "C-u"],
            timeout=5,
            check=True,
        )

    def _send_keys(self, tmux_target: str, text: str) -> None:
        """Send text via tmux send-keys."""
        subprocess.run(
            ["tmux", "send-keys", "-t", tmux_target, text],
            timeout=5,
            check=True,
        )

    def _send_enter(self, tmux_target: str) -> None:
        """Send Enter key."""
        subprocess.run(
            ["tmux", "send-keys", "-t", tmux_target, "Enter"],
            timeout=5,
            check=True,
        )

    def _verify_delivery(self, tmux_target: str, message_fragment: str) -> bool:
        """Delivery confirmation: Check if part of message is displayed in pane."""
        pane_content = self._capture_pane(tmux_target, lines=30)
        fragment = message_fragment[:30]
        return fragment in pane_content

    def _check_input_line_empty(self, tmux_target: str, message_fragment: str) -> bool:
        """Check if message is not remaining in input line.

        Text remaining in input line = not sent.
        If not remaining, can be considered sent (even during thinking or not immediately reflected in pane).
        """
        pane_content = self._capture_pane(tmux_target, lines=3)
        fragment = message_fragment[:20]
        # If fragment not remaining in input line (last few lines), considered sent
        return fragment not in pane_content

    def _build_success_reply(self, target: str, tmux_target: str, was_thinking: bool, message: str) -> str:
        """Generate concise response on successful delivery. Self-check + message content included."""
        pane = self._capture_pane(tmux_target, lines=3)
        if self._is_thinking(tmux_target):
            after = "thinking (processing started)"
        elif "❯" in pane:
            after = "waiting at prompt"
        else:
            after = "received"

        # Quote message content (truncate if too long)
        msg_preview = message if len(message) <= 200 else message[:200] + "..."

        if was_thinking:
            return f"✅ Delivered to leader {target} (was thinking during send → queued). Current: {after}\n> {msg_preview}"
        return f"✅ Delivered to leader {target}. Current: {after}\n> {msg_preview}"

    async def _post_to_log_channel(self, target: str, message: str) -> None:
        """Post sent content to Slack log channel (for user review).

        Skip if NYANCOBOT_LOG_CHANNEL is not set. Errors are warnings only.
        """
        if not self._LOG_CHANNEL or not self._SLACK_TOKEN:
            return

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={
                        "Authorization": f"Bearer {self._SLACK_TOKEN}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "channel": self._LOG_CHANNEL,
                        "text": f"📨 Messenger log → leader {target}\n```\n{message}\n```",
                    },
                )
                data = resp.json()
                if not data.get("ok"):
                    logger.warning(f"Slack log post failed: {data.get('error', 'unknown')}")
                else:
                    logger.info(f"Denrei logged to Slack channel {self._LOG_CHANNEL}")
        except Exception as e:
            logger.warning(f"Failed to post denrei log to Slack: {e}")

    # ── Anti-loop throttle ──
    _last_send: dict[str, tuple[float, str]] = {}  # target -> (timestamp, msg_hash)
    _THROTTLE_SEC = 10.0  # Minimum interval for sending same message

    async def execute(self, target: str, message: str, **kwargs: Any) -> str:
        tmux_target = self._LEADER_TARGETS.get(target)
        if not tmux_target:
            return f"Error: Unknown team number '{target}'. Please specify 1 or 2."

        # === Anti-loop: 同一メッセージ連続送信防止 ===
        import hashlib
        msg_hash = hashlib.md5(message.encode()).hexdigest()[:12]
        now = time.time()
        if target in self._last_send:
            last_time, last_hash = self._last_send[target]
            if msg_hash == last_hash and (now - last_time) < self._THROTTLE_SEC:
                elapsed = now - last_time
                logger.warning(
                    f"Denrei THROTTLED: same message to target {target} "
                    f"within {elapsed:.1f}s (limit={self._THROTTLE_SEC}s). Skipping."
                )
                return f"⚠️ Duplicate message send detected. Resend within {self._THROTTLE_SEC}s will be skipped."
        self._last_send[target] = (now, msg_hash)

        # === Step 1: Pre-send status check ===
        is_ready, status = self._check_pane_ready(tmux_target)
        is_thinking = self._is_thinking(tmux_target)
        logger.info(f"Denrei pre-check [{tmux_target}]: {status} (ready={is_ready}, thinking={is_thinking})")

        if not is_ready:
            logger.warning(f"Pane not ready ({status}), waiting {self.RETRY_DELAY_SEC}s...")
            await asyncio.sleep(self.RETRY_DELAY_SEC)
            is_ready, status = self._check_pane_ready(tmux_target)
            if not is_ready:
                logger.warning(f"Pane still not ready ({status}), proceeding anyway")

        # === Step 2: Message send (Clear + Input + Enter) ===
        escaped = message.replace("'", "'\\''")

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                # ★ Always clear input line before sending (prevent double input)
                self._clear_input_line(tmux_target)
                await asyncio.sleep(0.2)
                logger.info(f"Denrei input cleared [{tmux_target}] (attempt {attempt})")

                # Text input
                self._send_keys(tmux_target, escaped)
                logger.info(f"Denrei text input sent [{tmux_target}] (attempt {attempt})")

                # Wait a bit before Enter
                await asyncio.sleep(0.5)

                # Send Enter
                self._send_enter(tmux_target)
                logger.info(f"Denrei Enter sent [{tmux_target}] (attempt {attempt})")

                # === Step 3: Delivery confirmation ===
                # During thinking, not immediately reflected in pane, so check input line status
                verify_delay = self.THINKING_VERIFY_DELAY_SEC if is_thinking else self.VERIFY_DELAY_SEC
                await asyncio.sleep(verify_delay)

                # First check if input line is empty (if text disappeared, it was sent)
                input_empty = self._check_input_line_empty(tmux_target, message)
                if input_empty:
                    logger.info(f"Denrei DELIVERED [{tmux_target}] (input line empty): {message[:60]}")
                    await self._post_to_log_channel(target, message)
                    return self._build_success_reply(target, tmux_target, is_thinking, message)

                # Still remaining in input line → Enter may not have worked
                logger.warning(
                    f"Denrei text still in input line (attempt {attempt}), "
                    f"sending extra Enter"
                )
                self._send_enter(tmux_target)
                await asyncio.sleep(verify_delay)

                input_empty = self._check_input_line_empty(tmux_target, message)
                if input_empty:
                    logger.info(f"Denrei DELIVERED after extra Enter [{tmux_target}]")
                    await self._post_to_log_channel(target, message)
                    return self._build_success_reply(target, tmux_target, is_thinking, message)

                if attempt < self.MAX_RETRIES:
                    # ★ Clear input line before retry (essential for preventing double input)
                    self._clear_input_line(tmux_target)
                    await asyncio.sleep(0.3)
                    logger.warning(f"Retrying denrei (attempt {attempt + 1}), input cleared...")
                    await asyncio.sleep(self.RETRY_DELAY_SEC)
                    continue

            except subprocess.TimeoutExpired:
                logger.error(f"Denrei timeout [{tmux_target}] (attempt {attempt})")
                if attempt < self.MAX_RETRIES:
                    self._clear_input_line(tmux_target)
                    await asyncio.sleep(self.RETRY_DELAY_SEC)
                    continue
                return (
                    f"Error: Send to development team leader {target} timed out."
                    f"Please check tmux session."
                )
            except subprocess.CalledProcessError as e:
                logger.error(f"Denrei failed [{tmux_target}]: {e}")
                return f"Error: Failed to send to development team leader {target}: {e}"

        # All retries failed
        pane_final = self._capture_pane(tmux_target, lines=10)
        logger.error(
            f"Denrei delivery FAILED after {self.MAX_RETRIES} attempts [{tmux_target}]"
        )
        return (
            f"⚠️ Attempted messenger delivery to leader {target} {self.MAX_RETRIES} times, "
            f"but delivery confirmation failed.\n"
            f"【Pane status】:\n{pane_final}\n"
            f"Manual confirmation required."
        )
