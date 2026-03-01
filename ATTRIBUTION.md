# Attribution

## Original Project

**nyancobot** is a fork of [nanobot](https://github.com/HKUDS/nanobot) by HKUDS (HKU Data Science Lab).

The original **nanobot** project is licensed under the MIT License.

We are deeply grateful to the nanobot team for creating such an elegant and lightweight foundation for AI agent development.

---

## What We Changed

nyancobot builds upon nanobot with significant enhancements focused on **security**, **multi-agent collaboration**, and **production readiness**.

### Major Modifications (~7,000 lines added/modified)

#### 1. Security Hardening
- **SSRF Prevention**: Domain whitelist + local IP blocking
- **Permission Levels**: 4-tier access control system (Level 0-3)
- **Dangerous Operation Blocking**: Auto-refuse delete/purchase/payment/admin actions
- **Path Traversal Protection**: Sanitized screenshot/cookie names, secure file upload
- **Command Execution Guards**: Allowed directories, audit logging, path expansion fixes
- **Cookie Management**: Persistent storage, domain separation, secure permissions

#### 2. Multi-Agent Communication
- **tmux-based messaging**: send-keys with delivery confirmation and retry
- **Anti-loop protection**: MD5 hashing + 10-second throttle for duplicate messages
- **State detection**: Compacting/thinking/idle awareness
- **Communication logging**: All messages logged to dedicated channel
- **Custom MCP servers**: 5 specialized servers for agent coordination

#### 3. Browser Automation
- **AX Tree support**: Full accessibility tree via Chrome DevTools Protocol
- **Vision integration**: Screenshot → LLM analysis → action decision
- **Secure file upload**: Path validation + size limits
- **Job extraction**: CrowdWorks/Lancers scraping with filtering and deduplication

#### 4. Content Automation
- **Content repurpose**: 1 source → X/note/Instagram/SEO Blog auto-conversion
- **Quality validation**: Platform-specific checks + NG word detection + auto-fix
- **YouTube transcripts**: Multi-language support, 50KB limit, flexible URL formats

#### 5. LLM Provider Improvements
- **Qwen3.5 thinking fix**: Direct Ollama native API bypass (think:false)
- **Failover chains**: Retry + fallback_providers
- **Error classification**: Rate limit/timeout/auth/server error auto-detection
- **Path expansion bug fix**: Properly handle `~` in paths (expanduser + resolve)

#### 6. Operation Automation
- **Scheduled reports**: Morning/evening summaries + anomaly detection (cron jobs)
- **Job patrol**: Nightly crawling + application templates
- **Health checks**: 3-hour error monitoring

---

## Differences from nanobot

| Feature | nanobot | nyancobot |
|---------|---------|-----------|
| Codebase size | ~4,000 lines | ~11,000 lines |
| Security features | Basic | Production-grade (4-tier permissions, SSRF prevention) |
| Multi-agent support | No | Yes (tmux-based messaging, state detection) |
| Browser automation | Basic Playwright | Advanced (AX Tree, Vision, secure upload) |
| Content automation | No | Yes (repurpose, quality check, YouTube) |
| LLM providers | litellm | litellm + Ollama direct + failover |
| Production readiness | Prototype | Production (audit logs, health checks, cron jobs) |

---

## Acknowledgments

We acknowledge and respect the original nanobot project and its contributors. Without their excellent foundation, nyancobot would not exist.

Original project: https://github.com/HKUDS/nanobot

---

## License

Both nanobot and nyancobot modifications are released under the MIT License. See [LICENSE](LICENSE) for details.
