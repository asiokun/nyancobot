🌍 [English](README.md) | **日本語** | [中文](README_zh.md) | [한국어](README_ko.md) | [Español](README_es.md) | [Français](README_fr.md) | [Italiano](README_it.md) | [Português](README_pt.md) | [Deutsch](README_de.md)

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

> **安全でプロダクション対応のAIエージェントフレームワーク** — [nanobot](https://github.com/HKUDS/nanobot) をベースに、エンタープライズグレードのセキュリティ、マルチエージェント連携、高度な自動化機能を備えたハードニング版フォーク。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## 🎯 nyancobot とは？

**nyancobot** は、[nanobot](https://github.com/HKUDS/nanobot) をベースに構築されたオープンソースのAIエージェントフレームワークです。以下の機能が強化されています：

- **🔒 プロダクショングレードのセキュリティ**（SSRF防御、4段階権限制御、監査ログ）
- **🤝 マルチエージェントオーケストレーション**（tmuxベースのメッセージング、状態検知、ループ防止）
- **🌐 高度なブラウザ自動化**（Playwright + Vision + セキュアなファイル処理）
- **📝 コンテンツ自動化**（リパーパス、品質検証、YouTube文字起こし）
- **🚀 LLMプロバイダーの耐障害性**（フェイルオーバーチェーン、Ollama直接API、Qwen3.5修正）

**なぜ nyancobot なのか？**
nanobot は約4,000行の軽量で優れた基盤ですが、本番環境へのデプロイにはハードニングが必要です。nyancobot はオリジナルの優雅さを保ちながら、約7,000行のセキュリティ・信頼性・自動化機能を追加しています。

---

## ✨ 主な機能

### 🔒 セキュリティ強化（最大の差別化要素）

| 機能 | nanobot | nyancobot |
|------|---------|-----------|
| SSRF防御 | ❌ | ✅ ドメインホワイトリスト + ローカルIPブロック |
| 権限レベル | ❌ | ✅ 4段階システム（READ_ONLY → FULL） |
| 危険な操作 | ❌ | ✅ 削除/購入/決済/管理操作を自動拒否 |
| パストラバーサル | ❌ | ✅ ファイル名サニタイズ + パス検証 |
| コマンド実行 | 基本的な拒否のみ | ✅ 許可ディレクトリ + 監査ログ + `~` 展開修正 |
| Cookie セキュリティ | ❌ | ✅ 永続ストレージ + ドメイン分離 + 0o600パーミッション |

### 🤝 マルチエージェント連携

- **tmuxベースのメッセージング**: `send-keys` による配信確認とリトライ
- **ループ防止**: MD5ハッシュ + 10秒スロットリング
- **状態検知**: コンパクション中/思考中/アイドル状態の認識
- **通信ログ**: 全メッセージを専用監査チャンネルに記録
- **カスタムMCPサーバー**: 5つの専門サーバー（denrei、browser、vision、memory、web-tools）

### 🌐 ブラウザ自動化

- **AXツリーサポート**: Chrome DevTools Protocolによるアクセシビリティツリーのフルサポート
- **Vision連携**: スクリーンショット → LLM分析 → 次のアクション
- **セキュアなファイルアップロード**: パス検証 + 20MB制限
- **案件抽出**: CrowdWorks/Lancersスクレイピング（キーワードフィルタリング・重複排除対応）

### 📝 コンテンツ自動化

- **コンテンツリパーパス**: 1つのテキスト → X/note/Instagram/SEOブログへ自動変換
- **品質検証**: プラットフォーム固有チェック + NGワード検出 + 自動修正
- **YouTube文字起こし**: 多言語対応、50KB制限、柔軟なURL形式

### 🚀 LLMプロバイダーの改善

- **Qwen3.5 thinking修正**: Ollamaネイティブ APIへの直接バイパス（`think:false`）
- **フェイルオーバーチェーン**: リトライ + `fallback_providers`
- **エラー分類**: レート制限/タイムアウト/認証/サーバーエラーの検出
- **パス展開修正**: 設定パスの `~` を正しく処理

### ⚙️ 運用自動化

- **定時レポート**: 朝・夕のサマリー + 異常検知
- **案件パトロール**: 夜間クローリング + 応募テンプレート
- **ヘルスチェック**: cronによる3時間ごとのエラー監視

---

## 🚀 クイックスタート

### 前提条件

- Python 3.10+
- Playwrightブラウザバイナリ

### インストール

```bash
# PyPIからインストール（公開後）
pip install nyancobot

# または、ソースからインストール
git clone https://github.com/asiokun/nyancobot.git
cd nyancobot
pip install -e .

# Playwrightブラウザのインストール
playwright install chromium
```

### 基本セットアップ

1. **設定ファイルの作成**

```bash
mkdir -p ~/.nyancobot/config
cp config.example.json ~/.nyancobot/config/config.json
```

2. **環境変数の設定**

```bash
export OPENAI_API_KEY="YOUR_API_KEY"
export ANTHROPIC_API_KEY="YOUR_API_KEY"  # 任意
export OLLAMA_BASE_URL="http://localhost:11434"  # 任意
```

3. **ブラウザ権限レベルの設定**

```bash
# Level 0: READ_ONLY（安全）
# Level 1: TEST_WRITE（テストドメインのみ）
# Level 2: BROWSER_AUTO（ブラウザ自動化）
# Level 3: FULL（全操作）
echo "2" > ~/.nyancobot/config/permission_level.txt
```

4. **許可ドメインの設定**（SSRF防御用）

```bash
cat > ~/.nyancobot/config/allowed_domains.txt <<EOF
example.com
httpbin.org
crowdworks.jp
lancers.jp
EOF
```

5. **nyancobot の起動**

```bash
nyancobot
```

---

## ⚙️ 設定

### config.json の例

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

### 環境変数

| 変数名 | 説明 | デフォルト値 |
|--------|------|-------------|
| `OPENAI_API_KEY` | OpenAI APIキー（必須） | - |
| `ANTHROPIC_API_KEY` | Anthropic APIキー（任意） | - |
| `OLLAMA_BASE_URL` | OllamaサーバーURL（任意） | `http://localhost:11434` |
| `NYANCOBOT_CONFIG` | config.jsonのパス | `~/.nyancobot/config/config.json` |
| `NYANCOBOT_LOG_LEVEL` | ログレベル | `INFO` |

---

## 🏗️ アーキテクチャ

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

### マルチエージェント通信フロー

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

## 📚 帰属表示

nyancobot は HKUDS による [nanobot](https://github.com/HKUDS/nanobot) のフォークです。

オリジナルの nanobot チームが築いた優雅で軽量な基盤に深く感謝いたします。

詳細なクレジットと変更点については [ATTRIBUTION.md](ATTRIBUTION.md) をご参照ください。

---

## 📄 ライセンス

MIT License - 詳細は [LICENSE](LICENSE) をご参照ください。

**デュアルコピーライト：**
- オリジナル nanobot: Copyright (c) 2025 nanobot contributors
- nyancobot の変更部分: Copyright (c) 2026 nyancobot contributors

---

## 🤝 コントリビューション

コントリビューションを歓迎します！以下の手順でお願いします：

1. リポジトリをフォーク
2. フィーチャーブランチを作成（`git checkout -b feature/amazing-feature`）
3. 変更をコミット（`git commit -m 'Add amazing feature'`）
4. ブランチにプッシュ（`git push origin feature/amazing-feature`）
5. Pull Request を作成

**セキュリティ上の問題:** セキュリティ脆弱性は、公開Issueではなく GitHub Security Advisories から報告してください。

---

## 🔗 リンク

- **オリジナル nanobot**: https://github.com/HKUDS/nanobot
- **ドキュメント**: [準備中]
- **Issues**: https://github.com/asiokun/nyancobot/issues
- **Discussions**: https://github.com/asiokun/nyancobot/discussions

---

## 🙏 謝辞

- **HKUDS** — オリジナルの nanobot フレームワーク
- **Playwright** チーム — 堅牢なブラウザ自動化
- **litellm** — 統一されたLLMプロバイダーインターフェース
- **FastMCP** — MCPサーバーインフラストラクチャ
- nyancobot プロジェクトへの全コントリビューター

---

**Made with ❤️ by the nyancobot community**
