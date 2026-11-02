# Raccoon Daily

**小浣熊每日積分、微信掃碼登入、帳單核對與多帳號的單檔案青龍腳本。**

[简体中文](../README.md) | [English](README.en.md) | [繁體中文](README.zh-Hant.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Português (BR)](README.pt-BR.md)

> 本頁是繁體中文快速指南；完整選項與排錯請看[簡體中文 README](../README.md)。

## 快速概覽

| 項目 | 說明 |
| :--- | :--- |
| 用途 | 領取每日積分，補領首次電腦端 / 手機端登入獎勵 |
| 憑證 | `RACCOON_TOKENS`，建議格式 `備註\|token\|refresh_token` |
| 執行環境 | Python 3.8+、青龍、本機 cron、GitHub Actions |
| 依賴 | `requests`；終端二維碼可選 `qrcode` |
| 成功判據 | 帳單中必須真實出現今日入帳 |

## 內含腳本

- `raccoon_login.py`：掃碼登入、舊版網頁授權、桌面端 auth 匯入。
- `raccoon_daily.py`：每日積分、帳單核對、新手獎勵與推送。

## 快速開始

```bash
pip install requests
python raccoon_login.py
```

設定：

```text
RACCOON_TOKENS=備註|token|refresh_token
```

青龍定時任務：

```bash
python raccoon_daily.py
```

建議排程：

```cron
30 8 * * *
```

## GitHub Actions

Fork 後在 **Settings > Secrets and variables > Actions** 新增 `RACCOON_TOKENS`。可選推送 Secrets 包括 `PUSHPLUS_TOKEN`、`BARK_URL`、`WECOM_WEBHOOK`、`DINGTALK_WEBHOOK` 與 `DINGTALK_SECRET`。工作流預設手動觸發，驗證成功後再自行開啟排程。

## 重要變數

| 變數 | 用途 |
| :--- | :--- |
| `RACCOON_TOKENS` | 多帳號，換行或 `&` 分隔 |
| `RACCOON_STATE_FILE` | 可選新手獎勵狀態檔 |
| `RACCOON_TOKEN_FILE` | 可選 Token 輪換快取 |
| `PUSHPLUS_TOKEN`、`BARK_URL`、`WECOM_WEBHOOK`、`DINGTALK_WEBHOOK` | 可選推送 |

常用參數：`--query` 只查今日入帳；`--skip-onboarding` 跳過新手獎勵；`--only 2` 只跑第 2 個帳號；`--no-notify` 關閉推送。

## 安全提醒

Token、輪換快取與新手狀態檔都不要提交到 Git。請使用環境變數或加密 Secrets，也不要把憑證貼到 Issue。

## 連結

- [Releases](https://github.com/L0NE-6/Raccoon-Daily/releases)
- [Issues](https://github.com/L0NE-6/Raccoon-Daily/issues)
- [更新日誌](../CHANGELOG.md)
- [完整簡體中文文件](../README.md)
