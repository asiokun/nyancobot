# nyancobot

🌍 [English](README.md) | [日本語](README_ja.md) | [中文](README_zh.md) | **한국어** | [Español](README_es.md) | [Français](README_fr.md) | [Italiano](README_it.md) | [Português](README_pt.md) | [Deutsch](README_de.md)

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

> **안전하고 프로덕션에 바로 투입 가능한 AI 에이전트 프레임워크** — [nanobot](https://github.com/HKUDS/nanobot)을 기반으로, 엔터프라이즈급 보안, 멀티 에이전트 협업, 고급 자동화 기능을 강화한 포크입니다.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## 🎯 nyancobot이란?

**nyancobot**은 [nanobot](https://github.com/HKUDS/nanobot)을 기반으로 구축된 오픈소스 AI 에이전트 프레임워크로, 다음과 같은 기능이 강화되었습니다:

- **🔒 프로덕션급 보안** (SSRF 방지, 4단계 권한 체계, 감사 로깅)
- **🤝 멀티 에이전트 오케스트레이션** (tmux 기반 메시징, 상태 감지, 무한 루프 방지)
- **🌐 고급 브라우저 자동화** (Playwright + Vision + 안전한 파일 처리)
- **📝 콘텐츠 자동화** (리퍼포싱, 품질 검증, YouTube 자막 추출)
- **🚀 LLM 프로바이더 복원력** (페일오버 체인, Ollama 직접 API, Qwen3.5 수정)

**왜 nyancobot인가?**
nanobot은 뛰어난 경량 기반(약 4,000줄)이지만, 프로덕션 배포에는 보안 강화가 필수적입니다. nyancobot은 원본의 우아함을 유지하면서 약 7,000줄의 보안, 안정성, 자동화 기능을 추가했습니다.

---

## ✨ 주요 기능

### 🔒 보안 강화 (최대 차별점)

| 기능 | nanobot | nyancobot |
|------|---------|-----------|
| SSRF 방지 | ❌ | ✅ 도메인 화이트리스트 + 로컬 IP 차단 |
| 권한 수준 | ❌ | ✅ 4단계 시스템 (READ_ONLY → FULL) |
| 위험 동작 차단 | ❌ | ✅ 삭제/구매/결제/관리자 작업 자동 거부 |
| 경로 탐색 공격 방지 | ❌ | ✅ 파일명 살균 + 경로 검증 |
| 명령어 실행 | 기본 차단 | ✅ 허용 디렉토리 + 감사 로그 + `~` 확장 수정 |
| 쿠키 보안 | ❌ | ✅ 영속 저장 + 도메인 분리 + 0o600 권한 |

### 🤝 멀티 에이전트 협업

- **tmux 기반 메시징**: `send-keys`를 활용한 전달 확인 및 재시도
- **무한 루프 방지**: MD5 해싱 + 10초 쓰로틀링
- **상태 감지**: 압축 중/사고 중/유휴 상태 인식
- **통신 로깅**: 모든 메시지를 전용 감사 채널에 기록
- **커스텀 MCP 서버**: 5개의 전문 서버 (denrei, browser, vision, memory, web-tools)

### 🌐 브라우저 자동화

- **AX Tree 지원**: Chrome DevTools Protocol을 통한 전체 접근성 트리
- **Vision 연동**: 스크린샷 → LLM 분석 → 다음 동작 결정
- **안전한 파일 업로드**: 경로 검증 + 20MB 제한
- **구인 정보 추출**: CrowdWorks/Lancers 스크래핑, 키워드 필터링 및 중복 제거

### 📝 콘텐츠 자동화

- **콘텐츠 리퍼포싱**: 1개의 텍스트 → X/note/Instagram/SEO 블로그 자동 변환
- **품질 검증**: 플랫폼별 검사 + NG 단어 감지 + 자동 수정
- **YouTube 자막 추출**: 다국어 지원, 50KB 제한, 유연한 URL 형식

### 🚀 LLM 프로바이더 개선

- **Qwen3.5 thinking 수정**: Ollama 네이티브 API 직접 바이패스 (`think:false`)
- **페일오버 체인**: 재시도 + `fallback_providers`
- **에러 분류**: 속도 제한/타임아웃/인증/서버 에러 감지
- **경로 확장 수정**: 설정 경로의 `~` 올바른 처리

### ⚙️ 운영 자동화

- **정기 보고서**: 오전/저녁 요약 + 이상 감지
- **구인 순찰**: 야간 크롤링 + 지원 템플릿
- **헬스 체크**: cron을 통한 3시간 간격 에러 모니터링

---

## 💬 메시징 플랫폼 연동

[![Slack](https://img.shields.io/badge/Slack-4A154B?logo=slack&logoColor=white)](https://slack.com)
[![Discord](https://img.shields.io/badge/Discord-5865F2?logo=discord&logoColor=white)](https://discord.com)
[![LINE](https://img.shields.io/badge/LINE-00C300?logo=line&logoColor=white)](https://line.me)
[![WhatsApp](https://img.shields.io/badge/WhatsApp-25D366?logo=whatsapp&logoColor=white)](https://whatsapp.com)

nyancobot은 여러 메시징 플랫폼을 기본 지원합니다. 필요한 것만 설치할 수 있습니다:

```bash
# 특정 플랫폼만 설치
pip install nyancobot[slack]     # Slack만
pip install nyancobot[discord]   # Discord만
pip install nyancobot[line]      # LINE만
pip install nyancobot[whatsapp]  # WhatsApp만

# 모든 메시징 플랫폼 설치
pip install nyancobot[all-channels]
```

### 빠른 설정

**Slack**: [Slack API](https://api.slack.com/apps)에서 봇 토큰 획득 → Socket Mode 활성화 → `xoxb-`와 `xapp-` 토큰 복사.

**Discord**: [Discord Developer Portal](https://discord.com/developers/applications)에서 봇 생성 → 토큰 복사 → Message Content Intent 활성화.

**LINE**: [LINE Developers](https://developers.line.biz/)에서 채널 생성 → Channel Access Token과 Secret 획득 → Webhook URL 설정.

**WhatsApp**: [Meta for Developers](https://developers.facebook.com/)에서 등록 → 토큰과 Phone Number ID 획득 → Webhook 설정.

### 설정 방법

`~/.nyancobot/config/config.json` 업데이트:

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

## 🚀 빠른 시작

### 사전 요구 사항

- Python 3.10+
- Playwright 브라우저 바이너리

### 설치

```bash
# PyPI에서 설치 (공개 후)
pip install nyancobot

# 또는 소스에서 설치
git clone https://github.com/asiokun/nyancobot.git
cd nyancobot
pip install -e .

# Playwright 브라우저 설치
playwright install chromium
```

### 기본 설정

1. **설정 파일 생성**

```bash
mkdir -p ~/.nyancobot/config
cp config.example.json ~/.nyancobot/config/config.json
```

2. **환경 변수 설정**

```bash
export OPENAI_API_KEY="YOUR_API_KEY"
export ANTHROPIC_API_KEY="YOUR_API_KEY"  # 선택 사항
export OLLAMA_BASE_URL="http://localhost:11434"  # 선택 사항
```

3. **브라우저 권한 수준 설정**

```bash
# Level 0: READ_ONLY (안전)
# Level 1: TEST_WRITE (테스트 도메인만)
# Level 2: BROWSER_AUTO (브라우저 자동화)
# Level 3: FULL (모든 동작)
echo "2" > ~/.nyancobot/config/permission_level.txt
```

4. **허용 도메인 설정** (SSRF 방지용)

```bash
cat > ~/.nyancobot/config/allowed_domains.txt <<EOF
example.com
httpbin.org
crowdworks.jp
lancers.jp
EOF
```

5. **nyancobot 실행**

```bash
nyancobot
```

---

## ⚙️ 설정

### config.json 예시

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

### 환경 변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `OPENAI_API_KEY` | OpenAI API 키 (필수) | - |
| `ANTHROPIC_API_KEY` | Anthropic API 키 (선택 사항) | - |
| `OLLAMA_BASE_URL` | Ollama 서버 URL (선택 사항) | `http://localhost:11434` |
| `NYANCOBOT_CONFIG` | config.json 경로 | `~/.nyancobot/config/config.json` |
| `NYANCOBOT_LOG_LEVEL` | 로깅 수준 | `INFO` |

---

## 🏗️ 아키텍처

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

### 멀티 에이전트 통신 흐름

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

## 📚 출처 표기

nyancobot은 HKUDS의 [nanobot](https://github.com/HKUDS/nanobot) 포크입니다.

우아하고 경량인 기반을 제공해 주신 원본 nanobot 팀에 깊은 감사를 드립니다.

자세한 크레딧 및 수정 사항은 [ATTRIBUTION.md](ATTRIBUTION.md)를 참조하세요.

---

## 📄 라이선스

MIT License - 자세한 내용은 [LICENSE](LICENSE)를 참조하세요.

**이중 저작권:**
- 원본 nanobot: Copyright (c) 2025 nanobot contributors
- nyancobot 수정본: Copyright (c) 2026 nyancobot contributors

---

## 🤝 기여하기

기여를 환영합니다! 다음 절차를 따라 주세요:

1. 리포지토리를 포크합니다
2. 기능 브랜치를 생성합니다 (`git checkout -b feature/amazing-feature`)
3. 변경 사항을 커밋합니다 (`git commit -m 'Add amazing feature'`)
4. 브랜치에 푸시합니다 (`git push origin feature/amazing-feature`)
5. Pull Request를 생성합니다

**보안 문제:** 보안 취약점은 공개 이슈가 아닌 GitHub Security Advisories를 통해 신고해 주세요.

---

## 🔗 링크

- **원본 nanobot**: https://github.com/HKUDS/nanobot
- **문서**: [준비 중]
- **이슈**: https://github.com/asiokun/nyancobot/issues
- **토론**: https://github.com/asiokun/nyancobot/discussions

---

## 🙏 감사의 말

- **HKUDS** - 원본 nanobot 프레임워크 제공
- **Playwright** 팀 - 강력한 브라우저 자동화
- **litellm** - 통합 LLM 프로바이더 인터페이스
- **FastMCP** - MCP 서버 인프라
- nyancobot 프로젝트에 기여해 주신 모든 분들

---

**nyancobot 커뮤니티가 정성을 담아 만들었습니다 ❤️**
