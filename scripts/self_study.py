#!/usr/bin/env python3
"""self_study.py - CashClaw-inspired self-learning session for nyancobot.

Runs during idle periods (triggered by cron). Analyzes feedback, generates
knowledge entries, and stores them in BM25+ memory.

Study modes (rotated):
  1. feedback_analysis: Analyze feedback patterns, extract improvement insights
  2. knowledge_refresh: Review old knowledge, update or prune stale entries
  3. task_simulation: Generate practice scenarios based on past interactions

Usage:
  python3 self_study.py [mode]
  If mode is omitted, rotates automatically based on day of month.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Import memory functions from the MCP server
sys.path.insert(0, str(Path(__file__).parent))
from memory_search_server import (
    _get_index, _save_category, execute_memory_store, execute_memory_search,
    MEMORY_DIR, CATEGORIES
)

STUDY_LOG_DIR = MEMORY_DIR / "study_logs"
STUDY_MODES = ["feedback_analysis", "knowledge_refresh", "knowledge_consolidation"]


def get_study_mode(explicit_mode: str | None = None) -> str:
    """Get study mode - explicit or auto-rotate by day."""
    if explicit_mode and explicit_mode in STUDY_MODES:
        return explicit_mode
    day = datetime.now().day
    return STUDY_MODES[day % len(STUDY_MODES)]


def feedback_analysis():
    """Analyze feedback entries and extract patterns."""
    index = _get_index()
    feedback_docs = [d for d in index.docs if d["category"] == "feedback"]

    if not feedback_docs:
        return {"mode": "feedback_analysis", "result": "No feedback data yet."}

    # Group by rating if available
    rated = [d for d in feedback_docs if d["metadata"].get("rating")]
    unrated = [d for d in feedback_docs if not d["metadata"].get("rating")]

    # Extract common themes from low-rated feedback
    low_rated = [d for d in rated
                 if float(d["metadata"].get("rating", 5)) < 3]
    high_rated = [d for d in rated
                  if float(d["metadata"].get("rating", 5)) >= 4]

    insights = []
    if low_rated:
        insights.append(f"Low-rated feedback ({len(low_rated)} entries) - review needed")
        for d in low_rated[:5]:
            insights.append(f"  - [{d['metadata'].get('rating')}] {d['text'][:100]}")

    if high_rated:
        insights.append(f"High-rated feedback ({len(high_rated)} entries) - reinforce patterns")

    insights.append(f"Total feedback: {len(feedback_docs)} (rated: {len(rated)}, unrated: {len(unrated)})")

    # Store insight as knowledge
    if insights:
        insight_text = "\n".join(insights)
        execute_memory_store(
            text=f"[自己学習: feedback_analysis {datetime.now().strftime('%Y-%m-%d')}]\n{insight_text}",
            category="study",
            metadata={"source": "self_study", "mode": "feedback_analysis"},
        )

    return {"mode": "feedback_analysis", "insights": insights}


def knowledge_refresh():
    """Review and prune old knowledge entries."""
    index = _get_index()
    knowledge_docs = [d for d in index.docs if d["category"] == "knowledge"]

    if not knowledge_docs:
        return {"mode": "knowledge_refresh", "result": "No knowledge data yet."}

    # Find entries older than 60 days
    now = datetime.now()
    old_entries = []
    for d in knowledge_docs:
        try:
            doc_time = datetime.fromisoformat(d["timestamp"])
            age_days = (now - doc_time).total_seconds() / 86400
            if age_days > 60:
                old_entries.append({"id": d["id"], "text": d["text"][:80], "age_days": round(age_days)})
        except (ValueError, TypeError):
            pass

    result = {
        "mode": "knowledge_refresh",
        "total_knowledge": len(knowledge_docs),
        "old_entries_60d": len(old_entries),
    }

    if old_entries:
        # Log but don't auto-delete - just flag for review
        insight_text = f"Knowledge refresh: {len(old_entries)} entries older than 60 days found.\n"
        for e in old_entries[:10]:
            insight_text += f"  - [{e['age_days']}d] {e['text']}\n"

        execute_memory_store(
            text=f"[自己学習: knowledge_refresh {datetime.now().strftime('%Y-%m-%d')}]\n{insight_text}",
            category="study",
            metadata={"source": "self_study", "mode": "knowledge_refresh"},
        )
        result["flagged"] = old_entries[:10]

    return result


def knowledge_consolidation():
    """Consolidate scattered knowledge into coherent summaries."""
    index = _get_index()

    stats = {}
    for cat in CATEGORIES:
        count = index.count(cat)
        if count > 0:
            stats[cat] = count

    insight_text = f"Knowledge consolidation report {datetime.now().strftime('%Y-%m-%d')}:\n"
    insight_text += f"Total entries: {sum(stats.values())}\n"
    for cat, count in sorted(stats.items(), key=lambda x: -x[1]):
        insight_text += f"  {cat}: {count}\n"

    execute_memory_store(
        text=f"[自己学習: consolidation {datetime.now().strftime('%Y-%m-%d')}]\n{insight_text}",
        category="study",
        metadata={"source": "self_study", "mode": "knowledge_consolidation"},
    )

    return {"mode": "knowledge_consolidation", "stats": stats}


def run_study(mode: str) -> dict:
    """Run a study session."""
    runners = {
        "feedback_analysis": feedback_analysis,
        "knowledge_refresh": knowledge_refresh,
        "knowledge_consolidation": knowledge_consolidation,
    }
    runner = runners.get(mode, knowledge_consolidation)
    return runner()


def main():
    explicit_mode = sys.argv[1] if len(sys.argv) > 1 else None
    mode = get_study_mode(explicit_mode)

    print(f"[self_study] Mode: {mode}")
    print(f"[self_study] Time: {datetime.now().isoformat()}")

    result = run_study(mode)

    # Save study log
    STUDY_LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = STUDY_LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.json"

    logs = []
    if log_file.exists():
        try:
            logs = json.loads(log_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    logs.append({
        "timestamp": datetime.now().isoformat(),
        "mode": mode,
        "result": result,
    })

    log_file.write_text(json.dumps(logs, ensure_ascii=False, indent=2),
                        encoding="utf-8")

    print(f"[self_study] Result: {json.dumps(result, ensure_ascii=False, indent=2)}")
    print(f"[self_study] Log saved: {log_file}")


if __name__ == "__main__":
    main()
