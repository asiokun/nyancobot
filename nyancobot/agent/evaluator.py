"""Response evaluation pipeline for quality assurance.

Evaluates LLM responses using configurable evaluator backends:
- SelfCheckEvaluator: Uses a different LLM model via litellm for cross-model evaluation
- CodexEvaluator: Uses OpenAI Responses API (codex-mini)
- ClaudeEvaluator: Uses Anthropic Messages API (claude-sonnet)

The evaluation result determines whether web search augmentation is needed.
"""

import asyncio
import json
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from loguru import logger


# ============================================================================
# Data models
# ============================================================================

@dataclass
class EvaluationResult:
    """Result of evaluating an LLM response."""
    score: int  # 1-5
    factual_issues: list[str] = field(default_factory=list)
    needs_search: bool = False
    search_queries: list[str] = field(default_factory=list)
    confidence: float = 0.5
    evaluator_type: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "factual_issues": self.factual_issues,
            "needs_search": self.needs_search,
            "search_queries": self.search_queries,
            "confidence": self.confidence,
            "evaluator_type": self.evaluator_type,
        }


# ============================================================================
# Evaluation prompt
# ============================================================================

_EVAL_SYSTEM_PROMPT = """You are a response quality evaluator. Evaluate the following answer to a user's question.

Output ONLY valid JSON with this exact structure:
{
  "score": <1-5 integer>,
  "factual_issues": ["list of potential factual problems"],
  "needs_search": <true/false>,
  "search_queries": ["suggested search queries if needs_search is true"],
  "confidence": <0.0-1.0 float>
}

Scoring guide:
- 5: Excellent, factually accurate, comprehensive
- 4: Good, minor issues only
- 3: Acceptable but may have outdated info or gaps
- 2: Problematic, likely factual errors
- 1: Poor, mostly incorrect or irrelevant

Set needs_search=true if:
- Information may be outdated (dates, versions, prices, events)
- Claims that need verification
- Topics that change frequently
"""

_EVAL_USER_TEMPLATE = """## Question
{question}

## Answer to evaluate
{answer}

Evaluate this answer. Return ONLY JSON."""


# ============================================================================
# Base evaluator
# ============================================================================

class ResponseEvaluator(ABC):
    """Base class for response evaluators."""

    evaluator_type: str = "base"

    @abstractmethod
    async def evaluate(self, question: str, answer: str) -> EvaluationResult:
        """Evaluate a response and return scoring + search recommendations."""
        ...

    def _parse_evaluation_json(self, text: str) -> EvaluationResult:
        """Parse JSON evaluation result from LLM output."""
        # Extract JSON from potential markdown code blocks
        cleaned = text.strip()
        if "```" in cleaned:
            # Find JSON block
            for block in cleaned.split("```"):
                block = block.strip()
                if block.startswith("json"):
                    block = block[4:].strip()
                if block.startswith("{"):
                    cleaned = block
                    break

        try:
            data = json.loads(cleaned)
            return EvaluationResult(
                score=max(1, min(5, int(data.get("score", 3)))),
                factual_issues=data.get("factual_issues", []),
                needs_search=bool(data.get("needs_search", False)),
                search_queries=data.get("search_queries", []),
                confidence=float(data.get("confidence", 0.5)),
                evaluator_type=self.evaluator_type,
            )
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.warning(f"Failed to parse evaluation JSON: {e}")
            return EvaluationResult(
                score=3,
                factual_issues=["Evaluation parsing failed"],
                needs_search=False,
                confidence=0.3,
                evaluator_type=self.evaluator_type,
            )


# ============================================================================
# SelfCheckEvaluator (litellm cross-model)
# ============================================================================

class SelfCheckEvaluator(ResponseEvaluator):
    """Evaluate using a different LLM model via litellm."""

    evaluator_type = "self"

    def __init__(self, model: str = "gemini/gemini-2.5-flash", api_key: str | None = None):
        self.model = model
        if api_key:
            # Set appropriate env var based on model
            model_lower = model.lower()
            if "gemini" in model_lower:
                os.environ.setdefault("GEMINI_API_KEY", api_key)
            elif "deepseek" in model_lower:
                os.environ.setdefault("DEEPSEEK_API_KEY", api_key)

    async def evaluate(self, question: str, answer: str) -> EvaluationResult:
        try:
            from litellm import acompletion

            messages = [
                {"role": "system", "content": _EVAL_SYSTEM_PROMPT},
                {"role": "user", "content": _EVAL_USER_TEMPLATE.format(
                    question=question, answer=answer
                )},
            ]
            response = await acompletion(
                model=self.model,
                messages=messages,
                max_tokens=1024,
                temperature=0.3,
            )
            content = response.choices[0].message.content or ""
            return self._parse_evaluation_json(content)
        except Exception as e:
            logger.error(f"SelfCheckEvaluator failed: {e}")
            return EvaluationResult(
                score=3, confidence=0.2, evaluator_type=self.evaluator_type
            )


# ============================================================================
# CodexEvaluator (OpenAI Responses API)
# ============================================================================

class CodexEvaluator(ResponseEvaluator):
    """Evaluate using OpenAI Responses API."""

    evaluator_type = "codex"

    def __init__(self, api_key: str = "", model: str = "codex-mini"):
        self.api_key = api_key
        self.model = model

    async def evaluate(self, question: str, answer: str) -> EvaluationResult:
        if not self.api_key:
            logger.warning("CodexEvaluator: no API key configured")
            return EvaluationResult(score=3, confidence=0.1, evaluator_type=self.evaluator_type)

        try:
            prompt = (
                f"{_EVAL_SYSTEM_PROMPT}\n\n"
                f"{_EVAL_USER_TEMPLATE.format(question=question, answer=answer)}"
            )
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/responses",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "input": prompt,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            # Extract text from Responses API output
            content = ""
            for item in data.get("output", []):
                if item.get("type") == "message":
                    for block in item.get("content", []):
                        if block.get("type") == "output_text":
                            content += block.get("text", "")
            if not content:
                content = data.get("output_text", "")

            return self._parse_evaluation_json(content)
        except Exception as e:
            logger.error(f"CodexEvaluator failed: {e}")
            return EvaluationResult(
                score=3, confidence=0.2, evaluator_type=self.evaluator_type
            )


# ============================================================================
# ClaudeEvaluator (Anthropic Messages API)
# ============================================================================

class ClaudeEvaluator(ResponseEvaluator):
    """Evaluate using Anthropic Messages API."""

    evaluator_type = "claude"

    def __init__(self, api_key: str = "", model: str = "claude-sonnet-4-6"):
        self.api_key = api_key
        self.model = model

    async def evaluate(self, question: str, answer: str) -> EvaluationResult:
        if not self.api_key:
            logger.warning("ClaudeEvaluator: no API key configured")
            return EvaluationResult(score=3, confidence=0.1, evaluator_type=self.evaluator_type)

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "max_tokens": 1024,
                        "system": _EVAL_SYSTEM_PROMPT,
                        "messages": [
                            {"role": "user", "content": _EVAL_USER_TEMPLATE.format(
                                question=question, answer=answer
                            )},
                        ],
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            content = ""
            for block in data.get("content", []):
                if block.get("type") == "text":
                    content += block.get("text", "")

            return self._parse_evaluation_json(content)
        except Exception as e:
            logger.error(f"ClaudeEvaluator failed: {e}")
            return EvaluationResult(
                score=3, confidence=0.2, evaluator_type=self.evaluator_type
            )


# ============================================================================
# FT data collection
# ============================================================================

class FTDataCollector:
    """Collect fine-tuning data from evaluation pipeline runs."""

    def __init__(self, data_dir: str = "~/.nyancobot/ft-data"):
        self.data_path = Path(os.path.expanduser(data_dir)) / "evaluations.jsonl"
        self.data_path.parent.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        question: str,
        initial_answer: str,
        evaluation: EvaluationResult,
        search_results: str | None,
        final_answer: str,
        model: str,
    ) -> None:
        """Save evaluation data for future fine-tuning (DPO/RLHF)."""
        if evaluation.score >= 4:
            return  # Only save low-quality responses for improvement data

        record = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "question": question,
            "initial_answer": initial_answer,
            "evaluation": evaluation.to_dict(),
            "search_results": search_results,
            "final_answer": final_answer,
            "model": model,
        }
        try:
            with open(self.data_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            logger.info(f"FT data saved: score={evaluation.score}, model={model}")
        except Exception as e:
            logger.error(f"FT data save failed: {e}")


# ============================================================================
# Rule-based search trigger
# ============================================================================

# Keywords that strongly suggest the answer may need fresh data
_SEARCH_TRIGGER_KEYWORDS = [
    "最新", "いつ", "いくら", "誰が", "何年",
    "今日", "昨日", "今月", "今年", "現在",
    "latest", "current", "price", "when", "who",
    "how much", "update", "news", "recent",
]


def should_search_by_keywords(question: str) -> bool:
    """Check if the question contains keywords that warrant immediate search."""
    q_lower = question.lower()
    return any(kw in q_lower for kw in _SEARCH_TRIGGER_KEYWORDS)


# ============================================================================
# Factory
# ============================================================================

def create_evaluator(config: dict[str, Any]) -> ResponseEvaluator | None:
    """Create an evaluator from config.json evaluator section.

    Args:
        config: The "evaluator" section from config.json

    Returns:
        A ResponseEvaluator instance, or None if evaluator is disabled.
    """
    if not config or not config.get("enabled", False):
        return None

    eval_type = config.get("type", "none")
    if eval_type == "none":
        return None

    if eval_type == "self":
        return SelfCheckEvaluator(
            model=config.get("self_check_model", "gemini/gemini-2.5-flash"),
            api_key=config.get("api_key"),
        )
    elif eval_type == "codex":
        return CodexEvaluator(
            api_key=config.get("api_key", ""),
            model=config.get("model", "codex-mini"),
        )
    elif eval_type == "claude":
        return ClaudeEvaluator(
            api_key=config.get("api_key", ""),
            model=config.get("model", "claude-sonnet-4-6"),
        )
    else:
        logger.warning(f"Unknown evaluator type: {eval_type}")
        return None
