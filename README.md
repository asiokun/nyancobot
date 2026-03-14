🌍 **English** | [日本語](README_ja.md) | [中文](README_zh.md) | [한국어](README_ko.md) | [Español](README_es.md) | [Français](README_fr.md) | [Italiano](README_it.md) | [Português](README_pt.md) | [Deutsch](README_de.md)

# nyancobot

> **Version: 0.2.5** (CashClaw Edition)

```
  ___  ___    _  ___   ___   _  _  ___ ___  _
 / __|/ _ \  | \| \ \ / /_\ | \| |/ __/ _ \| |
| (_ | (_) | | .` |\ V / _ \| .` | (_| (_) |_|
 \___|\___/  |_|\_| |_/_/ \_\_|\_|\___\___/(_)

                  /\_/\
                 ( o.o )
                  > ^ <   Secure AI Agent Framework
                 /|   |\
                (_|   |_)
```

> **Secure, production-ready AI agent framework** — A hardened fork of [nanobot](https://github.com/HKUDS/nanobot) with enterprise-grade security, multi-agent collaboration, and advanced automation.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## What can nyancobot do?

<table>
<tr><th>Language</th><th>Description</th></tr>
<tr><td><strong>日本語</strong></td><td>セキュアなAIエージェント基盤。SSRF防御・4段階権限・マルチエージェント連携・ブラウザ自動操作・BM25+自己学習メモリ・案件自動検索を備えた、本番運用対応のフレームワーク。</td></tr>
<tr><td><strong>English</strong></td><td>Secure AI agent framework with SSRF prevention, 4-tier permissions, multi-agent orchestration, browser automation, BM25+ self-learning memory, and automated job hunting — production-ready out of the box.</td></tr>
<tr><td><strong>中文（简体）</strong></td><td>安全的AI代理框架。具备SSRF防御、四级权限、多代理协作、浏览器自动化、BM25+自学习记忆、自动搜索项目等功能，开箱即用于生产环境。</td></tr>
<tr><td><strong>한국어</strong></td><td>보안 AI 에이전트 프레임워크. SSRF 방어, 4단계 권한, 멀티 에이전트 협업, 브라우저 자동화, BM25+ 자기학습 메모리, 자동 프로젝트 검색 기능을 갖춘 프로덕션 대응 프레임워크.</td></tr>
</table>

---

## Feature Overview

| Category | Feature | Description |
|----------|---------|-------------|
| **Security** | SSRF Prevention | Domain whitelist + local IP blocking |
| **Security** | 4-Tier Permissions | READ_ONLY / TEST_WRITE / BROWSER_AUTO / FULL |
| **Security** | Dangerous Action Blocking | Auto-refuse delete/purchase/payment/admin |
| **Security** | Path Traversal Protection | Sanitized filenames + path validation |
| **Security** | Command Execution | Allowed dirs + audit logs + `~` expansion fix |
| **Security** | Cookie Security | Persistent storage + domain separation + 0o600 perms |
| **Multi-Agent** | tmux Messaging | send-keys with delivery confirmation & retry |
| **Multi-Agent** | Anti-Loop Protection | MD5 hashing + 10-second throttle |
| **Multi-Agent** | State Detection | Compacting/thinking/idle awareness |
| **Multi-Agent** | Custom MCP Servers | 5 specialized servers (denrei, browser, vision, memory, web-tools) |
| **Browser** | AX Tree Support | Full accessibility tree via Chrome DevTools Protocol |
| **Browser** | Vision Integration | Screenshot analysis + LLM-driven next action |
| **Browser** | Secure File Upload | Path validation + 20MB limit |
| **Content** | Content Repurpose | 1 text to X/note/Instagram/SEO blog auto-conversion |
| **Content** | Quality Validation | Platform checks + NG word detection + auto-fix |
| **Content** | YouTube Transcripts | Multi-language, 50KB limit, flexible URL formats |
| **LLM** | Failover Chains | Retry + fallback_providers |
| **LLM** | Error Classification | Rate limit/timeout/auth/server error detection |
| **LLM** | Qwen3.5 Thinking Fix | Direct Ollama native API bypass (`think:false`) |
| **Memory** | BM25+ Time-Decay Search | Pure Python BM25+ with 30-day half-life decay (no chromadb) |
| **Learning** | Self-Study Sessions | 3-mode rotation (feedback analysis / knowledge organization / integration report) |
| **Learning** | Feedback Accumulation | Feedback category for evaluator pipeline (v0.3.0) integration |
| **Automation** | CW Job Hunter | CrowdWorks scraping + skill matching + Slack notification |
| **Automation** | Scheduled Reports | Morning/evening summaries + anomaly detection |
| **Automation** | Health Checks | 3-hour error monitoring via cron |

---

## New in v0.2.5 — CashClaw Edition

### BM25+ Time-Decay Memory Search

Removed `chromadb` dependency entirely. Replaced with a pure Python BM25+ implementation featuring a 30-day half-life decay function. Older knowledge fades naturally, keeping the agent's memory relevant without manual pruning.

### Self-Study Sessions (`self_study.py`)

CashClaw-style autonomous learning. Rotates through 3 modes:

1. **Feedback Analysis** — Reviews accumulated feedback, extracts actionable patterns
2. **Knowledge Organization** — Consolidates scattered knowledge into structured categories
3. **Integration Report** — Produces a synthesis of recent learnings

Runs automatically via cron every 6 hours.

### Feedback Accumulation

New `feedback` category added to the memory system. Stores structured evaluations that connect directly to the evaluator pipeline planned for v0.3.0.

### CW Job Hunter (`cw_job_hunter.py`)

Automated CrowdWorks job search using Playwright. Scrapes listings, matches against configured skill profiles, and sends Slack notifications for relevant opportunities. Runs via cron every 2 hours.

---

## Messaging Integrations

[![Slack](https://img.shields.io/badge/Slack-4A154B?logo=slack&logoColor=white)](https://slack.com)
[![Discord](https://img.shields.io/badge/Discord-5865F2?logo=discord&logoColor=white)](https://discord.com)
[![LINE](https://img.shields.io/badge/LINE-00C300?logo=line&logoColor=white)](https://line.me)
[![WhatsApp](https://img.shields.io/badge/WhatsApp-25D366?logo=whatsapp&logoColor=white)](https://whatsapp.com)

nyancobot supports multiple messaging platforms out of the box. Install only what you need:

```bash
# Install specific platform
pip install nyancobot[slack]     # Slack only
pip install nyancobot[discord]   # Discord only
pip install nyancobot[line]      # LINE only
pip install nyancobot[whatsapp]  # WhatsApp only

# Install all messaging platforms
pip install nyancobot[all-channels]
```

### Quick Setup

**Slack**: Get bot token from [Slack API](https://api.slack.com/apps) → Enable Socket Mode → Copy `xoxb-` and `xapp-` tokens.

**Discord**: Create bot at [Discord Developer Portal](https://discord.com/developers/applications) → Copy token → Enable Message Content Intent.

**LINE**: Create channel at [LINE Developers](https://developers.line.biz/) → Get Channel Access Token and Secret → Set webhook URL.

**WhatsApp**: Register at [Meta for Developers](https://developers.facebook.com/) → Get token and Phone Number ID → Configure webhook.

### Configuration

Update `~/.nyancobot/config/config.json`:

```json
{
  "channels": {
    "slack": {
      "enabled": true,
      "bot_token": "xoxb-YOUR-TOKEN",
      "app_token": "xapp-YOUR-TOKEN",
      "signing_secret": "YOUR_SECRET"
    },
    "discord": {
      "enabled": true,
      "token": "YOUR_DISCORD_BOT_TOKEN"
    }
  }
}
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- Playwright browser binaries

### Installation

```bash
# Install from PyPI (when published)
pip install nyancobot

# Or install from source
git clone https://github.com/asiokun/nyancobot.git
cd nyancobot
pip install -e .

# Install Playwright browsers
playwright install chromium
```

### Basic Setup

1. **Create configuration file**

```bash
mkdir -p ~/.nyancobot/config
cp config.example.json ~/.nyancobot/config/config.json
```

2. **Set environment variables**

```bash
export OPENAI_API_KEY="YOUR_API_KEY"
export ANTHROPIC_API_KEY="YOUR_API_KEY"  # Optional
export OLLAMA_BASE_URL="http://localhost:11434"  # Optional
```

3. **Configure browser permission level**

```bash
# Level 0: READ_ONLY (safe)
# Level 1: TEST_WRITE (test domains only)
# Level 2: BROWSER_AUTO (browser automation)
# Level 3: FULL (all actions)
echo "2" > ~/.nyancobot/config/permission_level.txt
```

4. **Set allowed domains** (for SSRF prevention)

```bash
cat > ~/.nyancobot/config/allowed_domains.txt <<EOF
example.com
httpbin.org
crowdworks.jp
lancers.jp
EOF
```

5. **Run nyancobot**

```bash
nyancobot
```

---

## Configuration

### config.json Example

```json
{
  "llm": {
    "provider": "litellm",
    "model": "gpt-4-turbo",
    "fallback_providers": ["ollama/qwen2.5:32b"],
    "temperature": 0.7,
    "max_tokens": 4096
  },
  "browser": {
    "headless": true,
    "viewport": {"width": 1280, "height": 720},
    "timeout": 30000
  },
  "security": {
    "permission_level": 2,
    "audit_log": "~/.nyancobot/audit.jsonl",
    "allowed_dirs": ["~/projects", "/tmp"]
  },
  "mcp_servers": {
    "denrei": {
      "command": "python",
      "args": ["~/.nyancobot/scripts/denrei-mcp-server.py"]
    },
    "browser": {
      "command": "python",
      "args": ["~/.nyancobot/scripts/browser-mcp-server.py"]
    }
  }
}
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key (required) | - |
| `ANTHROPIC_API_KEY` | Anthropic API key (optional) | - |
| `OLLAMA_BASE_URL` | Ollama server URL (optional) | `http://localhost:11434` |
| `NYANCOBOT_CONFIG` | Path to config.json | `~/.nyancobot/config/config.json` |
| `NYANCOBOT_LOG_LEVEL` | Logging level | `INFO` |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      User / Scheduler                        │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   nyancobot Agent Loop                       │
│  ┌────────────────────────────────────────────────────┐     │
│  │  LLM Provider (litellm + failover)                 │     │
│  │  - OpenAI / Anthropic / Ollama                     │     │
│  │  - Auto-retry / Fallback chains                    │     │
│  └────────────────────────────────────────────────────┘     │
│                            │                                 │
│                            ▼                                 │
│  ┌────────────────────────────────────────────────────┐     │
│  │  Security Layer (4-tier permissions)               │     │
│  │  - SSRF prevention (domain whitelist)              │     │
│  │  - Path traversal protection                       │     │
│  │  - Dangerous action blocking                       │     │
│  │  - Audit logging                                   │     │
│  └────────────────────────────────────────────────────┘     │
│                            │                                 │
│                            ▼                                 │
│  ┌────────────────────────────────────────────────────┐     │
│  │  Tool Router                                       │     │
│  │  ┌──────────┬──────────┬──────────┬─────────────┐  │     │
│  │  │ Browser  │  Shell   │  Denrei  │  Content    │  │     │
│  │  │ (secure) │ (secure) │ (multi-  │ (repurpose) │  │     │
│  │  │          │          │  agent)  │             │  │     │
│  │  └──────────┴──────────┴──────────┴─────────────┘  │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│               External Systems / MCP Servers                 │
│  - Slack (notifications)                                     │
│  - Browser (Playwright)                                      │
│  - Vision Secretary (screenshot analysis)                    │
│  - Memory Search (BM25+ time-decay)                         │
│  - Web Tools                                                 │
└─────────────────────────────────────────────────────────────┘
```

### Multi-Agent Communication Flow

```
Agent A                    Agent B
   │                          │
   │  send-keys (message)     │
   ├─────────────────────────►│
   │                          │
   │  ◄─ State check ─────────┤
   │     (idle/busy?)         │
   │                          │
   │  ◄─ Delivery confirm ────┤
   │                          │
   │  [Anti-loop check]       │
   │  (MD5 hash + throttle)   │
   │                          │
   │  ◄─ Response ────────────┤
   │                          │
```

---

## Changelog

### v0.2.5 (2026-03-14) — CashClaw Edition

- **BM25+ Time-Decay Memory Search**: Removed chromadb dependency. Pure Python BM25+ with 30-day half-life decay for natural knowledge aging.
- **Self-Study Sessions** (`self_study.py`): CashClaw-style autonomous learning with 3-mode rotation (feedback analysis / knowledge organization / integration report). Cron every 6 hours.
- **Feedback Accumulation**: New feedback category in memory system. Ready for evaluator pipeline (v0.3.0) integration.
- **CW Job Hunter** (`cw_job_hunter.py`): CrowdWorks Playwright scraping + skill matching + Slack notification. Cron every 2 hours.

### v0.2.0

- **browser_stealth integration**: Enhanced anti-detection for browser automation.
- **xai-search fix**: Corrected search API integration issues.

### v0.1.0

- Initial release. Fork of nanobot with security hardening, multi-agent collaboration, and browser automation.

---

## Attribution

nyancobot is a fork of [nanobot](https://github.com/HKUDS/nanobot) by HKUDS.

We are deeply grateful to the original nanobot team for their elegant and lightweight foundation.

See [ATTRIBUTION.md](ATTRIBUTION.md) for detailed credits and modifications.

---

## License

MIT License - see [LICENSE](LICENSE) for details.

**Dual Copyright:**
- Original nanobot: Copyright (c) 2025 nanobot contributors
- nyancobot modifications: Copyright (c) 2026 nyancobot contributors

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

**Security Issues:** Please report security vulnerabilities via GitHub Security Advisories (not public issues).

---

## Links

- **Original nanobot**: https://github.com/HKUDS/nanobot
- **Documentation**: [Coming soon]
- **Issues**: https://github.com/asiokun/nyancobot/issues
- **Discussions**: https://github.com/asiokun/nyancobot/discussions

---

## Acknowledgments

- **HKUDS** for the original nanobot framework
- **Playwright** team for robust browser automation
- **litellm** for unified LLM provider interface
- **FastMCP** for MCP server infrastructure
- All contributors to the nyancobot project

---

**Made with care by the nyancobot community**
