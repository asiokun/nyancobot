"""LiteLLM provider implementation for multi-provider support."""

import asyncio
import os
from typing import Any

import litellm
from litellm import acompletion
from loguru import logger

from nyancobot.providers.base import LLMProvider, LLMResponse, ToolCallRequest


class LiteLLMProvider(LLMProvider):
    """
    LLM provider using LiteLLM for multi-provider support.
    
    Supports OpenRouter, Anthropic, OpenAI, Gemini, and many other providers through
    a unified interface.
    """
    
    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        default_model: str = "gpt-5.2",
        extra_headers: dict[str, str] | None = None,
        # P2-1: Failover configuration
        fallback_providers: list[dict[str, Any]] | None = None,
        retry_config: dict[str, Any] | None = None,
    ):
        super().__init__(api_key, api_base)
        self.default_model = default_model
        self.extra_headers = extra_headers or {}

        # P2-1: Failover config (default: no retry, no fallback = backward compatible)
        self.fallback_providers: list[dict[str, Any]] = fallback_providers or []
        _rc = retry_config or {}
        self._retry_max_attempts: int = _rc.get("max_attempts", 1)
        self._retry_backoff_seconds: int = _rc.get("backoff_seconds", 5)
        
        # Detect OpenRouter by api_key prefix or explicit api_base
        self.is_openrouter = (
            (api_key and api_key.startswith("sk-or-")) or
            (api_base and "openrouter" in api_base)
        )
        
        # Detect AiHubMix by api_base
        self.is_aihubmix = bool(api_base and "aihubmix" in api_base)
        
        # Track if using custom endpoint (vLLM, etc.)
        self.is_vllm = bool(api_base) and not self.is_openrouter and not self.is_aihubmix
        
        # Configure LiteLLM based on provider
        if api_key:
            if self.is_openrouter:
                # OpenRouter mode - set key
                os.environ["OPENROUTER_API_KEY"] = api_key
            elif self.is_aihubmix:
                # AiHubMix gateway - OpenAI-compatible
                os.environ["OPENAI_API_KEY"] = api_key
            elif self.is_vllm:
                # vLLM/custom endpoint - uses OpenAI-compatible API
                os.environ["HOSTED_VLLM_API_KEY"] = api_key
            elif "deepseek" in default_model:
                os.environ.setdefault("DEEPSEEK_API_KEY", api_key)
            elif "anthropic" in default_model:
                os.environ.setdefault("ANTHROPIC_API_KEY", api_key)
            elif "openai" in default_model or "gpt" in default_model:
                os.environ.setdefault("OPENAI_API_KEY", api_key)
            elif "gemini" in default_model.lower():
                os.environ.setdefault("GEMINI_API_KEY", api_key)
            elif "zhipu" in default_model or "glm" in default_model or "zai" in default_model:
                os.environ.setdefault("ZAI_API_KEY", api_key)
                os.environ.setdefault("ZHIPUAI_API_KEY", api_key)
            elif "dashscope" in default_model or "qwen" in default_model.lower():
                os.environ.setdefault("DASHSCOPE_API_KEY", api_key)
            elif "groq" in default_model:
                os.environ.setdefault("GROQ_API_KEY", api_key)
            elif "moonshot" in default_model or "kimi" in default_model:
                os.environ.setdefault("MOONSHOT_API_KEY", api_key)
                os.environ.setdefault("MOONSHOT_API_BASE", api_base or "https://api.moonshot.cn/v1")
        
        if api_base:
            litellm.api_base = api_base
        
        # Disable LiteLLM logging noise
        litellm.suppress_debug_info = True
    
    # P2-1: Error classification for retry/failover decisions
    @staticmethod
    def _classify_error(error: Exception) -> str:
        """Classify LLM error type for retry/failover strategy.

        Returns one of: rate_limit, timeout, auth, server_error, other.
        """
        err = str(error).lower()
        if "429" in err or "rate_limit" in err or "rate limit" in err:
            return "rate_limit"
        if "408" in err or "timeout" in err or "timed out" in err:
            return "timeout"
        if "401" in err or "unauthorized" in err or "authentication" in err:
            return "auth"
        if any(c in err for c in ("500", "502", "503", "504", "server_error", "internal server")):
            return "server_error"
        return "other"

    async def _ollama_chat_direct(
        self, kwargs: dict[str, Any]
    ) -> LLMResponse | None:
        """Call Ollama /api/chat directly with think=false to prevent infinite thinking.

        litellm's OpenAI-compatible endpoint does not pass 'think' parameter,
        so we bypass it and call Ollama's native API directly.
        """
        import httpx

        # Extract model name (remove hosted_vllm/ prefix)
        model = kwargs.get("model", "")
        if "/" in model:
            model = model.split("/", 1)[1]

        # Build Ollama-native request
        ollama_base = self.api_base.rstrip("/").replace("/v1", "")
        url = f"{ollama_base}/api/chat"

        payload = {
            "model": model,
            "messages": kwargs.get("messages", []),
            "stream": False,
            "think": False,
            "options": {
                "num_predict": kwargs.get("max_tokens", 4096),
                "temperature": kwargs.get("temperature", 0.7),
            },
        }

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()

            msg = data.get("message", {})
            content = msg.get("content", "")
            duration = round(data.get("total_duration", 0) / 1e9, 1)
            logger.info(f"Ollama direct: model={model}, duration={duration}s, content_len={len(content)}")

            return LLMResponse(content=content, finish_reason="stop")
        except Exception as e:
            logger.warning(f"Ollama direct call failed, falling back to litellm: {e}")
            return None

    async def _try_completion(
        self, kwargs: dict[str, Any], max_attempts: int
    ) -> LLMResponse | None:
        """P2-1: Attempt acompletion with retries. Returns None on total failure."""
        for attempt in range(max_attempts):
            try:
                response = await acompletion(**kwargs)
                return self._parse_response(response)
            except Exception as e:
                error_type = self._classify_error(e)
                model = kwargs.get("model", "unknown")
                logger.warning(
                    f"LLM call failed [{model}] attempt {attempt + 1}/{max_attempts}: {error_type} - {e}",
                )
                # rate_limit → immediate failover (no retry)
                # auth → skip this provider entirely
                if error_type in ("rate_limit", "auth"):
                    break
                # timeout, server_error, other → retry with backoff
                if attempt < max_attempts - 1:
                    await asyncio.sleep(self._retry_backoff_seconds)
        return None

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """
        Send a chat completion request via LiteLLM.

        P2-1: Supports retry + failover to fallback providers.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            tools: Optional list of tool definitions in OpenAI format.
            model: Model identifier (e.g., 'anthropic/claude-sonnet-4-5').
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature.

        Returns:
            LLMResponse with content and/or tool calls.
        """
        model = model or self.default_model

        # Gateway/endpoint-specific prefixes (detected by api_base/api_key, not model name)
        # NOTE: vllm/ollama custom endpoints skip auto-prefix rules entirely
        if self.is_openrouter and not model.startswith("openrouter/"):
            model = f"openrouter/{model}"
        elif self.is_aihubmix:
            model = f"openai/{model.split('/')[-1]}"
        elif self.is_vllm:
            model = f"hosted_vllm/{model}"
        else:
            # Auto-prefix model names for known cloud providers only
            # (keywords, target_prefix, skip_if_starts_with)
            _prefix_rules = [
                (("glm", "zhipu"), "zai", ("zhipu/", "zai/", "openrouter/", "hosted_vllm/")),
                (("qwen", "dashscope"), "dashscope", ("dashscope/", "openrouter/")),
                (("moonshot", "kimi"), "moonshot", ("moonshot/", "openrouter/")),
                (("gemini",), "gemini", ("gemini/",)),
            ]
            model_lower = model.lower()
            for keywords, prefix, skip in _prefix_rules:
                if any(kw in model_lower for kw in keywords) and not any(model.startswith(s) for s in skip):
                    model = f"{prefix}/{model}"
                    break

        # kimi-k2.5 only supports temperature=1.0
        if "kimi-k2.5" in model.lower():
            temperature = 1.0

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # Pass api_base directly for custom endpoints (vLLM, etc.)
        if self.api_base:
            kwargs["api_base"] = self.api_base

        # Pass extra headers (e.g. APP-Code for AiHubMix)
        if self.extra_headers:
            kwargs["extra_headers"] = self.extra_headers

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        # Debug: log system prompt presence and model
        sys_msgs = [m for m in messages if m.get("role") == "system"]
        _tools_count = len(tools) if tools else 0
        _tools_in_kwargs = len(kwargs.get("tools", [])) if "tools" in kwargs else 0
        logger.info(
            f"LLM request: model={model}, messages={len(messages)}, system_msgs={len(sys_msgs)}, "
            f"system_len={len(sys_msgs[0].get('content', '')) if sys_msgs else 0}, "
            f"tools_param={_tools_count}, tools_in_kwargs={_tools_in_kwargs}"
        )
        if sys_msgs:
            logger.debug(f"System prompt first 200 chars: {sys_msgs[0].get('content', '')[:200]}")

        # Qwen3.5+ on Ollama: bypass litellm, call Ollama /api/chat directly with think=false
        if self.is_vllm and "qwen3" in model.lower() and self.api_base:
            result = await self._ollama_chat_direct(kwargs)
            if result:
                return result

        # P2-1: Primary provider call with retry
        result = await self._try_completion(kwargs, self._retry_max_attempts)
        if result:
            return result

        # P2-1: Fallback providers
        for fb in self.fallback_providers:
            if not fb.get("api_key"):
                logger.info("P2-1: Skipping fallback %s (no API key)", fb.get("model"))
                continue

            fb_kwargs: dict[str, Any] = {
                "model": fb["model"],
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "api_key": fb["api_key"],
            }
            if fb.get("api_base"):
                fb_kwargs["api_base"] = fb["api_base"]
            if fb.get("extra_headers"):
                fb_kwargs["extra_headers"] = fb["extra_headers"]
            if tools:
                fb_kwargs["tools"] = tools
                fb_kwargs["tool_choice"] = "auto"

            logger.info("P2-1: Falling back to %s", fb["model"])
            result = await self._try_completion(fb_kwargs, self._retry_max_attempts)
            if result:
                return result

        # All providers exhausted
        return LLMResponse(
            content="Error: All LLM providers failed. Check logs for details.",
            finish_reason="error",
        )
    
    def _parse_response(self, response: Any) -> LLMResponse:
        """Parse LiteLLM response into our standard format."""
        choice = response.choices[0]
        message = choice.message
        
        tool_calls = []
        if hasattr(message, "tool_calls") and message.tool_calls:
            for tc in message.tool_calls:
                # Parse arguments from JSON string if needed
                args = tc.function.arguments
                if isinstance(args, str):
                    import json
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {"raw": args}
                
                tool_calls.append(ToolCallRequest(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=args,
                ))
        
        usage = {}
        if hasattr(response, "usage") and response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        
        return LLMResponse(
            content=message.content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
            usage=usage,
        )
    
    def get_default_model(self) -> str:
        """Get the default model."""
        return self.default_model
