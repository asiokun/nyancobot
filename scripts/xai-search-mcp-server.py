#!/usr/bin/env python3
"""xai-search-mcp-server.py - MCP stdio server for xAI x_search and x_analyze tools.

Provides two tools for searching X posts via xAI Grok:
  - x_search: Search X posts using xAI API (grok-3-mini model)
  - x_analyze: Analyze search results with custom analysis type (trend/competitor/sentiment)

Protocol: MCP stdio transport (JSON-RPC 2.0 over stdin/stdout)
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
load_dotenv(Path.home() / ".nyancobot" / ".env")

XAI_API_KEY = os.environ.get("XAI_API_KEY", "")
XAI_API_ENDPOINT = "https://api.x.ai/v1/responses"
XAI_MODEL = "grok-4-1-fast-non-reasoning"

SERVER_INFO = {
    "name": "nyancobot-xai-search",
    "version": "1.0.0",
}

TOOLS = [
    {
        "name": "x_search",
        "description": (
            "xAI Grokを使用してX（Twitter）上のポストを検索するツール。"
            "クエリに関連するポストを取得し、トレンド調査や市場監視に使用可。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "検索クエリ（例: 'AI startup funding', 'React.js trends'）",
                },
                "max_results": {
                    "type": "integer",
                    "description": "返す結果の最大件数（デフォルト: 10）",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "x_analyze",
        "description": (
            "xAI Grokを使用してX上の検索結果を分析するツール。"
            "トレンド分析、競合調査、感情分析など複数の分析タイプに対応。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "検索・分析対象のクエリ",
                },
                "analysis_type": {
                    "type": "string",
                    "enum": ["trend", "competitor", "sentiment"],
                    "description": "分析タイプ: trend(トレンド分析), competitor(競合調査), sentiment(感情分析)",
                },
            },
            "required": ["query"],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------
def execute_x_search(query: str, max_results: int = 10) -> str:
    """Search X posts using xAI Grok API."""
    if not XAI_API_KEY:
        return "Error: XAI_API_KEY not set in environment variables"

    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": XAI_MODEL,
        "input": f"Search for posts on X about: {query}. Return top {max_results} relevant posts with their content.",
        "tools": [
            {"type": "x_search"},
        ],
    }

    try:
        resp = requests.post(
            XAI_API_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()

        # Extract response content from Responses API format
        output = data.get("output", [])
        texts = []
        for item in output:
            if item.get("type") == "message":
                for content_item in item.get("content", []):
                    if content_item.get("type") == "output_text":
                        texts.append(content_item.get("text", ""))
        if texts:
            return "\n\n".join(texts)

        # Fallback: try to find any text in output
        return json.dumps(data.get("output", "No results"), ensure_ascii=False, indent=2)

    except requests.exceptions.Timeout:
        return "Error: xAI API request timed out (30s)"
    except requests.exceptions.HTTPError as e:
        return f"Error: xAI API HTTP error {e.response.status_code}: {e.response.text}"
    except requests.exceptions.RequestException as e:
        return f"Error: xAI API request failed: {e}"
    except Exception as e:
        return f"Error: Unexpected error during search: {e}"


def execute_x_analyze(query: str, analysis_type: str = "trend") -> str:
    """Analyze X posts using xAI Grok API."""
    if not XAI_API_KEY:
        return "Error: XAI_API_KEY not set in environment variables"

    analysis_prompts = {
        "trend": f"X上の「{query}」に関するトレンドを詳細に分析してください。主要なテーマ、成長ポイント、新しい動きを整理して報告してください。",
        "competitor": f"X上の「{query}」に関する競合情報を調査してください。主要なプレイヤー、差別化ポイント、市場シェアの動向を分析してください。",
        "sentiment": f"X上の「{query}」に関する感情分析をしてください。ポジティブ/ネガティブ/ニュートラルな言及の比率、主要な懸念点、好評な点を整理してください。",
    }

    if analysis_type not in analysis_prompts:
        return f"Error: Unknown analysis_type '{analysis_type}'. Supported: trend, competitor, sentiment"

    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": XAI_MODEL,
        "input": analysis_prompts[analysis_type],
        "tools": [
            {"type": "x_search"},
            {"type": "web_search"},
        ],
    }

    try:
        resp = requests.post(
            XAI_API_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()

        # Extract response content from Responses API format
        output = data.get("output", [])
        texts = []
        for item in output:
            if item.get("type") == "message":
                for content_item in item.get("content", []):
                    if content_item.get("type") == "output_text":
                        texts.append(content_item.get("text", ""))
        if texts:
            return "\n\n".join(texts)

        return json.dumps(data.get("output", "No results"), ensure_ascii=False, indent=2)

    except requests.exceptions.Timeout:
        return "Error: xAI API request timed out (30s)"
    except requests.exceptions.HTTPError as e:
        return f"Error: xAI API HTTP error {e.response.status_code}: {e.response.text}"
    except requests.exceptions.RequestException as e:
        return f"Error: xAI API request failed: {e}"
    except Exception as e:
        return f"Error: Unexpected error during analysis: {e}"


# ---------------------------------------------------------------------------
# JSON-RPC helpers
# ---------------------------------------------------------------------------
def send_response(id_val, result):
    """Send a JSON-RPC 2.0 response."""
    response = {"jsonrpc": "2.0", "id": id_val, "result": result}
    msg = json.dumps(response)
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()


def send_error(id_val, code, message):
    """Send a JSON-RPC 2.0 error response."""
    response = {
        "jsonrpc": "2.0",
        "id": id_val,
        "error": {"code": code, "message": message},
    }
    msg = json.dumps(response)
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# MCP message handlers
# ---------------------------------------------------------------------------
def handle_initialize(id_val, params):
    """Handle initialize request."""
    send_response(
        id_val,
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
            },
            "serverInfo": SERVER_INFO,
        },
    )


def handle_initialized(id_val, params):
    """Handle initialized notification."""
    pass


def handle_tools_list(id_val, params):
    """Handle tools/list request."""
    send_response(id_val, {"tools": TOOLS})


def handle_tools_call(id_val, params):
    """Handle tools/call request."""
    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})

    if tool_name == "x_search":
        query = arguments.get("query", "")
        max_results = arguments.get("max_results", 10)
        result_text = execute_x_search(query, max_results)
    elif tool_name == "x_analyze":
        query = arguments.get("query", "")
        analysis_type = arguments.get("analysis_type", "trend")
        result_text = execute_x_analyze(query, analysis_type)
    else:
        send_error(id_val, -32602, f"Unknown tool: {tool_name}")
        return

    is_error = result_text.startswith("Error:")
    send_response(
        id_val,
        {
            "content": [{"type": "text", "text": result_text}],
            "isError": is_error,
        },
    )


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
HANDLERS = {
    "initialize": handle_initialize,
    "notifications/initialized": handle_initialized,
    "initialized": handle_initialized,
    "tools/list": handle_tools_list,
    "tools/call": handle_tools_call,
    "ping": lambda id_val, params: send_response(id_val, {}),
}


def main():
    """Main JSON-RPC message loop over stdin/stdout."""
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
