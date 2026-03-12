"""Tests for nyancobot.agent.evaluator module."""

import json
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from nyancobot.agent.evaluator import (
    EvaluationResult,
    ResponseEvaluator,
    SelfCheckEvaluator,
    CodexEvaluator,
    ClaudeEvaluator,
    FTDataCollector,
    create_evaluator,
    should_search_by_keywords,
)


# ============================================================================
# EvaluationResult
# ============================================================================

class TestEvaluationResult:
    def test_to_dict(self):
        r = EvaluationResult(
            score=4,
            factual_issues=["outdated info"],
            needs_search=True,
            search_queries=["latest news"],
            confidence=0.8,
            evaluator_type="test",
        )
        d = r.to_dict()
        assert d["score"] == 4
        assert d["needs_search"] is True
        assert len(d["search_queries"]) == 1

    def test_defaults(self):
        r = EvaluationResult(score=3)
        assert r.factual_issues == []
        assert r.needs_search is False
        assert r.confidence == 0.5


# ============================================================================
# JSON parsing
# ============================================================================

class TestJSONParsing:
    def _make_evaluator(self):
        """Create a concrete evaluator for testing _parse_evaluation_json."""
        class MockEvaluator(ResponseEvaluator):
            evaluator_type = "mock"
            async def evaluate(self, question, answer):
                return EvaluationResult(score=3)
        return MockEvaluator()

    def test_parse_valid_json(self):
        e = self._make_evaluator()
        result = e._parse_evaluation_json(json.dumps({
            "score": 5,
            "factual_issues": [],
            "needs_search": False,
            "search_queries": [],
            "confidence": 0.9,
        }))
        assert result.score == 5
        assert result.confidence == 0.9

    def test_parse_markdown_code_block(self):
        e = self._make_evaluator()
        text = '```json\n{"score": 2, "factual_issues": ["wrong"], "needs_search": true, "search_queries": ["fix"], "confidence": 0.4}\n```'
        result = e._parse_evaluation_json(text)
        assert result.score == 2
        assert result.needs_search is True

    def test_parse_invalid_json(self):
        e = self._make_evaluator()
        result = e._parse_evaluation_json("not json at all")
        assert result.score == 3  # fallback
        assert result.confidence == 0.3

    def test_score_clamping(self):
        e = self._make_evaluator()
        result = e._parse_evaluation_json('{"score": 10}')
        assert result.score == 5  # clamped to max
        result = e._parse_evaluation_json('{"score": -1}')
        assert result.score == 1  # clamped to min


# ============================================================================
# Keyword search trigger
# ============================================================================

class TestKeywordSearch:
    def test_japanese_keywords(self):
        assert should_search_by_keywords("最新のPython情報を教えて") is True
        assert should_search_by_keywords("いくらですか") is True
        assert should_search_by_keywords("今年の売上は") is True

    def test_english_keywords(self):
        assert should_search_by_keywords("What is the latest version?") is True
        assert should_search_by_keywords("current price of BTC") is True

    def test_no_trigger(self):
        assert should_search_by_keywords("Pythonの基本文法を教えて") is False
        assert should_search_by_keywords("FizzBuzzを書いて") is False


# ============================================================================
# Factory
# ============================================================================

class TestCreateEvaluator:
    def test_disabled(self):
        assert create_evaluator({"enabled": False}) is None
        assert create_evaluator({}) is None
        assert create_evaluator(None) is None

    def test_none_type(self):
        assert create_evaluator({"enabled": True, "type": "none"}) is None

    def test_self_type(self):
        e = create_evaluator({
            "enabled": True,
            "type": "self",
            "self_check_model": "gemini/gemini-2.5-flash",
        })
        assert isinstance(e, SelfCheckEvaluator)
        assert e.model == "gemini/gemini-2.5-flash"

    def test_codex_type(self):
        e = create_evaluator({
            "enabled": True,
            "type": "codex",
            "api_key": "test-key",
            "model": "codex-mini",
        })
        assert isinstance(e, CodexEvaluator)

    def test_claude_type(self):
        e = create_evaluator({
            "enabled": True,
            "type": "claude",
            "api_key": "test-key",
        })
        assert isinstance(e, ClaudeEvaluator)


# ============================================================================
# SelfCheckEvaluator with mock
# ============================================================================

class TestSelfCheckEvaluator:
    @pytest.mark.asyncio
    async def test_evaluate_with_mock(self):
        evaluator = SelfCheckEvaluator(model="test-model")
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "score": 4,
            "factual_issues": [],
            "needs_search": False,
            "search_queries": [],
            "confidence": 0.85,
        })

        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            result = await evaluator.evaluate("What is Python?", "Python is a programming language.")

        assert result.score == 4
        assert result.confidence == 0.85
        assert result.evaluator_type == "self"

    @pytest.mark.asyncio
    async def test_evaluate_failure(self):
        evaluator = SelfCheckEvaluator(model="test-model")
        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = Exception("API error")
            result = await evaluator.evaluate("Q", "A")

        assert result.score == 3  # fallback
        assert result.confidence == 0.2


# ============================================================================
# FTDataCollector
# ============================================================================

class TestFTDataCollector:
    def test_save_low_score(self, tmp_path):
        collector = FTDataCollector(data_dir=str(tmp_path))
        evaluation = EvaluationResult(score=2, factual_issues=["wrong"])
        collector.save(
            question="Q",
            initial_answer="bad A",
            evaluation=evaluation,
            search_results="search data",
            final_answer="good A",
            model="test-model",
        )
        data_file = tmp_path / "evaluations.jsonl"
        assert data_file.exists()
        records = [json.loads(line) for line in data_file.read_text().splitlines()]
        assert len(records) == 1
        assert records[0]["evaluation"]["score"] == 2

    def test_skip_high_score(self, tmp_path):
        collector = FTDataCollector(data_dir=str(tmp_path))
        evaluation = EvaluationResult(score=5)
        collector.save(
            question="Q", initial_answer="A", evaluation=evaluation,
            search_results=None, final_answer="A", model="test",
        )
        data_file = tmp_path / "evaluations.jsonl"
        assert not data_file.exists()  # score >= 4 should be skipped
