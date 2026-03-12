"""
a11y_snapshot.py - Accessibility Tree Snapshot for Token-Efficient Page Representation

Uses Playwright's CDP connection to get the browser's accessibility tree,
filter it to interactive elements, and produce a compact text representation
that costs ~13x fewer tokens than a screenshot.

Based on PinchTab's snapshot approach (MIT License).

Requirements: Playwright Python async API, Chromium browser only (CDP).
"""

from typing import Optional, Tuple

from playwright.async_api import Page, CDPSession


# Roles that represent interactive/actionable elements
INTERACTIVE_ROLES = {
    "button",
    "link",
    "textbox",
    "searchbox",
    "combobox",
    "listbox",
    "option",
    "checkbox",
    "radio",
    "switch",
    "slider",
    "spinbutton",
    "menuitem",
    "menuitemcheckbox",
    "menuitemradio",
    "tab",
    "treeitem",
}

# Roles to always exclude (noise nodes)
EXCLUDED_ROLES = {
    "none",
    "generic",
    "InlineTextBox",
    "LineBreak",
    "paragraph",
    "Section",
}


def _is_ignored(node: dict) -> bool:
    """Check if an AX node should be ignored."""
    # Explicitly ignored by the browser
    if node.get("ignored", False):
        return True

    role = _get_role(node)
    if role in EXCLUDED_ROLES:
        return True

    # StaticText with empty name
    if role == "StaticText":
        name = _get_name(node)
        if not name or not name.strip():
            return True

    return False


def _get_role(node: dict) -> str:
    """Extract the role string from an AX node."""
    role_obj = node.get("role", {})
    return role_obj.get("value", "") if isinstance(role_obj, dict) else str(role_obj)


def _get_name(node: dict) -> str:
    """Extract the name string from an AX node."""
    name_obj = node.get("name", {})
    return name_obj.get("value", "") if isinstance(name_obj, dict) else str(name_obj)


def _get_value(node: dict) -> str:
    """Extract the value string from an AX node."""
    value_obj = node.get("value", {})
    return value_obj.get("value", "") if isinstance(value_obj, dict) else str(value_obj)


def _get_property(node: dict, prop_name: str) -> Optional[str]:
    """Extract a named property from an AX node's properties list."""
    for prop in node.get("properties", []):
        if prop.get("name") == prop_name:
            val = prop.get("value", {})
            if isinstance(val, dict):
                return val.get("value")
            return val
    return None


def _get_backend_dom_node_id(node: dict) -> Optional[int]:
    """Extract the backendDOMNodeId from an AX node."""
    return node.get("backendDOMNodeId")


async def get_accessibility_snapshot(
    page: Page,
    interactive_only: bool = True,
    compact: bool = True,
    max_depth: Optional[int] = None,
) -> Tuple[str, dict]:
    """
    Get the accessibility tree of the current page via CDP.

    Args:
        page: Playwright Page instance (must be Chromium).
        interactive_only: If True, only return interactive elements.
        compact: If True, produce a compact single-line-per-node format.
        max_depth: Maximum tree depth to include (None for unlimited).

    Returns:
        tuple of:
            - str: The formatted accessibility snapshot.
            - dict: Mapping of ref ID (e.g., "e0") to backendDOMNodeId.
    """
    cdp: CDPSession = await page.context.new_cdp_session(page)

    try:
        # Get the full accessibility tree
        result = await cdp.send("Accessibility.getFullAXTree")
        nodes = result.get("nodes", [])

        # Build parent-child relationships
        node_map = {}
        children_map = {}
        for node in nodes:
            node_id = node.get("nodeId", "")
            node_map[node_id] = node
            children_map[node_id] = []

        for node in nodes:
            node_id = node.get("nodeId", "")
            parent_id = node.get("parentId")
            if parent_id and parent_id in children_map:
                children_map[parent_id].append(node_id)

        # Flatten and filter the tree
        filtered_nodes = []
        ref_map = {}
        ref_counter = [0]

        def _walk(node_id: str, depth: int = 0):
            if max_depth is not None and depth > max_depth:
                return

            node = node_map.get(node_id)
            if node is None:
                return

            if not _is_ignored(node):
                role = _get_role(node)
                name = _get_name(node)
                value = _get_value(node)
                backend_id = _get_backend_dom_node_id(node)

                is_interactive = role in INTERACTIVE_ROLES
                is_disabled = _get_property(node, "disabled") == True
                is_focused = _get_property(node, "focused") == True
                is_checked = _get_property(node, "checked")
                is_expanded = _get_property(node, "expanded")

                include = True
                if interactive_only and not is_interactive:
                    # Still include non-interactive nodes that provide context
                    # (headings, images with alt text) if they have a name
                    if role not in ("heading", "img", "banner", "navigation",
                                     "main", "complementary", "contentinfo") or not name:
                        include = False

                if include:
                    ref = f"e{ref_counter[0]}"
                    ref_counter[0] += 1

                    if backend_id is not None:
                        ref_map[ref] = backend_id

                    filtered_nodes.append({
                        "ref": ref,
                        "role": role,
                        "name": name,
                        "value": value,
                        "depth": depth,
                        "disabled": is_disabled,
                        "focused": is_focused,
                        "checked": is_checked,
                        "expanded": is_expanded,
                    })

            # Walk children
            for child_id in children_map.get(node_id, []):
                _walk(child_id, depth + 1)

        # Find the root node and walk the tree
        root_ids = [
            n.get("nodeId", "")
            for n in nodes
            if not n.get("parentId") and not _is_ignored(n)
        ]
        if not root_ids and nodes:
            root_ids = [nodes[0].get("nodeId", "")]

        for root_id in root_ids:
            _walk(root_id)

        # Format output
        if compact:
            output = _format_compact(filtered_nodes)
        else:
            output = _format_tree(filtered_nodes)

        return output, ref_map

    finally:
        await cdp.detach()


def _format_compact(nodes: list[dict]) -> str:
    """
    Format nodes in compact single-line format:
        e0:button "Sign In"
        e1:textbox "Email" val="user@example.com" *
    """
    lines = []
    for node in nodes:
        parts = [f'{node["ref"]}:{node["role"]}']

        if node["name"]:
            parts.append(f'"{node["name"]}"')

        if node["value"]:
            parts.append(f'val="{node["value"]}"')

        if node["checked"] is not None:
            parts.append("checked" if node["checked"] else "unchecked")

        if node["expanded"] is not None:
            parts.append("expanded" if node["expanded"] else "collapsed")

        if node["disabled"]:
            parts.append("disabled")

        if node["focused"]:
            parts.append("*")  # asterisk = focused

        lines.append(" ".join(parts))

    return "\n".join(lines)


def _format_tree(nodes: list[dict]) -> str:
    """
    Format nodes as an indented tree:
        e0:button "Sign In"
          e1:textbox "Email" val="user@"
    """
    lines = []
    for node in nodes:
        indent = "  " * node["depth"]
        parts = [f'{node["ref"]}:{node["role"]}']

        if node["name"]:
            parts.append(f'"{node["name"]}"')

        if node["value"]:
            parts.append(f'val="{node["value"]}"')

        if node["checked"] is not None:
            parts.append("checked" if node["checked"] else "unchecked")

        if node["expanded"] is not None:
            parts.append("expanded" if node["expanded"] else "collapsed")

        if node["disabled"]:
            parts.append("disabled")

        if node["focused"]:
            parts.append("*")

        lines.append(f"{indent}{' '.join(parts)}")

    return "\n".join(lines)


async def click_by_ref(
    page: Page,
    ref: str,
    ref_map: dict,
) -> None:
    """
    Click an element using its stable accessibility reference ID.

    Args:
        page: Playwright Page instance.
        ref: The reference ID (e.g., "e5").
        ref_map: The ref-to-backendDOMNodeId mapping from get_accessibility_snapshot().
    """
    if ref not in ref_map:
        raise ValueError(f"Reference '{ref}' not found in ref_map")

    backend_node_id = ref_map[ref]
    cdp: CDPSession = await page.context.new_cdp_session(page)

    try:
        # Resolve the backendDOMNodeId to a RemoteObject
        result = await cdp.send(
            "DOM.resolveNode",
            {"backendNodeId": backend_node_id},
        )
        object_id = result["object"]["objectId"]

        # Click the element via JavaScript
        await cdp.send(
            "Runtime.callFunctionOn",
            {
                "objectId": object_id,
                "functionDeclaration": """
                    function() {
                        this.scrollIntoViewIfNeeded();
                        this.click();
                    }
                """,
                "returnByValue": True,
            },
        )
    finally:
        await cdp.detach()


async def focus_by_ref(
    page: Page,
    ref: str,
    ref_map: dict,
) -> None:
    """
    Focus an element using its stable accessibility reference ID.

    Args:
        page: Playwright Page instance.
        ref: The reference ID (e.g., "e3").
        ref_map: The ref-to-backendDOMNodeId mapping.
    """
    if ref not in ref_map:
        raise ValueError(f"Reference '{ref}' not found in ref_map")

    backend_node_id = ref_map[ref]
    cdp: CDPSession = await page.context.new_cdp_session(page)

    try:
        await cdp.send(
            "DOM.focus",
            {"backendNodeId": backend_node_id},
        )
    finally:
        await cdp.detach()


async def fill_by_ref(
    page: Page,
    ref: str,
    ref_map: dict,
    value: str,
) -> None:
    """
    Fill a text input using its stable accessibility reference ID.

    Args:
        page: Playwright Page instance.
        ref: The reference ID (e.g., "e1").
        ref_map: The ref-to-backendDOMNodeId mapping.
        value: The text value to fill.
    """
    if ref not in ref_map:
        raise ValueError(f"Reference '{ref}' not found in ref_map")

    backend_node_id = ref_map[ref]
    cdp: CDPSession = await page.context.new_cdp_session(page)

    try:
        result = await cdp.send(
            "DOM.resolveNode",
            {"backendNodeId": backend_node_id},
        )
        object_id = result["object"]["objectId"]

        # Focus, clear, and set value via JS
        await cdp.send(
            "Runtime.callFunctionOn",
            {
                "objectId": object_id,
                "functionDeclaration": f"""
                    function() {{
                        this.focus();
                        this.value = '';
                        this.value = {repr(value)};
                        this.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        this.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                """,
                "returnByValue": True,
            },
        )
    finally:
        await cdp.detach()
