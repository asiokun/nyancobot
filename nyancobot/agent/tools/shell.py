"""Shell execution tool."""

import asyncio
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from nyancobot.agent.tools.base import Tool


class ExecTool(Tool):
    """Tool to execute shell commands."""
    
    def __init__(
        self,
        timeout: int = 60,
        working_dir: str | None = None,
        deny_patterns: list[str] | None = None,
        allow_patterns: list[str] | None = None,
        restrict_to_workspace: bool = False,
        allowed_dirs: list[str] | None = None,
        audit_log: bool = True,
        audit_log_path: str = "~/.nyancobot/logs/audit.jsonl",
        additional_deny_patterns: list[str] | None = None,
    ):
        self.timeout = timeout
        self.working_dir = working_dir

        # Base deny patterns
        base_deny_patterns = [
            r"\brm\s+-[rf]{1,2}\b",          # rm -r, rm -rf, rm -fr
            r"\bdel\s+/[fq]\b",              # del /f, del /q
            r"\brmdir\s+/s\b",               # rmdir /s
            r"\b(format|mkfs|diskpart)\b",   # disk operations
            r"\bdd\s+if=",                   # dd
            r">\s*/dev/sd",                  # write to disk
            r"\b(shutdown|reboot|poweroff)\b",  # system power
            r":\(\)\s*\{.*\};\s*:",          # fork bomb
            # P1-2: Additional security patterns
            r"\b(curl|wget)\s+.*\s+-[oO]\b", # File download (curl -o, wget -O)
            r"\b(pip|npm|yarn|pnpm)\s+install\b",  # Package installation
            r"\bchmod\b|\bchown\b",          # Permission changes
            r"\b(ssh|scp|rsync)\b",          # Remote access
            r"\bcrontab\b",                  # Cron operations
            r"\b(kill|pkill|killall)\b",     # Process termination
            # Anti-spam: block loop + HTTP patterns (DDoS risk)
            r"\bfor\b.*\b(curl|wget)\b",     # for loop + HTTP request
            r"\bwhile\b.*\b(curl|wget)\b",   # while loop + HTTP request
            r"\b(mail|sendmail|mutt)\b",      # Email sending
        ]

        # Merge with custom deny patterns
        self.deny_patterns = deny_patterns or base_deny_patterns
        if additional_deny_patterns:
            self.deny_patterns.extend(additional_deny_patterns)

        self.allow_patterns = allow_patterns or []
        self.restrict_to_workspace = restrict_to_workspace
        self.allowed_dirs = allowed_dirs or []

        # P1-2: Audit log settings
        self.audit_log = audit_log
        self.audit_log_path = Path(audit_log_path).expanduser()

        # Ensure audit log directory exists
        if self.audit_log:
            self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
    
    @property
    def name(self) -> str:
        return "exec"
    
    @property
    def description(self) -> str:
        return "Execute a shell command and return its output. Use with caution."
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute"
                },
                "working_dir": {
                    "type": "string",
                    "description": "Optional working directory for the command"
                }
            },
            "required": ["command"]
        }
    
    async def execute(self, command: str, working_dir: str | None = None, **kwargs: Any) -> str:
        raw_cwd = working_dir or self.working_dir or os.getcwd()
        # Resolve ~ and ensure cwd is within allowed_dirs when restrict_to_workspace is enabled
        cwd = str(Path(raw_cwd).expanduser().resolve())
        if self.restrict_to_workspace and self.allowed_dirs:
            allowed_paths = [Path(d).expanduser().resolve() for d in self.allowed_dirs]
            cwd_path = Path(cwd)
            in_allowed = any(
                cwd_path == ap or ap in cwd_path.parents
                for ap in allowed_paths
            )
            if not in_allowed:
                # Fallback to first allowed dir (workspace)
                cwd = str(allowed_paths[0])
        start_time = time.perf_counter()

        # P1-2: Guard command and prepare audit log
        guard_error = self._guard_command(command, cwd)
        allowed = guard_error is None
        reason = "approve" if allowed else "deny_pattern"

        if guard_error:
            # Log blocked command
            self._write_audit_log(command, cwd, allowed=False, reason=reason, duration_ms=0)
            return guard_error

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                duration_ms = int((time.perf_counter() - start_time) * 1000)
                self._write_audit_log(command, cwd, allowed=True, reason="timeout", duration_ms=duration_ms)
                return f"Error: Command timed out after {self.timeout} seconds"

            output_parts = []

            if stdout:
                output_parts.append(stdout.decode("utf-8", errors="replace"))

            if stderr:
                stderr_text = stderr.decode("utf-8", errors="replace")
                if stderr_text.strip():
                    output_parts.append(f"STDERR:\n{stderr_text}")

            if process.returncode != 0:
                output_parts.append(f"\nExit code: {process.returncode}")

            result = "\n".join(output_parts) if output_parts else "(no output)"

            # Truncate very long output
            max_len = 10000
            if len(result) > max_len:
                result = result[:max_len] + f"\n... (truncated, {len(result) - max_len} more chars)"

            # P1-2: Log successful execution
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            self._write_audit_log(command, cwd, allowed=True, reason="approve", duration_ms=duration_ms)

            return result

        except Exception as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            self._write_audit_log(command, cwd, allowed=True, reason="error", duration_ms=duration_ms)
            return f"Error executing command: {str(e)}"

    def _guard_command(self, command: str, cwd: str) -> str | None:
        """Best-effort safety guard for potentially destructive commands."""
        cmd = command.strip()
        lower = cmd.lower()

        for pattern in self.deny_patterns:
            if re.search(pattern, lower):
                return "Error: Command blocked by safety guard (dangerous pattern detected)"

        if self.allow_patterns:
            if not any(re.search(p, lower) for p in self.allow_patterns):
                return "Error: Command blocked by safety guard (not in allowlist)"

        if self.restrict_to_workspace:
            if "..\\" in cmd or "../" in cmd:
                return "Error: Command blocked by safety guard (path traversal detected)"

            cwd_path = Path(cwd).resolve()

            # P1-3: Allowed directories (expanded paths)
            allowed_paths = [Path(d).expanduser().resolve() for d in self.allowed_dirs]

            win_paths = re.findall(r"[A-Za-z]:\\[^\\\"']+", cmd)
            posix_paths = re.findall(r"(?:~)?/[^\s\"']+", cmd)

            for raw in win_paths + posix_paths:
                try:
                    p = Path(raw).expanduser().resolve()
                except Exception:
                    continue

                # Check if path is within cwd or allowed_dirs
                allowed = (cwd_path in p.parents or p == cwd_path)
                if not allowed:
                    for allowed_path in allowed_paths:
                        if allowed_path in p.parents or p == allowed_path:
                            allowed = True
                            break

                if not allowed:
                    return "Error: Command blocked by safety guard (path outside working dir)"

        return None

    def _write_audit_log(self, command: str, cwd: str, allowed: bool, reason: str, duration_ms: int) -> None:
        """Write audit log entry for command execution."""
        if not self.audit_log:
            return

        try:
            log_entry = {
                "ts": datetime.utcnow().isoformat() + "Z",
                "tool": "exec",
                "command": command,
                "cwd": cwd,
                "allowed": allowed,
                "reason": reason,
                "session": os.environ.get("NYANCOBOT_SESSION", "unknown"),
                "duration_ms": duration_ms,
            }

            with open(self.audit_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")

        except Exception:
            # Silent failure - don't block command execution on log write errors
            pass
