🌍 [English](README.md) | [日本語](README_ja.md) | [中文](README_zh.md) | [한국어](README_ko.md) | [Español](README_es.md) | [Français](README_fr.md) | [Italiano](README_it.md) | [Português](README_pt.md) | **Deutsch**

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

> **Sicheres, produktionsreifes KI-Agenten-Framework** — Ein gehärteter Fork von [nanobot](https://github.com/HKUDS/nanobot) mit unternehmenstauglicher Sicherheit, Multi-Agenten-Zusammenarbeit und fortgeschrittener Automatisierung.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## 🎯 Was ist nyancobot?

**nyancobot** ist ein Open-Source-KI-Agenten-Framework, das auf [nanobot](https://github.com/HKUDS/nanobot) aufbaut und erweitert wurde um:

- **🔒 Produktionsreife Sicherheit** (SSRF-Prävention, 4-stufiges Berechtigungssystem, Audit-Logging)
- **🤝 Multi-Agenten-Orchestrierung** (tmux-basiertes Messaging, Zustandserkennung, Anti-Loop-Schutz)
- **🌐 Fortgeschrittene Browser-Automatisierung** (Playwright + Vision + sichere Dateiverarbeitung)
- **📝 Inhaltsautomatisierung** (Zweitverwertung, Qualitätsvalidierung, YouTube-Transkripte)
- **🚀 LLM-Anbieter-Resilienz** (Failover-Ketten, Ollama Direct API, Qwen3.5-Fix)

**Warum nyancobot?**
nanobot ist eine brillante, leichtgewichtige Grundlage (~4.000 Zeilen), aber Produktivumgebungen erfordern Härtung. nyancobot fügt ~7.000 Zeilen an Sicherheits-, Zuverlässigkeits- und Automatisierungsfunktionen hinzu und bewahrt dabei die Eleganz des Originals.

---

## ✨ Hauptfunktionen

### 🔒 Sicherheitshärtung (Größtes Alleinstellungsmerkmal)

| Funktion | nanobot | nyancobot |
|----------|---------|-----------|
| SSRF-Prävention | ❌ | ✅ Domain-Whitelist + lokale IP-Blockierung |
| Berechtigungsstufen | ❌ | ✅ 4-stufiges System (READ_ONLY → FULL) |
| Gefährliche Aktionen | ❌ | ✅ Automatische Ablehnung von Lösch-/Kauf-/Zahlungs-/Admin-Aktionen |
| Path Traversal | ❌ | ✅ Bereinigte Dateinamen + Pfadvalidierung |
| Befehlsausführung | Einfache Ablehnung | ✅ Erlaubte Verzeichnisse + Audit-Logs + `~`-Expansions-Fix |
| Cookie-Sicherheit | ❌ | ✅ Persistente Speicherung + Domain-Trennung + 0o600-Berechtigungen |

### 🤝 Multi-Agenten-Zusammenarbeit

- **tmux-basiertes Messaging**: `send-keys` mit Zustellbestätigung & Wiederholung
- **Anti-Loop-Schutz**: MD5-Hashing + 10-Sekunden-Drosselung
- **Zustandserkennung**: Erkennung von Kompaktierung/Denkphase/Leerlauf
- **Kommunikationsprotokollierung**: Alle Nachrichten in dediziertem Audit-Kanal
- **Benutzerdefinierte MCP-Server**: 5 spezialisierte Server (denrei, browser, vision, memory, web-tools)

### 🌐 Browser-Automatisierung

- **AX-Tree-Unterstützung**: Vollständiger Accessibility Tree über Chrome DevTools Protocol
- **Vision-Integration**: Screenshot → LLM-Analyse → nächste Aktion
- **Sicherer Datei-Upload**: Pfadvalidierung + 20-MB-Limit
- **Auftragsextraktion**: CrowdWorks/Lancers-Scraping mit Schlüsselwortfilterung & Deduplizierung

### 📝 Inhaltsautomatisierung

- **Inhaltszweitverwertung**: 1 Text → X/note/Instagram/SEO-Blog automatische Konvertierung
- **Qualitätsvalidierung**: Plattformspezifische Prüfungen + NG-Wort-Erkennung + Auto-Korrektur
- **YouTube-Transkripte**: Mehrsprachig, 50-KB-Limit, flexible URL-Formate

### 🚀 LLM-Anbieter-Verbesserungen

- **Qwen3.5-Thinking-Fix**: Direkter Ollama Native API Bypass (`think:false`)
- **Failover-Ketten**: Wiederholung + `fallback_providers`
- **Fehlerklassifizierung**: Erkennung von Rate-Limit/Timeout/Auth/Server-Fehlern
- **Pfad-Expansions-Fix**: Korrekte Verarbeitung von `~` in Konfigurationspfaden

### ⚙️ Betriebsautomatisierung

- **Geplante Berichte**: Morgen-/Abend-Zusammenfassungen + Anomalieerkennung
- **Auftragspatrouille**: Nächtliches Crawling + Bewerbungsvorlagen
- **Gesundheitsprüfungen**: 3-Stunden-Fehlerüberwachung über cron

---

## 💬 Messaging-Integrationen

[![Slack](https://img.shields.io/badge/Slack-4A154B?logo=slack&logoColor=white)](https://slack.com)
[![Discord](https://img.shields.io/badge/Discord-5865F2?logo=discord&logoColor=white)](https://discord.com)
[![LINE](https://img.shields.io/badge/LINE-00C300?logo=line&logoColor=white)](https://line.me)
[![WhatsApp](https://img.shields.io/badge/WhatsApp-25D366?logo=whatsapp&logoColor=white)](https://whatsapp.com)

nyancobot unterstützt mehrere Messaging-Plattformen von Haus aus. Installieren Sie nur, was Sie benötigen:

```bash
# Bestimmte Plattform installieren
pip install nyancobot[slack]     # Nur Slack
pip install nyancobot[discord]   # Nur Discord
pip install nyancobot[line]      # Nur LINE
pip install nyancobot[whatsapp]  # Nur WhatsApp

# Alle Messaging-Plattformen installieren
pip install nyancobot[all-channels]
```

### Schnelleinrichtung

**Slack**: Bot-Token von [Slack API](https://api.slack.com/apps) erhalten → Socket Mode aktivieren → `xoxb-` und `xapp-` Tokens kopieren.

**Discord**: Bot im [Discord Developer Portal](https://discord.com/developers/applications) erstellen → Token kopieren → Message Content Intent aktivieren.

**LINE**: Kanal bei [LINE Developers](https://developers.line.biz/) erstellen → Channel Access Token und Secret erhalten → Webhook-URL einrichten.

**WhatsApp**: Bei [Meta for Developers](https://developers.facebook.com/) registrieren → Token und Phone Number ID erhalten → Webhook konfigurieren.

---

## 🚀 Schnellstart

### Voraussetzungen

- Python 3.10+
- Playwright-Browser-Binärdateien

### Installation

```bash
# Installation von PyPI (sobald veröffentlicht)
pip install nyancobot

# Oder Installation aus dem Quellcode
git clone https://github.com/asiokun/nyancobot.git
cd nyancobot
pip install -e .

# Playwright-Browser installieren
playwright install chromium
```

### Grundlegende Einrichtung

1. **Konfigurationsdatei erstellen**

```bash
mkdir -p ~/.nyancobot/config
cp config.example.json ~/.nyancobot/config/config.json
```

2. **Umgebungsvariablen setzen**

```bash
export OPENAI_API_KEY="YOUR_API_KEY"
export ANTHROPIC_API_KEY="YOUR_API_KEY"  # Optional
export OLLAMA_BASE_URL="http://localhost:11434"  # Optional
```

3. **Browser-Berechtigungsstufe konfigurieren**

```bash
# Stufe 0: READ_ONLY (sicher)
# Stufe 1: TEST_WRITE (nur Testdomains)
# Stufe 2: BROWSER_AUTO (Browser-Automatisierung)
# Stufe 3: FULL (alle Aktionen)
echo "2" > ~/.nyancobot/config/permission_level.txt
```

4. **Erlaubte Domains festlegen** (zur SSRF-Prävention)

```bash
cat > ~/.nyancobot/config/allowed_domains.txt <<EOF
example.com
httpbin.org
crowdworks.jp
lancers.jp
EOF
```

5. **nyancobot starten**

```bash
nyancobot
```

---

## ⚙️ Konfiguration

### config.json Beispiel

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

### Umgebungsvariablen

| Variable | Beschreibung | Standard |
|----------|--------------|----------|
| `OPENAI_API_KEY` | OpenAI API-Schlüssel (erforderlich) | - |
| `ANTHROPIC_API_KEY` | Anthropic API-Schlüssel (optional) | - |
| `OLLAMA_BASE_URL` | Ollama-Server-URL (optional) | `http://localhost:11434` |
| `NYANCOBOT_CONFIG` | Pfad zur config.json | `~/.nyancobot/config/config.json` |
| `NYANCOBOT_LOG_LEVEL` | Logging-Stufe | `INFO` |

---

## 🏗️ Architektur

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

### Kommunikationsfluss der Multi-Agenten

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

## 📚 Namensnennung

nyancobot ist ein Fork von [nanobot](https://github.com/HKUDS/nanobot) von HKUDS.

Wir sind dem ursprünglichen nanobot-Team zutiefst dankbar für ihre elegante und leichtgewichtige Grundlage.

Siehe [ATTRIBUTION.md](ATTRIBUTION.md) für detaillierte Danksagungen und Änderungen.

---

## 📄 Lizenz

MIT-Lizenz - siehe [LICENSE](LICENSE) für Details.

**Doppeltes Urheberrecht:**
- Originales nanobot: Copyright (c) 2025 nanobot contributors
- nyancobot-Änderungen: Copyright (c) 2026 nyancobot contributors

---

## 🤝 Mitwirken

Beiträge sind willkommen! Bitte:

1. Forke das Repository
2. Erstelle einen Feature-Branch (`git checkout -b feature/amazing-feature`)
3. Committe deine Änderungen (`git commit -m 'Add amazing feature'`)
4. Pushe zum Branch (`git push origin feature/amazing-feature`)
5. Öffne einen Pull Request

**Sicherheitsprobleme:** Bitte melde Sicherheitslücken über GitHub Security Advisories (nicht über öffentliche Issues).

---

## 🔗 Links

- **Originales nanobot**: https://github.com/HKUDS/nanobot
- **Dokumentation**: [Kommt bald]
- **Issues**: https://github.com/asiokun/nyancobot/issues
- **Discussions**: https://github.com/asiokun/nyancobot/discussions

---

## 🙏 Danksagungen

- **HKUDS** für das ursprüngliche nanobot-Framework
- **Playwright**-Team für robuste Browser-Automatisierung
- **litellm** für die einheitliche LLM-Anbieter-Schnittstelle
- **FastMCP** für die MCP-Server-Infrastruktur
- Alle Mitwirkenden am nyancobot-Projekt

---

**Mit ❤️ erstellt von der nyancobot-Community**
