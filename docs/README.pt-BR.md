# Raccoon Daily

**Automação em arquivo único para créditos diários do Raccoon, login por QR, conferência do extrato e várias contas.**

[简体中文](../README.md) | [English](README.en.md) | [繁體中文](README.zh-Hant.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Português (BR)](README.pt-BR.md)

> Este é um guia rápido em português. Consulte o [README completo em chinês simplificado](../README.md) para todas as opções e diagnósticos.

## Visão geral

| Item | Detalhes |
| :--- | :--- |
| Objetivo | Resgatar créditos diários e recompensas únicas de login desktop/mobile |
| Credencial | `RACCOON_TOKENS`, preferencialmente `name\|token\|refresh_token` |
| Ambiente | Python 3.8+, Qinglong, cron local ou GitHub Actions |
| Dependências | `requests`; `qrcode` é opcional para QR no terminal |
| Verificação | `daily_grant` válido de hoje, ou crédito diário não expirado e não consumido |

## Scripts

- `raccoon_login.py`: login por QR, autorização web legada e importação do auth desktop.
- `raccoon_daily.py`: crédito diário, conferência do extrato, bônus inicial e notificações.

## Início rápido

```bash
pip install requests
python raccoon_login.py
```

Configure:

```text
RACCOON_TOKENS=name|token|refresh_token
```

Tarefa no Qinglong:

```bash
python raccoon_daily.py
```

Agenda sugerida:

```cron
30 8 * * *
```

## GitHub Actions

Faça Fork e adicione `RACCOON_TOKENS` em **Settings > Secrets and variables > Actions**. Notificações opcionais usam `PUSHPLUS_TOKEN`, `BARK_URL`, `WECOM_WEBHOOK`, `DINGTALK_WEBHOOK` e `DINGTALK_SECRET`. O workflow começa em modo manual; ative a agenda somente depois de validar.

## Variáveis principais

| Variável | Finalidade |
| :--- | :--- |
| `RACCOON_TOKENS` | Várias contas, separadas por linha ou `&` |
| `RACCOON_STATE_FILE` | Caminho opcional do estado de bônus |
| `RACCOON_TOKEN_FILE` | Caminho opcional do cache de tokens |
| `PUSHPLUS_TOKEN`, `BARK_URL`, `WECOM_WEBHOOK`, `DINGTALK_WEBHOOK` | Notificações opcionais |

Use `--query` para consultar, `--skip-onboarding` para ignorar bônus iniciais, `--only 2` para executar a segunda conta e `--no-notify` para desativar notificações.

## Segurança

Nunca envie tokens, caches ou arquivos de estado ao Git. Use variáveis de ambiente ou GitHub Secrets criptografados e não publique credenciais em Issues.

## Limites de uso e redistribuição

O repositório oficial, scripts, documentação e Releases são gratuitos. Não os repackage como recursos pagos, remova a atribuição, personifique o autor, use a identidade ou os QR codes do autor como endosso, nem reposte o projeto em contas ou grupos não relacionados para desviar tráfego. Consulte o [Aviso de uso e redistribuição](../NOTICE.md). Violações podem resultar em pedidos de remoção; o autor pode pausar atualizações, arquivar ou excluir o repositório.

## Links

- [Releases](https://github.com/L0NE-6/Raccoon-Daily/releases)
- [Issues](https://github.com/L0NE-6/Raccoon-Daily/issues)
- [Changelog](../CHANGELOG.md)
- [Documentação completa em chinês](../README.md)
