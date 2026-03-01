🌍 [English](README.md) | [日本語](README_ja.md) | [中文](README_zh.md) | [한국어](README_ko.md) | [Español](README_es.md) | **Français** | [Italiano](README_it.md) | [Português](README_pt.md) | [Deutsch](README_de.md)

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

> **Framework d'agent IA sécurisé et prêt pour la production** — Un fork renforcé de [nanobot](https://github.com/HKUDS/nanobot) avec une sécurité de niveau entreprise, une collaboration multi-agents et une automatisation avancée.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## 🎯 Qu'est-ce que nyancobot ?

**nyancobot** est un framework d'agent IA open-source construit sur [nanobot](https://github.com/HKUDS/nanobot), enrichi de :

- **🔒 Sécurité de niveau production** (prévention SSRF, permissions à 4 niveaux, journalisation d'audit)
- **🤝 Orchestration multi-agents** (messagerie basée sur tmux, détection d'état, protection anti-boucle)
- **🌐 Automatisation avancée du navigateur** (Playwright + Vision + gestion sécurisée des fichiers)
- **📝 Automatisation de contenu** (reformatage, validation qualité, transcriptions YouTube)
- **🚀 Résilience des fournisseurs LLM** (chaînes de basculement, API directe Ollama, correctif Qwen3.5)

**Pourquoi nyancobot ?**
nanobot est une fondation légère et brillante (~4 000 lignes), mais les déploiements en production nécessitent un renforcement. nyancobot ajoute ~7 000 lignes de fonctionnalités de sécurité, de fiabilité et d'automatisation tout en préservant l'élégance de l'original.

---

## ✨ Fonctionnalités clés

### 🔒 Renforcement de la sécurité (Principal atout différenciant)

| Fonctionnalité | nanobot | nyancobot |
|----------------|---------|-----------|
| Prévention SSRF | ❌ | ✅ Liste blanche de domaines + blocage des IP locales |
| Niveaux de permissions | ❌ | ✅ Système à 4 niveaux (READ_ONLY → FULL) |
| Actions dangereuses | ❌ | ✅ Refus automatique des suppressions/achats/paiements/admin |
| Traversée de chemin | ❌ | ✅ Noms de fichiers assainis + validation des chemins |
| Exécution de commandes | Blocage basique | ✅ Répertoires autorisés + journaux d'audit + correctif d'expansion `~` |
| Sécurité des cookies | ❌ | ✅ Stockage persistant + séparation par domaine + permissions 0o600 |

### 🤝 Collaboration multi-agents

- **Messagerie basée sur tmux** : `send-keys` avec confirmation de livraison et retry
- **Protection anti-boucle** : Hachage MD5 + limitation à 10 secondes
- **Détection d'état** : Reconnaissance des états compaction/réflexion/inactif
- **Journalisation des communications** : Tous les messages vers un canal d'audit dédié
- **Serveurs MCP personnalisés** : 5 serveurs spécialisés (denrei, browser, vision, memory, web-tools)

### 🌐 Automatisation du navigateur

- **Support AX Tree** : Arbre d'accessibilité complet via Chrome DevTools Protocol
- **Intégration Vision** : Capture d'écran → analyse LLM → action suivante
- **Upload sécurisé de fichiers** : Validation des chemins + limite de 20 Mo
- **Extraction d'offres** : Scraping CrowdWorks/Lancers avec filtrage par mots-clés et déduplication

### 📝 Automatisation de contenu

- **Reformatage de contenu** : 1 texte → conversion automatique en X/note/Instagram/blog SEO
- **Validation qualité** : Vérifications spécifiques à chaque plateforme + détection de mots interdits + correction automatique
- **Transcriptions YouTube** : Multi-langue, limite de 50 Ko, formats d'URL flexibles

### 🚀 Améliorations des fournisseurs LLM

- **Correctif Qwen3.5 thinking** : Contournement via l'API native Ollama directe (`think:false`)
- **Chaînes de basculement** : Retry + `fallback_providers`
- **Classification des erreurs** : Détection des limites de débit/timeout/authentification/erreurs serveur
- **Correctif d'expansion de chemin** : Gestion correcte de `~` dans les chemins de configuration

### ⚙️ Automatisation des opérations

- **Rapports planifiés** : Résumés matin/soir + détection d'anomalies
- **Veille d'offres** : Crawling nocturne + modèles de candidature
- **Vérifications de santé** : Surveillance des erreurs toutes les 3 heures via cron

---

## 🚀 Démarrage rapide

### Prérequis

- Python 3.10+
- Binaires de navigateur Playwright

### Installation

```bash
# Installer depuis PyPI (à venir)
pip install nyancobot

# Ou installer depuis les sources
git clone https://github.com/asiokun/nyancobot.git
cd nyancobot
pip install -e .

# Installer les navigateurs Playwright
playwright install chromium
```

### Configuration de base

1. **Créer le fichier de configuration**

```bash
mkdir -p ~/.nyancobot/config
cp config.example.json ~/.nyancobot/config/config.json
```

2. **Définir les variables d'environnement**

```bash
export OPENAI_API_KEY="YOUR_API_KEY"
export ANTHROPIC_API_KEY="YOUR_API_KEY"  # Optionnel
export OLLAMA_BASE_URL="http://localhost:11434"  # Optionnel
```

3. **Configurer le niveau de permission du navigateur**

```bash
# Niveau 0 : READ_ONLY (sûr)
# Niveau 1 : TEST_WRITE (domaines de test uniquement)
# Niveau 2 : BROWSER_AUTO (automatisation du navigateur)
# Niveau 3 : FULL (toutes les actions)
echo "2" > ~/.nyancobot/config/permission_level.txt
```

4. **Définir les domaines autorisés** (pour la prévention SSRF)

```bash
cat > ~/.nyancobot/config/allowed_domains.txt <<EOF
example.com
httpbin.org
crowdworks.jp
lancers.jp
EOF
```

5. **Lancer nyancobot**

```bash
nyancobot
```

---

## ⚙️ Configuration

### Exemple de config.json

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

### Variables d'environnement

| Variable | Description | Valeur par défaut |
|----------|-------------|-------------------|
| `OPENAI_API_KEY` | Clé API OpenAI (obligatoire) | - |
| `ANTHROPIC_API_KEY` | Clé API Anthropic (optionnel) | - |
| `OLLAMA_BASE_URL` | URL du serveur Ollama (optionnel) | `http://localhost:11434` |
| `NYANCOBOT_CONFIG` | Chemin vers config.json | `~/.nyancobot/config/config.json` |
| `NYANCOBOT_LOG_LEVEL` | Niveau de journalisation | `INFO` |

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

### Flux de communication multi-agents

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

nyancobot est un fork de [nanobot](https://github.com/HKUDS/nanobot) par HKUDS.

Nous sommes profondément reconnaissants envers l'equipe originale de nanobot pour leur fondation elegante et legere.

Voir [ATTRIBUTION.md](ATTRIBUTION.md) pour les credits detailles et les modifications.

---

## 📄 Licence

Licence MIT - voir [LICENSE](LICENSE) pour les details.

**Double copyright :**
- nanobot original : Copyright (c) 2025 nanobot contributors
- Modifications nyancobot : Copyright (c) 2026 nyancobot contributors

---

## 🤝 Contribuer

Les contributions sont les bienvenues ! Veuillez :

1. Forker le depot
2. Creer une branche de fonctionnalite (`git checkout -b feature/amazing-feature`)
3. Commiter vos modifications (`git commit -m 'Add amazing feature'`)
4. Pousser vers la branche (`git push origin feature/amazing-feature`)
5. Ouvrir une Pull Request

**Problemes de securite :** Veuillez signaler les vulnerabilites de securite via les GitHub Security Advisories (pas via les issues publiques).

---

## 🔗 Liens

- **nanobot original** : https://github.com/HKUDS/nanobot
- **Documentation** : [Bientot disponible]
- **Issues** : https://github.com/asiokun/nyancobot/issues
- **Discussions** : https://github.com/asiokun/nyancobot/discussions

---

## 🙏 Remerciements

- **HKUDS** pour le framework nanobot original
- L'equipe **Playwright** pour l'automatisation robuste du navigateur
- **litellm** pour l'interface unifiee des fournisseurs LLM
- **FastMCP** pour l'infrastructure des serveurs MCP
- Tous les contributeurs du projet nyancobot

---

**Fait avec ❤️ par la communaute nyancobot**
