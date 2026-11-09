# Raccoon Daily

**Raccoon のデイリークレジット、QR ログイン、請求確認、複数アカウントに対応する単一ファイルツール。**

[简体中文](../README.md) | [English](README.en.md) | [繁體中文](README.zh-Hant.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Português (BR)](README.pt-BR.md)

> これは日本語クイックガイドです。すべての設定とトラブルシューティングは[簡体字中国語 README](../README.md)を参照してください。

## 概要

| 項目 | 内容 |
| :--- | :--- |
| 目的 | 毎日のクレジット受取と初回デスクトップ / モバイルログイン報酬の取得 |
| 認証情報 | `RACCOON_TOKENS`、推奨形式は `name\|token\|refresh_token` |
| 実行環境 | Python 3.8+、Qinglong、ローカル cron、GitHub Actions |
| 依存関係 | `requests`、端末 QR 表示には任意で `qrcode` |
| 成功判定 | 本日の有効な `daily_grant`、または有効期限切れ・消去済みでないデイリークレジット |

## 収録スクリプト

- `raccoon_login.py`: QR ログイン、旧 Web 認可、デスクトップ auth の取り込み。
- `raccoon_daily.py`: デイリークレジット、請求確認、初回报酬、通知。

## クイックスタート

```bash
pip install requests
python raccoon_login.py
```

認証情報を設定します。

```text
RACCOON_TOKENS=name|token|refresh_token
```

Qinglong タスク:

```bash
python raccoon_daily.py
```

推奨スケジュール:

```cron
30 8 * * *
```

## GitHub Actions

Fork 後、**Settings > Secrets and variables > Actions** に `RACCOON_TOKENS` を追加します。通知には `PUSHPLUS_TOKEN`、`BARK_URL`、`WECOM_WEBHOOK`、`DINGTALK_WEBHOOK`、`DINGTALK_SECRET` を利用できます。最初は手動実行で確認してください。

## 主な変数

| 変数 | 用途 |
| :--- | :--- |
| `RACCOON_TOKENS` | 複数アカウント。改行または `&` 区切り |
| `RACCOON_STATE_FILE` | 初回报酬状態ファイルの任意パス |
| `RACCOON_TOKEN_FILE` | Token ローテーションキャッシュの任意パス |
| `PUSHPLUS_TOKEN`、`BARK_URL`、`WECOM_WEBHOOK`、`DINGTALK_WEBHOOK` | 任意の通知設定 |

`--query` は請求確認のみ、`--skip-onboarding` は初回报酬を省略、`--only 2` は 2 番目のアカウントのみ実行します。

## セキュリティ

Token、キャッシュ、状態ファイルを Git に保存しないでください。環境変数または暗号化された Secrets を使用してください。

## 利用範囲と再配布について

公式リポジトリ、スクリプト、ドキュメント、Releases は無料で公開されています。有料リソースへの再包装、著作者表示の削除、作者のなりすまし、作者名や QR コードによる推薦表現、無関係なアカウントやグループへの転載による集客は禁止です。詳細は[利用範囲と再配布に関する通知](../NOTICE.md)を参照してください。違反時は削除要請の対象となり、作者は更新停止、アーカイブ、リポジトリ削除を行う場合があります。

## リンク

- [Releases](https://github.com/L0NE-6/Raccoon-Daily/releases)
- [Issues](https://github.com/L0NE-6/Raccoon-Daily/issues)
- [変更履歴](../CHANGELOG.md)
- [完全な中国語ドキュメント](../README.md)
