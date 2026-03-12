"""Agent loop: the core processing engine."""

import asyncio
import json
import os
import re
import time
from pathlib import Path
from typing import Any

from loguru import logger

from nyancobot.bus.events import InboundMessage, OutboundMessage
from nyancobot.bus.queue import MessageBus
from nyancobot.providers.base import LLMProvider
from nyancobot.agent.context import ContextBuilder
from nyancobot.agent.tools.registry import ToolRegistry
from nyancobot.agent.tools.filesystem import ReadFileTool, WriteFileTool, EditFileTool, ListDirTool
from nyancobot.agent.tools.shell import ExecTool
from nyancobot.agent.tools.web import WebSearchTool, WebFetchTool
from nyancobot.agent.tools.message import MessageTool
from nyancobot.agent.tools.spawn import SpawnTool
from nyancobot.agent.tools.cron import CronTool
from nyancobot.agent.tools.denrei import DenreiTool
from nyancobot.agent.tools.memory_tool import MemoryTool
from nyancobot.agent.tools.browser import BrowserTool
from nyancobot.agent.tools.youtube_transcript import YouTubeTranscriptTool
from nyancobot.agent.tools.content_repurpose import ContentRepurposeTool
from nyancobot.agent.tools.quality_check import QualityCheckTool
from nyancobot.agent.subagent import SubagentManager
from nyancobot.agent.tool_prompt import parse_tool_calls
from nyancobot.agent.safety.budget import BudgetMeter
from nyancobot.agent.reflector import Reflector, ReflectionConfig
from nyancobot.agent.planner import Planner, Plan, PlanStep
from nyancobot.agent.task_state import TaskStateManager
from nyancobot.agent.evaluator import (
    create_evaluator, ResponseEvaluator, FTDataCollector,
    should_search_by_keywords, EvaluationResult,
)
from nyancobot.agent.multi_perspective import (
    MultiPerspectiveEvaluator, should_suggest_think,
)
from nyancobot.session.manager import SessionManager


# proactive-notify: Proactive notification helper (module-level for asyncio.to_thread compatibility)
def _send_slack_notification(token: str, channel: str, text: str) -> None:
    """Send a notification to Slack via urllib (synchronous, called via to_thread)."""
    import urllib.request as _urllib_request
    import json as _json_notify
    payload = _json_notify.dumps({"channel": channel, "text": text}).encode("utf-8")
    req = _urllib_request.Request(
        "https://slack.com/api/chat.postMessage",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    with _urllib_request.urlopen(req, timeout=5) as resp:
        result = _json_notify.loads(resp.read().decode("utf-8"))
        if not result.get("ok"):
            raise RuntimeError(f"Slack API error: {result.get('error', 'unknown')}")


class AgentLoop:
    """
    The agent loop is the core processing engine.
    
    It:
    1. Receives messages from the bus
    2. Builds context with history, memory, skills
    3. Calls the LLM
    4. Executes tool calls
    5. Sends responses back
    """
    
    def __init__(
        self,
        bus: MessageBus,
        provider: LLMProvider,
        workspace: Path,
        model: str | None = None,
        max_iterations: int = 20,
        brave_api_key: str | None = None,
        exec_config: "ExecToolConfig | None" = None,
        cron_service: "CronService | None" = None,
        restrict_to_workspace: bool = False,
        allowed_dirs: list[str] | None = None,  # P1-3: Pass allowed_dirs from config
        compaction_config: "CompactionConfig | None" = None,  # P2-2: Compaction config
        policy_config: dict | None = None,  # P1-1: ToolPolicy config
        task_board_config: dict | None = None,  # task-board: TaskBoard config
        slack_token: str | None = None,  # task-board: Slack token for TaskBoard
        safety_config: "SafetyConfig | None" = None,  # safety-valve: Safety valve config
        reflection_config: dict | None = None,  # reflector: Reflection config
        planner_config: dict | None = None,  # plan-execute: Plan-and-Execute config
        tiered_memory_config: dict | None = None,  # tiered-memory: Tiered Memory config
        rag_config: dict | None = None,  # rag-pipeline: RAG Pipeline config
        a2a_config: dict | None = None,  # a2a-protocol: A2A Protocol config
        evaluator_config: dict | None = None,  # v0.3.0: Evaluator pipeline config
    ):
        from nyancobot.config.schema import ExecToolConfig, SafetyConfig
        from nyancobot.cron.service import CronService
        from nyancobot.session.compaction import Compaction, CompactionConfig
        # safety-valve: Safety valve initialization
        self._safety = safety_config or SafetyConfig()
        self._budget = BudgetMeter(
            max_tokens=self._safety.budget.max_tokens_per_session,
            warn_at_percent=self._safety.budget.warn_at_percent,
        )
        self.bus = bus
        self.provider = provider
        self.workspace = workspace
        self.model = model or provider.get_default_model()
        self.max_iterations = max_iterations
        self.brave_api_key = brave_api_key
        self.exec_config = exec_config or ExecToolConfig()
        self.cron_service = cron_service
        self.restrict_to_workspace = restrict_to_workspace
        self.allowed_dirs = allowed_dirs or []  # P1-3: Store allowed_dirs

        self.context = ContextBuilder(workspace)
        self.skills = self.context.skills  # NYANCOBOT-MOD: skills loader reference for model lookup
        self.sessions = SessionManager(workspace)
        self.tools = ToolRegistry()
        # P1-3: pass allowed_dirs to SubagentManager
        self.subagents = SubagentManager(
            provider=provider,
            workspace=workspace,
            bus=bus,
            model=self.model,
            brave_api_key=brave_api_key,
            exec_config=self.exec_config,
            restrict_to_workspace=restrict_to_workspace,
            allowed_dirs=self.allowed_dirs,
        )

        # P2-2: Initialize compaction service
        self.compaction = Compaction(
            config=compaction_config or CompactionConfig(),
            provider=provider,
        )

        self._policy_config = policy_config  # P1-1: Store for _register_default_tools
        self._task_board_config = task_board_config  # task-board: TaskBoard config
        self._slack_token = slack_token  # task-board: Slack token

        # reflector: Initialize Reflector
        if reflection_config and reflection_config.get("enabled", False):
            self.reflector = Reflector(
                config=ReflectionConfig(
                    enabled=reflection_config.get("enabled", False),
                    max_reflections=reflection_config.get("max_reflections", 3),
                    threshold=reflection_config.get("threshold", 3.5),
                    auto_enable=reflection_config.get("auto_enable", False),
                    keywords=reflection_config.get("keywords", []),
                ),
                llm_provider=provider,
            )
            logger.info("Reflector enabled: threshold=%.2f, max_reflections=%d",
                       self.reflector.config.threshold,
                       self.reflector.config.max_reflections)
        else:
            self.reflector = None

        # plan-execute: Plan-and-Execute initialization
        self._planner_config = planner_config or {}
        if self._planner_config.get("enabled", False):
            self._planner = Planner(
                provider=provider,
                model=model or provider.get_default_model(),
                max_steps=self._planner_config.get("max_steps", 10),
            )
            self._task_state_mgr = TaskStateManager(bus=bus)
            logger.info("Planner enabled: auto_detect=%s, max_steps=%d",
                       self._planner_config.get("auto_detect", True),
                       self._planner_config.get("max_steps", 10))
        else:
            self._planner = None
            self._task_state_mgr = None

        # rag-pipeline: RAG Pipeline initialization
        self._rag_config = rag_config or {}
        self._rag_pipeline = None

        # tiered-memory: Tiered Memory initialization
        self._tiered_memory_config = tiered_memory_config or {}
        self._tiered_memory = None
        if self._tiered_memory_config.get("enabled", False):
            from nyancobot.agent.memory.tiered import TieredMemoryManager
            self._tiered_memory = TieredMemoryManager(
                workspace=workspace,
                db_path=self._tiered_memory_config.get("archival_db_path", "~/.nyancobot/archival.db"),
                core_max_chars=self._tiered_memory_config.get("core_max_chars", 4000),
                auto_archive_on_exit=self._tiered_memory_config.get("auto_archive_on_exit", True),
            )
            logger.info(
                "TieredMemory enabled: core=%d/%d, archival=%d entries, recall=%d messages",
                self._tiered_memory.core.size,
                self._tiered_memory.core.max_chars,
                self._tiered_memory.archival.count(),
                self._tiered_memory.recall.count(),
            )

        # rag-pipeline: RAG Pipeline initialization (requires TieredMemory/ArchivalMemory)
        if self._rag_config.get("enabled", False):
            archival_for_rag = None
            if self._tiered_memory:
                archival_for_rag = self._tiered_memory.archival
            else:
                # Create a standalone ArchivalMemory if TieredMemory is not enabled
                from nyancobot.agent.memory.archival import ArchivalMemory
                _rag_db = self._tiered_memory_config.get("archival_db_path", "~/.nyancobot/archival.db")
                archival_for_rag = ArchivalMemory(db_path=_rag_db)

            from nyancobot.agent.rag.pipeline import RAGPipeline
            self._rag_pipeline = RAGPipeline(
                archival=archival_for_rag,
                chunk_size=self._rag_config.get("chunk_size", 500),
                chunk_overlap=self._rag_config.get("chunk_overlap", 50),
                top_k=self._rag_config.get("top_k", 5),
            )
            logger.info(
                "RAG Pipeline enabled: chunk_size=%d, overlap=%d, top_k=%d",
                self._rag_config.get("chunk_size", 500),
                self._rag_config.get("chunk_overlap", 50),
                self._rag_config.get("top_k", 5),
            )

            # Auto-ingest directories if configured
            for d in self._rag_config.get("auto_ingest_dirs", []):
                try:
                    result = self._rag_pipeline.ingest(d)
                    logger.info(f"RAG auto-ingest: {d} -> {result.get('total_chunks', result.get('chunks', 0))} chunks")
                except Exception as e:
                    logger.error(f"RAG auto-ingest failed for {d}: {e}")

        # a2a-protocol: A2A Protocol initialization
        self._a2a_config = a2a_config or {}
        self._a2a_registry = None
        if self._a2a_config.get("enabled", False):
            from nyancobot.agent.a2a.registry import TaskRegistry
            from nyancobot.agent.a2a.webhook import WebhookNotifier
            webhook = WebhookNotifier(
                webhook_url=self._a2a_config.get("webhook_url", ""),
            )
            self._a2a_registry = TaskRegistry(
                db_path=self._a2a_config.get("task_db_path", "~/.nyancobot/tasks.db"),
                webhook_notifier=webhook if webhook.enabled else None,
            )
            logger.info("A2A Protocol enabled: db=%s, webhook=%s",
                        self._a2a_config.get("task_db_path", "~/.nyancobot/tasks.db"),
                        "on" if webhook.enabled else "off")

        # v0.3.0: Evaluator pipeline initialization
        # Auto-load evaluator config from config.json if not explicitly passed
        if not evaluator_config:
            try:
                _cfg_path = Path(os.path.expanduser("~/.nyancobot/config.json"))
                if _cfg_path.exists():
                    with open(_cfg_path) as _f:
                        _raw_cfg = json.load(_f)
                    evaluator_config = _raw_cfg.get("evaluator", {})
            except Exception as _e:
                logger.warning(f"Failed to load evaluator config from config.json: {_e}")
        self._evaluator_config = evaluator_config or {}
        self._evaluator: ResponseEvaluator | None = None
        self._ft_collector: FTDataCollector | None = None
        self._multi_perspective: MultiPerspectiveEvaluator | None = None
        if self._evaluator_config.get("enabled", False):
            self._evaluator = create_evaluator(self._evaluator_config)
            self._ft_collector = FTDataCollector()
            if self._evaluator:
                logger.info(
                    "Evaluator enabled: type=%s, threshold=%d",
                    self._evaluator_config.get("type", "none"),
                    self._evaluator_config.get("threshold", 3),
                )
        # /think multi-perspective (always init if api_keys present)
        if self._evaluator_config.get("api_keys"):
            self._multi_perspective = MultiPerspectiveEvaluator(self._evaluator_config)
            logger.info("MultiPerspective evaluator initialized")

        self._running = False
        self._last_notification_time: float = 0.0  # proactive-notify: proactive notification throttle
        self._register_default_tools()
    
    def _register_default_tools(self) -> None:
        """Register the default set of tools."""
        # File tools (restrict to workspace if configured)
        allowed_dir = self.workspace if self.restrict_to_workspace else None
        extra_dirs = [Path(d).expanduser().resolve() for d in self.allowed_dirs] if self.allowed_dirs else None
        self.tools.register(ReadFileTool(allowed_dir=allowed_dir, allowed_dirs=extra_dirs))
        self.tools.register(WriteFileTool(allowed_dir=allowed_dir, allowed_dirs=extra_dirs))
        self.tools.register(EditFileTool(allowed_dir=allowed_dir, allowed_dirs=extra_dirs))
        self.tools.register(ListDirTool(allowed_dir=allowed_dir, allowed_dirs=extra_dirs))
        
        # Shell tool (P1-2, P1-3: enhanced with audit log and allowed_dirs)
        self.tools.register(ExecTool(
            working_dir=str(self.workspace),
            timeout=self.exec_config.timeout,
            restrict_to_workspace=self.restrict_to_workspace,
            allowed_dirs=self.allowed_dirs,
            audit_log=self.exec_config.audit_log,
            audit_log_path=self.exec_config.audit_log_path,
            additional_deny_patterns=self.exec_config.additional_deny_patterns,
        ))
        
        # Web tools
        self.tools.register(WebSearchTool(api_key=self.brave_api_key))
        self.tools.register(WebFetchTool())
        
        # Message tool
        message_tool = MessageTool(send_callback=self.bus.publish_outbound)
        self.tools.register(message_tool)
        
        # Spawn tool (for subagents)
        spawn_tool = SpawnTool(manager=self.subagents)
        self.tools.register(spawn_tool)
        
        # Cron tool (for scheduling)
        if self.cron_service:
            self.tools.register(CronTool(self.cron_service))

        # Messenger tool (send messages to leader agents)
        self.tools.register(DenreiTool())

        # Memory tool (persistent learning via MEMORY.md)
        self.tools.register(MemoryTool())

        # Browser tool (Playwright headless Chromium)
        self.tools.register(BrowserTool())

        # YouTube transcript tool (youtube-transcript-api)
        self.tools.register(YouTubeTranscriptTool())
        logger.info("YouTubeTranscriptTool registered")

        # Content Repurpose tool (NoimosAI Social Agent equivalent)
        self.tools.register(ContentRepurposeTool())
        logger.info("ContentRepurposeTool registered")

        # Quality Check tool (pre-publication validation)
        self.tools.register(QualityCheckTool())
        logger.info("QualityCheckTool registered")

        # Vector Memory tools (chromadb + nomic-embed-text)
        try:
            from nyancobot.agent.tools.vector_memory_tools import get_vector_memory_tools
            for tool in get_vector_memory_tools():
                self.tools.register(tool)
            logger.info("VectorMemory: 2 tools registered (memory_store, memory_search)")
        except Exception as e:
            logger.warning(f"VectorMemory tools not available: {e}")

        # tiered-memory: Tiered Memory tools (6 tools)
        if self._tiered_memory:
            from nyancobot.agent.tools.tiered_memory_tools import get_tiered_memory_tools
            for tool in get_tiered_memory_tools(self._tiered_memory):
                self.tools.register(tool)
            logger.info("TieredMemory: 6 tools registered")

        # rag-pipeline: RAG tools (3 tools)
        if self._rag_pipeline:
            from nyancobot.agent.tools.rag_tools import get_rag_tools
            for tool in get_rag_tools(self._rag_pipeline):
                self.tools.register(tool)
            logger.info("RAG Pipeline: 3 tools registered")

        # a2a-protocol: A2A Protocol tools (4 tools)
        if self._a2a_registry:
            from nyancobot.agent.tools.a2a_tools import get_a2a_tools
            for tool in get_a2a_tools(self._a2a_registry):
                self.tools.register(tool)
            logger.info("A2A Protocol: 4 tools registered")

        # P1-1: ToolPolicy integration (default off = no restrictions)
        if self._policy_config:
            from nyancobot.agent.tools.policy import ToolPolicy
            self.tools.policy = ToolPolicy(self._policy_config)
            logger.info("ToolPolicy enabled: mode=%s", self._policy_config.get("mode", "off"))

        # task-board: TaskBoard tool integration (default off)
        if self._task_board_config and self._task_board_config.get("enabled", False):
            try:
                from nyancobot.agent.task_board import TaskBoard
                from nyancobot.agent.tools.task_board_tool import TaskBoardTool

                # Initialize TaskBoard with Slack token and config
                task_board = TaskBoard(
                    slack_token=self._slack_token,
                    config=self._task_board_config
                )
                self.tools.register(TaskBoardTool(task_board))
                logger.info("TaskBoard tool enabled")
            except ImportError as e:
                logger.warning(f"TaskBoard not available: {e}")
    
    async def run(self) -> None:
        """Run the agent loop, processing messages from the bus."""
        self._running = True
        logger.info("Agent loop started")
        
        while self._running:
            try:
                # Wait for next message
                msg = await asyncio.wait_for(
                    self.bus.consume_inbound(),
                    timeout=1.0
                )
                
                # Process it
                try:
                    response = await self._process_message(msg)
                    if response:
                        await self.bus.publish_outbound(response)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    # Send error response
                    await self.bus.publish_outbound(OutboundMessage(
                        channel=msg.channel,
                        chat_id=msg.chat_id,
                        content=f"Sorry, I encountered an error: {str(e)}"
                    ))
            except asyncio.TimeoutError:
                continue
    
    def stop(self) -> None:
        """Stop the agent loop."""
        self._running = False
        logger.info("Agent loop stopping")
    
    async def _process_message(self, msg: InboundMessage, model_override: str | None = None) -> OutboundMessage | None:  # NYANCOBOT-MOD: model_override param
        """
        Process a single inbound message.

        Args:
            msg: The inbound message to process.
            model_override: Optional model override (e.g. from cron payload or skill).

        Returns:
            The response message, or None if no response needed.
        """
        # Handle system messages (subagent announces)
        # The chat_id contains the original "channel:chat_id" to route back to
        if msg.channel == "system":
            return await self._process_system_message(msg)
        
        preview = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
        logger.info(f"Processing message from {msg.channel}:{msg.sender_id}: {preview}")
        _msg_start_time = time.time()  # proactive-notify: track processing start time

        # Determine message_type for outbound routing
        # DMs or notification channel → user_response (routes to notification)
        # Everything else → log (routes to log channel)
        import os as _os
        _notification_ch = _os.environ.get("NYANCOBOT_NOTIFICATION_CHANNEL", "")
        if not _notification_ch:
            import json as _json2
            try:
                with open(_os.path.expanduser("~/.nyancobot/config.json")) as f:
                    _cfg2 = _json2.load(f)
                _notification_ch = _cfg2.get("channels", {}).get("slack", {}).get("channel_routing", {}).get("notification_channel", "")
            except Exception:
                pass
        if msg.chat_id.startswith("D") or (_notification_ch and msg.chat_id == _notification_ch):
            _outbound_message_type = "user_response"
        else:
            _outbound_message_type = "log"
        
        # Get or create session
        session = self.sessions.get_or_create(msg.session_key)
        
        # Update tool contexts
        message_tool = self.tools.get("message")
        if isinstance(message_tool, MessageTool):
            message_tool.set_context(msg.channel, msg.chat_id)
        
        spawn_tool = self.tools.get("spawn")
        if isinstance(spawn_tool, SpawnTool):
            spawn_tool.set_context(msg.channel, msg.chat_id)
        
        cron_tool = self.tools.get("cron")
        if isinstance(cron_tool, CronTool):
            cron_tool.set_context(msg.channel, msg.chat_id)
        
        # === Pre-LLM: 2-step denrei (案B) ===
        # Step 2: User approves sending with "OK/発令/送れ/許可" etc.
        # -> Send the PREVIOUS assistant message directly via denrei, skip LLM entirely.
        user_msg_stripped = re.sub(r'<@[A-Z0-9]+>\s*', '', msg.content).strip()
        user_msg_lower = user_msg_stripped.lower()
        _send_commands = [
            "発令せよ", "発令して", "発令しろ", "発令せい", "発令",
            "送れ", "送信せよ", "送信して", "送信しろ",
            "send message", "send it", "notify", "send",
            "許可する", "ok", "おk", "よし",
            "それで送れ", "それでよい", "それで良い", "それを送れ",
            "加えて発令", "発令じゃ",
        ]
        is_send_command = any(user_msg_lower.startswith(cmd) or user_msg_lower == cmd
                             for cmd in _send_commands)
        # Also match "加えて発令" anywhere in the message
        if not is_send_command:
            is_send_command = any(kw in user_msg_lower for kw in [
                "加えて発令", "発令せい", "発令せよ", "発令じゃ",
            ])

        if is_send_command:
            # Find the last non-empty assistant message from session history
            prev_msgs = [m for m in session.messages if m.get("role") == "assistant"]
            if prev_msgs:
                last_assistant = prev_msgs[-1].get("content", "")
                if last_assistant and len(last_assistant) > 10:
                    # Determine target
                    target = "1"
                    if any(kw in user_msg_lower for kw in ["leader", "leader", "team"]):
                        target = "2"
                    # If user added extra instructions, append them
                    extra = user_msg_stripped
                    for cmd in _send_commands:
                        extra = extra.replace(cmd, "").strip()
                    if extra and len(extra) > 3:
                        last_assistant = f"{last_assistant}\n\n【追記】{extra}"

                    logger.info(f"Denrei 2-step: sending prev assistant msg ({len(last_assistant)} chars) to target={target}")
                    denrei_tool = self.tools.get("denrei")
                    if denrei_tool:
                        result = await denrei_tool.execute(target=target, message=last_assistant)
                        logger.info(f"Denrei 2-step result: {result[:120]}")
                        # Save to session and return directly (skip LLM)
                        session.add_message("user", msg.content)
                        session.add_message("assistant", result)
                        self.sessions.save(session)
                        return OutboundMessage(
                            channel=msg.channel,
                            chat_id=msg.chat_id,
                            content=result,
                            reply_to=msg,
                            message_type=_outbound_message_type,
                        )
            # If no previous message found, fall through to LLM
            logger.warning("Denrei 2-step: no previous assistant message found, falling through to LLM")

        # === Pre-LLM: browser auto-dispatch ===
        # Detect "open URL" patterns and call browser tool directly (LLM bypass)
        import re as _re_mod
        # URL pattern: ASCII chars only (letters, digits, and URL-safe punctuation)
        _URL_PAT = r'(https?://[A-Za-z0-9\-._~:/?#\[\]@!$&\'()*+,;=%]+)'
        _url_open_match = _re_mod.search(
            r'(?:browser(?:ツール)?(?:で|の)?|ブラウザで|開いて|開け|アクセスして|確認して)\s*'
            + _URL_PAT,
            user_msg_stripped,
        )
        if not _url_open_match:
            # Also match "URL を開いて/確認して" pattern
            _url_open_match = _re_mod.search(
                _URL_PAT + r'\s*(?:を|を\s*)?(?:開いて|開け|確認して|アクセスして|見て|調べて|読んで)',
                user_msg_stripped,
            )
        if _url_open_match:
            _target_url = _url_open_match.group(1).rstrip('。、）)')
            logger.info(f"Browser auto-dispatch: opening {_target_url}")
            _browser_tool = self.tools.get("browser")
            if _browser_tool:
                _browser_result = await _browser_tool.execute(action="open", url=_target_url)
                # Truncate for response
                if len(_browser_result) > 3000:
                    _browser_result = _browser_result[:3000] + "\n...(以下省略)"
                _response_text = f"【nyancobot】承知つかまつった。{_target_url} を開いた結果でござる:\n\n{_browser_result}"
                session.add_message("user", msg.content)
                session.add_message("assistant", _response_text)
                self.sessions.save(session)
                return OutboundMessage(
                    channel=msg.channel,
                    chat_id=msg.chat_id,
                    content=_response_text,
                    reply_to=msg,
                    message_type=_outbound_message_type,
                )

        # === Pre-LLM: /think multi-perspective evaluation ===
        if self._multi_perspective and user_msg_stripped.startswith("/think"):
            _think_idea = user_msg_stripped[len("/think"):].strip()
            if _think_idea:
                logger.info(f"/think command: evaluating idea ({len(_think_idea)} chars)")
                try:
                    _think_result = await self._multi_perspective.evaluate(_think_idea)
                except Exception as e:
                    _think_result = f"多角評価中にエラーが発生しました: {e}"
                session.add_message("user", msg.content)
                session.add_message("assistant", _think_result)
                self.sessions.save(session)
                return OutboundMessage(
                    channel=msg.channel,
                    chat_id=msg.chat_id,
                    content=_think_result,
                    reply_to=msg,
                    message_type=_outbound_message_type,
                )

        # Get tool definitions for native tool calling (OpenAI tools param)
        tool_defs = self.tools.get_definitions()
        logger.info(f"Tool definitions count: {len(tool_defs)}, names: {[t['function']['name'] for t in tool_defs]}")

        # Build initial messages (use get_history for LLM-formatted messages)
        # NOTE: Do NOT pass tool_definitions to build_messages when using native tool calling.
        # Passing them causes tools to be embedded TWICE: once in the system prompt (text-based)
        # and once in the LLM API tools param (native). This confuses the model.
        messages = self.context.build_messages(
            history=session.get_history(),
            current_message=msg.content,
            media=msg.media if msg.media else None,
            channel=msg.channel,
            chat_id=msg.chat_id,
            tool_definitions=None,
        )

        # tiered-memory: Inject core memory into system prompt
        if self._tiered_memory and messages and messages[0].get("role") == "system":
            core_ctx = self._tiered_memory.get_core_context()
            if core_ctx:
                messages[0]["content"] += f"\n\n# Core Memory\n{core_ctx}"

        # rag-pipeline: RAG context augmentation - inject relevant chunks
        if self._rag_pipeline and messages and messages[0].get("role") == "system":
            try:
                rag_ctx = self._rag_pipeline.augment_context(msg.content)
                if rag_ctx:
                    messages[0]["content"] += f"\n\n# Retrieved Context\n{rag_ctx}"
            except Exception as e:
                logger.error(f"RAG context augmentation failed: {e}")

        # NYANCOBOT-MOD: determine effective model (override > skill > default)
        effective_model = model_override or self.skills.get_active_model() or self.model

        # plan-execute: Plan-and-Execute check
        if (self._planner and
                Planner.should_use_plan_mode(msg.content, self._planner_config)):
            logger.info("Plan mode activated for message (%d chars)", len(msg.content))
            plan_result = await self._execute_with_plan(
                msg=msg,
                messages=messages,
                tool_defs=tool_defs,
                effective_model=effective_model,
                session=session,
                outbound_message_type=_outbound_message_type,
            )
            if plan_result is not None:
                return plan_result
            # If plan execution returned None (e.g. plan generation failed),
            # fall through to normal agent loop
            logger.warning("Plan execution returned None, falling through to normal loop")

        # Agent loop
        iteration = 0
        final_content = None
        _tool_call_history: list[str] = []  # Track tool calls to detect loops
        _TOOL_LOOP_THRESHOLD = 2  # Max times same tool+args can repeat
        # Anti-loop: denrei per-session limit
        _denrei_session_count: int = 0
        _MAX_DENREI_PER_SESSION = 3  # denrei max calls per single message session
        # Anti-loop: message per-session limit (prevent Qwen hallucination spam)
        _message_session_count: int = 0
        _MAX_MESSAGE_PER_SESSION = 3  # message max calls per single message session
        # Anti-loop: global external-action limit (message, denrei, spawn, task_board, cron)
        _EXTERNAL_TOOLS = {"message", "denrei", "spawn", "task_board", "cron", "content_repurpose"}
        _external_action_count: int = 0
        _MAX_EXTERNAL_PER_SESSION = 5  # total external actions across all tools
        # safety-valve: Safety valve state
        _tool_call_count: int = 0  # Explicit tool call counter
        _max_tool_iters = self._safety.max_tool_iterations if self._safety.enabled else self.max_iterations * 100
        _burst_timestamps: dict[str, list[float]] = {}  # tool_name -> [timestamps]
        _safety_enabled = self._safety.enabled

        while iteration < self.max_iterations:
            iteration += 1

            # Call LLM (pass tools for native tool_use; also embedded in prompt as fallback)
            response = await self.provider.chat(
                messages=messages,
                tools=tool_defs,
                model=effective_model  # NYANCOBOT-MOD: use effective model
            )

            # safety-valve: Record token usage in budget meter
            if _safety_enabled and response.usage:
                self._budget.record(response.usage)
                if self._budget.should_warn:
                    logger.warning(
                        f"BUDGET WARNING: {self._budget.usage_percent:.0f}% of token budget used "
                        f"({self._budget.total_tokens}/{self._budget.max_tokens})"
                    )
                if self._budget.exceeded:
                    logger.error(
                        f"BUDGET EXCEEDED: {self._budget.total_tokens}/{self._budget.max_tokens} tokens. "
                        f"Stopping agent loop."
                    )
                    final_content = (
                        f"⚠️ トークン予算超過: {self._budget.total_tokens:,}/{self._budget.max_tokens:,}トークン消費。"
                        f"セッションを停止しました。"
                    )
                    break

            # Check for empty response from codex-proxy and retry once
            if response.content and response.content.strip() == "(empty response from codex)":
                logger.warning("Empty response from codex, retrying once...")
                # Find the last user message and append retry notice
                for i in range(len(messages) - 1, -1, -1):
                    if messages[i].get("role") == "user":
                        messages[i]["content"] += "（※前回応答が空。必ず応答を返せ）"
                        break
                # Retry once
                response = await self.provider.chat(
                    messages=messages,
                    tools=tool_defs,
                    model=effective_model
                )
                logger.info(f"Retry response length: {len(response.content or '')}")

            # Handle native tool calls (OpenAI tool_use API)
            if response.has_tool_calls:
                # Add assistant message with tool calls
                tool_call_dicts = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)  # Must be JSON string
                        }
                    }
                    for tc in response.tool_calls
                ]
                messages = self.context.add_assistant_message(
                    messages, response.content, tool_call_dicts
                )

                # Execute tools (with loop detection + safety valves)
                for tool_call in response.tool_calls:
                    # safety-valve: Check max_tool_iterations
                    _tool_call_count += 1
                    if _safety_enabled and _tool_call_count > _max_tool_iters:
                        logger.error(
                            f"MAX TOOL ITERATIONS ({_max_tool_iters}) exceeded. "
                            f"Total tool calls: {_tool_call_count}. Stopping."
                        )
                        final_content = (
                            f"⚠️ ツール呼び出し上限({_max_tool_iters}回)に到達。"
                            f"安全のため停止しました。（合計{_tool_call_count}回）"
                        )
                        break

                    # ── denrei per-session limit ──
                    if tool_call.name == "denrei":
                        _denrei_session_count += 1
                        if _denrei_session_count > _MAX_DENREI_PER_SESSION:
                            logger.error(
                                f"DENREI SAFETY: {_denrei_session_count} calls in session "
                                f"(limit={_MAX_DENREI_PER_SESSION}). Blocking."
                            )
                            result = (
                                f"⚠️ Messenger consecutive call limit ({_MAX_DENREI_PER_SESSION} times/session) reached. "
                                f"Respond to user via text."
                            )
                            messages = self.context.add_tool_result(
                                messages, tool_call.id, tool_call.name, result
                            )
                            continue

                    # ── message per-session limit (prevent Qwen hallucination spam) ──
                    if tool_call.name == "message":
                        _message_session_count += 1
                        if _message_session_count > _MAX_MESSAGE_PER_SESSION:
                            logger.error(
                                f"MESSAGE SAFETY: {_message_session_count} calls in session "
                                f"(limit={_MAX_MESSAGE_PER_SESSION}). Blocking."
                            )
                            result = (
                                f"⚠️ message連続呼び出し上限({_MAX_MESSAGE_PER_SESSION}回/セッション)に到達。"
                                f"これ以上のメッセージ送信は不要。テキストで完了報告せよ。"
                            )
                            messages = self.context.add_tool_result(
                                messages, tool_call.id, tool_call.name, result
                            )
                            continue

                    # ── global external-action limit ──
                    if tool_call.name in _EXTERNAL_TOOLS:
                        _external_action_count += 1
                        if _external_action_count > _MAX_EXTERNAL_PER_SESSION:
                            logger.error(
                                f"EXTERNAL SAFETY: {tool_call.name} blocked. "
                                f"Total external calls={_external_action_count} "
                                f"(limit={_MAX_EXTERNAL_PER_SESSION})."
                            )
                            result = (
                                f"⚠️ 外部送信ツールの合計呼び出し上限({_MAX_EXTERNAL_PER_SESSION}回/セッション)に到達。"
                                f"これ以上の外部操作は不可。テキストで応答せよ。"
                            )
                            messages = self.context.add_tool_result(
                                messages, tool_call.id, tool_call.name, result
                            )
                            continue

                    args_str = json.dumps(tool_call.arguments, ensure_ascii=False)
                    call_sig = f"{tool_call.name}:{args_str[:300]}"
                    dup_count = _tool_call_history.count(call_sig)

                    if dup_count >= _TOOL_LOOP_THRESHOLD:
                        logger.error(
                            f"TOOL LOOP DETECTED: {tool_call.name} called {dup_count + 1} times "
                            f"with same args. Breaking loop."
                        )
                        result = (
                            f"⚠️ ループ検知: {tool_call.name}を同一引数で{dup_count + 1}回呼び出し。"
                            f"これ以上の繰り返しは禁止。ユーザーにテキストで応答せよ。"
                        )
                        messages = self.context.add_tool_result(
                            messages, tool_call.id, tool_call.name, result
                        )
                        continue

                    # safety-valve: Burst detection (same tool, many calls in short window)
                    if _safety_enabled and self._safety.loop_detection:
                        now = time.monotonic()
                        if tool_call.name not in _burst_timestamps:
                            _burst_timestamps[tool_call.name] = []
                        ts_list = _burst_timestamps[tool_call.name]
                        ts_list.append(now)
                        # Prune timestamps outside the window
                        window = self._safety.burst_window_seconds
                        ts_list[:] = [t for t in ts_list if now - t <= window]
                        if len(ts_list) >= self._safety.burst_threshold:
                            logger.error(
                                f"BURST DETECTED: {tool_call.name} called {len(ts_list)} times "
                                f"within {window}s. Breaking."
                            )
                            result = (
                                f"⚠️ バースト検知: {tool_call.name}が{window}秒以内に"
                                f"{len(ts_list)}回呼び出されました。停止します。"
                            )
                            messages = self.context.add_tool_result(
                                messages, tool_call.id, tool_call.name, result
                            )
                            continue

                    _tool_call_history.append(call_sig)
                    logger.info(f"Tool call: {tool_call.name}({args_str[:200]})")
                    result = await self.tools.execute(tool_call.name, tool_call.arguments)
                    messages = self.context.add_tool_result(
                        messages, tool_call.id, tool_call.name, result
                    )

                # safety-valve: Break outer loop if max_tool_iterations exceeded
                if _safety_enabled and _tool_call_count > _max_tool_iters:
                    break
            else:
                # Check for text-based tool calls (<tool_call> blocks in response text)
                raw_content = response.content or ""
                logger.info(f"LLM FULL response ({len(raw_content)} chars): {repr(raw_content[:1000])}")
                has_tag = "<tool_call>" in raw_content
                logger.info(f"Text tool call check: has_tag={has_tag}, content_len={len(raw_content)}")
                clean_text, text_tool_calls = parse_tool_calls(raw_content)

                if text_tool_calls:
                    # Execute text-based tool calls
                    tool_results = []
                    for tc in text_tool_calls:
                        args_str = json.dumps(tc["arguments"], ensure_ascii=False)
                        logger.info(f"Text tool call: {tc['name']}({args_str[:200]})")
                        result = await self.tools.execute(tc["name"], tc["arguments"])
                        tool_results.append(f"[{tc['name']}] {result}")

                    # Add assistant message + tool results as user message for next iteration
                    messages.append({"role": "assistant", "content": response.content})
                    results_text = "\n\n".join(tool_results)
                    messages.append({
                        "role": "user",
                        "content": f"Tool results:\n\n{results_text}\n\nPlease continue your response based on the tool results above."
                    })
                    # Continue loop for LLM to process results
                else:
                    # No tool calls. LLM response as-is.
                    final_content = response.content
                    break
        
        if final_content is None:
            final_content = "I've completed processing but have no response to give."

        # reflector: Apply reflection if enabled
        reflection_metadata = None
        if self.reflector and final_content:
            try:
                final_content, reflection_metadata = await self.reflector.reflect(
                    initial_response=final_content,
                    user_message=msg.content,
                    context_messages=messages,
                    model=effective_model,
                )
                if reflection_metadata and reflection_metadata.get("reflections_performed", 0) > 0:
                    logger.info(
                        f"Reflection applied: {reflection_metadata['reflections_performed']} iterations, "
                        f"score {reflection_metadata['initial_score']:.2f} → {reflection_metadata['final_score']:.2f}"
                    )
            except Exception as e:
                logger.error(f"Reflection failed: {e}")

        # v0.3.0: Evaluator pipeline (post-reflector)
        if final_content and self._evaluator:
            try:
                _eval_threshold = self._evaluator_config.get("threshold", 3)
                _keyword_search = should_search_by_keywords(msg.content)
                _eval_result: EvaluationResult | None = None

                if _keyword_search:
                    # Keywords suggest fresh data needed - search immediately
                    logger.info("Evaluator: keyword-triggered search for question")
                    _eval_result = EvaluationResult(
                        score=2, needs_search=True,
                        search_queries=[msg.content[:100]],
                        evaluator_type="keyword",
                    )
                else:
                    _eval_result = await self._evaluator.evaluate(msg.content, final_content)
                    logger.info(
                        f"Evaluator: score={_eval_result.score}, needs_search={_eval_result.needs_search}, "
                        f"type={_eval_result.evaluator_type}"
                    )

                # If low score or search needed, augment with web search
                _search_text = None
                if _eval_result and (_eval_result.score <= _eval_threshold or _eval_result.needs_search):
                    _search_queries = _eval_result.search_queries or [msg.content[:100]]
                    _search_results_parts = []
                    _web_search_tool = self.tools.get("web_search")
                    if _web_search_tool:
                        for sq in _search_queries[:2]:  # max 2 queries
                            try:
                                sr = await _web_search_tool.execute(query=sq, count=3)
                                _search_results_parts.append(sr)
                            except Exception as se:
                                logger.warning(f"Evaluator search failed for '{sq}': {se}")
                    _search_text = "\n".join(_search_results_parts) if _search_results_parts else None

                    if _search_text:
                        # Re-generate with search context
                        _augmented_messages = list(messages)
                        _augmented_messages.append({
                            "role": "user",
                            "content": (
                                f"前回の回答に事実誤認の可能性があります。以下の最新情報を踏まえて回答を改善してください:\n\n"
                                f"## 検索結果\n{_search_text}\n\n"
                                f"## 元の質問\n{msg.content}\n\n"
                                f"改善した回答のみを出力してください。"
                            ),
                        })
                        _regen_response = await self.provider.chat(
                            messages=_augmented_messages,
                            model=effective_model,
                        )
                        if _regen_response.content:
                            final_content = _regen_response.content
                            logger.info("Evaluator: regenerated response with search augmentation")

                # Save FT data
                if self._ft_collector and _eval_result:
                    self._ft_collector.save(
                        question=msg.content,
                        initial_answer=final_content,
                        evaluation=_eval_result,
                        search_results=_search_text,
                        final_answer=final_content,
                        model=effective_model,
                    )
            except Exception as e:
                logger.error(f"Evaluator pipeline failed (non-fatal): {e}")

        # v0.3.0: /think suggestion (if suggest_think enabled)
        if (final_content and self._multi_perspective
                and self._evaluator_config.get("suggest_think", False)
                and should_suggest_think(msg.content)):
            final_content += "\n\n💡 多角評価しますか？ `/think` で実行できます"

        # Log response preview
        preview = final_content[:120] + "..." if len(final_content) > 120 else final_content
        logger.info(f"Response to {msg.channel}:{msg.sender_id}: {preview}")

        # Save to session (skip error responses to prevent history bloat cascade)
        _is_error = final_content.startswith("Error: All LLM providers failed")
        if _is_error:
            # Error cascade prevention: don't save error to history
            # Also auto-reset session if too large (compaction can't help when LLM is down)
            estimated_chars = sum(len(m.get("content", "")) for m in session.messages)
            if estimated_chars > 16000:  # ~4000 tokens
                logger.warning(
                    f"Session {session.key}: auto-reset due to LLM failure + large history "
                    f"({estimated_chars} chars). Clearing to prevent cascade."
                )
                session.messages = []
                self.sessions.save(session)
            # Notify user with a friendlier message
            final_content = "申し訳ござらぬ、只今応答に時間がかかりすぎたでござる。もう一度お声がけくだされ。"
        else:
            session.add_message("user", msg.content)
            session.add_message("assistant", final_content)

            # Limit session messages to 20 (keep first 2 as initial context)
            self._limit_session_messages(session)

            # P2-2: Check and perform compaction if needed
            await self.compaction.check_and_compact(session)

            # tiered-memory: Archive session messages to recall memory
            if self._tiered_memory:
                try:
                    self._tiered_memory.archive_session(
                        session_id=session.key,
                        messages=session.messages[-2:],  # Last user+assistant pair
                    )
                except Exception as e:
                    logger.error(f"TieredMemory archive failed: {e}")

            self.sessions.save(session)

            # proactive-notify: Proactive completion notification to notification channel
            try:
                import os as _os_notify
                _now_notify = time.time()
                _NOTIFY_INTERVAL = 60.0  # seconds between notifications (throttle)
                if _now_notify - self._last_notification_time >= _NOTIFY_INTERVAL:
                    _notify_token = self._slack_token or _os_notify.environ.get(
                        "NYANCOBOT_CHANNELS__SLACK__TOKEN", ""
                    )
                    _notify_ch = _os_notify.environ.get(
                        "NYANCOBOT_NOTIFICATION_CHANNEL", ""
                    )
                    if _notify_token and _notify_ch:
                        _task_summary = msg.content[:100].replace("\n", " ")
                        _elapsed = _now_notify - _msg_start_time
                        _notify_text = (
                            f"✅ タスク完了: {_task_summary}（所要時間: {_elapsed:.1f}秒）"
                        )
                        await asyncio.to_thread(
                            _send_slack_notification,
                            _notify_token,
                            _notify_ch,
                            _notify_text,
                        )
                        self._last_notification_time = _now_notify
                        logger.info(
                            f"proactive-notify: proactive notification sent to {_notify_ch} "
                            f"(elapsed={_elapsed:.1f}s)"
                        )
            except Exception as _ne:
                logger.warning(f"proactive-notify: notification failed (non-critical): {_ne}")

        return OutboundMessage(
            channel=msg.channel,
            chat_id=msg.chat_id,
            content=final_content,
            metadata=msg.metadata,
            message_type=_outbound_message_type,
        )
    
    def _limit_session_messages(self, session) -> None:
        """
        Limit session messages to 20 (keep first 2 as initial context).

        Args:
            session: The session to limit.
        """
        MAX_MESSAGES = 12
        PRESERVE_FIRST = 0  # No need to preserve old context for local LLMs

        if len(session.messages) > MAX_MESSAGES:
            # Keep first 2 messages + last (MAX_MESSAGES - PRESERVE_FIRST) messages
            preserved = session.messages[:PRESERVE_FIRST]
            recent = session.messages[-(MAX_MESSAGES - PRESERVE_FIRST):]
            session.messages = preserved + recent
            logger.info(
                f"Session {session.key}: limited to {MAX_MESSAGES} messages "
                f"(kept first {PRESERVE_FIRST}, removed {len(session.messages) - MAX_MESSAGES} old messages)"
            )

    async def _process_system_message(self, msg: InboundMessage) -> OutboundMessage | None:
        """
        Process a system message (e.g., subagent announce).
        
        The chat_id field contains "original_channel:original_chat_id" to route
        the response back to the correct destination.
        """
        logger.info(f"Processing system message from {msg.sender_id}")
        
        # Parse origin from chat_id (format: "channel:chat_id")
        if ":" in msg.chat_id:
            parts = msg.chat_id.split(":", 1)
            origin_channel = parts[0]
            origin_chat_id = parts[1]
        else:
            # Fallback
            origin_channel = "cli"
            origin_chat_id = msg.chat_id
        
        # Use the origin session for context
        session_key = f"{origin_channel}:{origin_chat_id}"
        session = self.sessions.get_or_create(session_key)
        
        # Update tool contexts
        message_tool = self.tools.get("message")
        if isinstance(message_tool, MessageTool):
            message_tool.set_context(origin_channel, origin_chat_id)
        
        spawn_tool = self.tools.get("spawn")
        if isinstance(spawn_tool, SpawnTool):
            spawn_tool.set_context(origin_channel, origin_chat_id)
        
        cron_tool = self.tools.get("cron")
        if isinstance(cron_tool, CronTool):
            cron_tool.set_context(origin_channel, origin_chat_id)
        
        # Get tool definitions for prompt embedding
        tool_defs = self.tools.get_definitions()

        # Build messages with the announce content
        messages = self.context.build_messages(
            history=session.get_history(),
            current_message=msg.content,
            channel=origin_channel,
            chat_id=origin_chat_id,
            tool_definitions=tool_defs,
        )

        # Agent loop (limited for announce handling)
        iteration = 0
        final_content = None

        while iteration < self.max_iterations:
            iteration += 1

            response = await self.provider.chat(
                messages=messages,
                tools=tool_defs,
                model=self.model
            )

            if response.has_tool_calls:
                tool_call_dicts = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)
                        }
                    }
                    for tc in response.tool_calls
                ]
                messages = self.context.add_assistant_message(
                    messages, response.content, tool_call_dicts
                )

                for tool_call in response.tool_calls:
                    args_str = json.dumps(tool_call.arguments, ensure_ascii=False)
                    logger.info(f"Tool call: {tool_call.name}({args_str[:200]})")
                    result = await self.tools.execute(tool_call.name, tool_call.arguments)
                    messages = self.context.add_tool_result(
                        messages, tool_call.id, tool_call.name, result
                    )
            else:
                # Check for text-based tool calls
                raw_content2 = response.content or ""
                has_tag2 = "<tool_call>" in raw_content2
                logger.info(f"Text tool call check (bg): has_tag={has_tag2}, content_len={len(raw_content2)}")
                clean_text, text_tool_calls = parse_tool_calls(raw_content2)

                if text_tool_calls:
                    tool_results = []
                    for tc in text_tool_calls:
                        args_str = json.dumps(tc["arguments"], ensure_ascii=False)
                        logger.info(f"Text tool call: {tc['name']}({args_str[:200]})")
                        result = await self.tools.execute(tc["name"], tc["arguments"])
                        tool_results.append(f"[{tc['name']}] {result}")

                    messages.append({"role": "assistant", "content": response.content})
                    results_text = "\n\n".join(tool_results)
                    messages.append({
                        "role": "user",
                        "content": f"Tool results:\n\n{results_text}\n\nPlease continue your response based on the tool results above."
                    })
                else:
                    final_content = response.content
                    break
        
        if final_content is None:
            final_content = "Background task completed."

        # Save to session (mark as system message in history)
        session.add_message("user", f"[System: {msg.sender_id}] {msg.content}")
        session.add_message("assistant", final_content)

        # Limit session messages to 20 (keep first 2 as initial context)
        self._limit_session_messages(session)

        # P2-2: Check and perform compaction if needed
        await self.compaction.check_and_compact(session)

        self.sessions.save(session)
        
        # Determine message_type for system messages
        import os as _os2
        _notification_sys = _os2.environ.get("NYANCOBOT_NOTIFICATION_CHANNEL", "")
        if not _notification_sys:
            import json as _json3
            try:
                with open(_os2.path.expanduser("~/.nyancobot/config.json")) as f:
                    _cfg3 = _json3.load(f)
                _notification_sys = _cfg3.get("channels", {}).get("slack", {}).get("channel_routing", {}).get("notification_channel", "")
            except Exception:
                pass
        if origin_chat_id.startswith("D") or (_notification_sys and origin_chat_id == _notification_sys):
            _sys_msg_type = "user_response"
        else:
            _sys_msg_type = "log"

        return OutboundMessage(
            channel=origin_channel,
            chat_id=origin_chat_id,
            content=final_content,
            message_type=_sys_msg_type,
        )

    async def process_direct(
        self,
        content: str,
        session_key: str = "cli:direct",
        channel: str = "cli",
        chat_id: str = "direct",
        model: str | None = None,  # NYANCOBOT-MOD: model override param
    ) -> str:
        """
        Process a message directly (for CLI or cron usage).

        Args:
            content: The message content.
            session_key: Session identifier.
            channel: Source channel (for context).
            chat_id: Source chat ID (for context).
            model: Optional model override for this call.

        Returns:
            The agent's response.
        """
        msg = InboundMessage(
            channel=channel,
            sender_id="user",
            chat_id=chat_id,
            content=content
        )

        response = await self._process_message(msg, model_override=model)  # NYANCOBOT-MOD: pass model
        return response.content if response else ""

    # === plan-execute: Plan-and-Execute execution ===

    async def _execute_with_plan(
        self,
        msg: InboundMessage,
        messages: list[dict[str, Any]],
        tool_defs: list[dict[str, Any]],
        effective_model: str,
        session: Any,
        outbound_message_type: str,
    ) -> OutboundMessage | None:
        """Execute a message using the Plan-and-Execute pattern.

        Generates a multi-step plan, then executes each step as a focused
        LLM invocation using the existing tool call mechanism.

        Returns an OutboundMessage on success, or None to fall through
        to the normal agent loop.
        """
        if not self._planner or not self._task_state_mgr:
            return None

        # Generate plan
        available_tools = self.tools.tool_names
        try:
            plan = await self._planner.plan(msg.content, available_tools)
        except Exception as e:
            logger.error(f"Plan generation failed: {e}")
            return None

        if not plan.steps:
            return None

        # Create task state
        import uuid
        task_id = f"plan_{uuid.uuid4().hex[:8]}"
        self._task_state_mgr.create_task(task_id, step_count=len(plan.steps))
        self._task_state_mgr.start_task(task_id)

        step_results: list[str] = []
        max_replans = 1  # Allow one replan attempt

        for step in plan.steps:
            self._task_state_mgr.start_step(task_id, step.step_id)
            step.status = "running"
            step.started_at = __import__("datetime").datetime.now()

            # Build focused prompt for this step
            context_from_prev = ""
            if step_results:
                context_from_prev = "\n\nPrevious step results:\n" + "\n".join(
                    f"- Step {i+1}: {r[:200]}" for i, r in enumerate(step_results)
                )

            step_prompt = (
                f"Execute the following step of a plan.\n\n"
                f"Overall goal: {plan.goal}\n"
                f"Current step ({step.step_id}/{len(plan.steps)}): {step.description}\n"
                f"Expected output: {step.expected_output}"
                f"{context_from_prev}\n\n"
                f"Execute this step now. Use tools if needed. Be concise in your response."
            )

            # Build messages for this step (fresh context with step prompt)
            step_messages = self.context.build_messages(
                history=session.get_history(),
                current_message=step_prompt,
                channel=msg.channel,
                chat_id=msg.chat_id,
                tool_definitions=tool_defs,
            )

            # Mini agent loop for this step
            step_content = await self._run_step_loop(
                step_messages, tool_defs, effective_model
            )

            if step_content and not step_content.startswith("Error:"):
                step.status = "completed"
                step.result = step_content
                step.completed_at = __import__("datetime").datetime.now()
                self._task_state_mgr.complete_step(task_id, step.step_id, step_content[:500])
                step_results.append(step_content)
            else:
                step.status = "failed"
                step.completed_at = __import__("datetime").datetime.now()
                failure_reason = step_content or "No response"
                self._task_state_mgr.fail_step(task_id, step.step_id, failure_reason[:200])

                # Attempt replan
                if max_replans > 0:
                    max_replans -= 1
                    logger.info(f"Step {step.step_id} failed, attempting replan")
                    try:
                        new_plan = await self._planner.replan(
                            plan, failure_reason, available_tools
                        )
                        # Replace remaining steps with new plan
                        plan.steps = [
                            s for s in plan.steps if s.status == "completed"
                        ] + new_plan.steps
                        plan.status = "replanned"
                        # Update task state for new steps
                        for ns in new_plan.steps:
                            self._task_state_mgr._tasks[task_id].steps.append(
                                __import__("nyancobot.agent.task_state", fromlist=["StepState"]).StepState(
                                    step_id=ns.step_id
                                )
                            )
                        continue
                    except Exception as e:
                        logger.error(f"Replan failed: {e}")

                step_results.append(f"[FAILED] {failure_reason}")
                # Continue with remaining steps instead of stopping

        # Aggregate results
        all_completed = all(s.status == "completed" for s in plan.steps)
        if all_completed:
            self._task_state_mgr.complete_task(task_id)
        else:
            failed_count = sum(1 for s in plan.steps if s.status == "failed")
            if failed_count == len(plan.steps):
                self._task_state_mgr.fail_task(task_id, "All steps failed")
            else:
                self._task_state_mgr.complete_task(task_id)

        # Build final aggregated response
        summary_parts = [f"【計画実行完了】目標: {plan.goal}\n"]
        for i, step in enumerate(plan.steps):
            status_icon = "✅" if step.status == "completed" else "❌"
            result_preview = (step.result or step.error or "")[:300]
            summary_parts.append(
                f"{status_icon} Step {step.step_id}: {step.description}\n"
                f"   結果: {result_preview}"
            )
        final_content = "\n".join(summary_parts)

        # Save to session
        session.add_message("user", msg.content)
        session.add_message("assistant", final_content)
        self._limit_session_messages(session)
        await self.compaction.check_and_compact(session)
        self.sessions.save(session)

        return OutboundMessage(
            channel=msg.channel,
            chat_id=msg.chat_id,
            content=final_content,
            metadata=msg.metadata,
            message_type=outbound_message_type,
        )

    async def _run_step_loop(
        self,
        messages: list[dict[str, Any]],
        tool_defs: list[dict[str, Any]],
        model: str,
        max_iterations: int = 10,
    ) -> str:
        """Run a mini agent loop for a single plan step.

        Similar to the main agent loop but limited in scope.
        Returns the final text response.
        """
        iteration = 0
        final_content = None

        while iteration < max_iterations:
            iteration += 1

            response = await self.provider.chat(
                messages=messages, tools=tool_defs, model=model
            )

            if response.has_tool_calls:
                tool_call_dicts = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in response.tool_calls
                ]
                messages = self.context.add_assistant_message(
                    messages, response.content, tool_call_dicts
                )

                for tool_call in response.tool_calls:
                    args_str = json.dumps(tool_call.arguments, ensure_ascii=False)
                    logger.info(f"[PlanStep] Tool call: {tool_call.name}({args_str[:200]})")
                    result = await self.tools.execute(tool_call.name, tool_call.arguments)
                    messages = self.context.add_tool_result(
                        messages, tool_call.id, tool_call.name, result
                    )
            else:
                raw_content = response.content or ""
                clean_text, text_tool_calls = parse_tool_calls(raw_content)

                if text_tool_calls:
                    tool_results = []
                    for tc in text_tool_calls:
                        result = await self.tools.execute(tc["name"], tc["arguments"])
                        tool_results.append(f"[{tc['name']}] {result}")

                    messages.append({"role": "assistant", "content": response.content})
                    results_text = "\n\n".join(tool_results)
                    messages.append({
                        "role": "user",
                        "content": f"Tool results:\n\n{results_text}\n\nContinue.",
                    })
                else:
                    final_content = response.content
                    break

        return final_content or "Step completed (no output)."

    # === Direct message dispatch (bypass LLM) ===
    # Patterns: "message to leaderN：...", "notify leaderN：...", "send to teamN：..."
    _DENREI_PATTERNS = [
        re.compile(r"message\s+to\s+leader\s*([12])[：:]?\s*(.+)", re.DOTALL | re.IGNORECASE),
        re.compile(r"notify\s+leader\s*([12])[：:]?\s*(.+)", re.DOTALL | re.IGNORECASE),
        re.compile(r"send\s+to\s+leader\s*([12])[：:]?\s*(.+)", re.DOTALL | re.IGNORECASE),
        re.compile(r"message\s+to\s+team\s*([12])[：:]?\s*(.+)", re.DOTALL | re.IGNORECASE),
        re.compile(r"messenger.*leader\s*([12])[：:]?\s*(.+)", re.DOTALL),
        re.compile(r"messenger.*team\s*([12])[：:]?\s*(.+)", re.DOTALL),
    ]

    async def _try_direct_denrei(self, content: str) -> str | None:
        """Try to detect and execute denrei requests directly without LLM.

        Returns the response string if a denrei was detected and executed,
        or None if the message is not a denrei request.
        """
        for pattern in self._DENREI_PATTERNS:
            m = pattern.search(content)
            if m:
                target = m.group(1)
                message = m.group(2).strip()
                if not message:
                    return None  # Empty message, let LLM handle

                logger.info(f"Direct denrei detected: target={target}, message={message[:80]}")
                denrei_tool = self.tools.get("denrei")
                if denrei_tool is None:
                    logger.error("DenreiTool not registered")
                    return "Error: Messenger tool is not registered."

                result = await denrei_tool.execute(target=target, message=message)
                logger.info(f"Direct denrei result: {result[:120]}")
                return result

        return None
