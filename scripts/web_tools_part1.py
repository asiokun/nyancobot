#!/usr/bin/env python3
"""web_tools_part1.py - Web operation tools (scraping, search, screenshot).

Provides three standalone functions:
  - web_scrape(url, selector): Fetch HTML and extract text
  - web_search(query, num_results): DuckDuckGo search
  - web_screenshot(url, output_path): Playwright screenshot

This is a standalone module (not MCP). Later to be integrated with web_tools_part2.
"""

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from pathlib import Path
from urllib.parse import quote_plus
import ipaddress
import socket
from urllib.parse import urlparse

_BLOCKED_SCHEMES = {"file", "ftp", "gopher", "data", "javascript"}
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
]
_ALLOWED_SCREENSHOT_DIRS = [
    str(Path.home() / ".nyancobot" / "workspace"),
    str(Path.home() / "Desktop"),
    "/tmp",
]

def _validate_url(url: str) -> tuple:
    """URLを検証。(is_safe: bool, error: str) を返す。"""
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL format"
    if parsed.scheme in _BLOCKED_SCHEMES:
        return False, f"Blocked scheme: {parsed.scheme}"
    if not parsed.hostname:
        return False, "No hostname"
    try:
        ip = ipaddress.ip_address(socket.gethostbyname(parsed.hostname))
        for net in _BLOCKED_NETWORKS:
            if ip in net:
                return False, f"Blocked IP range: {net}"
    except (socket.gaierror, ValueError):
        pass
    return True, ""

def _validate_output_path(path: str) -> tuple:
    """出力パスが許可ディレクトリ内か検証。(is_safe: bool, error: str) を返す。"""
    try:
        resolved = str(Path(path).resolve())
    except Exception:
        return False, "Invalid path"
    for allowed in _ALLOWED_SCREENSHOT_DIRS:
        if resolved.startswith(str(Path(allowed).expanduser().resolve())):
            return True, ""
    return False, f"Path outside allowed directories: {resolved}"


# User-Agent to avoid blocking
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/119.0.0.0 Safari/537.36"
)

MAX_SCRAPE_LENGTH = 5000


def web_scrape(url: str, selector: str = None) -> str:
    """Fetch HTML from URL and extract text.

    Args:
        url: Target URL to scrape
        selector: CSS selector to extract specific element (None = body text)

    Returns:
        Extracted text (max 5000 chars), or error message
    """
    try:
        safe, err = _validate_url(url)
        if not safe:
            return f"Error: URL validation failed: {err}"
        headers = {"User-Agent": DEFAULT_USER_AGENT}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        if selector:
            # Extract text from selected element
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
            else:
                return f"Error: Selector '{selector}' not found"
        else:
            # Extract body text
            body = soup.find("body")
            text = body.get_text(strip=True) if body else soup.get_text(strip=True)

        # Limit output
        if len(text) > MAX_SCRAPE_LENGTH:
            text = text[:MAX_SCRAPE_LENGTH] + f"\n... (truncated, original length: {len(text)})"

        return text

    except requests.RequestException as e:
        return f"Error: Failed to fetch {url}: {e}"
    except Exception as e:
        return f"Error: Scraping failed: {e}"


def web_search(query: str, num_results: int = 5) -> str:
    """Search using DuckDuckGo and return results.

    Args:
        query: Search query string
        num_results: Number of results to return (default 5)

    Returns:
        Formatted search results (title + URL per line)
    """
    try:
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        headers = {"User-Agent": DEFAULT_USER_AGENT}

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Extract results
        results = []
        for result in soup.find_all("div", class_="result", limit=num_results * 2):
            # Title and URL
            link = result.find("a", class_="result__url")
            title = result.find("a", class_="result__title")

            if link and title:
                result_url = link.get("href")
                result_title = title.get_text(strip=True)

                if result_url and result_title:
                    results.append(f"- {result_title}\n  {result_url}")

                    if len(results) >= num_results:
                        break

        if results:
            return "\n".join(results)
        else:
            return f"No results found for '{query}'"

    except requests.RequestException as e:
        return f"Error: Search failed: {e}"
    except Exception as e:
        return f"Error: DuckDuckGo scraping failed: {e}"


def web_screenshot(url: str, output_path: str) -> str:
    """Capture website screenshot using Playwright.

    Args:
        url: Target URL to screenshot
        output_path: File path to save screenshot (PNG format)

    Returns:
        Output path on success, error message on failure
    """
    try:
        safe_url, err_url = _validate_url(url)
        if not safe_url:
            return f"Error: URL validation failed: {err_url}"
        safe_path, err_path = _validate_output_path(output_path)
        if not safe_path:
            return f"Error: Path validation failed: {err_path}"
        output_path = str(Path(output_path).resolve())

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()

                # Set viewport
                page.set_viewport_size({"width": 1280, "height": 720})

                # Navigate and wait for load
                page.goto(url, wait_until="networkidle", timeout=30000)

                # Take screenshot
                page.screenshot(path=output_path)
            finally:
                browser.close()

        return output_path

    except Exception as e:
        return f"Error: Screenshot failed: {e}"


if __name__ == "__main__":
    # Quick test
    print("Testing web_scrape...")
    result = web_scrape("https://example.com")
    print(f"Scrape result length: {len(result)}")

    print("\nTesting web_search...")
    result = web_search("python web scraping", num_results=3)
    print(result[:200])

    print("\nTesting web_screenshot...")
    result = web_screenshot("https://example.com", "/tmp/test_screenshot.png")
    print(f"Screenshot: {result}")
