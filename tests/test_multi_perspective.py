"""Tests for nyancobot.agent.multi_perspective module."""

import pytest
from unittest.mock import AsyncMock, patch

from nyancobot.agent.multi_perspective import (
    MultiPerspectiveEvaluator,
    should_suggest_think,
)


# ============================================================================
# should_suggest_think
# ============================================================================

class TestShouldSuggestThink:
    def test_business_decision(self):
        assert should_suggest_think("新しいサービスを始めたい") is True
        assert should_suggest_think("月10万円の売上を目指したい") is True

    def test_casual_message(self):
        assert should_suggest_think("こんにちは") is False
        assert should_suggest_think("Pythonの書き方を教えて") is False

    def test_only_decision(self):
        # Decision words without business context
        assert should_suggest_think("ラーメン食べたい") is False

    def test_only_business(self):
        # Business words without decision context
        assert should_suggest_think("売上が100万円だった") is False


# ============================================================================
# MultiPerspectiveEvaluator
# ============================================================================

class TestMultiPerspectiveEvaluator:
    def test_init(self):
        config = {
            "api_keys": {
                "anthropic_api_key": "test-key",
                "gemini_api_key": "test-key",
            },
        }
        evaluator = MultiPerspectiveEvaluator(config)
        assert evaluator._get_api_key("anthropic") == "test-key"
        assert evaluator._get_api_key("gemini") == "test-key"
        assert evaluator._get_api_key("deepseek") is None

    def test_no_keys(self):
        evaluator = MultiPerspectiveEvaluator({})
        assert evaluator._get_api_key("anthropic") is None

    @pytest.mark.asyncio
    async def test_insufficient_keys(self):
        evaluator = MultiPerspectiveEvaluator({
            "api_keys": {"anthropic_api_key": "test-key"},
        })
        result = await evaluator.evaluate("test idea")
        assert "最低2つ" in result

    @pytest.mark.asyncio
    async def test_evaluate_with_mocks(self):
        config = {
            "api_keys": {
                "anthropic_api_key": "key1",
                "gemini_api_key": "key2",
                "deepseek_api_key": "key3",
            },
        }
        evaluator = MultiPerspectiveEvaluator(config)

        with patch.object(evaluator, "_call_model", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "- ポイント1\n- ポイント2"
            result = await evaluator.evaluate("AIビジネスを始めたい")

        assert "多角評価結果" in result
        assert mock_call.call_count == 3  # 3 keys configured

    def test_custom_models(self):
        config = {
            "api_keys": {"anthropic_api_key": "key"},
            "think_models": {"Claude": "claude-opus-4-6"},
        }
        evaluator = MultiPerspectiveEvaluator(config)
        from nyancobot.agent.multi_perspective import _PERSPECTIVES
        claude_p = next(p for p in _PERSPECTIVES if p["name"] == "Claude")
        assert evaluator._get_model(claude_p) == "claude-opus-4-6"
