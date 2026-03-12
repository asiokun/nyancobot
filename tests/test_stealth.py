"""
test_stealth.py - Integration test for the browser_stealth module.

Tests:
  1. Visit bot detection test site (bot.sannysoft.com)
  2. Capture accessibility snapshot and measure token count
  3. Demonstrate human_click on a page element

Usage:
    cd /Users/ShotaNakahira/multi-agent-shogun-2
    python -m scripts.browser_stealth.test_stealth
"""

import asyncio
import sys
import os
import time

# Ensure parent directory is in path for module imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from playwright.async_api import async_playwright

from scripts.browser_stealth import (
    create_stealth_browser,
    human_click,
    human_scroll,
    get_accessibility_snapshot,
)


def estimate_tokens(text: str) -> int:
    """Rough token count estimate (~4 chars per token for English text)."""
    return max(1, len(text) // 4)


async def test_bot_detection():
    """Test 1: Visit bot detection site and take a screenshot."""
    print("=" * 60)
    print("TEST 1: Bot Detection Evasion")
    print("=" * 60)

    async with async_playwright() as p:
        context = await create_stealth_browser(p, headless=True)
        page = await context.new_page()

        try:
            print("[*] Navigating to bot.sannysoft.com ...")
            await page.goto(
                "https://bot.sannysoft.com/",
                wait_until="networkidle",
                timeout=30000,
            )
            await page.wait_for_timeout(3000)  # Let all JS tests run

            # Screenshot
            os.makedirs("/tmp/screenshots", exist_ok=True)
            screenshot_path = "/tmp/screenshots/bot_detection_test.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"[+] Screenshot saved: {screenshot_path}")

            # Check key stealth indicators via JS evaluation
            checks = await page.evaluate("""
                () => ({
                    webdriver: navigator.webdriver,
                    languages: navigator.languages,
                    platform: navigator.platform,
                    pluginCount: navigator.plugins.length,
                    chromeRuntime: typeof window.chrome?.runtime,
                    hardwareConcurrency: navigator.hardwareConcurrency,
                })
            """)
            print(f"[+] Stealth checks:")
            print(f"    webdriver = {checks['webdriver']} (should be None/undefined)")
            print(f"    languages = {checks['languages']}")
            print(f"    platform  = {checks['platform']}")
            print(f"    plugins   = {checks['pluginCount']} (should be >= 3)")
            print(f"    chrome.runtime = {checks['chromeRuntime']} (should be 'object')")
            print(f"    hardwareConcurrency = {checks['hardwareConcurrency']}")

            passed = (
                checks["webdriver"] is None
                and checks["pluginCount"] >= 3
                and "ja" in checks["languages"]
            )
            status = "PASS" if passed else "PARTIAL"
            print(f"\n[{'+'if passed else '!'}] Bot detection evasion: {status}")

        finally:
            await context.close()


async def test_accessibility_snapshot():
    """Test 2: Get accessibility snapshot and measure token efficiency."""
    print("\n" + "=" * 60)
    print("TEST 2: Accessibility Snapshot Token Efficiency")
    print("=" * 60)

    async with async_playwright() as p:
        context = await create_stealth_browser(p, headless=True)
        page = await context.new_page()

        try:
            print("[*] Navigating to example.com ...")
            await page.goto("https://example.com", wait_until="domcontentloaded")
            await page.wait_for_timeout(1000)

            # Full snapshot (non-interactive)
            t0 = time.time()
            full_snapshot, full_refs = await get_accessibility_snapshot(
                page, interactive_only=False, compact=False,
            )
            full_time = time.time() - t0
            full_tokens = estimate_tokens(full_snapshot)

            # Interactive-only compact snapshot
            t0 = time.time()
            compact_snapshot, compact_refs = await get_accessibility_snapshot(
                page, interactive_only=True, compact=True,
            )
            compact_time = time.time() - t0
            compact_tokens = estimate_tokens(compact_snapshot)

            # Full page HTML for comparison
            html = await page.content()
            html_tokens = estimate_tokens(html)

            print(f"\n[+] Results:")
            print(f"    HTML tokens (full page):     ~{html_tokens:,}")
            print(f"    Full snapshot tokens:         ~{full_tokens:,} ({full_time:.3f}s)")
            print(f"    Compact snapshot tokens:      ~{compact_tokens:,} ({compact_time:.3f}s)")
            print(f"    Token reduction (HTML->compact): {html_tokens / max(compact_tokens, 1):.1f}x")
            print(f"    Ref map entries (full):       {len(full_refs)}")
            print(f"    Ref map entries (compact):    {len(compact_refs)}")
            print(f"\n[+] Full snapshot preview (first 500 chars):")
            print(full_snapshot[:500])
            print(f"\n[+] Compact snapshot:")
            print(compact_snapshot[:500])

        finally:
            await context.close()


async def test_human_actions():
    """Test 3: Human-like click and scroll on a test page."""
    print("\n" + "=" * 60)
    print("TEST 3: Human-like Actions")
    print("=" * 60)

    async with async_playwright() as p:
        context = await create_stealth_browser(p, headless=True)
        page = await context.new_page()

        try:
            print("[*] Navigating to example.com ...")
            await page.goto("https://example.com", wait_until="domcontentloaded")
            await page.wait_for_timeout(1000)

            # Find the "More information..." link
            link = page.get_by_role("link", name="More information...")
            count = await link.count()
            print(f"[+] Found 'More information...' link: {count > 0}")

            if count > 0:
                # Human-like click
                print("[*] Performing human_click ...")
                t0 = time.time()
                await human_click(page, link)
                click_time = time.time() - t0
                print(f"[+] human_click completed in {click_time:.3f}s")
                await page.wait_for_timeout(2000)

                # Take screenshot after click
                os.makedirs("/tmp/screenshots", exist_ok=True)
                await page.screenshot(path="/tmp/screenshots/after_human_click.png")
                print("[+] Screenshot saved: /tmp/screenshots/after_human_click.png")

            # Navigate back and test scrolling
            await page.goto("https://example.com", wait_until="domcontentloaded")
            print("[*] Performing human_scroll ...")
            t0 = time.time()
            await human_scroll(page, direction="down", amount=300)
            scroll_time = time.time() - t0
            print(f"[+] human_scroll completed in {scroll_time:.3f}s")

        finally:
            await context.close()


async def main():
    """Run all tests."""
    print("Browser Stealth Module - Integration Tests")
    print("=" * 60)

    try:
        await test_bot_detection()
    except Exception as e:
        print(f"[!] Test 1 failed: {e}")

    try:
        await test_accessibility_snapshot()
    except Exception as e:
        print(f"[!] Test 2 failed: {e}")

    try:
        await test_human_actions()
    except Exception as e:
        print(f"[!] Test 3 failed: {e}")

    print("\n" + "=" * 60)
    print("All tests completed.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
