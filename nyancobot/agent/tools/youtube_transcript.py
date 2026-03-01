"""YouTube transcript tool: fetch video subtitles/captions."""

import re
from typing import Any

from nyancobot.agent.tools.base import Tool

MAX_TRANSCRIPT_CHARS = 50000  # 50KB limit


class YouTubeTranscriptTool(Tool):
    """Fetch the transcript (subtitles/captions) of a YouTube video."""

    name = "youtube_transcript"
    description = "YouTube動画の文字起こし（字幕）を取得する"
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "YouTube URL (e.g. https://www.youtube.com/watch?v=xxxxx or https://youtu.be/xxxxx)",
            },
            "language": {
                "type": "string",
                "description": "言語コード (ja, en 等)。省略時は ja を優先し、なければ en を試みる",
            },
        },
        "required": ["url"],
    }

    def _extract_video_id(self, url: str) -> str | None:
        """Extract the 11-char video ID from various YouTube URL formats."""
        patterns = [
            r"(?:v=)([a-zA-Z0-9_-]{11})",   # ?v=VIDEO_ID
            r"youtu\.be/([a-zA-Z0-9_-]{11})",  # youtu.be/VIDEO_ID
            r"embed/([a-zA-Z0-9_-]{11})",      # /embed/VIDEO_ID
            r"shorts/([a-zA-Z0-9_-]{11})",     # /shorts/VIDEO_ID
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    async def execute(self, url: str, language: str = "ja", **kwargs: Any) -> str:
        """
        Fetch transcript for a YouTube video.

        Args:
            url: YouTube video URL.
            language: Preferred language code (default "ja").

        Returns:
            Transcript text (up to 50KB), or error message string.
        """
        try:
            from youtube_transcript_api import (
                YouTubeTranscriptApi,
                NoTranscriptFound,
                TranscriptsDisabled,
                VideoUnavailable,
            )
        except ImportError:
            return "Error: youtube-transcript-api がインストールされていません。pip install youtube-transcript-api を実行してください。"

        video_id = self._extract_video_id(url)
        if not video_id:
            return f"Error: YouTube URLからvideo_idを抽出できませんでした。URL: {url}"

        # Try requested language first, then English as fallback
        languages_to_try = [language]
        if language != "en":
            languages_to_try.append("en")
        # Also accept auto-generated captions for each language
        languages_with_auto = []
        for lang in languages_to_try:
            languages_with_auto.append(lang)
            languages_with_auto.append(f"{lang}-auto")

        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(
                video_id,
                languages=languages_to_try,
            )
            text = " ".join(entry["text"] for entry in transcript_list)
            if len(text) > MAX_TRANSCRIPT_CHARS:
                text = text[:MAX_TRANSCRIPT_CHARS]
                text += f"\n\n[注意: 文字起こしが50KB制限で切り捨てられました。video_id={video_id}]"
            return text

        except Exception as primary_exc:
            # If specific language not found, try to get any available transcript
            try:
                transcript_api_list = YouTubeTranscriptApi.list_transcripts(video_id)
                # Try to find any transcript
                for transcript in transcript_api_list:
                    try:
                        fetched = transcript.fetch()
                        text = " ".join(entry["text"] for entry in fetched)
                        lang_info = f"言語: {transcript.language_code}"
                        if transcript.is_generated:
                            lang_info += " (自動生成)"
                        if len(text) > MAX_TRANSCRIPT_CHARS:
                            text = text[:MAX_TRANSCRIPT_CHARS]
                            text += f"\n\n[注意: 文字起こしが50KB制限で切り捨てられました。video_id={video_id}]"
                        return f"[{lang_info}]\n{text}"
                    except Exception:
                        continue
                return f"Error: 利用可能な文字起こしが見つかりませんでした。video_id={video_id}"
            except Exception as fallback_exc:
                return f"Error: 文字起こし取得に失敗しました。video_id={video_id}, error={primary_exc}"
