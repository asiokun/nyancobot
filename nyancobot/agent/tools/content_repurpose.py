"""Content Repurpose Tool: Multi-platform content converter.

Converts text to platform-specific formats (X, note, Instagram, SEO blog).
Uses tiered LLM strategy: qwen3-14B (local) for short/simple, claude --print for long/complex.
"""

import asyncio
import json
import logging
import os
import subprocess
import urllib.request
import urllib.error
from typing import Any

from nyancobot.agent.tools.base import Tool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1/chat/completions")
OLLAMA_MODEL = "qwen3-nyancobot"
OLLAMA_TIMEOUT = 60  # seconds
CLAUDE_TIMEOUT = 120  # seconds
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"

# Platform character limits
PLATFORM_LIMITS = {
    "x": 280,
    "instagram": 2200,
    "note": None,      # no strict limit
    "seo_blog": None,   # no strict limit
}

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------
PROMPT_TEMPLATES = {
    "x": (
        "以下のテキストを280字以内のツイートに要約せよ。\n"
        "ハッシュタグ2-3個付与。\n"
        "改行は使わず、自然な日本語で1文にまとめよ。\n"
        "{style_instruction}\n"
        "---\n{text}"
    ),
    "note": (
        "以下のテキストを3000字程度の記事にリライトせよ。\n"
        "以下の構造で出力:\n"
        "- タイトル（## で始める）\n"
        "- 導入（読者の興味を引く1段落）\n"
        "- 見出し1（### で始める）\n"
        "- 本文\n"
        "- 見出し2（### で始める）\n"
        "- 本文\n"
        "- まとめ\n"
        "{style_instruction}\n"
        "{seo_instruction}\n"
        "---\n{text}"
    ),
    "instagram": (
        "以下のテキストをInstagramキャプションに変換せよ。\n"
        "ハッシュタグ10-15個付与。\n"
        "絵文字を適度に使用し、読みやすい改行を入れよ。\n"
        "{style_instruction}\n"
        "---\n{text}"
    ),
    "seo_blog": (
        "以下のテキストをSEO最適化された記事にせよ。\n"
        "出力フォーマット:\n"
        "1. メタディスクリプション（160字以内、<!-- meta: ... --> で囲む）\n"
        "2. H1タイトル（# で始める）\n"
        "3. H2セクション（## で始める）×3-5個\n"
        "4. 各H2内にH3サブセクション（### で始める）×1-3個\n"
        "5. 各セクション200-400字\n"
        "{style_instruction}\n"
        "{seo_instruction}\n"
        "---\n{text}"
    ),
}

STYLE_INSTRUCTIONS = {
    "casual": "文体: カジュアルで親しみやすいトーン。",
    "formal": "文体: フォーマルで丁寧なビジネストーン。",
    "mystic": "文体: 神秘的な占い師キャラクター。優しく幻想的な語り口。",
}


class ContentRepurposeTool(Tool):
    """Repurpose text content for multiple platforms (Multi-platform content converter)."""

    name = "content_repurpose"
    description = (
        "テキストを複数プラットフォーム（X, note, Instagram, SEOブログ）向けに"
        "自動変換する。マルチプラットフォーム変換機能。"
        "短文・定型はローカルLLM(qwen3)、長文・高品質はclaude --printで処理。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "変換元テキスト",
            },
            "platforms": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["x", "note", "instagram", "seo_blog"],
                },
                "description": "ターゲットプラットフォーム",
            },
            "style": {
                "type": "string",
                "description": "文体指定 (casual, formal, mystic等)",
            },
            "seo_keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "SEO対象キーワード(seo_blog時に使用)",
            },
        },
        "required": ["text", "platforms"],
    }

    # ------------------------------------------------------------------
    # Execute
    # ------------------------------------------------------------------

    # Maximum input text size (100KB)
    MAX_INPUT_CHARS = 100000

    async def execute(
        self,
        text: str,
        platforms: list,
        style: str = "casual",
        seo_keywords: list | None = None,
        **kwargs: Any,
    ) -> str:
        if not text or not text.strip():
            return json.dumps({"error": "text is empty"}, ensure_ascii=False)

        if len(text) > self.MAX_INPUT_CHARS:
            return json.dumps(
                {"error": f"text too large ({len(text)} chars, max {self.MAX_INPUT_CHARS})"},
                ensure_ascii=False,
            )

        if not platforms:
            return json.dumps({"error": "platforms is empty"}, ensure_ascii=False)

        results = {}

        for platform in platforms:
            if platform not in PROMPT_TEMPLATES:
                results[platform] = {"error": f"Unknown platform: {platform}"}
                continue

            # Tier decision: short/simple -> qwen3, long/complex -> claude
            use_claude = self._should_use_claude(text, platform, style)

            prompt = self._build_prompt(text, platform, style, seo_keywords)

            try:
                if use_claude:
                    output = await self._call_claude(prompt)
                else:
                    output = await self._call_ollama(prompt)

                # Quality check
                is_valid, issue = self._quality_check(output, platform)
                if not is_valid:
                    logger.info(
                        "Quality check failed for %s (%s), falling back to claude",
                        platform,
                        issue,
                    )
                    # Fallback to claude --print
                    output = await self._call_claude(prompt)
                    is_valid_retry, issue_retry = self._quality_check(output, platform)
                    if not is_valid_retry:
                        results[platform] = {
                            "content": output,
                            "warning": f"Quality issue persists after fallback: {issue_retry}",
                            "model": "claude-fallback",
                        }
                        continue

                results[platform] = {
                    "content": output,
                    "model": "claude" if use_claude else "qwen3-local",
                    "char_count": len(output),
                }

            except Exception as e:
                logger.error("Error processing platform %s: %s", platform, e)
                results[platform] = {"error": str(e)}

        return json.dumps(results, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # Tier decision
    # ------------------------------------------------------------------

    @staticmethod
    def _should_use_claude(text: str, platform: str, style: str) -> bool:
        """Determine whether to use claude --print (Tier 2) or qwen3 (Tier 1)."""
        # Long-form platforms always use claude
        if platform in ("note", "seo_blog"):
            return True
        # Mystic style requires nuanced generation
        if style == "mystic":
            return True
        # Very long source text needs better comprehension
        if len(text) > 2000:
            return True
        # Default: use local LLM
        return False

    # ------------------------------------------------------------------
    # Prompt building
    # ------------------------------------------------------------------

    @staticmethod
    def _build_prompt(
        text: str, platform: str, style: str, seo_keywords: list | None
    ) -> str:
        """Build platform-specific prompt from template."""
        template = PROMPT_TEMPLATES.get(platform, PROMPT_TEMPLATES["x"])

        style_instruction = STYLE_INSTRUCTIONS.get(style, f"文体: {style}")

        seo_instruction = ""
        if seo_keywords and platform in ("note", "seo_blog"):
            kw_str = ", ".join(seo_keywords)
            seo_instruction = f"SEOキーワード（本文中に自然に含めよ）: {kw_str}"

        return template.format(
            text=f"<content>\n{text}\n</content>",
            style_instruction=style_instruction,
            seo_instruction=seo_instruction,
        )

    # ------------------------------------------------------------------
    # LLM calls
    # ------------------------------------------------------------------

    async def _call_claude(self, prompt: str) -> str:
        """Call claude --print via subprocess (runs in thread to avoid blocking event loop)."""

        def _run() -> str:
            try:
                result = subprocess.run(
                    ["claude", "--print", "--model", CLAUDE_MODEL],
                    input=prompt,
                    capture_output=True,
                    text=True,
                    timeout=CLAUDE_TIMEOUT,
                )
                if result.returncode != 0:
                    stderr = result.stderr.strip()
                    raise RuntimeError(
                        f"claude --print failed (rc={result.returncode}): {stderr}"
                    )
                output = result.stdout.strip()
                if not output:
                    raise RuntimeError("claude --print returned empty output")
                return output
            except subprocess.TimeoutExpired:
                raise RuntimeError(
                    f"claude --print timed out after {CLAUDE_TIMEOUT}s"
                )

        return await asyncio.to_thread(_run)

    async def _call_ollama(self, prompt: str) -> str:
        """Call local Ollama qwen3 via OpenAI-compatible API (runs in thread)."""

        def _run() -> str:
            payload = json.dumps(
                {
                    "model": OLLAMA_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 2048,
                }
            ).encode("utf-8")

            req = urllib.request.Request(
                OLLAMA_BASE_URL,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            try:
                with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    choices = data.get("choices", [])
                    if not choices:
                        raise RuntimeError("Ollama returned no choices")
                    content = choices[0].get("message", {}).get("content", "")
                    if not content:
                        raise RuntimeError("Ollama returned empty content")
                    return content.strip()
            except urllib.error.URLError as e:
                raise RuntimeError(
                    f"Ollama API unreachable ({OLLAMA_BASE_URL}): {e}"
                )
            except Exception as e:
                raise RuntimeError(f"Ollama API error: {e}")

        try:
            return await asyncio.to_thread(_run)
        except RuntimeError as e:
            # Fallback: if Ollama is down, try claude
            logger.warning("Ollama failed (%s), falling back to claude", e)
            return await self._call_claude(prompt)

    # ------------------------------------------------------------------
    # Quality checks
    # ------------------------------------------------------------------

    @staticmethod
    def _quality_check(output: str, platform: str) -> tuple[bool, str]:
        """Validate output quality for the target platform.

        Returns (is_valid, issue_description).
        """
        if not output or not output.strip():
            return False, "empty output"

        char_count = len(output)

        # X: must be <= 280 chars
        if platform == "x" and char_count > 280:
            return False, f"exceeds 280 chars ({char_count})"

        # Instagram: must be <= 2200 chars
        if platform == "instagram" and char_count > 2200:
            return False, f"exceeds 2200 chars ({char_count})"

        # note: should be at least 500 chars for a proper article
        if platform == "note" and char_count < 500:
            return False, f"too short for note article ({char_count} chars)"

        # seo_blog: should have heading structure
        if platform == "seo_blog":
            if "#" not in output:
                return False, "missing heading structure (no # found)"
            if char_count < 500:
                return False, f"too short for SEO blog ({char_count} chars)"

        return True, ""
