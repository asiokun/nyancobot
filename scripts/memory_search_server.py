#!/usr/bin/env python3
"""memory_search_server.py - MCP stdio server for vector memory (chromadb + nomic-embed-text).

Provides two tools:
  - memory_store: Embed text and store in chromadb
  - memory_search: Search similar texts from chromadb

Protocol: MCP stdio transport (JSON-RPC 2.0 over stdin/stdout)
"""

import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

import chromadb
import httpx


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
VECTOR_DB_PATH = str(Path.home() / ".nyancobot" / "vector_db")
COLLECTION_NAME = "nyancobot_memory"
OLLAMA_EMBED_URL = os.environ.get("OLLAMA_EMBED_URL", "http://127.0.0.1:11434/api/embeddings")
EMBED_MODEL = "nomic-embed-text"

SERVER_INFO = {
    "name": "nyancobot-memory-search",
    "version": "1.0.0",
}

TOOLS = [
    {
        "name": "memory_store",
        "description": (
            "テキストをembedding化してベクトルDBに保存するツール。"
            "重要な会話・知識・ログを長期記憶として保存する場合に使え。"
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
                    "enum": ["slack", "command", "knowledge", "log"],
                    "description": "カテゴリ: slack/command/knowledge/log",
                },
                "metadata": {
                    "type": "object",
                    "description": "追加メタデータ（timestamp等）",
                },
            },
            "required": ["text", "category"],
        },
    },
    {
        "name": "memory_search",
        "description": (
            "クエリに類似するテキストをベクトルDBから検索するツール。"
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
                    "enum": ["slack", "command", "knowledge", "log"],
                    "description": "カテゴリフィルタ（省略時は全カテゴリ）",
                },
            },
            "required": ["query"],
        },
    },
]


# ---------------------------------------------------------------------------
# Embedding & ChromaDB helpers
# ---------------------------------------------------------------------------
_chroma_client = None
_collection = None


def _get_collection():
    """Get or initialize chromadb collection (lazy init)."""
    global _chroma_client, _collection
    if _collection is not None:
        return _collection
    try:
        Path(VECTOR_DB_PATH).mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
        _collection = _chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        return _collection
    except Exception as e:
        raise RuntimeError(f"ChromaDB initialization failed: {e}")


def _get_embedding(text: str) -> list[float]:
    """Get embedding from Ollama nomic-embed-text."""
    resp = httpx.post(
        OLLAMA_EMBED_URL,
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["embedding"]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------
def execute_memory_store(text: str, category: str, metadata: dict | None = None) -> str:
    """Embed and store text in chromadb."""
    try:
        embedding = _get_embedding(text)
    except Exception as e:
        return json.dumps({"error": "Ollama API unavailable", "text": f"embedding生成に失敗しました: {e}"})

    try:
        collection = _get_collection()
    except RuntimeError as e:
        return json.dumps({"error": str(e)})

    doc_id = str(uuid.uuid4())
    doc_metadata = {
        "category": category,
        "timestamp": datetime.now().isoformat(),
    }
    if metadata:
        doc_metadata.update({k: str(v) for k, v in metadata.items()})

    collection.add(
        ids=[doc_id],
        embeddings=[embedding],
        documents=[text],
        metadatas=[doc_metadata],
    )

    return json.dumps({"stored": True, "id": doc_id})


def execute_memory_search(query: str, n_results: int = 5, category: str | None = None) -> str:
    """Search similar texts from chromadb."""
    try:
        embedding = _get_embedding(query)
    except Exception as e:
        return json.dumps({"error": "Ollama API unavailable", "text": f"embedding生成に失敗しました: {e}"})

    try:
        collection = _get_collection()
    except RuntimeError as e:
        return json.dumps({"error": str(e)})

    where_filter = {"category": category} if category else None

    try:
        results = collection.query(
            query_embeddings=[embedding],
            n_results=min(n_results, collection.count() or 1),
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as e:
        return json.dumps({"error": f"Search failed: {e}"})

    items = []
    if results and results["documents"]:
        for i, doc in enumerate(results["documents"][0]):
            distance = results["distances"][0][i] if results["distances"] else 0
            similarity = round(1 - distance, 4)
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            items.append({
                "text": doc,
                "similarity": similarity,
                "category": meta.get("category", ""),
                "metadata": meta,
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
