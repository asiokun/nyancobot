#!/usr/bin/env python3
"""web-tools-mcp-server.py - MCP stdio server for web tools.

Provides five tools for web operations:
  - web_scrape: Fetch HTML and extract text
  - web_search: DuckDuckGo search
  - web_screenshot: Playwright screenshot
  - web_post_note: Post article to note.com
  - web_post_x: Post tweet to X API

Protocol: MCP stdio transport (JSON-RPC 2.0 over stdin/stdout)
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import web tools from part1 and part2
try:
    from web_tools_part1 import web_scrape, web_search, web_screenshot
    from web_tools_part2 import web_post_note, web_post_x
except ImportError as e:
    # Graceful degradation if imports fail
    def web_scrape(*args, **kwargs):
        return f"Error: web_tools_part1 import failed: {e}"
    def web_search(*args, **kwargs):
        return f"Error: web_tools_part1 import failed: {e}"
    def web_screenshot(*args, **kwargs):
        return f"Error: web_tools_part1 import failed: {e}"
    def web_post_note(*args, **kwargs):
        return f"Error: web_tools_part2 import failed: {e}"
    def web_post_x(*args, **kwargs):
        return f"Error: web_tools_part2 import failed: {e}"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SERVER_INFO = {
    "name": "nyancobot-web-tools",
    "version": "1.0.0",
}

TOOLS = [
    {
        "name": "web_scrape",
        "description": "Fetch HTML from URL and extract text using CSS selector",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Target URL to scrape",
                },
                "selector": {
                    "type": "string",
                    "description": "CSS selector to extract specific element (optional, defaults to body text)",
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "web_search",
        "description": "Search using DuckDuckGo and return results",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return (default: 5)",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "web_screenshot",
        "description": "Capture website screenshot using Playwright",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Target URL to screenshot",
                },
                "output_path": {
                    "type": "string",
                    "description": "File path to save screenshot (PNG format)",
                },
            },
            "required": ["url", "output_path"],
        },
    },
    {
        "name": "web_post_note",
        "description": "Post an article to note.com using Playwright and saved cookies",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Article title",
                },
                "content": {
                    "type": "string",
                    "description": "Article body text",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of tags (optional)",
                },
                "price": {
                    "type": "integer",
                    "description": "Price for paid content (default: 0 = free)",
                },
            },
            "required": ["title", "content"],
        },
    },
    {
        "name": "web_post_x",
        "description": "Post a tweet to X (Twitter) API v2 using OAuth 1.0a",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Tweet text content",
                },
                "media_path": {
                    "type": "string",
                    "description": "Path to media file (optional)",
                },
            },
            "required": ["text"],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool implementations (wrappers with error handling)
# ---------------------------------------------------------------------------
def execute_web_scrape(url: str, selector: str = None) -> str:
    """Execute web_scrape with error handling."""
    try:
        result = web_scrape(url, selector)
        return result
    except Exception as e:
        return f"Error: web_scrape failed: {e}"


def execute_web_search(query: str, num_results: int = 5) -> str:
    """Execute web_search with error handling."""
    try:
        result = web_search(query, num_results)
        return result
    except Exception as e:
        return f"Error: web_search failed: {e}"


def execute_web_screenshot(url: str, output_path: str) -> str:
    """Execute web_screenshot with error handling."""
    try:
        result = web_screenshot(url, output_path)
        return result
    except Exception as e:
        return f"Error: web_screenshot failed: {e}"


def execute_web_post_note(title: str, content: str, tags: list = None, price: int = 0) -> str:
    """Execute web_post_note with error handling."""
    try:
        result = web_post_note(title, content, tags, price)
        return result
    except Exception as e:
        return f"Error: web_post_note failed: {e}"


def execute_web_post_x(text: str, media_path: str = None) -> str:
    """Execute web_post_x with error handling."""
    try:
        result = web_post_x(text, media_path)
        return result
    except Exception as e:
        return f"Error: web_post_x failed: {e}"


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


def send_notification(method, params=None):
    """Send a JSON-RPC 2.0 notification (no id)."""
    notification = {"jsonrpc": "2.0", "method": method}
    if params:
        notification["params"] = params
    msg = json.dumps(notification)
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# MCP message handlers
# ---------------------------------------------------------------------------
def handle_initialize(id_val, params):
    """Handle initialize request."""
    send_response(id_val, {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {},
        },
        "serverInfo": SERVER_INFO,
    })


def handle_initialized(id_val, params):
    """Handle initialized notification."""
    # No response needed for notifications
    pass


def handle_tools_list(id_val, params):
    """Handle tools/list request."""
    send_response(id_val, {"tools": TOOLS})


def handle_tools_call(id_val, params):
    """Handle tools/call request."""
    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})

    if tool_name == "web_scrape":
        result_text = execute_web_scrape(
            url=arguments.get("url", ""),
            selector=arguments.get("selector"),
        )
    elif tool_name == "web_search":
        result_text = execute_web_search(
            query=arguments.get("query", ""),
            num_results=arguments.get("num_results", 5),
        )
    elif tool_name == "web_screenshot":
        result_text = execute_web_screenshot(
            url=arguments.get("url", ""),
            output_path=arguments.get("output_path", ""),
        )
    elif tool_name == "web_post_note":
        result_text = execute_web_post_note(
            title=arguments.get("title", ""),
            content=arguments.get("content", ""),
            tags=arguments.get("tags"),
            price=arguments.get("price", 0),
        )
    elif tool_name == "web_post_x":
        result_text = execute_web_post_x(
            text=arguments.get("text", ""),
            media_path=arguments.get("media_path"),
        )
    else:
        send_error(id_val, -32602, f"Unknown tool: {tool_name}")
        return

    is_error = result_text.startswith("Error:")
    send_response(id_val, {
        "content": [{"type": "text", "text": result_text}],
        "isError": is_error,
    })


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
        except json.JSONDecodeError as e:
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
