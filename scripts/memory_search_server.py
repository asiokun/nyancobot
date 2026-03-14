#!/usr/bin/env python3
"""memory_search_server.py - MCP stdio server for BM25+ memory with temporal decay.

v2.0: Replaced chromadb+Ollama vector search with pure-Python BM25+ and 30-day
half-life temporal decay. Zero external dependencies beyond stdlib.

Provides tools:
  - memory_store: Store text with category and timestamp
  - memory_search: BM25+ search with temporal decay scoring

Storage: ~/.nyancobot/memory/knowledge.json, feedback.json, etc.
Protocol: MCP stdio transport (JSON-RPC 2.0 over stdin/stdout)
"""

import json
import math
import os
import re
import sys
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MEMORY_DIR = Path(os.environ.get("NYANCOBOT_MEMORY_DIR",
                                  str(Path.home() / ".nyancobot" / "memory")))
HALF_LIFE_DAYS = 30  # temporal decay half-life
MAX_ENTRIES_PER_FILE = 500  # cap per category to prevent unbounded growth

SERVER_INFO = {
    "name": "nyancobot-memory-search",
    "version": "2.0.0",
}

CATEGORIES = ["slack", "command", "knowledge", "log", "feedback", "study"]

TOOLS = [
    {
        "name": "memory_store",
        "description": (
            "テキストをBM25+インデックスに保存するツール。"
            "重要な会話・知識・フィードバックを長期記憶として保存する場合に使え。"
            "外部API不要、ローカルで即座に保存される。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "保存するテキスト",
                },
                "category": {
                    "type": "string",
                    "enum": CATEGORIES,
                    "description": "カテゴリ: slack/command/knowledge/log/feedback/study",
                },
                "metadata": {
                    "type": "object",
                    "description": "追加メタデータ（source, rating等）",
                },
            },
            "required": ["text", "category"],
        },
    },
    {
        "name": "memory_search",
        "description": (
            "クエリに類似するテキストをBM25+時間減衰で検索するツール。"
            "新しい知識ほど高スコア、古い知識は自然に減衰する。"
            "過去の会話・知識を思い出したい場合に使え。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "検索クエリ",
                },
                "n_results": {
                    "type": "integer",
                    "description": "返す件数（デフォルト5）",
                },
                "category": {
                    "type": "string",
                    "enum": CATEGORIES,
                    "description": "カテゴリフィルタ（省略時は全カテゴリ）",
                },
            },
            "required": ["query"],
        },
    },
]


# ---------------------------------------------------------------------------
# Japanese tokenizer (simple bigram + word split)
# ---------------------------------------------------------------------------
_STOP_WORDS = frozenset([
    "の", "に", "は", "を", "た", "が", "で", "て", "と", "し", "れ", "さ",
    "ある", "いる", "する", "なる", "こと", "もの", "それ", "これ", "ため",
    "よう", "など", "から", "まで", "この", "その", "あの", "どの",
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "shall", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "and",
    "or", "but", "not", "no", "if", "then", "else", "when", "where",
    "that", "this", "it", "he", "she", "they", "we", "you", "i",
])


def tokenize(text: str) -> list[str]:
    """Tokenize text using word boundaries + CJK bigrams."""
    text = text.lower()
    # Extract ASCII words
    ascii_words = re.findall(r'[a-z0-9]+', text)
    # Extract CJK characters and create bigrams
    cjk_chars = re.findall(r'[\u3000-\u9fff\uf900-\ufaff]', text)
    bigrams = [cjk_chars[i] + cjk_chars[i + 1] for i in range(len(cjk_chars) - 1)]
    # Also include individual CJK chars for single-char matching
    tokens = ascii_words + bigrams + cjk_chars
    # Filter stop words
    return [t for t in tokens if t not in _STOP_WORDS and len(t) > 0]


# ---------------------------------------------------------------------------
# BM25+ implementation
# ---------------------------------------------------------------------------
class BM25Index:
    """Pure-Python BM25+ with temporal decay scoring."""

    def __init__(self, k1: float = 1.5, b: float = 0.75, delta: float = 1.0):
        self.k1 = k1
        self.b = b
        self.delta = delta  # BM25+ lower bound
        self.docs: list[dict] = []  # [{id, text, category, timestamp, metadata, tokens}]
        self.df: Counter = Counter()  # document frequency per term
        self.avgdl: float = 0.0

    def _rebuild_stats(self):
        """Rebuild df and avgdl from current docs."""
        self.df = Counter()
        total_len = 0
        for doc in self.docs:
            terms = set(doc["tokens"])
            for t in terms:
                self.df[t] += 1
            total_len += len(doc["tokens"])
        self.avgdl = total_len / len(self.docs) if self.docs else 1.0

    def add(self, doc_id: str, text: str, category: str,
            timestamp: str, metadata: dict | None = None):
        """Add a document to the index."""
        tokens = tokenize(text)
        self.docs.append({
            "id": doc_id,
            "text": text,
            "category": category,
            "timestamp": timestamp,
            "metadata": metadata or {},
            "tokens": tokens,
        })
        # Update df
        for t in set(tokens):
            self.df[t] += 1
        # Update avgdl
        total_len = sum(len(d["tokens"]) for d in self.docs)
        self.avgdl = total_len / len(self.docs) if self.docs else 1.0

    def search(self, query: str, n_results: int = 5,
               category: str | None = None) -> list[dict]:
        """BM25+ search with temporal decay."""
        query_tokens = tokenize(query)
        if not query_tokens or not self.docs:
            return []

        now = datetime.now()
        n_docs = len(self.docs)
        results = []

        for doc in self.docs:
            if category and doc["category"] != category:
                continue

            # BM25+ score
            tf_counter = Counter(doc["tokens"])
            doc_len = len(doc["tokens"])
            bm25_score = 0.0

            for term in query_tokens:
                if term not in self.df:
                    continue
                tf = tf_counter.get(term, 0)
                if tf == 0:
                    continue
                df = self.df[term]
                idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1)
                tf_norm = ((tf * (self.k1 + 1)) /
                           (tf + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)))
                bm25_score += idf * (tf_norm + self.delta)

            if bm25_score <= 0:
                continue

            # Temporal decay: score *= 2^(-age_days / half_life)
            try:
                doc_time = datetime.fromisoformat(doc["timestamp"])
                age_days = (now - doc_time).total_seconds() / 86400
            except (ValueError, TypeError):
                age_days = HALF_LIFE_DAYS  # default to half-life if parse fails

            decay = 2 ** (-age_days / HALF_LIFE_DAYS)
            final_score = bm25_score * decay

            results.append({
                "text": doc["text"],
                "score": round(final_score, 4),
                "bm25_raw": round(bm25_score, 4),
                "decay": round(decay, 4),
                "age_days": round(age_days, 1),
                "category": doc["category"],
                "metadata": doc["metadata"],
                "id": doc["id"],
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:n_results]

    def remove(self, doc_id: str) -> bool:
        """Remove a document by ID."""
        before = len(self.docs)
        self.docs = [d for d in self.docs if d["id"] != doc_id]
        if len(self.docs) < before:
            self._rebuild_stats()
            return True
        return False

    def count(self, category: str | None = None) -> int:
        if category:
            return sum(1 for d in self.docs if d["category"] == category)
        return len(self.docs)


# ---------------------------------------------------------------------------
# Persistence (JSON files per category)
# ---------------------------------------------------------------------------
_index: BM25Index | None = None


def _get_index() -> BM25Index:
    """Get or load the BM25 index from disk."""
    global _index
    if _index is not None:
        return _index

    _index = BM25Index()
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    for cat in CATEGORIES:
        cat_file = MEMORY_DIR / f"{cat}.json"
        if not cat_file.exists():
            continue
        try:
            entries = json.loads(cat_file.read_text(encoding="utf-8"))
            for entry in entries:
                _index.add(
                    doc_id=entry["id"],
                    text=entry["text"],
                    category=entry["category"],
                    timestamp=entry["timestamp"],
                    metadata=entry.get("metadata", {}),
                )
        except (json.JSONDecodeError, KeyError) as e:
            sys.stderr.write(f"Warning: Failed to load {cat_file}: {e}\n")

    return _index


def _save_category(category: str):
    """Save all docs of a category to disk."""
    index = _get_index()
    entries = []
    for doc in index.docs:
        if doc["category"] != category:
            continue
        entries.append({
            "id": doc["id"],
            "text": doc["text"],
            "category": doc["category"],
            "timestamp": doc["timestamp"],
            "metadata": doc["metadata"],
        })

    # Cap entries (keep newest)
    if len(entries) > MAX_ENTRIES_PER_FILE:
        entries.sort(key=lambda x: x["timestamp"], reverse=True)
        entries = entries[:MAX_ENTRIES_PER_FILE]

    cat_file = MEMORY_DIR / f"{category}.json"
    cat_file.write_text(json.dumps(entries, ensure_ascii=False, indent=2),
                        encoding="utf-8")


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------
def execute_memory_store(text: str, category: str,
                         metadata: dict | None = None) -> str:
    """Store text in BM25+ index."""
    if category not in CATEGORIES:
        return json.dumps({"error": f"Invalid category: {category}. Use: {CATEGORIES}"})

    index = _get_index()
    doc_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()

    index.add(doc_id=doc_id, text=text, category=category,
              timestamp=timestamp, metadata=metadata)
    _save_category(category)

    return json.dumps({
        "stored": True,
        "id": doc_id,
        "category": category,
        "total_in_category": index.count(category),
    })


def execute_memory_search(query: str, n_results: int = 5,
                           category: str | None = None) -> str:
    """BM25+ search with temporal decay."""
    index = _get_index()
    results = index.search(query, n_results=n_results, category=category)

    # Return clean results (remove internal fields)
    items = []
    for r in results:
        items.append({
            "text": r["text"],
            "score": r["score"],
            "bm25_raw": r["bm25_raw"],
            "decay": r["decay"],
            "age_days": r["age_days"],
            "category": r["category"],
            "metadata": r["metadata"],
        })

    return json.dumps(items, ensure_ascii=False)


# ---------------------------------------------------------------------------
# JSON-RPC helpers
# ---------------------------------------------------------------------------
def send_response(id_val, result):
    response = {"jsonrpc": "2.0", "id": id_val, "result": result}
    sys.stdout.write(json.dumps(response) + "\n")
    sys.stdout.flush()


def send_error(id_val, code, message):
    response = {
        "jsonrpc": "2.0",
        "id": id_val,
        "error": {"code": code, "message": message},
    }
    sys.stdout.write(json.dumps(response) + "\n")
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# MCP message handlers
# ---------------------------------------------------------------------------
def handle_initialize(id_val, params):
    send_response(id_val, {
        "protocolVersion": "2024-11-05",
        "capabilities": {"tools": {}},
        "serverInfo": SERVER_INFO,
    })


def handle_tools_list(id_val, params):
    send_response(id_val, {"tools": TOOLS})


def handle_tools_call(id_val, params):
    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})

    if tool_name == "memory_store":
        result_text = execute_memory_store(
            text=arguments.get("text", ""),
            category=arguments.get("category", "knowledge"),
            metadata=arguments.get("metadata"),
        )
    elif tool_name == "memory_search":
        result_text = execute_memory_search(
            query=arguments.get("query", ""),
            n_results=arguments.get("n_results", 5),
            category=arguments.get("category"),
        )
    else:
        send_error(id_val, -32602, f"Unknown tool: {tool_name}")
        return

    is_error = '"error"' in result_text
    send_response(id_val, {
        "content": [{"type": "text", "text": result_text}],
        "isError": is_error,
    })


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
HANDLERS = {
    "initialize": handle_initialize,
    "notifications/initialized": lambda id_val, params: None,
    "initialized": lambda id_val, params: None,
    "tools/list": handle_tools_list,
    "tools/call": handle_tools_call,
    "ping": lambda id_val, params: send_response(id_val, {}),
}


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = msg.get("method", "")
        id_val = msg.get("id")
        params = msg.get("params", {})

        handler = HANDLERS.get(method)
        if handler:
            handler(id_val, params)
        elif id_val is not None:
            send_error(id_val, -32601, f"Method not found: {method}")


if __name__ == "__main__":
    main()
