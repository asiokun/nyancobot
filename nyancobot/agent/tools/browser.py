"""Browser tool: Playwright-based web browsing for nyancobot.

Enhanced with AX tree, cookie persistence, vision integration,
and security hardening (security-hardening).
"""

import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Security: Import _validate_url for SSRF prevention
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "scripts"))
from web_tools_part1 import _validate_url

from nyancobot.agent.tools.base import Tool

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCREENSHOT_DIR = Path("/tmp/nyancobot-browser")
COOKIE_DIR = Path.home() / ".nyancobot" / "browser-cookies"

ACTION_LIMIT = 50
MAX_SCREENSHOTS = 50

_SENSITIVE_FIELDS = {
    "password", "passwd", "token", "secret", "apikey", "api_key",
    "credit", "cvv", "ssn", "auth", "key",
}

# ---------------------------------------------------------------------------
# Domain whitelist — only these domains can be opened
# ---------------------------------------------------------------------------
_ALLOWED_DOMAINS_FILE = Path.home() / ".nyancobot" / "config" / "allowed_domains.txt"


def _load_allowed_domains() -> set[str]:
    """Load allowed domains from config file (cached per process)."""
    if _ALLOWED_DOMAINS_FILE.exists():
        domains = set()
        for line in _ALLOWED_DOMAINS_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                domains.add(line.lower())
        if domains:
            return domains
    # Fallback if file missing or empty
    return {"example.com"}


ALLOWED_DOMAINS = _load_allowed_domains()

# ---------------------------------------------------------------------------
# Dangerous click patterns — refuse to click these
# ---------------------------------------------------------------------------
_DANGEROUS_CLICK_PATTERNS = re.compile(
    r'(?:削除|delete|remove|退会|解約|unsubscribe|cancel\s*(?:account|subscription)'
    r'|deactivate|購入|purchase|buy\s*now|支払|pay(?:ment)?|checkout'
    r'|送金|transfer|withdraw|権限.*(?:変更|付与)|grant.*(?:access|permission)'
    r'|全て.*(?:削除|消去)|clear\s*all|reset\s*all|format'
    r'|admin|sudo|root|install|download\s*\.exe)',
    re.IGNORECASE,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Permission level system
# ---------------------------------------------------------------------------
PERMISSION_LEVEL_FILE = Path.home() / ".nyancobot" / "config" / "permission_level.txt"
LEVEL_NAMES = {0: "READ_ONLY", 1: "TEST_WRITE", 2: "BROWSER_AUTO", 3: "FULL"}
TEST_DOMAINS = {"example.com", "httpbin.org"}
LEVEL_ACTIONS = {
    0: {"open", "read", "ax_tree", "screenshot", "close"},
    1: {"open", "read", "ax_tree", "screenshot", "close", "click", "type", "scroll"},
    2: {"open", "read", "ax_tree", "screenshot", "close", "click", "type", "scroll",
        "save_cookies", "load_cookies", "vision", "extract_jobs", "upload"},
    3: {"open", "read", "ax_tree", "screenshot", "close", "click", "type", "scroll",
        "save_cookies", "load_cookies", "vision", "extract_jobs", "upload"},
}


def _get_permission_level() -> int:
    """Read current permission level from config file (0-3). Defaults to 0 (safe)."""
    try:
        if PERMISSION_LEVEL_FILE.exists():
            for line in PERMISSION_LEVEL_FILE.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    return max(0, min(3, int(line)))
    except Exception:
        pass
    return 0  # デフォルトは安全側（Level 0）


class BrowserTool(Tool):
    """Browse web pages using Playwright (headless Chromium).

    Actions:
      open         - Navigate to URL, return AX tree + page text
      click        - Click element by text or selector
      type         - Type text into an input field
      scroll       - Scroll page (up/down)
      screenshot   - Take screenshot and save to file
      read         - Read current page content (no navigation)
      ax_tree      - Get accessibility tree only
      vision       - Screenshot + vision secretary analysis
      save_cookies - Save cookies to file
      load_cookies - Load cookies from file
      close        - Close browser and reset action count
    """

    name = "browser"
    description = (
        "Control a headless browser. Actions: "
        "open(url), click(selector), type(selector,text), "
        "scroll(direction), screenshot(path), read(), "
        "ax_tree(), vision(), save_cookies(name), load_cookies(name), close(), "
        "extract_jobs(url,path) - CrowdWorks案件一覧をMarkdownで抽出・保存."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "open", "click", "type", "scroll", "screenshot", "read",
                    "ax_tree", "vision", "save_cookies", "load_cookies", "close",
                    "extract_jobs",
                ],
                "description": "Browser action to perform",
            },
            "url": {"type": "string", "description": "URL to open (for 'open' action)"},
            "selector": {
                "type": "string",
                "description": "CSS selector or text content to target",
            },
            "text": {"type": "string", "description": "Text to type (for 'type' action)"},
            "direction": {
                "type": "string",
                "enum": ["up", "down"],
                "description": "Scroll direction",
            },
            "path": {"type": "string", "description": "File path to save screenshot"},
            "name": {
                "type": "string",
                "description": "Cookie store name (for save_cookies/load_cookies)",
            },
        },
        "required": ["action"],
    }

    _MAX_TEXT_LEN = 30000  # Truncate page text to avoid token explosion

    def __init__(self):
        self._browser = None
        self._context = None
        self._page = None
        self._pw = None
        self._action_count = 0
        self._vision_secretary = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_sensitive(target: str) -> bool:
        """Return True if target name matches a sensitive field."""
        t = target.lower()
        return any(s in t for s in _SENSITIVE_FIELDS)

    @staticmethod
    def _cleanup_old_screenshots():
        """Remove old screenshots, keeping only the most recent MAX_SCREENSHOTS."""
        try:
            files = sorted(
                SCREENSHOT_DIR.glob("screen_*.png"),
                key=lambda f: f.stat().st_mtime,
            )
            if len(files) > MAX_SCREENSHOTS:
                for f in files[:-MAX_SCREENSHOTS]:
                    f.unlink(missing_ok=True)
        except Exception:
            pass

    async def _ensure_browser(self):
        """Lazy-init: start browser on first use."""
        if self._page is not None:
            return
        from playwright.async_api import async_playwright

        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=True)
        self._context = await self._browser.new_context(
            accept_downloads=False,
            viewport={"width": 1280, "height": 720},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        self._page = await self._context.new_page()

        # Auto-dismiss all dialogs for safety
        self._page.on("dialog", lambda d: asyncio.ensure_future(d.dismiss()))

    def _truncate(self, text: str) -> str:
        if len(text) > self._MAX_TEXT_LEN:
            return text[: self._MAX_TEXT_LEN] + f"\n...(truncated, total {len(text)} chars)"
        return text

    @staticmethod
    def _clean_text(raw: str) -> str:
        """Collapse whitespace for readable output."""
        text = re.sub(r"[ \t]+", " ", raw)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _get_cdp_value(self, prop) -> str:
        """Extract string value from a CDP AXValue dict."""
        if not prop:
            return ""
        if isinstance(prop, dict):
            return str(prop.get("value", ""))
        return str(prop)

    # ------------------------------------------------------------------
    # AX Tree (ported from browser_session.py)
    # ------------------------------------------------------------------

    async def _get_ax_tree(self, max_depth: int = 5) -> str:
        """Get accessibility tree in compact format via CDP."""
        page_title = await self._page.title()
        page_url = self._page.url
        lines = [f"[PAGE] {page_title} | {page_url}"]

        try:
            cdp = await self._context.new_cdp_session(self._page)
            try:
                ax_result = await cdp.send("Accessibility.getFullAXTree")
                nodes = ax_result.get("nodes", [])
                self._format_ax_nodes_cdp(nodes, lines, max_depth=max_depth)
            finally:
                await cdp.detach()
        except Exception as e:
            lines.append(f"[ERROR] AX tree unavailable: {e}")

        return "\n".join(lines)

    def _format_ax_nodes_cdp(self, nodes: list, lines: list, max_depth: int) -> None:
        """Format CDP Accessibility.getFullAXTree nodes into compact lines."""
        node_map = {}
        children_map: dict[str, list] = {}
        root_ids = []

        for node in nodes:
            nid = node.get("nodeId", "")
            node_map[nid] = node
            children_map[nid] = []

        for node in nodes:
            nid = node.get("nodeId", "")
            parent_id = node.get("parentId")
            if parent_id and parent_id in children_map:
                children_map[parent_id].append(nid)
            elif not parent_id:
                root_ids.append(nid)

        def recurse(nid: str, depth: int):
            if depth > max_depth:
                return
            n = node_map.get(nid)
            if not n:
                return

            role = self._get_cdp_value(n.get("role")).upper()

            name_prop = n.get("name")
            name = self._get_cdp_value(name_prop).strip() if name_prop else ""

            desc_prop = n.get("description")
            desc = self._get_cdp_value(desc_prop) if desc_prop else ""

            val_prop = n.get("value")
            val = self._get_cdp_value(val_prop) if val_prop else ""

            # Skip ignored nodes
            if n.get("ignored", False):
                for cid in children_map.get(nid, []):
                    recurse(cid, depth)
                return

            # Skip structural nodes with no name
            skip_roles = {"GENERIC", "NONE", "PRESENTATION", "INLINETEXT", "STATICTEXT", ""}
            if role in skip_roles and not name:
                for cid in children_map.get(nid, []):
                    recurse(cid, depth)
                return

            # Format line by role
            if role in {"TEXTBOX", "SEARCHBOX", "SPINBUTTON", "COMBOBOX"}:
                combined = (name + desc).lower()
                if "email" in combined:
                    input_type = "email"
                elif "password" in combined or "passwd" in combined:
                    input_type = "password"
                elif "search" in combined:
                    input_type = "search"
                else:
                    input_type = "text"
                parts = [f"[INPUT:{input_type}]"]
                if desc:
                    parts.append(f'placeholder="{desc}"')
                if val:
                    safe_val = "***" if self._is_sensitive(name + desc) else val
                    parts.append(f'value="{safe_val}"')
                else:
                    parts.append('value=""')
                if nid:
                    parts.append(f"| id={nid}")
                lines.append(" ".join(parts))

            elif role == "HEADING":
                level = ""
                for prop in n.get("properties", []):
                    if prop.get("name") == "level":
                        level = self._get_cdp_value(prop.get("value"))
                tag = f"[H{level}]" if level else "[HEADING]"
                lines.append(f"{tag} {name}")

            elif role == "LINK":
                url_val = ""
                for prop in n.get("properties", []):
                    if prop.get("name") == "url":
                        url_val = self._get_cdp_value(prop.get("value"))
                if url_val:
                    lines.append(f"[LINK] {name} | href={url_val}")
                else:
                    lines.append(f"[LINK] {name}")

            elif role == "BUTTON":
                suffix = f" | id={nid}" if nid else ""
                lines.append(f"[BUTTON] {name}{suffix}")

            elif role in {"CHECKBOX", "RADIO"}:
                checked = False
                for prop in n.get("properties", []):
                    if prop.get("name") == "checked":
                        checked = self._get_cdp_value(prop.get("value")) == "true"
                state = "checked" if checked else "unchecked"
                lines.append(f"[{role}] {name} | {state}")

            elif role == "IMAGE":
                if name:
                    lines.append(f"[IMG] {name}")

            elif name:
                lines.append(f"[{role}] {name}")

            for cid in children_map.get(nid, []):
                recurse(cid, depth + 1)

        for root_id in root_ids:
            recurse(root_id, 0)

    # ------------------------------------------------------------------
    # Execute dispatcher
    # ------------------------------------------------------------------

    async def execute(self, action: str, **kwargs: Any) -> str:
        # close doesn't need browser and doesn't count toward limit
        if action == "close":
            return await self._action_close()

        try:
            await self._ensure_browser()
        except Exception as e:
            return f"Error: Failed to start browser: {e}"

        # V-D01: Action limit enforcement
        self._action_count += 1
        if self._action_count > ACTION_LIMIT:
            return (
                f"Error: Action limit exceeded ({self._action_count} > {ACTION_LIMIT}). "
                "Use 'close' action to reset."
            )

        # Permission level check
        current_level = _get_permission_level()
        allowed = LEVEL_ACTIONS.get(current_level, LEVEL_ACTIONS[0])
        if action not in allowed:
            required = next(
                (lvl for lvl in sorted(LEVEL_ACTIONS) if action in LEVEL_ACTIONS[lvl]), 3
            )
            return (f"Error: Action '{action}' requires permission level {required} "
                    f"({LEVEL_NAMES[required]}), current level is {current_level} "
                    f"({LEVEL_NAMES[current_level]}). Ask admin to upgrade.")

        # Level 1: write actions only on test domains
        if current_level == 1 and action in {"click", "type", "scroll"}:
            if self._page and self._page.url and self._page.url != "about:blank":
                from urllib.parse import urlparse
                host = urlparse(self._page.url).hostname or ""
                if host not in TEST_DOMAINS:
                    return (f"Error: Action '{action}' at Level 1 (TEST_WRITE) only allowed "
                            f"on test domains {TEST_DOMAINS}. Current: {host}. "
                            f"Ask admin to upgrade to Level 2.")

        try:
            if action == "open":
                return await self._action_open(kwargs.get("url", ""))
            elif action == "click":
                return await self._action_click(kwargs.get("selector", ""))
            elif action == "type":
                return await self._action_type(
                    kwargs.get("selector", ""), kwargs.get("text", "")
                )
            elif action == "scroll":
                return await self._action_scroll(kwargs.get("direction", "down"))
            elif action == "screenshot":
                return await self._action_screenshot(kwargs.get("path", ""))
            elif action == "read":
                return await self._action_read()
            elif action == "ax_tree":
                return await self._action_ax_tree()
            elif action == "vision":
                return await self._action_vision()
            elif action == "save_cookies":
                return await self._action_save_cookies(kwargs.get("name", "default"))
            elif action == "load_cookies":
                return await self._action_load_cookies(kwargs.get("name", "default"))
            elif action == "extract_jobs":
                return await self._action_extract_jobs(
                    kwargs.get("url", ""), kwargs.get("path", "")
                )
            elif action == "upload":
                return await self._action_upload(
                    kwargs.get("selector", ""), kwargs.get("path", "")
                )
            else:
                return f"Error: Unknown action '{action}'"
        except Exception as e:
            return f"Error: {e}"

    # ------------------------------------------------------------------
    # Action implementations
    # ------------------------------------------------------------------

    async def _action_open(self, url: str) -> str:
        if not url:
            return "Error: url is required for 'open' action"

        # Domain whitelist check
        from urllib.parse import urlparse
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        # Check domain and parent domains (e.g. "news.yahoo.co.jp" matches "yahoo.co.jp")
        domain_ok = any(
            hostname == d or hostname.endswith("." + d)
            for d in ALLOWED_DOMAINS
        )
        if not domain_ok:
            return (
                f"Error: Domain '{hostname}' is not in the allowed list. "
                f"Allowed: {', '.join(sorted(ALLOWED_DOMAINS))}"
            )

        # SSRF prevention
        is_safe, err = _validate_url(url)
        if not is_safe:
            return f"Error: URL blocked - {err}"

        await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # V-A01: Validate final URL after redirects
        final_url = self._page.url
        is_safe_final, err_final = _validate_url(final_url)
        if not is_safe_final:
            await self._page.goto("about:blank")
            return f"Error: Redirect to unsafe URL blocked - {err_final}"

        await self._page.wait_for_timeout(1000)  # Let JS render

        # AX tree + page text
        ax_tree = await self._get_ax_tree()
        text = await self._page.inner_text("body")
        text = self._clean_text(text)

        # V-D02: Cleanup old screenshots
        self._cleanup_old_screenshots()

        return self._truncate(f"{ax_tree}\n\n{text}")

    async def _action_click(self, selector: str) -> str:
        if not selector:
            return "Error: selector is required for 'click' action"

        # Dangerous click guard
        if _DANGEROUS_CLICK_PATTERNS.search(selector):
            return (
                f"Error: Refused to click '{selector}' — "
                f"matches a dangerous pattern (delete/purchase/payment/admin). "
                f"If this is intentional, ask the operator to execute manually."
            )

        try:
            await self._page.click(selector, timeout=5000)
        except Exception:
            await self._page.get_by_text(selector, exact=False).first.click(timeout=5000)

        # Post-click: check if navigation happened to disallowed domain
        await self._page.wait_for_timeout(1000)
        from urllib.parse import urlparse
        post_url = self._page.url
        post_host = urlparse(post_url).hostname or ""
        if post_host and not any(
            post_host == d or post_host.endswith("." + d)
            for d in ALLOWED_DOMAINS
        ):
            await self._page.go_back(timeout=5000)
            return (
                f"Error: Click navigated to disallowed domain '{post_host}'. "
                f"Navigated back. Allowed: {', '.join(sorted(ALLOWED_DOMAINS))}"
            )

        title = await self._page.title()
        return f"Clicked '{selector}'. Page: {title} | URL: {self._page.url}"

    async def _action_type(self, selector: str, text: str) -> str:
        if not selector or not text:
            return "Error: selector and text are required for 'type' action"
        try:
            await self._page.fill(selector, text, timeout=5000)
        except Exception:
            locator = self._page.get_by_placeholder(selector).or_(
                self._page.get_by_label(selector)
            ).first
            await locator.fill(text, timeout=5000)
        # Do not echo typed text for security
        return f"Typed into '{selector}'"

    async def _action_scroll(self, direction: str) -> str:
        delta = -500 if direction == "up" else 500
        await self._page.mouse.wheel(0, delta)
        await self._page.wait_for_timeout(500)
        return f"Scrolled {direction}"

    async def _action_screenshot(self, path: str) -> str:
        if not path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            path = str(SCREENSHOT_DIR / f"screen_{timestamp}.png")
        else:
            # V-E02: Validate path is under SCREENSHOT_DIR
            resolved = str(Path(path).resolve())
            if not resolved.startswith(str(SCREENSHOT_DIR)):
                return f"Error: Screenshot path must be under {SCREENSHOT_DIR}"
        await self._page.screenshot(path=path, full_page=False)
        self._cleanup_old_screenshots()
        return f"Screenshot saved to {path}"

    async def _action_read(self) -> str:
        title = await self._page.title()
        url = self._page.url
        ax_tree = await self._get_ax_tree()
        text = await self._page.inner_text("body")
        text = self._clean_text(text)
        return self._truncate(f"{ax_tree}\n\n{text}")

    async def _action_ax_tree(self) -> str:
        return await self._get_ax_tree()

    async def _action_vision(self) -> str:
        # Take screenshot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        screenshot_path = str(SCREENSHOT_DIR / f"screen_{timestamp}.png")
        await self._page.screenshot(path=screenshot_path, full_page=False)
        self._cleanup_old_screenshots()

        # Lazy-init vision secretary
        if self._vision_secretary is None:
            try:
                from vision_secretary import VisionSecretary

                self._vision_secretary = VisionSecretary()
            except ImportError:
                return "Error: vision_secretary.py not found in scripts path"

        result = self._vision_secretary.analyze(screenshot_path)
        return json.dumps(result, ensure_ascii=False, indent=2)

    async def _action_save_cookies(self, name: str) -> str:
        # V-C02: Sanitize name to prevent path traversal
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "", name)
        if not safe_name:
            return "Error: Invalid cookie name (use alphanumeric, dash, underscore only)"
        os.makedirs(str(COOKIE_DIR), mode=0o700, exist_ok=True)
        cookie_path = COOKIE_DIR / f"{safe_name}.json"
        cookies = await self._context.cookies()
        with open(cookie_path, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        os.chmod(str(cookie_path), 0o600)
        return f"Saved {len(cookies)} cookies to {cookie_path}"

    async def _action_load_cookies(self, name: str) -> str:
        # V-C02: Sanitize name to prevent path traversal
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "", name)
        if not safe_name:
            return "Error: Invalid cookie name (use alphanumeric, dash, underscore only)"
        cookie_path = COOKIE_DIR / f"{safe_name}.json"
        if not cookie_path.exists():
            return f"Error: Cookie file not found: {cookie_path}"
        with open(cookie_path, "r", encoding="utf-8") as f:
            cookies = json.load(f)
        await self._context.add_cookies(cookies)
        return f"Loaded {len(cookies)} cookies from {cookie_path}"

    async def _action_close(self) -> str:
        """Close browser resources and reset action count."""
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._context = None
            self._page = None
        if self._pw:
            await self._pw.stop()
            self._pw = None
        self._action_count = 0
        return "Browser closed"

    # ------------------------------------------------------------------
    # upload: Upload a file to an input[type=file] element
    # ------------------------------------------------------------------

    async def _action_upload(self, selector: str, path: str) -> str:
        """Upload a file to an input[type=file] element."""
        if not selector or not path:
            return "Error: Both 'selector' and 'path' are required."
        # セキュリティ: パス検証
        resolved = Path(path).resolve()
        # ホームディレクトリ外・システムファイルへのアクセス禁止
        home = Path.home()
        allowed_dirs = [home, Path("/tmp")]
        if not any(str(resolved).startswith(str(d)) for d in allowed_dirs):
            return f"Error: Upload path must be under {home} or /tmp. Got: {resolved}"
        if not resolved.exists():
            return f"Error: File not found: {resolved}"
        if not resolved.is_file():
            return f"Error: Not a file: {resolved}"
        # ファイルサイズ制限（20MB）
        max_size = 20 * 1024 * 1024
        if resolved.stat().st_size > max_size:
            return f"Error: File too large ({resolved.stat().st_size} bytes, max {max_size})"
        # アップロード実行
        locator = self._page.locator(selector)
        await locator.set_input_files(str(resolved))
        return f"Uploaded {resolved.name} ({resolved.stat().st_size} bytes) to {selector}"

    # ------------------------------------------------------------------
    # extract_jobs: Structured job extraction from crowdsourcing sites
    # ------------------------------------------------------------------

    async def _action_extract_jobs(self, url: str, path: str) -> str:
        """Extract job listings from crowdworks/lancers and save as Markdown.

        Works by fetching HTML directly (no browser needed) and parsing
        the embedded JSON data that these sites include in their pages.

        Filters:
        - Includes jobs with keywords: AI, automation, scraping, LLM, ChatGPT, etc.
        - Excludes jobs requiring on-site/in-office work
        - Skips previously applied jobs (tracked in ~/.nyancobot/data/applied_jobs.json)
        """
        import html as html_mod
        from urllib.parse import urlparse
        import urllib.request

        if not url:
            return "Error: url is required for 'extract_jobs' action"

        # Domain whitelist check
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        domain_ok = any(
            hostname == d or hostname.endswith("." + d)
            for d in ALLOWED_DOMAINS
        )
        if not domain_ok:
            return f"Error: Domain '{hostname}' is not in the allowed list."

        # Load applied jobs history
        applied_jobs_file = Path.home() / ".nyancobot" / "data" / "applied_jobs.json"
        applied_jobs_file.parent.mkdir(parents=True, exist_ok=True)
        applied_job_ids = set()
        if applied_jobs_file.exists():
            try:
                with open(applied_jobs_file, "r", encoding="utf-8") as f:
                    applied_data = json.load(f)
                    applied_job_ids = set(applied_data.get("job_ids", []))
            except (json.JSONDecodeError, KeyError):
                pass

        # Keyword filters
        include_keywords = {
            "スクレイピング", "scraping", "ai", "人工知能", "機械学習",
            "自動化", "automation", "llm", "chatgpt", "gpt", "claude",
            "python", "api", "データ分析", "data", "ウェブスクレイピング",
            "rpa", "ボット", "bot", "クローリング", "crawling"
        }
        exclude_keywords = {
            "出社", "常駐", "対面", "オフィス", "office", "出勤",
            "通勤", "駐在", "現地", "訪問", "来社", "面談", "in-person",
            "on-site", "onsite"
        }

        # Fetch HTML via urllib (no browser overhead)
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0.0.0 Safari/537.36"
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw_html = resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            return f"Error: Failed to fetch {url}: {e}"

        jobs = []

        # --- CrowdWorks: JSON embedded in data attribute ---
        if "crowdworks.jp" in hostname:
            match = re.search(r'data="(\{.+?\})"', raw_html)
            if match:
                try:
                    decoded = html_mod.unescape(match.group(1))
                    data = json.loads(decoded)
                    offers = data.get("searchResult", {}).get("job_offers", [])
                    for item in offers:
                        jo = item.get("job_offer", {})
                        pay = item.get("payment", {})
                        entry = item.get("entry", {})

                        # Payment extraction
                        fp = pay.get("fixed_price_payment", {})
                        hp = pay.get("hourly_payment", {})
                        tp = pay.get("task_payment", {})
                        if fp:
                            min_b = fp.get("min_budget")
                            max_b = fp.get("max_budget")
                            if min_b and max_b:
                                price = f"¥{int(min_b):,}〜¥{int(max_b):,}"
                            elif max_b:
                                price = f"〜¥{int(max_b):,}"
                            elif min_b:
                                price = f"¥{int(min_b):,}〜"
                            else:
                                price = "応相談"
                        elif hp:
                            price = f"¥{int(hp.get('min_hourly_wage',0)):,}〜/時"
                        elif tp:
                            price = f"¥{int(tp.get('task_price',0)):,}/件"
                        else:
                            price = "不明"

                        # Entry count
                        pe = entry.get("project_entry", {})
                        te = entry.get("task_entry", {})
                        apps = pe.get("num_application_conditions", 0) or te.get("num_done_tasks", 0)

                        job_id = str(jo.get("id", ""))
                        title = jo.get("title", "")
                        description = jo.get("description", "")
                        category = jo.get("body_category", {}).get("name", "")

                        # Filter: Skip already applied jobs
                        if job_id in applied_job_ids:
                            continue

                        # Filter: Check exclude keywords (on-site/in-office)
                        text_to_check = f"{title} {description} {category}".lower()
                        if any(kw in text_to_check for kw in exclude_keywords):
                            continue

                        # Filter: Check include keywords (AI, automation, etc.)
                        if not any(kw.lower() in text_to_check for kw in include_keywords):
                            continue

                        jobs.append({
                            "id": job_id,
                            "title": title,
                            "price": price,
                            "deadline": jo.get("expired_on", ""),
                            "applicants": apps,
                            "category": category,
                            "url": f"https://crowdworks.jp/public/jobs/{job_id}",
                        })
                except (json.JSONDecodeError, KeyError) as e:
                    return f"Error: Failed to parse CrowdWorks data: {e}"
            else:
                return "Error: Could not find job data in CrowdWorks page HTML"

        # --- Lancers: TODO when needed ---
        elif "lancers.jp" in hostname:
            return "Error: Lancers extraction not yet implemented"

        else:
            return f"Error: No extraction logic for '{hostname}'"

        if not jobs:
            return "No jobs found on the page (after filtering)."

        # Build Markdown
        lines = [
            f"# CrowdWorks 案件一覧（フィルタ済み）",
            f"",
            f"取得日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"URL: {url}",
            f"抽出件数: {len(jobs)}件",
            f"",
            f"**フィルタ条件:**",
            f"- 含有キーワード: AI, 自動化, スクレイピング, LLM, ChatGPT, Python, API等",
            f"- 除外キーワード: 出社, 常駐, 対面, オフィス等",
            f"- 重複案件: 応募済み案件を除外",
            f"",
            f"| No | 案件名 | カテゴリ | 報酬 | 締切 | 応募数 | リンク |",
            f"|----|--------|----------|------|------|--------|--------|",
        ]
        for i, j in enumerate(jobs, 1):
            title = j["title"][:40] + ("…" if len(j["title"]) > 40 else "")
            category = j.get("category", "")[:15]
            lines.append(
                f"| {i} | {title} | {category} | {j['price']} | {j['deadline']} | {j['applicants']} | [詳細]({j['url']}) |"
            )

        md_content = "\n".join(lines) + "\n"

        # Save to file if path specified
        if path:
            # Security: validate path
            save_path = Path(path).resolve()
            allowed_base = Path.home()
            if not str(save_path).startswith(str(allowed_base)):
                return f"Error: Path must be under {allowed_base}"
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_text(md_content, encoding="utf-8")
            return f"Saved {len(jobs)} jobs to {save_path}\n\n{md_content}"

        return md_content

    async def close(self):
        """Clean up browser resources (compatibility method)."""
        await self._action_close()
