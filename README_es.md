🌍 [English](README.md) | [日本語](README_ja.md) | [中文](README_zh.md) | [한국어](README_ko.md) | **Español** | [Français](README_fr.md) | [Italiano](README_it.md) | [Português](README_pt.md) | [Deutsch](README_de.md)

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

> **Framework de agentes de IA seguro y listo para produccion** — Un fork reforzado de [nanobot](https://github.com/HKUDS/nanobot) con seguridad de nivel empresarial, colaboracion multiagente y automatizacion avanzada.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## 🎯 Que es nyancobot?

**nyancobot** es un framework de agentes de IA de codigo abierto construido sobre [nanobot](https://github.com/HKUDS/nanobot), mejorado con:

- **🔒 Seguridad de nivel produccion** (prevencion de SSRF, permisos de 4 niveles, registro de auditoria)
- **🤝 Orquestacion multiagente** (mensajeria basada en tmux, deteccion de estado, proteccion anti-bucle)
- **🌐 Automatizacion avanzada del navegador** (Playwright + Vision + manejo seguro de archivos)
- **📝 Automatizacion de contenido** (reutilizacion, validacion de calidad, transcripciones de YouTube)
- **🚀 Resiliencia de proveedores LLM** (cadenas de failover, API directa de Ollama, correccion de Qwen3.5)

**Por que nyancobot?**
nanobot es una base ligera y brillante (~4,000 lineas), pero los despliegues en produccion requieren endurecimiento. nyancobot agrega ~7,000 lineas de funcionalidades de seguridad, fiabilidad y automatizacion manteniendo la elegancia del original.

---

## ✨ Caracteristicas principales

### 🔒 Endurecimiento de seguridad (mayor diferenciador)

| Caracteristica | nanobot | nyancobot |
|----------------|---------|-----------|
| Prevencion de SSRF | ❌ | ✅ Lista blanca de dominios + bloqueo de IP locales |
| Niveles de permisos | ❌ | ✅ Sistema de 4 niveles (READ_ONLY → FULL) |
| Acciones peligrosas | ❌ | ✅ Rechazo automatico de eliminar/comprar/pagar/admin |
| Recorrido de rutas | ❌ | ✅ Nombres de archivo saneados + validacion de rutas |
| Ejecucion de comandos | Denegacion basica | ✅ Directorios permitidos + logs de auditoria + correccion de expansion de `~` |
| Seguridad de cookies | ❌ | ✅ Almacenamiento persistente + separacion de dominios + permisos 0o600 |

### 🤝 Colaboracion multiagente

- **Mensajeria basada en tmux**: `send-keys` con confirmacion de entrega y reintentos
- **Proteccion anti-bucle**: Hashing MD5 + limitacion de 10 segundos
- **Deteccion de estado**: Reconocimiento de compactacion/procesamiento/inactividad
- **Registro de comunicaciones**: Todos los mensajes a un canal de auditoria dedicado
- **Servidores MCP personalizados**: 5 servidores especializados (denrei, browser, vision, memory, web-tools)

### 🌐 Automatizacion del navegador

- **Soporte de AX Tree**: Arbol de accesibilidad completo via Chrome DevTools Protocol
- **Integracion de Vision**: Captura de pantalla → analisis LLM → siguiente accion
- **Carga segura de archivos**: Validacion de rutas + limite de 20MB
- **Extraccion de trabajos**: Scraping de CrowdWorks/Lancers con filtrado por palabras clave y deduplicacion

### 📝 Automatizacion de contenido

- **Reutilizacion de contenido**: 1 texto → conversion automatica a X/note/Instagram/blog SEO
- **Validacion de calidad**: Verificaciones especificas por plataforma + deteccion de palabras prohibidas + correccion automatica
- **Transcripciones de YouTube**: Multi-idioma, limite de 50KB, formatos de URL flexibles

### 🚀 Mejoras de proveedores LLM

- **Correccion de pensamiento de Qwen3.5**: Bypass directo de la API nativa de Ollama (`think:false`)
- **Cadenas de failover**: Reintentos + `fallback_providers`
- **Clasificacion de errores**: Deteccion de limite de tasa/timeout/autenticacion/error de servidor
- **Correccion de expansion de rutas**: Manejo correcto de `~` en rutas de configuracion

### ⚙️ Automatizacion de operaciones

- **Informes programados**: Resumenes matutinos/vespertinos + deteccion de anomalias
- **Patrulla de trabajos**: Rastreo nocturno + plantillas de solicitud
- **Verificaciones de salud**: Monitoreo de errores cada 3 horas via cron

---

## 🚀 Inicio rapido

### Requisitos previos

- Python 3.10+
- Binarios de navegador de Playwright

### Instalacion

```bash
# Instalar desde PyPI (cuando se publique)
pip install nyancobot

# O instalar desde el codigo fuente
git clone https://github.com/asiokun/nyancobot.git
cd nyancobot
pip install -e .

# Instalar navegadores de Playwright
playwright install chromium
```

### Configuracion basica

1. **Crear archivo de configuracion**

```bash
mkdir -p ~/.nyancobot/config
cp config.example.json ~/.nyancobot/config/config.json
```

2. **Establecer variables de entorno**

```bash
export OPENAI_API_KEY="YOUR_API_KEY"
export ANTHROPIC_API_KEY="YOUR_API_KEY"  # Opcional
export OLLAMA_BASE_URL="http://localhost:11434"  # Opcional
```

3. **Configurar el nivel de permisos del navegador**

```bash
# Nivel 0: READ_ONLY (seguro)
# Nivel 1: TEST_WRITE (solo dominios de prueba)
# Nivel 2: BROWSER_AUTO (automatizacion del navegador)
# Nivel 3: FULL (todas las acciones)
echo "2" > ~/.nyancobot/config/permission_level.txt
```

4. **Establecer dominios permitidos** (para prevencion de SSRF)

```bash
cat > ~/.nyancobot/config/allowed_domains.txt <<EOF
example.com
httpbin.org
crowdworks.jp
lancers.jp
EOF
```

5. **Ejecutar nyancobot**

```bash
nyancobot
```

---

## ⚙️ Configuracion

### Ejemplo de config.json

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

### Variables de entorno

| Variable | Descripcion | Valor por defecto |
|----------|-------------|-------------------|
| `OPENAI_API_KEY` | Clave de API de OpenAI (requerida) | - |
| `ANTHROPIC_API_KEY` | Clave de API de Anthropic (opcional) | - |
| `OLLAMA_BASE_URL` | URL del servidor Ollama (opcional) | `http://localhost:11434` |
| `NYANCOBOT_CONFIG` | Ruta al config.json | `~/.nyancobot/config/config.json` |
| `NYANCOBOT_LOG_LEVEL` | Nivel de registro | `INFO` |

---

## 🏗️ Arquitectura

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

### Flujo de comunicacion multiagente

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

## 📚 Atribucion

nyancobot es un fork de [nanobot](https://github.com/HKUDS/nanobot) por HKUDS.

Estamos profundamente agradecidos al equipo original de nanobot por su base elegante y ligera.

Consulta [ATTRIBUTION.md](ATTRIBUTION.md) para creditos detallados y modificaciones.

---

## 📄 Licencia

Licencia MIT - consulta [LICENSE](LICENSE) para mas detalles.

**Doble Copyright:**
- nanobot original: Copyright (c) 2025 nanobot contributors
- Modificaciones de nyancobot: Copyright (c) 2026 nyancobot contributors

---

## 🤝 Contribuciones

Las contribuciones son bienvenidas! Por favor:

1. Haz un fork del repositorio
2. Crea una rama de funcionalidad (`git checkout -b feature/amazing-feature`)
3. Haz commit de tus cambios (`git commit -m 'Add amazing feature'`)
4. Sube la rama (`git push origin feature/amazing-feature`)
5. Abre un Pull Request

**Problemas de seguridad:** Por favor, reporta vulnerabilidades de seguridad a traves de GitHub Security Advisories (no en issues publicos).

---

## 🔗 Enlaces

- **nanobot original**: https://github.com/HKUDS/nanobot
- **Documentacion**: [Proximamente]
- **Issues**: https://github.com/asiokun/nyancobot/issues
- **Discusiones**: https://github.com/asiokun/nyancobot/discussions

---

## 🙏 Agradecimientos

- **HKUDS** por el framework original de nanobot
- Equipo de **Playwright** por la robusta automatizacion del navegador
- **litellm** por la interfaz unificada de proveedores LLM
- **FastMCP** por la infraestructura de servidores MCP
- Todos los contribuidores al proyecto nyancobot

---

**Hecho con ❤️ por la comunidad de nyancobot**
