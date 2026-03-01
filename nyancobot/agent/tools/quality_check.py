"""Quality check tool for pre-publication content validation.

Validates text content before posting to social platforms.
Supports X (Twitter), note, and Instagram with platform-specific rules.
"""

import re
from typing import Any

from nyancobot.agent.tools.base import Tool


# ============================================================================
# Constants
# ============================================================================

# NG words that indicate draft / placeholder content
_NG_WORDS = [
    "テスト", "ダミー", "TODO", "FIXME", "PLACEHOLDER",
    "サンプル投稿", "ここに入力", "仮テキスト",
]

# Platform-specific limits
_X_MAX_CHARS = 280
_X_MAX_URLS = 3
_NOTE_MIN_CHARS = 500
_INSTAGRAM_MIN_HASHTAGS = 3


# ============================================================================
# QualityCheckTool
# ============================================================================

class QualityCheckTool(Tool):
    """Validate content quality before posting to social platforms.

    Performs platform-specific checks and optionally auto-fixes issues.

    Platforms: x, note, instagram
    """

    name = "quality_check"
    description = (
        "投稿前の品質チェックツール。"
        "プラットフォーム別ルールに基づきテキストを検証し、"
        "問題点を列挙する。auto_fix=trueで自動修正も可能。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "チェック対象のテキスト",
            },
            "platform": {
                "type": "string",
                "enum": ["x", "note", "instagram"],
                "description": "投稿先プラットフォーム (x / note / instagram)",
            },
            "auto_fix": {
                "type": "boolean",
                "description": "trueの場合、検出した問題を自動修正する (default: false)",
            },
        },
        "required": ["text", "platform"],
    }

    # ------------------------------------------------------------------
    # Execute
    # ------------------------------------------------------------------

    async def execute(
        self,
        text: str,
        platform: str,
        auto_fix: bool = False,
        **kwargs: Any,
    ) -> str:
        """Run quality checks and optionally apply auto-fix."""

        issues: list[str] = []
        fixed_text = text

        # --- Common checks ---
        issues += self._check_empty(fixed_text)
        ng_issues, fixed_text = self._check_ng_words(fixed_text, auto_fix)
        issues += ng_issues

        # --- Platform-specific checks ---
        if platform == "x":
            platform_issues, fixed_text = self._check_x(fixed_text, auto_fix)
            issues += platform_issues
        elif platform == "note":
            platform_issues, fixed_text = self._check_note(fixed_text, auto_fix)
            issues += platform_issues
        elif platform == "instagram":
            platform_issues, fixed_text = self._check_instagram(fixed_text, auto_fix)
            issues += platform_issues
        else:
            return f"Error: Unknown platform '{platform}'. Use x, note, or instagram."

        # --- Build result ---
        return self._build_result(text, fixed_text, platform, issues, auto_fix)

    # ------------------------------------------------------------------
    # Common checks
    # ------------------------------------------------------------------

    def _check_empty(self, text: str) -> list[str]:
        """Detect empty or whitespace-only text."""
        if not text or not text.strip():
            return ["[ERROR] テキストが空です。投稿内容を入力してください。"]
        return []

    def _check_ng_words(
        self, text: str, auto_fix: bool
    ) -> tuple[list[str], str]:
        """Detect (and optionally remove) NG words."""
        issues = []
        fixed = text
        for word in _NG_WORDS:
            if word.lower() in text.lower():
                issues.append(
                    f"[WARN] NGワード検出: '{word}' が含まれています。"
                    " 下書き・プレースホルダーが残っている可能性があります。"
                )
                if auto_fix:
                    # Remove NG words (case-insensitive)
                    pattern = re.compile(re.escape(word), re.IGNORECASE)
                    fixed = pattern.sub("", fixed).strip()
        return issues, fixed

    # ------------------------------------------------------------------
    # X-specific checks
    # ------------------------------------------------------------------

    def _check_x(
        self, text: str, auto_fix: bool
    ) -> tuple[list[str], str]:
        """X (Twitter) specific validation.

        Rules:
          - Text must not exceed 280 characters
          - URL count must not exceed 3
        """
        issues = []
        fixed = text

        # Character count check
        char_count = len(text)
        if char_count > _X_MAX_CHARS:
            overage = char_count - _X_MAX_CHARS
            issues.append(
                f"[ERROR] 文字数超過: {char_count}字 (上限 {_X_MAX_CHARS}字、"
                f"超過 {overage}字)。"
            )
            if auto_fix:
                fixed = fixed[:_X_MAX_CHARS]
                issues.append(
                    f"[AUTO_FIX] {_X_MAX_CHARS}字にトリミングしました。"
                )

        # URL count check
        url_pattern = re.compile(
            r"https?://[^\s\u3000\u300c\u300d\u3002\u3001\uff01\uff1f]+"
        )
        urls = url_pattern.findall(text)
        if len(urls) > _X_MAX_URLS:
            issues.append(
                f"[WARN] URL数超過: {len(urls)}件 (推奨 {_X_MAX_URLS}件以内)。"
                " エンゲージメント低下の恐れあり。"
            )

        return issues, fixed

    # ------------------------------------------------------------------
    # note-specific checks
    # ------------------------------------------------------------------

    def _check_note(
        self, text: str, auto_fix: bool
    ) -> tuple[list[str], str]:
        """note.com specific validation.

        Rules:
          - Body text must be at least 500 characters
          - Must have a title (first line or explicit title marker)
        """
        issues = []
        fixed = text

        # Minimum character count
        char_count = len(text)
        if char_count < _NOTE_MIN_CHARS:
            shortage = _NOTE_MIN_CHARS - char_count
            issues.append(
                f"[ERROR] 文字数不足: {char_count}字 (最低 {_NOTE_MIN_CHARS}字、"
                f"残り {shortage}字)。"
            )

        # Title check: first non-empty line should exist and be non-trivial
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if not lines:
            issues.append("[ERROR] タイトルが見つかりません。最初の行にタイトルを記載してください。")
        elif len(lines[0]) < 5:
            issues.append(
                f"[WARN] タイトルが短すぎます: '{lines[0]}' ({len(lines[0])}字)。"
                " 5字以上のタイトルを推奨します。"
            )

        return issues, fixed

    # ------------------------------------------------------------------
    # Instagram-specific checks
    # ------------------------------------------------------------------

    def _check_instagram(
        self, text: str, auto_fix: bool
    ) -> tuple[list[str], str]:
        """Instagram specific validation.

        Rules:
          - Must contain at least 3 hashtags
        """
        issues = []
        fixed = text

        hashtag_pattern = re.compile(r"#\S+")
        hashtags = hashtag_pattern.findall(text)

        if len(hashtags) < _INSTAGRAM_MIN_HASHTAGS:
            shortage = _INSTAGRAM_MIN_HASHTAGS - len(hashtags)
            issues.append(
                f"[ERROR] ハッシュタグ不足: {len(hashtags)}個 "
                f"(最低 {_INSTAGRAM_MIN_HASHTAGS}個、あと {shortage}個必要)。"
            )
            if auto_fix:
                # Append generic hashtags to reach minimum
                generic_tags = ["#投稿", "#シェア", "#日常"]
                needed = generic_tags[:shortage]
                fixed = fixed.rstrip() + "\n" + " ".join(needed)
                issues.append(
                    f"[AUTO_FIX] ハッシュタグを追加しました: {' '.join(needed)}"
                )

        return issues, fixed

    # ------------------------------------------------------------------
    # Result builder
    # ------------------------------------------------------------------

    def _build_result(
        self,
        original_text: str,
        fixed_text: str,
        platform: str,
        issues: list[str],
        auto_fix: bool,
    ) -> str:
        """Build human-readable result string."""
        lines: list[str] = []

        # Summary header
        error_count = sum(1 for i in issues if i.startswith("[ERROR]"))
        warn_count = sum(1 for i in issues if i.startswith("[WARN]"))
        fix_count = sum(1 for i in issues if i.startswith("[AUTO_FIX]"))

        if not issues:
            status = "OK"
        elif error_count > 0:
            status = "NG"
        else:
            status = "WARN"

        lines.append(f"=== quality_check: {platform.upper()} | status={status} ===")
        lines.append(
            f"文字数: {len(original_text)}字 | "
            f"エラー: {error_count}件 | 警告: {warn_count}件"
        )

        if issues:
            lines.append("")
            lines.append("--- 検出項目 ---")
            for issue in issues:
                lines.append(issue)

        if auto_fix and fixed_text != original_text:
            lines.append("")
            lines.append("--- 修正後テキスト ---")
            lines.append(fixed_text)

        if not issues:
            lines.append("")
            lines.append("問題なし。投稿可能です。")

        return "\n".join(lines)
