"""Multi-perspective evaluation module for /think command.

Sends the same idea/question to multiple LLMs with different viewpoint prompts,
then aggregates their evaluations into a comprehensive multi-angle analysis.

Models and their assigned perspectives:
- Claude (Anthropic): Context understanding, nuance, ethics
- Kimi K2.5 (DeepInfra): Feasibility, cost, efficiency
- DeepSeek (DeepSeek API): Logic, math, structural flaws
- Gemini (Google AI): Market, users, broad perspective
- Codex (OpenAI Responses API): Code, implementation, technical feasibility
- Grok (xAI API + x_search): SNS trends, public opinion, real-time data
"""

import asyncio
import json
import os
from typing import Any

import httpx
from loguru import logger


# ============================================================================
# Model perspectives
# ============================================================================

_PERSPECTIVES: list[dict[str, str]] = [
    {
        "name": "Claude",
        "label": "文脈・ニュアンス",
        "provider": "anthropic",
        "default_model": "claude-sonnet-4-6",
        "prompt": (
            "あなたは文脈理解とニュアンスの専門家です。以下のアイデア/提案について:\n"
            "1. その表現の誤解リスクを指摘せよ\n"
            "2. 本当にやりたいことの言語化を試みよ\n"
            "3. 倫理的懸念があれば指摘せよ\n"
            "簡潔に箇条書きで回答せよ。"
        ),
    },
    {
        "name": "Kimi",
        "label": "コスト・効率",
        "provider": "deepinfra",
        "default_model": "moonshotai/Kimi-K2.5",
        "prompt": (
            "あなたはコスト効率の専門家です。以下のアイデア/提案について:\n"
            "1. より安く効率的な代替案を提示せよ\n"
            "2. この構成の無駄を指摘せよ\n"
            "3. ROIの観点から評価せよ\n"
            "簡潔に箇条書きで回答せよ。"
        ),
    },
    {
        "name": "DeepSeek",
        "label": "論理・構造",
        "provider": "deepseek",
        "default_model": "deepseek-chat",
        "prompt": (
            "あなたは論理分析の専門家です。以下のアイデア/提案について:\n"
            "1. 前提を疑え。論理的に破綻している点を指摘せよ\n"
            "2. 数字が成り立たない箇所を指摘せよ\n"
            "3. 隠れたリスクや依存関係を洗い出せ\n"
            "簡潔に箇条書きで回答せよ。"
        ),
    },
    {
        "name": "Gemini",
        "label": "市場・ユーザー",
        "provider": "gemini",
        "default_model": "gemini-2.5-flash",
        "prompt": (
            "あなたは市場分析の専門家です。以下のアイデア/提案について:\n"
            "1. ターゲットユーザーの立場で評価せよ\n"
            "2. 別の市場・別のアプローチの方が大きくないか\n"
            "3. 競合状況と差別化ポイントを分析せよ\n"
            "簡潔に箇条書きで回答せよ。"
        ),
    },
    {
        "name": "Codex",
        "label": "技術的実現性",
        "provider": "openai",
        "default_model": "codex-mini",
        "prompt": (
            "あなたは技術実装の専門家です。以下のアイデア/提案について:\n"
            "1. 技術的に実装可能か検証せよ\n"
            "2. より良いアーキテクチャ・技術選定を提案せよ\n"
            "3. 実装コストと保守性を評価せよ\n"
            "簡潔に箇条書きで回答せよ。"
        ),
    },
    {
        "name": "Grok",
        "label": "SNSトレンド・世論",
        "provider": "xai",
        "default_model": "grok-3-mini",
        "prompt": (
            "あなたはSNSトレンド分析の専門家です。以下のアイデア/提案について:\n"
            "1. 今Xでこのテーマはどう議論されているか\n"
            "2. 世間の受け止め方と市場の温度感を報告せよ\n"
            "3. SNS上のリスクや炎上可能性を評価せよ\n"
            "簡潔に箇条書きで回答せよ。"
        ),
    },
]


# ============================================================================
# API config keys (config.json evaluator.api_keys section)
# ============================================================================

_PROVIDER_KEY_MAP = {
    "anthropic": "anthropic_api_key",
    "deepinfra": "deepinfra_api_key",
    "deepseek": "deepseek_api_key",
    "gemini": "gemini_api_key",
    "openai": "openai_api_key",
    "xai": "xai_api_key",
}

_PROVIDER_ENV_MAP = {
    "anthropic": "ANTHROPIC_API_KEY",
    "deepinfra": "DEEPINFRA_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "xai": "XAI_API_KEY",
}


# ============================================================================
# MultiPerspectiveEvaluator
# ============================================================================

class MultiPerspectiveEvaluator:
    """Run multi-model evaluation from different perspectives."""

    def __init__(self, config: dict[str, Any]):
        """Initialize with evaluator config section from config.json.

        Expected config structure:
        {
            "api_keys": {
                "anthropic_api_key": "...",
                "deepinfra_api_key": "...",
                ...
            },
            "think_models": {
                "Claude": "claude-sonnet-4-6",
                ...
            }
        }
        """
        self.api_keys = config.get("api_keys", {})
        self.custom_models = config.get("think_models", {})
        self.suggest_mode = config.get("suggest_think", False)

    def _get_api_key(self, provider: str) -> str | None:
        """Get API key from config or environment."""
        key_name = _PROVIDER_KEY_MAP.get(provider, "")
        key = self.api_keys.get(key_name, "")
        if not key:
            env_name = _PROVIDER_ENV_MAP.get(provider, "")
            key = os.environ.get(env_name, "")
        return key if key else None

    def _get_model(self, perspective: dict[str, str]) -> str:
        """Get model name, allowing config override."""
        name = perspective["name"]
        return self.custom_models.get(name, perspective["default_model"])

    async def evaluate(self, idea: str) -> str:
        """Run multi-perspective evaluation on an idea.

        Args:
            idea: The idea/proposal to evaluate

        Returns:
            Formatted markdown result with all perspectives
        """
        tasks = []
        active_perspectives = []

        for p in _PERSPECTIVES:
            api_key = self._get_api_key(p["provider"])
            if not api_key:
                logger.info(f"Skipping {p['name']}: no API key")
                continue
            active_perspectives.append(p)
            model = self._get_model(p)
            tasks.append(
                self._call_model(p, model, api_key, idea)
            )

        if len(tasks) < 2:
            return "多角評価には最低2つのAPIキーが必要です。config.jsonのevaluator.api_keysを設定してください。"

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Build formatted output
        lines = [f"## 多角評価結果（{len(active_perspectives)}視点）\n"]

        for p, result in zip(active_perspectives, results):
            lines.append(f"### {p['name']}（{p['label']}）")
            if isinstance(result, Exception):
                lines.append(f"- エラー: {result}\n")
            else:
                lines.append(f"{result}\n")

        # Synthesis
        lines.append("### 総合")
        lines.append("- 上記の各視点を踏まえ、多面的に検討してください。")

        return "\n".join(lines)

    async def _call_model(
        self, perspective: dict[str, str], model: str, api_key: str, idea: str
    ) -> str:
        """Call a single model with its assigned perspective."""
        provider = perspective["provider"]
        prompt = perspective["prompt"]
        user_msg = f"{prompt}\n\n## 対象\n{idea}"

        try:
            if provider == "anthropic":
                return await self._call_anthropic(model, api_key, user_msg)
            elif provider == "xai":
                return await self._call_xai(model, api_key, user_msg, idea)
            elif provider == "openai":
                return await self._call_openai_responses(model, api_key, user_msg)
            else:
                # DeepInfra, DeepSeek, Gemini -> OpenAI-compatible
                return await self._call_openai_compat(provider, model, api_key, user_msg)
        except Exception as e:
            logger.error(f"MultiPerspective {perspective['name']} failed: {e}")
            raise

    async def _call_anthropic(self, model: str, api_key: str, user_msg: str) -> str:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": user_msg}],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return "".join(
                b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"
            )

    async def _call_openai_responses(self, model: str, api_key: str, user_msg: str) -> str:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.openai.com/v1/responses",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "input": user_msg,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = ""
            for item in data.get("output", []):
                if item.get("type") == "message":
                    for block in item.get("content", []):
                        if block.get("type") == "output_text":
                            content += block.get("text", "")
            return content or data.get("output_text", "(no response)")

    async def _call_openai_compat(
        self, provider: str, model: str, api_key: str, user_msg: str
    ) -> str:
        """Call OpenAI-compatible API (DeepInfra, DeepSeek, Gemini)."""
        base_urls = {
            "deepinfra": "https://api.deepinfra.com/v1/openai",
            "deepseek": "https://api.deepseek.com",
            "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
        }
        base_url = base_urls.get(provider, "https://api.openai.com")

        # Kimi K2.5 requires temperature=1.0
        temperature = 1.0 if "kimi-k2.5" in model.lower() else 0.7

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": user_msg}],
                    "max_tokens": 1024,
                    "temperature": temperature,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def _call_xai(
        self, model: str, api_key: str, user_msg: str, idea: str
    ) -> str:
        """Call xAI Grok API with x_search tool for real-time SNS data."""
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(
                "https://api.x.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": user_msg}],
                    "max_tokens": 1024,
                    "temperature": 0.7,
                    "search": {
                        "mode": "auto",
                        "sources": [{"type": "x_posts"}, {"type": "web"}],
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]


# ============================================================================
# Suggestion detection
# ============================================================================

_DECISION_KEYWORDS = ["したい", "始めたい", "どう思う", "やろうと思う", "考えている", "検討中", "予定", "つもり"]
_BUSINESS_KEYWORDS = ["万円", "事業", "サービス", "売上", "案件", "収益", "コスト", "投資", "市場"]


def should_suggest_think(message: str) -> bool:
    """Check if a message looks like a business decision that could benefit from /think."""
    has_decision = any(kw in message for kw in _DECISION_KEYWORDS)
    has_business = any(kw in message for kw in _BUSINESS_KEYWORDS)
    return has_decision and has_business
