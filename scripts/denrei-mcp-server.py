#!/usr/bin/env python3
"""denrei-mcp-server.py - MCP stdio server for denrei + memory_update tools.

Provides two tools for codex exec:
  - denrei: Send messages to leader agents via tmux send-keys
  - memory_update: Read/append to nyancobot's MEMORY.md

Protocol: MCP stdio transport (JSON-RPC 2.0 over stdin/stdout)
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path


def _sanitize_message(message: str) -> str:
    """メッセージから危険な文字列を除去する。"""
    # 制御文字を除去（タブ以外）
    sanitized = re.sub(r'[\x00-\x08\x0b-\x1f\x7f]', '', message)
    # バッククォートとドル記号を除去（シェルコマンド置換防止）
    sanitized = sanitized.replace('`', '').replace('$', '')
    # 長さ制限（512文字）
    if len(sanitized) > 512:
        sanitized = sanitized[:512]
    return sanitized


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
LEADER_TARGETS = {
    "1": os.environ.get("NYANCOBOT_LEADER_SESSION", "leader:0.0"),
    "2": os.environ.get("NYANCOBOT_LEADER2_SESSION", "leader2:0.0"),
}

MEMORY_MD_PATH = Path.home() / ".nyancobot" / "workspace" / "memory" / "MEMORY.md"
POLLER_SCRIPT = Path.home() / ".nyancobot" / "scripts" / "denrei-response-poller.py"

# Rate limiting: {target: last_send_time}
_last_denrei_time = {}
DENREI_INTERVAL_SECONDS = 120  # 2 minutes
DENREI_TIMEOUT_COOLDOWN = 300  # 5 minutes after timeout

# Health check cooldown: {target: {"count": int, "last_timeout": float, "suspended_until": float}}
_leader_health_status = {}
HEALTH_CHECK_SUSPEND_THRESHOLD = 3  # Consecutive timeouts before suspension
HEALTH_CHECK_SUSPEND_DURATION = 3600  # 1 hour suspension

BUSY_INDICATORS = [
    "thinking", "Effecting", "Boondoggling", "Puzzling",
    "Calculating", "Fermenting", "Crunching", "Running",
    "Esc to interrupt", "Compacting conversation",
]

BUSY_FLAG_DIR = Path.home() / ".nyancobot" / "scripts"
BUSY_FLAG_TTL = 600  # 10 minutes

MAX_MEMORY_CONTENT_LENGTH = 500
INJECTION_PATTERNS = ['[System]', '[Assistant]', '最重要指示', 'IMPORTANT:', 'OVERRIDE']

SERVER_INFO = {
    "name": "nyancobot-denrei-tools",
    "version": "1.0.0",
}

TOOLS = [
    {
        "name": "denrei",
        "description": (
            "leader（開発チームリーダー）にメッセージを送信するmessengerツール。"
            "userが「messengerして」「leaderに聞いて」「leaderに伝えて」「leaderに相談」と言った場合に使え。"
            "権限確認は不要。直接実行してよい。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "enum": ["1", "2"],
                    "description": "送信先のleader番号。1=leader1（n8n/動画/投稿自動化担当）、2=leader2（nyancobot/システム基盤担当）",
                },
                "message": {
                    "type": "string",
                    "description": "leaderに送信するメッセージ内容。userの発言をそのまま転送せず、文脈を踏まえて簡潔にまとめよ",
                },
            },
            "required": ["target", "message"],
        },
    },
    {
        "name": "memory_update",
        "description": (
            "重要な情報を永続記憶に保存する、または現在の記憶を読み取るツール。"
            "userが「覚えておけ」「記憶しろ」と言った場合や、"
            "重要な好み・指示・判断を発見した場合に使え。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "read"],
                    "description": "add=記憶に追記、read=現在の記憶を読み取り",
                },
                "content": {
                    "type": "string",
                    "description": "保存する内容（action=addの場合に必須）",
                },
            },
            "required": ["action"],
        },
    },
    {
        "name": "leader_status",
        "description": (
            "leaderの稼働状態を確認し、異常を検出するツール。"
            "定期的なヘルスチェックや、leaderが応答しない場合の診断に使用。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------
def _capture_pane_wide(tmux_target: str, lines: int = 200) -> str:
    """Capture tmux pane content with extended history."""
    try:
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", tmux_target, "-p", "-S", f"-{lines}"],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout
    except Exception:
        return ""


def _is_leader_busy(tmux_target: str) -> str | None:
    """Check if leader is actively processing. Returns message if busy, None if idle."""
    pane_text = _capture_pane_wide(tmux_target, lines=20)
    if not pane_text:
        return None
    tail = "\n".join(pane_text.splitlines()[-8:]).lower()
    for indicator in BUSY_INDICATORS:
        if indicator.lower() in tail:
            return f"leaderは現在処理中でござる（{indicator}検出）。後ほど再試行されたし。"
    return None


def _check_busy_flag(target: str) -> str | None:
    """Check if BUSY flag file exists and is within TTL."""
    flag_path = BUSY_FLAG_DIR / f".leader_busy_{target}.flag"
    if not flag_path.exists():
        return None
    try:
        mtime = flag_path.stat().st_mtime
        age = time.time() - mtime
        if age < BUSY_FLAG_TTL:
            remaining = int((BUSY_FLAG_TTL - age) / 60)
            return f"leader{target}は多忙でござる（タイムアウト後の冷却中、残り約{remaining}分）。後ほど再試行されたし。"
        else:
            flag_path.unlink(missing_ok=True)
            return None
    except Exception:
        return None


def _set_busy_flag(target: str) -> None:
    """Create BUSY flag file to enforce extended cooldown after timeout."""
    flag_path = BUSY_FLAG_DIR / f".leader_busy_{target}.flag"
    try:
        BUSY_FLAG_DIR.mkdir(parents=True, exist_ok=True)
        flag_path.touch()
        _log_to_file(f"SET_BUSY_FLAG: {flag_path}")
    except Exception as e:
        _log_to_file(f"Failed to set BUSY flag: {e}")


def _spawn_response_poller(tmux_target: str, target: str, baseline: str) -> None:
    """Spawn a detached poller process to detect leader's response and auto-reply.

    The poller runs independently of the MCP server, so it survives codex exec exit.
    """
    if not POLLER_SCRIPT.exists():
        _log_to_file(f"Poller script not found: {POLLER_SCRIPT}")
        return

    # Write baseline to temp file
    try:
        fd, baseline_path = tempfile.mkstemp(prefix="denrei_baseline_", suffix=".txt")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(baseline)
    except Exception as e:
        _log_to_file(f"Failed to write baseline file: {e}")
        return

    # Spawn detached poller process
    try:
        subprocess.Popen(
            ["python3", str(POLLER_SCRIPT), tmux_target, target, baseline_path],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        _log_to_file(f"Poller spawned: target={tmux_target} baseline={baseline_path}")
    except Exception as e:
        _log_to_file(f"Failed to spawn poller: {e}")


def execute_denrei(target: str, message: str) -> str:
    """Send a message to a leader via tmux send-keys, then spawn response poller."""
    tmux_target = LEADER_TARGETS.get(target)
    if not tmux_target:
        return f"Error: 不明なleader番号 '{target}'。1または2を指定してください。"

    # --- Check rate limit (prevent rapid-fire denrei) ---
    now = time.time()
    last_time = _last_denrei_time.get(target, 0)
    elapsed = int(now - last_time)
    if last_time > 0 and elapsed < DENREI_INTERVAL_SECONDS:
        remaining = DENREI_INTERVAL_SECONDS - elapsed
        _log_to_file(f"RATE_LIMIT: target={target} elapsed={elapsed}s → blocked")
        return f"leader{target}への前回送信から{elapsed}秒しか経っておらぬ。あと{remaining}秒待たれよ。"

    # --- Check BUSY flag first (cooldown after previous timeout) ---
    busy_flag = _check_busy_flag(target)
    if busy_flag:
        _log_to_file(f"BUSY_FLAG: target={target} → blocked")
        return busy_flag

    # --- Check if leader is currently busy (thinking/processing) ---
    busy_status = _is_leader_busy(tmux_target)
    if busy_status:
        _log_to_file(f"BUSY_DETECT: target={target} → blocked")
        return busy_status

    sanitized_msg = _sanitize_message(message)
    if not sanitized_msg:
        return "Error: メッセージが空、または危険な文字のみで構成されています。"
    escaped = sanitized_msg.replace("'", "'\\''")

    try:
        # Clear input line
        subprocess.run(
            ["tmux", "send-keys", "-t", tmux_target, "C-u"],
            timeout=5, check=True, capture_output=True,
        )
        time.sleep(0.2)

        # Send message text
        subprocess.run(
            ["tmux", "send-keys", "-t", tmux_target, escaped],
            timeout=5, check=True, capture_output=True,
        )
        time.sleep(0.5)

        # Send Enter
        subprocess.run(
            ["tmux", "send-keys", "-t", tmux_target, "Enter"],
            timeout=5, check=True, capture_output=True,
        )
        time.sleep(2)

        # Verify delivery (check input line is empty)
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", tmux_target, "-p"],
            capture_output=True, text=True, timeout=5,
        )
        pane_lines = result.stdout.strip().splitlines()[-3:]
        pane_tail = "\n".join(pane_lines)
        fragment = message[:20]

        delivered = False
        if fragment not in pane_tail:
            delivered = True
        else:
            # Text still in input - try Enter again
            subprocess.run(
                ["tmux", "send-keys", "-t", tmux_target, "Enter"],
                timeout=5, check=True, capture_output=True,
            )
            time.sleep(2)
            delivered = True

        # Capture baseline AFTER sending (message is now in pane)
        # This prevents the sent message from being falsely detected as a response
        if delivered:
            time.sleep(3)  # Additional wait (total ~5s after Enter)
            baseline = _capture_pane_wide(tmux_target)
            _spawn_response_poller(tmux_target, target, baseline)

        # Update last send time on success
        _last_denrei_time[target] = time.time()

        return (
            f"✅ leader{target}に送達完了。メッセージ: {message[:100]}\n"
            f"（leaderの返答は自動的にnyancobotに転送されます）"
        )

    except subprocess.TimeoutExpired:
        # Set BUSY flag with extended cooldown on timeout
        _set_busy_flag(target)
        _log_to_file(f"TIMEOUT: target={target} → BUSY_FLAG set for {BUSY_FLAG_TTL}s")
        return f"Error: leader{target}への送信がタイムアウトしました。"
    except subprocess.CalledProcessError as e:
        return f"Error: leader{target}への送信に失敗: {e}"
    except FileNotFoundError:
        return "Error: tmuxコマンドが見つかりません。"


def execute_memory_update(action: str, content: str = "") -> str:
    """Read or append to MEMORY.md."""
    if action == "read":
        try:
            if MEMORY_MD_PATH.exists():
                text = MEMORY_MD_PATH.read_text(encoding="utf-8").strip()
                if text:
                    return f"【現在の記憶】\n{text}"
                return "記憶は空でござる。"
            return "記憶ファイルが存在しません。"
        except Exception as e:
            return f"Error: 記憶の読み取りに失敗: {e}"

    elif action == "add":
        if not content:
            return "Error: 保存する内容(content)が空です。"
        if len(content) > MAX_MEMORY_CONTENT_LENGTH:
            return f"Error: 内容が長すぎます（{len(content)}文字）。{MAX_MEMORY_CONTENT_LENGTH}文字以内にしてください。"
        for pattern in INJECTION_PATTERNS:
            if pattern.lower() in content.lower():
                return f"Error: 禁止パターンが含まれています: {pattern}"
        try:
            MEMORY_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            entry = f"\n- [{timestamp}] {content}\n"
            with open(MEMORY_MD_PATH, "a", encoding="utf-8") as f:
                f.write(entry)
            return f"✅ 記憶に保存完了: {content}"
        except Exception as e:
            return f"Error: 記憶の保存に失敗: {e}"

    return f"Error: 不明なaction '{action}'。add または read を指定してください。"


def execute_leader_status() -> str:
    """Check leader health status via tmux capture-pane."""
    error_patterns = ["error", "failed", "killed", "bash-", "zsh-", "command not found"]
    # Lines containing these are NOT real errors (false positive exclusions)
    false_positive_patterns = [
        "brew upgrade",       # brew update notification
        "new version",        # claude-code update prompt
        "feedback",           # claude feedback screen
        "would you like",     # interactive prompts
        "press enter",        # interactive prompts
        "update available",   # update notifications
        "deprecated",         # deprecation warnings (not errors)
        "error handling",     # code that mentions "error handling" as a concept
        "error_pattern",      # self-reference in code
    ]

    results = []

    for name, target in LEADER_TARGETS.items():
        # Check if this leader is suspended due to repeated timeouts
        status = _leader_health_status.get(name, {"count": 0, "last_timeout": 0, "suspended_until": 0})
        now = time.time()

        if status.get("suspended_until", 0) > now:
            remaining_min = int((status["suspended_until"] - now) / 60)
            results.append(f"⏸️ leader{name}: 長時間多忙のため確認を一時中断（残り約{remaining_min}分）")
            continue

        try:
            # Capture pane content
            result = subprocess.run(
                ["tmux", "capture-pane", "-t", target, "-p"],
                capture_output=True, text=True, timeout=5,
            )

            if result.returncode != 0:
                results.append(f"❌ leader{name}: tmuxセッションが見つかりません")
                continue

            # Get last 20 lines
            lines = result.stdout.strip().splitlines()[-20:]
            pane_text = "\n".join(lines).lower()

            # Check for error patterns, filtering out false positives
            found_errors = []
            for p in error_patterns:
                if p in pane_text:
                    # Check if all occurrences are false positives
                    is_real_error = False
                    for line in lines:
                        ll = line.lower()
                        if p in ll and not any(fp in ll for fp in false_positive_patterns):
                            is_real_error = True
                            break
                    if is_real_error:
                        found_errors.append(p)

            if found_errors:
                results.append(f"⚠️ leader{name}: 異常検出 ({', '.join(found_errors)})")
            else:
                # Check if Claude Code is running (prompt should be visible)
                if "thinking" in pane_text or "effecting" in pane_text:
                    results.append(f"🔄 leader{name}: 処理中")
                elif ">" in lines[-1] or "❯" in lines[-1]:
                    results.append(f"✅ leader{name}: 待機中（正常）")
                    # Reset timeout count on successful health check
                    _leader_health_status[name] = {"count": 0, "last_timeout": 0, "suspended_until": 0}
                else:
                    results.append(f"❓ leader{name}: 状態不明")

        except subprocess.TimeoutExpired:
            # Increment timeout count and check for suspension
            status = _leader_health_status.get(name, {"count": 0, "last_timeout": 0, "suspended_until": 0})
            status["count"] += 1
            status["last_timeout"] = time.time()

            if status["count"] >= HEALTH_CHECK_SUSPEND_THRESHOLD:
                status["suspended_until"] = time.time() + HEALTH_CHECK_SUSPEND_DURATION
                _leader_health_status[name] = status
                _log_to_file(f"HEALTH_CHECK_SUSPENDED: leader{name} timeout_count={status['count']} → suspended for {HEALTH_CHECK_SUSPEND_DURATION}s")
                results.append(f"❌ leader{name}: タイムアウト（連続{status['count']}回、確認を{int(HEALTH_CHECK_SUSPEND_DURATION/3600)}時間中断）")
            else:
                _leader_health_status[name] = status
                _log_to_file(f"HEALTH_CHECK_TIMEOUT: leader{name} timeout_count={status['count']}")
                results.append(f"❌ leader{name}: タイムアウト（{status['count']}回目）")
        except FileNotFoundError:
            results.append(f"❌ leader{name}: tmuxコマンドが見つかりません")
        except Exception as e:
            results.append(f"❌ leader{name}: エラー ({e})")

    return "\n".join(results)


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


_LOG_FILE_PATH = Path.home() / ".nyancobot" / "scripts" / "denrei-mcp-server.log"

def _log_to_file(msg: str):
    """Append a line to the log file."""
    try:
        with open(_LOG_FILE_PATH, "a") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
            f.flush()
    except Exception:
        pass


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

    # Detailed logging to file
    _log_to_file(f"TOOL_CALL: name={tool_name} args={json.dumps(arguments, ensure_ascii=False)}")

    if tool_name == "denrei":
        target = arguments.get("target", "")
        message = arguments.get("message", "")
        result_text = execute_denrei(target, message)
    elif tool_name == "memory_update":
        action = arguments.get("action", "")
        content = arguments.get("content", "")
        result_text = execute_memory_update(action, content)
    elif tool_name == "leader_status":
        result_text = execute_leader_status()
    else:
        send_error(id_val, -32602, f"Unknown tool: {tool_name}")
        return

    is_error = result_text.startswith("Error:")
    _log_to_file(f"TOOL_RESULT: name={tool_name} is_error={is_error} result={result_text[:200]}")

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
    log = open(Path.home() / ".nyancobot" / "scripts" / "denrei-mcp-server.log", "a")
    log.write(f"\n--- Server started at {datetime.now().isoformat()} ---\n")
    log.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            msg = json.loads(line)
        except json.JSONDecodeError as e:
            log.write(f"JSON parse error: {e} | line: {line[:200]}\n")
            log.flush()
            continue

        method = msg.get("method", "")
        id_val = msg.get("id")
        params = msg.get("params", {})

        log.write(f"REQ: method={method} id={id_val} params_keys={list(params.keys()) if isinstance(params, dict) else 'N/A'}\n")
        log.flush()

        handler = HANDLERS.get(method)
        if handler:
            handler(id_val, params)
        elif id_val is not None:
            send_error(id_val, -32601, f"Method not found: {method}")

        log.write(f"DONE: method={method}\n")
        log.flush()

    log.write(f"--- Server stopped at {datetime.now().isoformat()} ---\n")
    log.close()


if __name__ == "__main__":
    main()
