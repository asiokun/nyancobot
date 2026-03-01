# nyancobot

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

## 🎯 What is nyancobot?

**nyancobot** is an open-source AI agent framework built on top of [nanobot](https://github.com/HKUDS/nanobot), enhanced with:

- **🔒 Production-grade security** (SSRF prevention, 4-tier permissions, audit logging)
- **🤝 Multi-agent orchestration** (tmux-based messaging, state detection, anti-loop protection)
- **🌐 Advanced browser automation** (Playwright + Vision + secure file handling)
- **📝 Content automation** (repurpose, quality validation, YouTube transcripts)
- **🚀 LLM provider resilience** (failover chains, Ollama direct API, Qwen3.5 fix)

**Why nyancobot?**
nanobot is a brilliant lightweight foundation (~4,000 lines), but production deployments require hardening. nyancobot adds ~7,000 lines of security, reliability, and automation features while maintaining the elegance of the original.

---

## ✨ Key Features

### 🔒 Security Hardening (Biggest Differentiator)

| Feature | nanobot | nyancobot |
|---------|---------|-----------|
| SSRF Prevention | ❌ | ✅ Domain whitelist + local IP blocking |
| Permission Levels | ❌ | ✅ 4-tier system (READ_ONLY → FULL) |
| Dangerous Actions | ❌ | ✅ Auto-refuse delete/purchase/payment/admin |
| Path Traversal | ❌ | ✅ Sanitized filenames + path validation |
| Command Execution | Basic deny | ✅ Allowed dirs + audit logs + `~` expansion fix |
| Cookie Security | ❌ | ✅ Persistent storage + domain separation + 0o600 perms |

### 🤝 Multi-Agent Collaboration

- **tmux-based messaging**: `send-keys` with delivery confirmation & retry
- **Anti-loop protection**: MD5 hashing + 10-second throttle
- **State detection**: Compacting/thinking/idle awareness
- **Communication logging**: All messages to dedicated audit channel
- **Custom MCP servers**: 5 specialized servers (denrei, browser, vision, memory, web-tools)

### 🌐 Browser Automation

- **AX Tree support**: Full accessibility tree via Chrome DevTools Protocol
- **Vision integration**: Screenshot → LLM analysis → next action
- **Secure file upload**: Path validation + 20MB limit
- **Job extraction**: CrowdWorks/Lancers scraping with keyword filtering & deduplication

### 📝 Content Automation

- **Content repurpose**: 1 text → X/note/Instagram/SEO blog auto-conversion
- **Quality validation**: Platform-specific checks + NG word detection + auto-fix
- **YouTube transcripts**: Multi-language, 50KB limit, flexible URL formats

### 🚀 LLM Provider Improvements

- **Qwen3.5 thinking fix**: Direct Ollama native API bypass (`think:false`)
- **Failover chains**: Retry + `fallback_providers`
- **Error classification**: Rate limit/timeout/auth/server error detection
- **Path expansion fix**: Properly handle `~` in config paths

### ⚙️ Operation Automation

- **Scheduled reports**: Morning/evening summaries + anomaly detection
- **Job patrol**: Nightly crawling + application templates
- **Health checks**: 3-hour error monitoring via cron

---

## 🚀 Quick Start

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

## ⚙️ Configuration

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

## 🏗️ Architecture

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
│  - Memory Search                                             │
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

## 📚 Attribution

nyancobot is a fork of [nanobot](https://github.com/HKUDS/nanobot) by HKUDS.

We are deeply grateful to the original nanobot team for their elegant and lightweight foundation.

See [ATTRIBUTION.md](ATTRIBUTION.md) for detailed credits and modifications.

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

**Dual Copyright:**
- Original nanobot: Copyright (c) 2025 nanobot contributors
- nyancobot modifications: Copyright (c) 2026 nyancobot contributors

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

**Security Issues:** Please report security vulnerabilities via GitHub Security Advisories (not public issues).

---

## 🔗 Links

- **Original nanobot**: https://github.com/HKUDS/nanobot
- **Documentation**: [Coming soon]
- **Issues**: https://github.com/asiokun/nyancobot/issues
- **Discussions**: https://github.com/asiokun/nyancobot/discussions

---

## 🙏 Acknowledgments

- **HKUDS** for the original nanobot framework
- **Playwright** team for robust browser automation
- **litellm** for unified LLM provider interface
- **FastMCP** for MCP server infrastructure
- All contributors to the nyancobot project

---

**Made with ❤️ by the nyancobot community**
