"""
human_actions.py - Human-like Browser Interaction Simulator

Provides realistic mouse movement (cubic Bezier curves), typing with
random delays and occasional typos, and smooth scrolling.

Requires: Playwright Python async API (Chromium only for CDP features).

Based on PinchTab's human simulation approach (MIT License).
"""

import asyncio
import math
import random
import string
from typing import Optional, Tuple, Union

from playwright.async_api import Page, Locator, ElementHandle


# ---------------------------------------------------------------------------
# Internal state: track last known mouse position per page
# ---------------------------------------------------------------------------
_last_mouse_pos: dict[int, Tuple[float, float]] = {}


# ---------------------------------------------------------------------------
# Bezier curve helpers
# ---------------------------------------------------------------------------

def _cubic_bezier(
    t: float,
    p0: Tuple[float, float],
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    p3: Tuple[float, float],
) -> Tuple[float, float]:
    """Evaluate cubic Bezier curve at parameter t in [0, 1]."""
    u = 1.0 - t
    x = u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0]
    y = u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1]
    return (x, y)


def _generate_bezier_path(
    start: Tuple[float, float],
    end: Tuple[float, float],
    steps: int = 20,
) -> list[Tuple[float, float]]:
    """Generate a path of points along a cubic Bezier curve with random control points."""
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    offset = 50.0  # +-50px control point randomness

    cp1 = (
        start[0] + dx * 0.25 + random.uniform(-offset, offset),
        start[1] + dy * 0.25 + random.uniform(-offset, offset),
    )
    cp2 = (
        start[0] + dx * 0.75 + random.uniform(-offset, offset),
        start[1] + dy * 0.75 + random.uniform(-offset, offset),
    )

    path = []
    for i in range(steps + 1):
        t = i / steps
        point = _cubic_bezier(t, start, cp1, cp2, end)
        # Add micro-jitter (+-2px)
        jittered = (
            point[0] + random.uniform(-2, 2),
            point[1] + random.uniform(-2, 2),
        )
        path.append(jittered)

    return path


async def _get_element_center(
    page: Page, target: Union[str, Locator, ElementHandle]
) -> Tuple[float, float]:
    """Get the center coordinates of an element."""
    if isinstance(target, str):
        locator = page.locator(target)
    elif isinstance(target, Locator):
        locator = target
    elif isinstance(target, ElementHandle):
        box = await target.bounding_box()
        if not box:
            raise ValueError("Element has no bounding box (may be hidden)")
        return (box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    else:
        raise TypeError(f"Unsupported target type: {type(target)}")

    box = await locator.bounding_box()
    if not box:
        raise ValueError("Element has no bounding box (may be hidden or detached)")
    # Add small random offset within the element (not always dead center)
    offset_x = random.uniform(-box["width"] * 0.15, box["width"] * 0.15)
    offset_y = random.uniform(-box["height"] * 0.15, box["height"] * 0.15)
    return (
        box["x"] + box["width"] / 2 + offset_x,
        box["y"] + box["height"] / 2 + offset_y,
    )


def _get_start_position(page: Page) -> Tuple[float, float]:
    """Get the starting mouse position (last known or random)."""
    page_id = id(page)
    if page_id in _last_mouse_pos:
        return _last_mouse_pos[page_id]
    # Random starting position in the viewport area
    return (random.uniform(100, 600), random.uniform(100, 400))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def human_click(
    page: Page,
    selector_or_element: Union[str, Locator, ElementHandle],
    options: Optional[dict] = None,
) -> None:
    """
    Click an element with human-like mouse movement along a cubic Bezier curve.

    Args:
        page: Playwright Page instance.
        selector_or_element: CSS selector string, Locator, or ElementHandle.
        options: Optional dict with:
            - steps (int): Number of mouse movement steps (default 20).
            - button (str): Mouse button - 'left', 'right', 'middle' (default 'left').
    """
    options = options or {}
    steps = options.get("steps", 20)
    button = options.get("button", "left")

    target_pos = await _get_element_center(page, selector_or_element)
    start_pos = _get_start_position(page)

    # Generate and follow the Bezier path
    path = _generate_bezier_path(start_pos, target_pos, steps=steps)

    for point in path:
        await page.mouse.move(point[0], point[1])
        # Random delay per step: 16-24ms (roughly 1 frame at 60fps)
        await asyncio.sleep(random.uniform(0.016, 0.024))

    # Pre-click pause: 50-200ms (human reaction)
    await asyncio.sleep(random.uniform(0.05, 0.2))

    # mousedown
    await page.mouse.down(button=button)

    # Hold duration: 30-120ms
    await asyncio.sleep(random.uniform(0.03, 0.12))

    # Release with slight offset (+-1px)
    release_x = target_pos[0] + random.uniform(-1, 1)
    release_y = target_pos[1] + random.uniform(-1, 1)
    await page.mouse.move(release_x, release_y)
    await page.mouse.up(button=button)

    # Track final position
    _last_mouse_pos[id(page)] = (release_x, release_y)


async def human_type(
    page: Page,
    selector_or_element: Union[str, Locator, ElementHandle],
    text: str,
    options: Optional[dict] = None,
) -> None:
    """
    Type text with human-like random delays and occasional typos.

    Args:
        page: Playwright Page instance.
        selector_or_element: CSS selector string, Locator, or ElementHandle.
        text: The text to type.
        options: Optional dict with:
            - min_delay (float): Minimum delay between keystrokes in seconds (default 0.08).
            - max_delay (float): Maximum delay between keystrokes in seconds (default 0.12).
            - typo_rate (float): Probability of a typo per character (default 0.03).
            - pause_rate (float): Probability of a thinking pause (default 0.05).
            - max_pause (float): Maximum thinking pause in seconds (default 0.5).
            - click_first (bool): Whether to click the element first (default True).
    """
    options = options or {}
    min_delay = options.get("min_delay", 0.08)
    max_delay = options.get("max_delay", 0.12)
    typo_rate = options.get("typo_rate", 0.03)
    pause_rate = options.get("pause_rate", 0.05)
    max_pause = options.get("max_pause", 0.5)
    click_first = options.get("click_first", True)

    # Focus the element
    if click_first:
        await human_click(page, selector_or_element)
        await asyncio.sleep(random.uniform(0.1, 0.3))

    prev_char = ""

    for char in text:
        # Thinking pause: 5% chance
        if random.random() < pause_rate:
            await asyncio.sleep(random.uniform(0.1, max_pause))

        # Typo simulation: 3% chance
        if random.random() < typo_rate and char.isalpha():
            # Type a wrong character
            wrong_char = random.choice(string.ascii_lowercase)
            await page.keyboard.press(wrong_char)
            await asyncio.sleep(random.uniform(0.1, 0.15))

            # Pause to "notice" the typo
            await asyncio.sleep(random.uniform(0.05, 0.15))

            # Backspace to fix it
            await page.keyboard.press("Backspace")
            await asyncio.sleep(random.uniform(0.05, 0.1))

        # Type the correct character
        await page.keyboard.press(char)

        # Delay between keystrokes
        delay = random.uniform(min_delay, max_delay)

        # Same key repeated: halve the delay
        if char == prev_char:
            delay *= 0.5

        await asyncio.sleep(delay)
        prev_char = char


async def human_scroll(
    page: Page,
    direction: str = "down",
    amount: int = 300,
    options: Optional[dict] = None,
) -> None:
    """
    Scroll the page smoothly in small increments to mimic human behavior.

    Args:
        page: Playwright Page instance.
        direction: 'down', 'up', 'left', or 'right'.
        amount: Total scroll amount in pixels.
        options: Optional dict with:
            - steps (int): Number of scroll increments (default 8).
            - min_delay (float): Minimum delay between steps in seconds (default 0.03).
            - max_delay (float): Maximum delay between steps in seconds (default 0.08).
    """
    options = options or {}
    steps = options.get("steps", 8)
    min_delay = options.get("min_delay", 0.03)
    max_delay = options.get("max_delay", 0.08)

    # Calculate scroll per step with some variation
    base_per_step = amount / steps

    total_scrolled = 0

    for i in range(steps):
        remaining = amount - total_scrolled
        if remaining <= 0:
            break

        # Vary the scroll amount per step (ease-in/ease-out effect)
        # Middle steps are larger, start and end steps are smaller
        progress = i / max(steps - 1, 1)
        ease = math.sin(progress * math.pi)  # 0 -> 1 -> 0
        step_amount = base_per_step * (0.5 + ease * 0.8)
        step_amount = min(step_amount, remaining)
        step_amount = max(step_amount, 10)  # Minimum 10px per step

        # Random jitter
        step_amount += random.uniform(-5, 5)
        step_amount = max(1, step_amount)

        dx, dy = 0, 0
        if direction == "down":
            dy = step_amount
        elif direction == "up":
            dy = -step_amount
        elif direction == "right":
            dx = step_amount
        elif direction == "left":
            dx = -step_amount

        await page.evaluate(f"window.scrollBy({dx}, {dy})")
        total_scrolled += abs(step_amount)

        await asyncio.sleep(random.uniform(min_delay, max_delay))


async def human_hover(
    page: Page,
    selector_or_element: Union[str, Locator, ElementHandle],
    options: Optional[dict] = None,
) -> None:
    """
    Move the mouse to an element with human-like Bezier movement (without clicking).

    Args:
        page: Playwright Page instance.
        selector_or_element: CSS selector string, Locator, or ElementHandle.
        options: Optional dict with:
            - steps (int): Number of mouse movement steps (default 15).
    """
    options = options or {}
    steps = options.get("steps", 15)

    target_pos = await _get_element_center(page, selector_or_element)
    start_pos = _get_start_position(page)

    path = _generate_bezier_path(start_pos, target_pos, steps=steps)

    for point in path:
        await page.mouse.move(point[0], point[1])
        await asyncio.sleep(random.uniform(0.016, 0.024))

    _last_mouse_pos[id(page)] = target_pos
