🌍 [English](README.md) | [日本語](README_ja.md) | **中文** | [한국어](README_ko.md) | [Español](README_es.md) | [Français](README_fr.md) | [Italiano](README_it.md) | [Português](README_pt.md) | [Deutsch](README_de.md)

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

> **安全、生产就绪的 AI 智能体框架** — 基于 [nanobot](https://github.com/HKUDS/nanobot) 的强化分支，提供企业级安全防护、多智能体协作和高级自动化能力。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## 🎯 什么是 nyancobot？

**nyancobot** 是一个基于 [nanobot](https://github.com/HKUDS/nanobot) 构建的开源 AI 智能体框架，新增了以下增强功能：

- **🔒 生产级安全防护**（SSRF 防御、四级权限体系、审计日志）
- **🤝 多智能体协作编排**（基于 tmux 的消息传递、状态检测、防循环保护）
- **🌐 高级浏览器自动化**（Playwright + 视觉识别 + 安全文件处理）
- **📝 内容自动化**（内容改写分发、质量验证、YouTube 字幕提取）
- **🚀 LLM 提供商容灾**（故障转移链、Ollama 直连 API、Qwen3.5 修复）

**为什么选择 nyancobot？**
nanobot 是一个出色的轻量级基础框架（约 4,000 行代码），但生产环境部署需要更强的安全加固。nyancobot 在保持原项目简洁优雅的同时，新增了约 7,000 行安全、可靠性和自动化功能代码。

---

## ✨ 核心特性

### 🔒 安全加固（最大差异化优势）

| 特性 | nanobot | nyancobot |
|------|---------|-----------|
| SSRF 防御 | ❌ | ✅ 域名白名单 + 本地 IP 拦截 |
| 权限级别 | ❌ | ✅ 四级体系（READ_ONLY → FULL） |
| 危险操作拦截 | ❌ | ✅ 自动拒绝删除/购买/支付/管理员操作 |
| 路径遍历防护 | ❌ | ✅ 文件名消毒 + 路径验证 |
| 命令执行 | 基础拒绝 | ✅ 允许目录 + 审计日志 + `~` 展开修复 |
| Cookie 安全 | ❌ | ✅ 持久化存储 + 域名隔离 + 0o600 权限 |

### 🤝 多智能体协作

- **基于 tmux 的消息传递**：`send-keys` 支持投递确认和重试
- **防循环保护**：MD5 哈希 + 10 秒节流
- **状态检测**：感知压缩中/思考中/空闲状态
- **通信日志**：所有消息记录到专用审计频道
- **自定义 MCP 服务器**：5 个专用服务器（denrei、browser、vision、memory、web-tools）

### 🌐 浏览器自动化

- **AX Tree 支持**：通过 Chrome DevTools Protocol 获取完整无障碍树
- **视觉集成**：截图 → LLM 分析 → 下一步操作
- **安全文件上传**：路径验证 + 20MB 限制
- **任务抓取**：CrowdWorks/Lancers 页面抓取，支持关键词过滤和去重

### 📝 内容自动化

- **内容改写分发**：一篇文本 → 自动转换为 X/note/Instagram/SEO 博客
- **质量验证**：平台专属检查 + 违禁词检测 + 自动修复
- **YouTube 字幕提取**：多语言支持，50KB 限制，灵活的 URL 格式

### 🚀 LLM 提供商改进

- **Qwen3.5 思考模式修复**：直接调用 Ollama 原生 API 绕过（`think:false`）
- **故障转移链**：重试 + `fallback_providers`
- **错误分类**：速率限制/超时/认证/服务器错误检测
- **路径展开修复**：正确处理配置路径中的 `~`

### ⚙️ 运维自动化

- **定时报告**：早晚汇总 + 异常检测
- **任务巡逻**：每晚爬取 + 申请模板
- **健康检查**：通过 cron 每 3 小时进行错误监控

---

## 💬 消息平台集成

[![Slack](https://img.shields.io/badge/Slack-4A154B?logo=slack&logoColor=white)](https://slack.com)
[![Discord](https://img.shields.io/badge/Discord-5865F2?logo=discord&logoColor=white)](https://discord.com)
[![LINE](https://img.shields.io/badge/LINE-00C300?logo=line&logoColor=white)](https://line.me)
[![WhatsApp](https://img.shields.io/badge/WhatsApp-25D366?logo=whatsapp&logoColor=white)](https://whatsapp.com)

nyancobot 开箱即支持多个消息平台。只需安装所需的平台：

```bash
# 安装特定平台
pip install nyancobot[slack]     # 仅 Slack
pip install nyancobot[discord]   # 仅 Discord
pip install nyancobot[line]      # 仅 LINE
pip install nyancobot[whatsapp]  # 仅 WhatsApp

# 安装所有消息平台
pip install nyancobot[all-channels]
```

### 快速设置

**Slack**：从 [Slack API](https://api.slack.com/apps) 获取机器人令牌 → 启用 Socket Mode → 复制 `xoxb-` 和 `xapp-` 令牌。

**Discord**：在 [Discord Developer Portal](https://discord.com/developers/applications) 创建机器人 → 复制令牌 → 启用 Message Content Intent。

**LINE**：在 [LINE Developers](https://developers.line.biz/) 创建频道 → 获取 Channel Access Token 和 Secret → 设置 webhook URL。

**WhatsApp**：在 [Meta for Developers](https://developers.facebook.com/) 注册 → 获取令牌和 Phone Number ID → 配置 webhook。

### 配置

更新 `~/.nyancobot/config/config.json`：

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

## 🚀 快速开始

### 前置要求

- Python 3.10+
- Playwright 浏览器内核

### 安装

```bash
# 从 PyPI 安装（发布后可用）
pip install nyancobot

# 或从源码安装
git clone https://github.com/asiokun/nyancobot.git
cd nyancobot
pip install -e .

# 安装 Playwright 浏览器
playwright install chromium
```

### 基本配置

1. **创建配置文件**

```bash
mkdir -p ~/.nyancobot/config
cp config.example.json ~/.nyancobot/config/config.json
```

2. **设置环境变量**

```bash
export OPENAI_API_KEY="YOUR_API_KEY"
export ANTHROPIC_API_KEY="YOUR_API_KEY"  # 可选
export OLLAMA_BASE_URL="http://localhost:11434"  # 可选
```

3. **配置浏览器权限级别**

```bash
# Level 0: READ_ONLY（安全模式）
# Level 1: TEST_WRITE（仅限测试域名）
# Level 2: BROWSER_AUTO（浏览器自动化）
# Level 3: FULL（全部操作）
echo "2" > ~/.nyancobot/config/permission_level.txt
```

4. **设置允许域名**（用于 SSRF 防御）

```bash
cat > ~/.nyancobot/config/allowed_domains.txt <<EOF
example.com
httpbin.org
crowdworks.jp
lancers.jp
EOF
```

5. **启动 nyancobot**

```bash
nyancobot
```

---

## ⚙️ 配置说明

### config.json 示例

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

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OPENAI_API_KEY` | OpenAI API 密钥（必填） | - |
| `ANTHROPIC_API_KEY` | Anthropic API 密钥（可选） | - |
| `OLLAMA_BASE_URL` | Ollama 服务器地址（可选） | `http://localhost:11434` |
| `NYANCOBOT_CONFIG` | config.json 路径 | `~/.nyancobot/config/config.json` |
| `NYANCOBOT_LOG_LEVEL` | 日志级别 | `INFO` |

---

## 🏗️ 架构

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

### 多智能体通信流程

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

## 📚 致谢声明

nyancobot 是 HKUDS 开发的 [nanobot](https://github.com/HKUDS/nanobot) 的分支项目。

我们衷心感谢 nanobot 原始团队打造的优雅而轻量的基础框架。

详细的致谢信息和修改说明请参阅 [ATTRIBUTION.md](ATTRIBUTION.md)。

---

## 📄 许可证

MIT 许可证 - 详情请参阅 [LICENSE](LICENSE)。

**双重版权：**
- 原始 nanobot：Copyright (c) 2025 nanobot contributors
- nyancobot 修改部分：Copyright (c) 2026 nyancobot contributors

---

## 🤝 参与贡献

欢迎贡献代码！请按照以下步骤操作：

1. Fork 本仓库
2. 创建功能分支（`git checkout -b feature/amazing-feature`）
3. 提交更改（`git commit -m 'Add amazing feature'`）
4. 推送到分支（`git push origin feature/amazing-feature`）
5. 创建 Pull Request

**安全问题：** 请通过 GitHub Security Advisories 报告安全漏洞（请勿使用公开 Issues）。

---

## 🔗 相关链接

- **原始 nanobot**：https://github.com/HKUDS/nanobot
- **文档**：[即将上线]
- **Issues**：https://github.com/asiokun/nyancobot/issues
- **Discussions**：https://github.com/asiokun/nyancobot/discussions

---

## 🙏 鸣谢

- **HKUDS** 提供了原始的 nanobot 框架
- **Playwright** 团队提供了强大的浏览器自动化工具
- **litellm** 提供了统一的 LLM 提供商接口
- **FastMCP** 提供了 MCP 服务器基础设施
- 所有为 nyancobot 项目做出贡献的开发者

---

**由 nyancobot 社区用 ❤️ 打造**
