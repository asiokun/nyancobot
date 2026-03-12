🌍 [English](README.md) | [日本語](README_ja.md) | [中文](README_zh.md) | [한국어](README_ko.md) | [Español](README_es.md) | [Français](README_fr.md) | **Italiano** | [Português](README_pt.md) | [Deutsch](README_de.md)

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

> **Framework per agenti IA sicuro e pronto per la produzione** — Un fork rafforzato di [nanobot](https://github.com/HKUDS/nanobot) con sicurezza di livello enterprise, collaborazione multi-agente e automazione avanzata.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## 🎯 Cos'è nyancobot?

**nyancobot** è un framework open-source per agenti IA costruito su [nanobot](https://github.com/HKUDS/nanobot), potenziato con:

- **🔒 Sicurezza di livello produzione** (prevenzione SSRF, permessi a 4 livelli, registrazione audit)
- **🤝 Orchestrazione multi-agente** (messaggistica basata su tmux, rilevamento dello stato, protezione anti-loop)
- **🌐 Automazione browser avanzata** (Playwright + Vision + gestione sicura dei file)
- **📝 Automazione dei contenuti** (riadattamento, validazione qualità, trascrizioni YouTube)
- **🚀 Resilienza dei provider LLM** (catene di failover, API diretta Ollama, fix per Qwen3.5)

**Perché nyancobot?**
nanobot è una base leggera e brillante (~4.000 righe), ma i deployment in produzione richiedono un rafforzamento. nyancobot aggiunge ~7.000 righe di funzionalità di sicurezza, affidabilità e automazione mantenendo l'eleganza dell'originale.

---

## ✨ Funzionalità Principali

### 🔒 Rafforzamento della Sicurezza (Principale Differenziatore)

| Funzionalità | nanobot | nyancobot |
|--------------|---------|-----------|
| Prevenzione SSRF | ❌ | ✅ Whitelist domini + blocco IP locali |
| Livelli di Permesso | ❌ | ✅ Sistema a 4 livelli (READ_ONLY → FULL) |
| Azioni Pericolose | ❌ | ✅ Rifiuto automatico eliminazione/acquisto/pagamento/admin |
| Path Traversal | ❌ | ✅ Nomi file sanitizzati + validazione percorso |
| Esecuzione Comandi | Blocco base | ✅ Directory consentite + log di audit + fix espansione `~` |
| Sicurezza Cookie | ❌ | ✅ Archiviazione persistente + separazione domini + permessi 0o600 |

### 🤝 Collaborazione Multi-Agente

- **Messaggistica basata su tmux**: `send-keys` con conferma di consegna e retry
- **Protezione anti-loop**: Hashing MD5 + throttle di 10 secondi
- **Rilevamento dello stato**: Consapevolezza degli stati compacting/thinking/idle
- **Registrazione comunicazioni**: Tutti i messaggi su canale di audit dedicato
- **Server MCP personalizzati**: 5 server specializzati (denrei, browser, vision, memory, web-tools)

### 🌐 Automazione Browser

- **Supporto AX Tree**: Albero di accessibilità completo tramite Chrome DevTools Protocol
- **Integrazione Vision**: Screenshot → analisi LLM → azione successiva
- **Upload file sicuro**: Validazione percorso + limite 20MB
- **Estrazione offerte di lavoro**: Scraping CrowdWorks/Lancers con filtro per parole chiave e deduplicazione

### 📝 Automazione dei Contenuti

- **Riadattamento contenuti**: 1 testo → conversione automatica X/note/Instagram/blog SEO
- **Validazione qualità**: Controlli specifici per piattaforma + rilevamento parole NG + correzione automatica
- **Trascrizioni YouTube**: Multi-lingua, limite 50KB, formati URL flessibili

### 🚀 Miglioramenti Provider LLM

- **Fix thinking Qwen3.5**: Bypass diretto API nativa Ollama (`think:false`)
- **Catene di failover**: Retry + `fallback_providers`
- **Classificazione errori**: Rilevamento rate limit/timeout/auth/errore server
- **Fix espansione percorso**: Gestione corretta di `~` nei percorsi di configurazione

### ⚙️ Automazione Operativa

- **Report programmati**: Riepiloghi mattutini/serali + rilevamento anomalie
- **Pattuglia offerte di lavoro**: Crawling notturno + template per candidature
- **Controlli di integrità**: Monitoraggio errori ogni 3 ore tramite cron

---

## 💬 Integrazioni Messaggistica

[![Slack](https://img.shields.io/badge/Slack-4A154B?logo=slack&logoColor=white)](https://slack.com)
[![Discord](https://img.shields.io/badge/Discord-5865F2?logo=discord&logoColor=white)](https://discord.com)
[![LINE](https://img.shields.io/badge/LINE-00C300?logo=line&logoColor=white)](https://line.me)
[![WhatsApp](https://img.shields.io/badge/WhatsApp-25D366?logo=whatsapp&logoColor=white)](https://whatsapp.com)

nyancobot supporta nativamente diverse piattaforme di messaggistica. Installa solo quelle di cui hai bisogno:

```bash
# Installare una piattaforma specifica
pip install nyancobot[slack]     # Solo Slack
pip install nyancobot[discord]   # Solo Discord
pip install nyancobot[line]      # Solo LINE
pip install nyancobot[whatsapp]  # Solo WhatsApp

# Installare tutte le piattaforme di messaggistica
pip install nyancobot[all-channels]
```

### Configurazione Rapida

**Slack**: Ottenere il token del bot da [Slack API](https://api.slack.com/apps) → Attivare Socket Mode → Copiare i token `xoxb-` e `xapp-`.

**Discord**: Creare un bot nel [Discord Developer Portal](https://discord.com/developers/applications) → Copiare il token → Attivare Message Content Intent.

**LINE**: Creare un canale su [LINE Developers](https://developers.line.biz/) → Ottenere Channel Access Token e Secret → Impostare l'URL del webhook.

**WhatsApp**: Registrarsi su [Meta for Developers](https://developers.facebook.com/) → Ottenere token e Phone Number ID → Configurare il webhook.

---

## 🚀 Guida Rapida

### Prerequisiti

- Python 3.10+
- Binary di browser Playwright

### Installazione

```bash
# Installa da PyPI (quando pubblicato)
pip install nyancobot

# Oppure installa dal sorgente
git clone https://github.com/asiokun/nyancobot.git
cd nyancobot
pip install -e .

# Installa i browser Playwright
playwright install chromium
```

### Configurazione Base

1. **Crea il file di configurazione**

```bash
mkdir -p ~/.nyancobot/config
cp config.example.json ~/.nyancobot/config/config.json
```

2. **Imposta le variabili d'ambiente**

```bash
export OPENAI_API_KEY="YOUR_API_KEY"
export ANTHROPIC_API_KEY="YOUR_API_KEY"  # Opzionale
export OLLAMA_BASE_URL="http://localhost:11434"  # Opzionale
```

3. **Configura il livello di permesso del browser**

```bash
# Livello 0: READ_ONLY (sicuro)
# Livello 1: TEST_WRITE (solo domini di test)
# Livello 2: BROWSER_AUTO (automazione browser)
# Livello 3: FULL (tutte le azioni)
echo "2" > ~/.nyancobot/config/permission_level.txt
```

4. **Imposta i domini consentiti** (per la prevenzione SSRF)

```bash
cat > ~/.nyancobot/config/allowed_domains.txt <<EOF
example.com
httpbin.org
crowdworks.jp
lancers.jp
EOF
```

5. **Avvia nyancobot**

```bash
nyancobot
```

---

## ⚙️ Configurazione

### Esempio config.json

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

### Variabili d'Ambiente

| Variabile | Descrizione | Default |
|-----------|-------------|---------|
| `OPENAI_API_KEY` | Chiave API OpenAI (obbligatoria) | - |
| `ANTHROPIC_API_KEY` | Chiave API Anthropic (opzionale) | - |
| `OLLAMA_BASE_URL` | URL del server Ollama (opzionale) | `http://localhost:11434` |
| `NYANCOBOT_CONFIG` | Percorso del config.json | `~/.nyancobot/config/config.json` |
| `NYANCOBOT_LOG_LEVEL` | Livello di logging | `INFO` |

---

## 🏗️ Architettura

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

### Flusso di Comunicazione Multi-Agente

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

## 📚 Attribuzioni

nyancobot è un fork di [nanobot](https://github.com/HKUDS/nanobot) di HKUDS.

Siamo profondamente grati al team originale di nanobot per la loro base elegante e leggera.

Consulta [ATTRIBUTION.md](ATTRIBUTION.md) per crediti dettagliati e modifiche.

---

## 📄 Licenza

Licenza MIT - consulta [LICENSE](LICENSE) per i dettagli.

**Doppio Copyright:**
- nanobot originale: Copyright (c) 2025 nanobot contributors
- Modifiche nyancobot: Copyright (c) 2026 nyancobot contributors

---

## 🤝 Contribuire

I contributi sono benvenuti! Per favore:

1. Fai un fork del repository
2. Crea un branch per la funzionalità (`git checkout -b feature/amazing-feature`)
3. Effettua il commit delle modifiche (`git commit -m 'Add amazing feature'`)
4. Fai push sul branch (`git push origin feature/amazing-feature`)
5. Apri una Pull Request

**Problemi di Sicurezza:** Segnala le vulnerabilità di sicurezza tramite GitHub Security Advisories (non tramite issue pubbliche).

---

## 🔗 Link

- **nanobot originale**: https://github.com/HKUDS/nanobot
- **Documentazione**: [In arrivo]
- **Issue**: https://github.com/asiokun/nyancobot/issues
- **Discussioni**: https://github.com/asiokun/nyancobot/discussions

---

## 🙏 Ringraziamenti

- **HKUDS** per il framework originale nanobot
- Il team di **Playwright** per la robusta automazione browser
- **litellm** per l'interfaccia unificata dei provider LLM
- **FastMCP** per l'infrastruttura dei server MCP
- Tutti i contributori al progetto nyancobot

---

**Realizzato con ❤️ dalla community di nyancobot**
