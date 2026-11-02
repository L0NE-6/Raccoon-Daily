# Raccoon Daily

**Raccoon 일일 크레딧, QR 로그인, 청구 내역 확인, 다중 계정을 지원하는 단일 파일 자동화입니다.**

[简体中文](../README.md) | [English](README.en.md) | [繁體中文](README.zh-Hant.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Português (BR)](README.pt-BR.md)

> 이 문서는 한국어 빠른 안내입니다. 전체 옵션과 문제 해결은 [중국어 간체 README](../README.md)를 확인하세요.

## 개요

| 항목 | 설명 |
| :--- | :--- |
| 목적 | 일일 크레딧 수령과 데스크톱 / 모바일 최초 로그인 보상 |
| 자격 증명 | `RACCOON_TOKENS`, 권장 형식 `name\|token\|refresh_token` |
| 실행 환경 | Python 3.8+, Qinglong, 로컬 cron, GitHub Actions |
| 의존성 | `requests`, 터미널 QR 표시에는 선택적으로 `qrcode` |
| 성공 기준 | 계정 청구 내역에 오늘의 크레딧 입금이 표시되어야 함 |

## 포함 스크립트

- `raccoon_login.py`: QR 로그인, 구형 웹 인증, 데스크톱 auth 가져오기.
- `raccoon_daily.py`: 일일 크레딧, 청구 확인, 초기 보상, 알림.

## 빠른 시작

```bash
pip install requests
python raccoon_login.py
```

자격 증명을 설정합니다.

```text
RACCOON_TOKENS=name|token|refresh_token
```

Qinglong 작업:

```bash
python raccoon_daily.py
```

권장 스케줄:

```cron
30 8 * * *
```

## GitHub Actions

Fork 후 **Settings > Secrets and variables > Actions** 에 `RACCOON_TOKENS`를 추가합니다. 알림에는 `PUSHPLUS_TOKEN`, `BARK_URL`, `WECOM_WEBHOOK`, `DINGTALK_WEBHOOK`, `DINGTALK_SECRET`을 사용할 수 있습니다. 먼저 수동 실행으로 검증하세요.

## 주요 변수

| 변수 | 용도 |
| :--- | :--- |
| `RACCOON_TOKENS` | 여러 계정, 줄바꿈 또는 `&` 구분 |
| `RACCOON_STATE_FILE` | 선택형 초기 보상 상태 파일 |
| `RACCOON_TOKEN_FILE` | 선택형 Token 갱신 캐시 |
| `PUSHPLUS_TOKEN`, `BARK_URL`, `WECOM_WEBHOOK`, `DINGTALK_WEBHOOK` | 선택형 알림 |

`--query`는 조회만, `--skip-onboarding`은 초기 보상 생략, `--only 2`는 두 번째 계정만 실행합니다.

## 보안

Token, 갱신 캐시, 상태 파일을 Git에 커밋하지 마세요. 환경 변수 또는 암호화된 Secrets를 사용해야 합니다.

## 사용 범위 및 재배포 안내

공식 저장소, 스크립트, 문서 및 Releases는 무료로 공개됩니다. 유료 리소스로 재포장하거나 저작자 표시를 제거하고, 작성자를 사칭하거나 작성자 이름 또는 QR 코드를 보증 수단으로 사용하는 행위, 무관한 계정이나 그룹으로 옮겨 트래픽을 유도하는 행위를 금지합니다. 자세한 내용은 [사용 범위 및 재배포 안내](../NOTICE.md)를 참고하세요. 위반 시 삭제 요청 대상이 될 수 있으며 작성자는 업데이트 중단, 보관 또는 저장소 삭제를 진행할 수 있습니다.

## 링크

- [Releases](https://github.com/L0NE-6/Raccoon-Daily/releases)
- [Issues](https://github.com/L0NE-6/Raccoon-Daily/issues)
- [변경 로그](../CHANGELOG.md)
- [전체 중국어 문서](../README.md)
