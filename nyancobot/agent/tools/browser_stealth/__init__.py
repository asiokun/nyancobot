"""
browser_stealth - Stealth Browser Automation Module

Combines PinchTab-inspired techniques with Playwright:
  - stealth.js injection for bot detection evasion
  - Human-like mouse/keyboard simulation
  - Accessibility tree snapshots for token-efficient page representation

Usage:
    from nyancobot.agent.tools.browser_stealth import (
        create_stealth_browser,
        create_stealth_context,
        human_click,
        human_type,
        human_scroll,
        human_hover,
        get_accessibility_snapshot,
        click_by_ref,
        focus_by_ref,
        fill_by_ref,
    )

    async with async_playwright() as p:
        context = await create_stealth_browser(p, headless=False)
        page = await context.new_page()
        await page.goto("https://example.com")

        # Human-like interactions
        await human_click(page, 'button#submit')
        await human_type(page, 'input[name="email"]', 'user@example.com')

        # Token-efficient page representation
        snapshot, ref_map = await get_accessibility_snapshot(page)
        print(snapshot)
        await click_by_ref(page, "e0", ref_map)
"""

import os
from pathlib import Path
from typing import Optional

from playwright.async_api import (
    Playwright,
    BrowserContext,
    Browser,
)

# Re-export public API from submodules
from .human_actions import human_click, human_type, human_scroll, human_hover
from .a11y_snapshot import (
    get_accessibility_snapshot,
    click_by_ref,
    focus_by_ref,
    fill_by_ref,
    INTERACTIVE_ROLES,
)

__all__ = [
    "create_stealth_browser",
    "create_stealth_context",
    "human_click",
    "human_type",
    "human_scroll",
    "human_hover",
    "get_accessibility_snapshot",
    "click_by_ref",
    "focus_by_ref",
    "fill_by_ref",
    "INTERACTIVE_ROLES",
]

# Path to the stealth injection script
_STEALTH_JS_PATH = Path(__file__).parent / "stealth.js"


def _get_stealth_js() -> str:
    """Read the stealth.js injection script."""
    return _STEALTH_JS_PATH.read_text(encoding="utf-8")


# Default browser launch arguments for stealth
_STEALTH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-infobars",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-background-networking",
    "--disable-component-update",
    "--disable-domain-reliability",
    "--disable-sync",
]

# Default context options
_DEFAULT_CONTEXT_OPTIONS = {
    "viewport": {"width": 1280, "height": 800},
    "user_agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "locale": "ja-JP",
    "timezone_id": "Asia/Tokyo",
    "color_scheme": "light",
    "has_touch": False,
    "is_mobile": False,
    "java_script_enabled": True,
    "bypass_csp": False,
    "ignore_https_errors": False,
}


async def create_stealth_browser(
    playwright: Playwright,
    headless: bool = True,
    user_data_dir: Optional[str] = None,
    extra_args: Optional[list[str]] = None,
    context_options: Optional[dict] = None,
) -> BrowserContext:
    """
    Launch a Chromium browser with stealth settings and return a BrowserContext.

    If user_data_dir is provided, uses launch_persistent_context (session persistence).
    Otherwise, launches a regular browser and creates a new context.
    """
    args = list(_STEALTH_ARGS)
    if extra_args:
        args.extend(extra_args)

    ctx_opts = dict(_DEFAULT_CONTEXT_OPTIONS)
    if context_options:
        ctx_opts.update(context_options)

    stealth_js = _get_stealth_js()

    if user_data_dir:
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir,
            headless=headless,
            args=args,
            **ctx_opts,
        )
    else:
        browser = await playwright.chromium.launch(
            headless=headless,
            args=args,
        )
        context = await browser.new_context(**ctx_opts)

    # Inject stealth.js into every page (current and future)
    await context.add_init_script(stealth_js)

    return context


async def create_stealth_context(
    browser: Browser,
    context_options: Optional[dict] = None,
    storage_state: Optional[str] = None,
) -> BrowserContext:
    """
    Create a new stealth-configured BrowserContext on an existing browser.
    """
    ctx_opts = dict(_DEFAULT_CONTEXT_OPTIONS)
    if context_options:
        ctx_opts.update(context_options)

    if storage_state:
        ctx_opts["storage_state"] = storage_state

    context = await browser.new_context(**ctx_opts)

    stealth_js = _get_stealth_js()
    await context.add_init_script(stealth_js)

    return context
