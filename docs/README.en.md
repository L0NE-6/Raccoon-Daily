# Raccoon Daily

**A single-file Qinglong automation for Raccoon daily credits, QR login, billing verification, and multiple accounts.**

[简体中文](../README.md) | [English](README.en.md) | [繁體中文](README.zh-Hant.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Português (BR)](README.pt-BR.md)

> This is a localized quick start. The [complete Simplified Chinese README](../README.md) contains every option and troubleshooting note.

## At a glance

| Item | Details |
| :--- | :--- |
| Purpose | Claim daily Raccoon credits and one-time desktop/mobile onboarding rewards |
| Credential | `RACCOON_TOKENS`, preferably `name\|token\|refresh_token` |
| Runtime | Python 3.8+, Qinglong, local cron, or GitHub Actions |
| Dependencies | `requests`; optional `qrcode` for terminal QR output |
| Success check | A valid today `daily_grant`, or an unexpired and unconsumed daily grant |

## Included scripts

- `raccoon_login.py`: QR login, legacy web authorization, or desktop auth import.
- `raccoon_daily.py`: daily credit claim, billing verification, onboarding rewards, and notifications.

## Quick start

```bash
pip install requests
python raccoon_login.py
```

Set the returned credential:

```text
RACCOON_TOKENS=name|token|refresh_token
```

Create a Qinglong task:

```bash
python raccoon_daily.py
```

Suggested schedule:

```cron
30 8 * * *
```

## GitHub Actions

Fork the repository and add `RACCOON_TOKENS` under **Settings > Secrets and variables > Actions**. Optional notification Secrets include `PUSHPLUS_TOKEN`, `BARK_URL`, `WECOM_WEBHOOK`, `DINGTALK_WEBHOOK`, and `DINGTALK_SECRET`. The default workflow is manual; uncomment the schedule after validating your own deployment.

## Important variables

| Variable | Purpose |
| :--- | :--- |
| `RACCOON_TOKENS` | One or more accounts, separated by newlines or `&` |
| `RACCOON_STATE_FILE` | Optional onboarding-state file path |
| `RACCOON_TOKEN_FILE` | Optional rotating-token cache path |
| `PUSHPLUS_TOKEN`, `BARK_URL`, `WECOM_WEBHOOK`, `DINGTALK_WEBHOOK` | Optional notifications |

Useful flags:

- `--query`: query today's bill without triggering a claim.
- `--skip-onboarding`: skip one-time onboarding rewards.
- `--only 2`: run only the second account.
- `--no-notify`: suppress notifications.

## Security

Tokens, rotation caches, and onboarding state must remain outside Git. Use environment variables or encrypted GitHub Secrets and never paste credentials into an Issue.

## Usage and redistribution

The official repository, scripts, documentation, and Releases are free. Do not repackage them as paid resources, remove attribution, impersonate the author, use the author's identity or QR codes as endorsement, or repost them through unrelated accounts or groups for traffic. See the [Usage and Redistribution Notice](../NOTICE.md). Violations may result in takedown requests; the author may pause updates, archive, or delete the repository.

## Links

- [Releases](https://github.com/L0NE-6/Raccoon-Daily/releases)
- [Issues](https://github.com/L0NE-6/Raccoon-Daily/issues)
- [Changelog](../CHANGELOG.md)
- [Complete Chinese documentation](../README.md)
