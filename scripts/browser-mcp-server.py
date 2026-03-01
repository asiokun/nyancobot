#!/usr/bin/env python3
"""browser-mcp-server.py - MCP stdio server for browser automation tools.

Provides nine tools for browser operations:
  - browser_navigate: Navigate to URL and get page info
  - browser_act: Perform browser action (click, fill, press, select, scroll)
  - browser_snapshot: Get current page screenshot + AX tree
  - browser_state: Get lightweight browser session state
  - browser_vision: Analyze screenshot via VisionSecretary
  - browser_close: Close browser session
  - web_scrape: Fetch HTML and extract text
  - web_search: DuckDuckGo search
  - web_post_x: Post tweet to X API

Protocol: MCP stdio transport (JSON-RPC 2.0 over stdin/stdout)
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# ---------------------------------------------------------------------------
# Import modules with graceful degradation
# ---------------------------------------------------------------------------
_browser_import_error = None
_vision_import_error = None

try:
    from browser_session import BrowserSession
except ImportError as e:
    BrowserSession = None
    _browser_import_error = str(e)

try:
    from vision_secretary import VisionSecretary
except ImportError as e:
    VisionSecretary = None
    _vision_import_error = str(e)

try:
    from web_tools_part1 import web_scrape, web_search
except ImportError as e:
    def web_scrape(*args, **kwargs):
        return f"Error: web_tools_part1 import failed: {e}"
    def web_search(*args, **kwargs):
        return f"Error: web_tools_part1 import failed: {e}"

try:
    from web_tools_part2 import web_post_x
except ImportError as e:
    def web_post_x(*args, **kwargs):
        return f"Error: web_tools_part2 import failed: {e}"


# ---------------------------------------------------------------------------
# Persistent event loop for async BrowserSession operations
# ---------------------------------------------------------------------------
_loop = asyncio.new_event_loop()
asyncio.set_event_loop(_loop)


def _run_async(coro):
    """Run async coroutine in persistent event loop."""
    return _loop.run_until_complete(coro)


# ---------------------------------------------------------------------------
# Global instances (lazy initialization)
# ---------------------------------------------------------------------------
_browser_session = None
_vision_secretary = None


def _get_browser():
    """Get or create global BrowserSession instance."""
    global _browser_session
    if _browser_session is None:
        if BrowserSession is None:
            raise RuntimeError(f"BrowserSession import failed: {_browser_import_error}")
        _browser_session = BrowserSession()
    return _browser_session


def _get_vision():
    """Get or create global VisionSecretary instance."""
    global _vision_secretary
    if _vision_secretary is None:
        if VisionSecretary is None:
            raise RuntimeError(f"VisionSecretary import failed: {_vision_import_error}")
        _vision_secretary = VisionSecretary()
    return _vision_secretary


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SERVER_INFO = {
    "name": "nyancobot-browser-v2",
    "version": "1.0.0",
}

TOOLS = [
    {
        "name": "browser_navigate",
        "description": "Navigate to URL and return page info (title, AX tree, screenshot)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Target URL to navigate to",
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "browser_act",
        "description": "Perform browser action on element (click, fill, press, select, scroll)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["click", "fill", "press", "select", "scroll"],
                    "description": "Action to perform",
                },
                "target": {
                    "type": "string",
                    "description": "Element selector (CSS, text=, label=, role=, #id, .class)",
                },
                "value": {
                    "type": "string",
                    "description": "Value for fill/press/select/scroll (optional)",
                },
            },
            "required": ["action", "target"],
        },
    },
    {
        "name": "browser_snapshot",
        "description": "Get current page screenshot and accessibility tree",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "browser_state",
        "description": "Get lightweight browser session state (URL, title, action count)",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "browser_vision",
        "description": "Analyze browser screenshot using AI vision (page type, elements, forms, suggested actions)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "screenshot_path": {
                    "type": "string",
                    "description": "Path to screenshot PNG file",
                },
                "question": {
                    "type": "string",
                    "description": "Optional analysis question",
                },
            },
            "required": ["screenshot_path"],
        },
    },
    {
        "name": "browser_close",
        "description": "Close browser session and release resources",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "web_scrape",
        "description": "Fetch HTML from URL and extract text",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Target URL to scrape",
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
                "max_results": {
                    "type": "integer",
                    "description": "Number of results to return (default: 5)",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "web_post_x",
        "description": "Post a tweet to X (Twitter) API v2",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Tweet text content",
                },
            },
            "required": ["content"],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------
def execute_browser_navigate(url):
    """Navigate to URL and return page info."""
    try:
        session = _get_browser()
        result = _run_async(session.navigate(url))
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f"Error: browser_navigate failed: {e}"


def execute_browser_act(action, target, value=None):
    """Perform browser action on element."""
    try:
        session = _get_browser()
        result = _run_async(session.act(action, target, value))
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f"Error: browser_act failed: {e}"


def execute_browser_snapshot():
    """Get current page screenshot and AX tree."""
    try:
        session = _get_browser()
        if session._page is None:
            return "Error: No browser session active. Use browser_navigate first."

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        screenshot_path = f"/tmp/nyancobot-browser/screen_{timestamp}.png"
        Path("/tmp/nyancobot-browser").mkdir(parents=True, exist_ok=True)

        _run_async(session._page.screenshot(path=screenshot_path))
        ax_tree = _run_async(session.get_ax_tree())
        title = _run_async(session._page.title())

        result = {
            "url": session._page.url,
            "title": title,
            "ax_tree": ax_tree,
            "screenshot_path": screenshot_path,
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f"Error: browser_snapshot failed: {e}"


def execute_browser_state():
    """Get lightweight browser session state."""
    try:
        session = _get_browser()
        started = session._page is not None

        if started:
            title = _run_async(session._page.title())
            cookies = _run_async(session._context.cookies())
            result = {
                "started": True,
                "url": session._page.url,
                "title": title,
                "cookie_count": len(cookies),
                "action_count": session._action_count,
            }
        else:
            result = {
                "started": False,
                "url": None,
                "title": None,
                "cookie_count": 0,
                "action_count": session._action_count,
            }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f"Error: browser_state failed: {e}"


def execute_browser_vision(screenshot_path, question=None):
    """Analyze screenshot via VisionSecretary."""
    try:
        vision = _get_vision()
        result = vision.analyze(screenshot_path, question)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f"Error: browser_vision failed: {e}"


def execute_browser_close():
    """Close browser session and release resources."""
    global _browser_session
    try:
        if _browser_session is not None:
            _run_async(_browser_session.close())
            _browser_session = None
        return json.dumps({"closed": True})
    except Exception as e:
        _browser_session = None
        return f"Error: browser_close failed: {e}"


def execute_web_scrape(url):
    """Fetch HTML from URL and extract text."""
    try:
        return web_scrape(url)
    except Exception as e:
        return f"Error: web_scrape failed: {e}"


def execute_web_search(query, max_results=5):
    """Search using DuckDuckGo."""
    try:
        return web_search(query, max_results)
    except Exception as e:
        return f"Error: web_search failed: {e}"


def execute_web_post_x(content):
    """Post tweet to X API."""
    try:
        return web_post_x(content)
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
    pass


def handle_tools_list(id_val, params):
    """Handle tools/list request."""
    send_response(id_val, {"tools": TOOLS})


def handle_tools_call(id_val, params):
    """Handle tools/call request."""
    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})

    if tool_name == "browser_navigate":
        result_text = execute_browser_navigate(
            url=arguments.get("url", ""),
        )
    elif tool_name == "browser_act":
        result_text = execute_browser_act(
            action=arguments.get("action", ""),
            target=arguments.get("target", ""),
            value=arguments.get("value"),
        )
    elif tool_name == "browser_snapshot":
        result_text = execute_browser_snapshot()
    elif tool_name == "browser_state":
        result_text = execute_browser_state()
    elif tool_name == "browser_vision":
        result_text = execute_browser_vision(
            screenshot_path=arguments.get("screenshot_path", ""),
            question=arguments.get("question"),
        )
    elif tool_name == "browser_close":
        result_text = execute_browser_close()
    elif tool_name == "web_scrape":
        result_text = execute_web_scrape(
            url=arguments.get("url", ""),
        )
    elif tool_name == "web_search":
        result_text = execute_web_search(
            query=arguments.get("query", ""),
            max_results=arguments.get("max_results", 5),
        )
    elif tool_name == "web_post_x":
        result_text = execute_web_post_x(
            content=arguments.get("content", ""),
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
    try:
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
    finally:
        # Clean up browser on exit
        global _browser_session
        if _browser_session is not None:
            try:
                _run_async(_browser_session.close())
            except Exception:
                pass
            _browser_session = None


if __name__ == "__main__":
    main()
