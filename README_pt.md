🌍 [English](README.md) | [日本語](README_ja.md) | [中文](README_zh.md) | [한국어](README_ko.md) | [Español](README_es.md) | [Français](README_fr.md) | [Italiano](README_it.md) | **Português** | [Deutsch](README_de.md)

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

> **Framework de agente de IA seguro e pronto para produção** — Um fork reforçado do [nanobot](https://github.com/HKUDS/nanobot) com segurança de nível empresarial, colaboração multi-agente e automação avançada.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## 🎯 O que é o nyancobot?

**nyancobot** é um framework de agente de IA open-source construído sobre o [nanobot](https://github.com/HKUDS/nanobot), aprimorado com:

- **🔒 Segurança de nível de produção** (prevenção de SSRF, permissões em 4 níveis, registro de auditoria)
- **🤝 Orquestração multi-agente** (mensagens via tmux, detecção de estado, proteção anti-loop)
- **🌐 Automação avançada de navegador** (Playwright + Visão + manipulação segura de arquivos)
- **📝 Automação de conteúdo** (reaproveitamento, validação de qualidade, transcrições do YouTube)
- **🚀 Resiliência de provedores LLM** (cadeias de failover, API direta do Ollama, correção do Qwen3.5)

**Por que nyancobot?**
O nanobot é uma base leve e brilhante (~4.000 linhas), mas implantações em produção exigem um reforço de segurança. O nyancobot adiciona ~7.000 linhas de recursos de segurança, confiabilidade e automação, mantendo a elegância do original.

---

## ✨ Principais Funcionalidades

### 🔒 Reforço de Segurança (Maior Diferencial)

| Recurso | nanobot | nyancobot |
|---------|---------|-----------|
| Prevenção de SSRF | ❌ | ✅ Whitelist de domínios + bloqueio de IP local |
| Níveis de Permissão | ❌ | ✅ Sistema de 4 níveis (READ_ONLY → FULL) |
| Ações Perigosas | ❌ | ✅ Recusa automática de delete/compra/pagamento/admin |
| Path Traversal | ❌ | ✅ Sanitização de nomes de arquivo + validação de caminho |
| Execução de Comandos | Bloqueio básico | ✅ Diretórios permitidos + logs de auditoria + correção de `~` |
| Segurança de Cookies | ❌ | ✅ Armazenamento persistente + separação por domínio + permissões 0o600 |

### 🤝 Colaboração Multi-Agente

- **Mensagens via tmux**: `send-keys` com confirmação de entrega e retry
- **Proteção anti-loop**: Hashing MD5 + throttle de 10 segundos
- **Detecção de estado**: Consciência de compactação/processamento/ocioso
- **Registro de comunicação**: Todas as mensagens em canal de auditoria dedicado
- **Servidores MCP personalizados**: 5 servidores especializados (denrei, browser, vision, memory, web-tools)

### 🌐 Automação de Navegador

- **Suporte a AX Tree**: Árvore de acessibilidade completa via Chrome DevTools Protocol
- **Integração de visão**: Captura de tela → análise LLM → próxima ação
- **Upload seguro de arquivos**: Validação de caminho + limite de 20MB
- **Extração de vagas**: Scraping de CrowdWorks/Lancers com filtragem por palavras-chave e deduplicação

### 📝 Automação de Conteúdo

- **Reaproveitamento de conteúdo**: 1 texto → conversão automática para X/note/Instagram/blog SEO
- **Validação de qualidade**: Verificações específicas por plataforma + detecção de palavras proibidas + correção automática
- **Transcrições do YouTube**: Multi-idioma, limite de 50KB, formatos de URL flexíveis

### 🚀 Melhorias nos Provedores LLM

- **Correção do thinking do Qwen3.5**: Bypass direto via API nativa do Ollama (`think:false`)
- **Cadeias de failover**: Retry + `fallback_providers`
- **Classificação de erros**: Detecção de rate limit/timeout/autenticação/erro de servidor
- **Correção de expansão de caminho**: Tratamento adequado de `~` nos caminhos de configuração

### ⚙️ Automação Operacional

- **Relatórios agendados**: Resumos matinais/vespertinos + detecção de anomalias
- **Patrulha de vagas**: Crawling noturno + templates de candidatura
- **Verificações de saúde**: Monitoramento de erros a cada 3 horas via cron

---

## 💬 Integrações de Mensagens

[![Slack](https://img.shields.io/badge/Slack-4A154B?logo=slack&logoColor=white)](https://slack.com)
[![Discord](https://img.shields.io/badge/Discord-5865F2?logo=discord&logoColor=white)](https://discord.com)
[![LINE](https://img.shields.io/badge/LINE-00C300?logo=line&logoColor=white)](https://line.me)
[![WhatsApp](https://img.shields.io/badge/WhatsApp-25D366?logo=whatsapp&logoColor=white)](https://whatsapp.com)

nyancobot suporta múltiplas plataformas de mensagens nativamente. Instale apenas o que você precisa:

```bash
# Instalar plataforma específica
pip install nyancobot[slack]     # Apenas Slack
pip install nyancobot[discord]   # Apenas Discord
pip install nyancobot[line]      # Apenas LINE
pip install nyancobot[whatsapp]  # Apenas WhatsApp

# Instalar todas as plataformas de mensagens
pip install nyancobot[all-channels]
```

### Configuração Rápida

**Slack**: Obter token do bot em [Slack API](https://api.slack.com/apps) → Ativar Socket Mode → Copiar tokens `xoxb-` e `xapp-`.

**Discord**: Criar bot no [Discord Developer Portal](https://discord.com/developers/applications) → Copiar token → Ativar Message Content Intent.

**LINE**: Criar canal no [LINE Developers](https://developers.line.biz/) → Obter Channel Access Token e Secret → Configurar URL do webhook.

**WhatsApp**: Registrar no [Meta for Developers](https://developers.facebook.com/) → Obter token e Phone Number ID → Configurar webhook.

---

## 🚀 Início Rápido

### Pré-requisitos

- Python 3.10+
- Binários do navegador Playwright

### Instalação

```bash
# Instalar do PyPI (quando publicado)
pip install nyancobot

# Ou instalar a partir do código-fonte
git clone https://github.com/asiokun/nyancobot.git
cd nyancobot
pip install -e .

# Instalar navegadores do Playwright
playwright install chromium
```

### Configuração Básica

1. **Criar arquivo de configuração**

```bash
mkdir -p ~/.nyancobot/config
cp config.example.json ~/.nyancobot/config/config.json
```

2. **Definir variáveis de ambiente**

```bash
export OPENAI_API_KEY="YOUR_API_KEY"
export ANTHROPIC_API_KEY="YOUR_API_KEY"  # Opcional
export OLLAMA_BASE_URL="http://localhost:11434"  # Opcional
```

3. **Configurar nível de permissão do navegador**

```bash
# Nível 0: READ_ONLY (seguro)
# Nível 1: TEST_WRITE (apenas domínios de teste)
# Nível 2: BROWSER_AUTO (automação de navegador)
# Nível 3: FULL (todas as ações)
echo "2" > ~/.nyancobot/config/permission_level.txt
```

4. **Definir domínios permitidos** (para prevenção de SSRF)

```bash
cat > ~/.nyancobot/config/allowed_domains.txt <<EOF
example.com
httpbin.org
crowdworks.jp
lancers.jp
EOF
```

5. **Executar o nyancobot**

```bash
nyancobot
```

---

## ⚙️ Configuração

### Exemplo de config.json

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

### Variáveis de Ambiente

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `OPENAI_API_KEY` | Chave de API do OpenAI (obrigatória) | - |
| `ANTHROPIC_API_KEY` | Chave de API do Anthropic (opcional) | - |
| `OLLAMA_BASE_URL` | URL do servidor Ollama (opcional) | `http://localhost:11434` |
| `NYANCOBOT_CONFIG` | Caminho para o config.json | `~/.nyancobot/config/config.json` |
| `NYANCOBOT_LOG_LEVEL` | Nível de logging | `INFO` |

---

## 🏗️ Arquitetura

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

### Fluxo de Comunicação Multi-Agente

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

## 📚 Atribuição

nyancobot é um fork do [nanobot](https://github.com/HKUDS/nanobot) por HKUDS.

Somos profundamente gratos à equipe original do nanobot pela sua base elegante e leve.

Consulte [ATTRIBUTION.md](ATTRIBUTION.md) para créditos detalhados e modificações.

---

## 📄 Licença

Licença MIT - veja [LICENSE](LICENSE) para detalhes.

**Direitos Autorais Duplos:**
- nanobot original: Copyright (c) 2025 nanobot contributors
- Modificações do nyancobot: Copyright (c) 2026 nyancobot contributors

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Faça um fork do repositório
2. Crie um branch de funcionalidade (`git checkout -b feature/amazing-feature`)
3. Faça commit das suas alterações (`git commit -m 'Add amazing feature'`)
4. Envie para o branch (`git push origin feature/amazing-feature`)
5. Abra um Pull Request

**Problemas de Segurança:** Por favor, reporte vulnerabilidades de segurança via GitHub Security Advisories (não em issues públicas).

---

## 🔗 Links

- **nanobot original**: https://github.com/HKUDS/nanobot
- **Documentação**: [Em breve]
- **Issues**: https://github.com/asiokun/nyancobot/issues
- **Discussões**: https://github.com/asiokun/nyancobot/discussions

---

## 🙏 Agradecimentos

- **HKUDS** pelo framework original do nanobot
- Equipe do **Playwright** pela automação de navegador robusta
- **litellm** pela interface unificada de provedores LLM
- **FastMCP** pela infraestrutura de servidor MCP
- Todos os contribuidores do projeto nyancobot

---

**Feito com ❤️ pela comunidade nyancobot**
