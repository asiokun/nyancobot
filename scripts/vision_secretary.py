#!/usr/bin/env python3
"""vision_secretary.py - Browser screenshot analyzer via claude --print

VisionSecretary: Analyzes browser screenshots and returns structured JSON
with page type detection, form field identification, and suggested actions.

Uses subprocess to invoke claude --print with rate limiting and timeout.
"""

import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Any, Optional


class VisionSecretary:
    """Analyzes browser screenshots using claude --print subcommand.

    Features:
    - Rate limiting (10 calls/minute)
    - 30-second timeout with process kill
    - JSON-only output enforced via system prompt
    - Structured response with page type, elements, forms, and actions
    """

    RATE_LIMIT = 10  # max calls per minute
    TIMEOUT = 30     # seconds
    ALLOWED_ACTIONS = {"click", "fill", "press", "select", "scroll"}
    ALLOWED_SCREENSHOT_DIR = "/tmp/nyancobot-browser"
    _SYSTEM_PROMPT = "ブラウザスクリーンショット分析専門エージェント。JSONのみ返せ。他の文章は禁止。"
    _CLAUDE_PATH = shutil.which("claude")

    def __init__(self):
        """Initialize with empty call tracking for rate limiting."""
        self._call_times: List[float] = []  # Timestamps of recent calls

    def _is_rate_limited(self) -> bool:
        """Check if rate limit (10/minute) exceeded.

        Returns:
            True if next call would exceed rate limit, False otherwise
        """
        now = time.time()
        # Remove calls older than 60 seconds
        self._call_times = [t for t in self._call_times if now - t < 60]
        # Check limit
        if len(self._call_times) >= self.RATE_LIMIT:
            return True
        return False

    def _record_call(self) -> None:
        """Record the current call timestamp for rate limiting."""
        self._call_times.append(time.time())

    def _run_claude_subprocess(
        self,
        screenshot_path: str,
        question: Optional[str] = None
    ) -> tuple:
        """Execute claude --print subprocess to analyze screenshot.

        Args:
            screenshot_path: Path to screenshot PNG file
            question: Optional question (currently unused per spec)

        Returns:
            (stdout: str, error: Optional[str])
            error is None on success, error message string on failure
        """
        # V-F01: Use resolved absolute path for claude CLI
        claude_path = self._CLAUDE_PATH
        if not claude_path:
            return "", "claude command not found in PATH"

        # Build prompt with screenshot path
        prompt = f"このファイルを読んでページ状態をJSON形式で分析せよ: {screenshot_path}"

        cmd = [
            claude_path,
            "--print",
            "--model", "claude-haiku-4-5-20251001",
            "--allowedTools", "Read",
            "--output-format", "json",
            "--no-session-persistence",
            "--append-system-prompt", self._SYSTEM_PROMPT,
            prompt
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.TIMEOUT
            )
            if result.returncode != 0:
                return "", f"claude command failed: {result.stderr}"
            return result.stdout, None
        except subprocess.TimeoutExpired:
            return "", f"claude subprocess timeout after {self.TIMEOUT}s"
        except FileNotFoundError:
            return "", "claude command not found. Try: which claude"
        except Exception as e:
            return "", f"subprocess error: {str(e)}"

    def _filter_suggested_actions(
        self,
        actions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Filter suggested actions to only allowed action types.

        Args:
            actions: List of action dictionaries from claude response

        Returns:
            Filtered actions with only allowed types
        """
        filtered = []
        for action in actions:
            if isinstance(action, dict) and action.get("action") in self.ALLOWED_ACTIONS:
                filtered.append(action)
        return filtered

    def _error_response(self, error: str) -> Dict[str, Any]:
        """Build standard error response JSON.

        Args:
            error: Error message

        Returns:
            Standard error JSON structure
        """
        return {
            "page_type": "unknown",
            "elements": [],
            "forms": [],
            "errors": [error],
            "current_state": "分析失敗",
            "suggested_actions": []
        }

    def analyze(
        self,
        screenshot_path: str,
        question: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze browser screenshot and return structured JSON response.

        Args:
            screenshot_path: Path to screenshot PNG file
            question: Optional analysis question (unused in current version)

        Returns:
            Dict with keys:
            - page_type: "login|form|article|dashboard|error|unknown"
            - elements: List of page elements (buttons, inputs, links)
            - forms: List of form structures with fields
            - errors: List of error messages (empty if successful)
            - current_state: One-line description of current page state
            - suggested_actions: List of recommended interactions
        """
        # Check rate limit
        if self._is_rate_limited():
            return self._error_response(
                f"Rate limit exceeded: max {self.RATE_LIMIT} calls per minute"
            )

        # V-B01/V-E01: Validate screenshot path is under allowed directory
        path = Path(screenshot_path)
        try:
            resolved = str(path.resolve())
            if not resolved.startswith(self.ALLOWED_SCREENSHOT_DIR):
                return self._error_response(
                    f"Screenshot path outside allowed directory: must be under {self.ALLOWED_SCREENSHOT_DIR}"
                )
        except Exception:
            return self._error_response("Invalid screenshot path")

        # Verify screenshot exists
        if not path.exists():
            return self._error_response(f"Screenshot not found: {screenshot_path}")

        # Record call for rate limiting
        self._record_call()

        # Run claude subprocess
        stdout, error = self._run_claude_subprocess(screenshot_path, question)
        if error:
            return self._error_response(error)

        # Parse JSON from claude output
        try:
            response = json.loads(stdout)
        except json.JSONDecodeError as e:
            return self._error_response(f"JSON parse failed: {str(e)}")

        # Validate response structure and filter actions
        if not isinstance(response, dict):
            return self._error_response("Invalid response: not a JSON object")

        # Filter suggested_actions to allowed types only
        if "suggested_actions" in response and isinstance(response["suggested_actions"], list):
            response["suggested_actions"] = self._filter_suggested_actions(
                response["suggested_actions"]
            )

        return response
