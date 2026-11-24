<div align="center">

<sub><strong>L0NE-6 · DAILY SIGNAL</strong></sub>

# 🐻 Raccoon Daily

**小浣熊每日积分 · 微信扫码登录 · 单文件青龙脚本 · 多账号**

> 当前版本：**v1.1.1**（2026-11-10） · 认证方式：登录 JWT + Refresh Token

**[简体中文](README.md)** · [English](docs/README.en.md) · [繁體中文](docs/README.zh-Hant.md) · [日本語](docs/README.ja.md) · [한국어](docs/README.ko.md) · [Português (BR)](docs/README.pt-BR.md)

每日积分 · 新手奖励 · 账单回读 · Token 续期 · 多账号 · 青龙 · Actions

<img src="https://img.shields.io/badge/Version-v1.1.1-2ea44f?style=for-the-badge&logo=github" alt="Version v1.1.1" />
<img src="https://img.shields.io/github/stars/L0NE-6/Raccoon-Daily?style=for-the-badge&label=Stars&color=FFC75F&logo=github" alt="Stars" />
<img src="https://img.shields.io/badge/Python-3.8%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.8+" />
<img src="https://img.shields.io/badge/Qinglong-ready-4EAA25?style=for-the-badge" alt="Qinglong" />
<img src="https://img.shields.io/badge/GitHub%20Actions-supported-2088FF?style=for-the-badge&logo=githubactions&logoColor=white" alt="GitHub Actions" />

[边界](#policy) · [速览](#overview) · [协议](#protocol) · [凭据](#credentials) · [快速开始](#quickstart) · [青龙](#qinglong) · [Actions](#actions) · [CLI](#cli) · [结果码](#result-codes) · [成功判据](#success) · [测试](#tests) · [目录](#layout) · [版本](#release) · [赞赏](#donate) · [反馈](#feedback)

</div>

---

<a id="policy"></a>
## 🚫 使用边界

### 🚫 使用边界与转载声明

> [!IMPORTANT]
> **官方版本永久免费。** 未经作者书面许可，禁止付费包装、搬运引流、冒充作者，或使用作者身份与二维码制造官方授权假象。违规内容可能被要求下架；作者可暂停更新、归档或删除仓库及相关 Release。

本项目仓库、脚本、部署说明和 Release 下载始终免费公开。未经作者明确书面许可，禁止将本项目包装为付费资源、内部版、独家版、会员权益、收费课程、付费部署或包更新服务；禁止搬运到其他账号、群组、频道、网盘、电商或付费平台进行涨粉、截流、倒卖和引流；禁止删除作者与版权信息后冒充原创；禁止使用作者昵称、头像、二维码和项目名称制造官方授权假象。

> 如需商业合作、品牌授权、联合分发或使用作者名义提供付费服务，请先取得作者明确书面授权。完整规则、收款码防诈骗说明和违规处理方式见 **[NOTICE.md](NOTICE.md)**。

> 官方仓库和 Release 始终免费。第三方以“下载费 / 激活费 / 内部版 / 代部署 / 会员门槛”等名义收费，均与作者无关，请停止付款并保留证据。

> 对上述违规行为，作者有权要求立即停止传播、删除内容并下架相关商品或页面；并可视情况暂停更新、归档或删除本仓库及相关 Release、向平台投诉或采取进一步必要措施。

---

---

<a id="overview"></a>
## ✨ 30 秒速览

### ✨ 30 秒速览

| 维度 | 说明 |
| :--- | :--- |
| **做什么** | 页面访问延期每日积分，核对 daily_grant、到期时间与余额，并补领首次电脑端 / 手机端登录奖励。 |
| **输入** | `RACCOON_TOKENS`；个人账号推荐 `备注\|token\|refresh_token`，组织账号可使用 `备注\|token\|refresh_token\|office_identity`。 |
| **输出** | 今日积分入账结果、新手奖励状态、分账号日志和可选推送。 |
| **部署** | 青龙面板、本地定时任务、GitHub Actions。 |
| **依赖** | Python 3.8+；主流程仅需 `requests`，扫码模式可选 `qrcode`。 |
| **成功判据** | 今日 daily_grant，或仍存在未过期且未清零的 daily_grant；01:30 前账单未同步时保留重跑提示。 |

---

<a id="what"></a>
## 🧭 这是什么

### ✨ 这是什么

小浣熊每日积分领取：网页 user_info 访问 → 余额核对 → 拉最近 60 条账单核对 daily_grant → 自动补领首次电脑端 / 手机端登录奖励（各一次性）。今日没有新流水但仍有未过期积分时按可用额度确认；凌晨账单同步未完成时提示 01:30 后重跑，不虚报、不重复领。

> 🎯 一句话：**配好 Token，剩下的交给它。**
>
> 📦 单文件自包含：不需要额外模块，青龙上传脚本、填好环境变量就能跑。
>
> ☁️ 除了青龙，也可以直接跑在 **GitHub Actions** 上，零服务器定时执行（见下文部署方式二）。

核心特性：

- ✅ **签到 + 新手奖励**：每日发放、账单核对，另自动补领首次电脑端 / 手机端登录奖励（各一次性，本机台账防重复）
- 🧾 **账单为准**：只认 `daily_grant`；未过期旧额度可确认已签，过期、缺失到期时间或已被 `daily_expire` 清零的积分不算
- 🕐 **北京时间口径**：账单「今日入账」按 UTC+8 切日，非中国时区部署也一致
- 🔐 **微信扫码登录**：电脑上出二维码，微信扫一次即得 Token + 续期凭据（旧版网页授权保留）
- 👥 **多账号** + 📢 **多渠道推送** + 🐧 **青龙 / Actions 双部署**

---

<a id="protocol"></a>
## 🔁 协议与回读

### 每日积分链

```text
GET /api/web/auth/v1/user_info
GET /api/web/points/v1/balance
GET /api/web/points/v2/bills?paging.limit=60&type=income
```

基础站点为 `https://xiaohuanxiong.com`。桌面端与移动端新手奖励使用不同 grant 路径。

### 回读

账单只认 `daily_grant`、到期时间与清零配对。签到成功以可用每日积分入账为准，不以某一步 HTTP 200 为准。

---

<a id="credentials"></a>
## 🔑 凭据与账号

| 变量 | 必需 | 说明 |
| :--- | :---: | :--- |
| `RACCOON_TOKENS` | 是 | `备注|token|refresh_token|office_identity` 多账号 |
| `RACCOON_TOKEN_FILE` | 否 | 续期缓存路径 |
| `RACCOON_STATE_FILE` | 否 | 新手奖励台账路径 |
| `RACCOON_MAIN_SITE_URL` | 否 | 站点基址覆盖 |

Access Token 寿命较短，推荐同时提供 refresh token。组织账号必须使用显式组织身份，不能从备注猜测。

### 🔑 获取 Token

```bash
python raccoon_login.py            # 微信扫码（推荐）
python raccoon_login.py --web      # 旧版网页授权（粘贴回调地址）
python raccoon_login.py --auth-file  # 导入桌面客户端 auth.json（自动探测新旧路径）
```

- **导入桌面端 auth.json**：客户端登录过即可，读取其中的 `access_token` / `refresh_token`，并在存在时保留 `officeIdentity` / `office_identity`，不弹二维码（也可在参数后传自己的路径）。自动按顺序探测 `~/.office-raccoon/agent/config/auth.json`（新版客户端）、`~/.box-agent/config/auth.json`（旧版客户端）、`%LOCALAPPDATA%` / `%APPDATA%` 下的 `office-raccoon\agent\config\auth.json`。
- **扫码模式**：终端会显示二维码（需可选依赖 `pip install qrcode`），用微信扫一扫登录「商汤小浣熊」；也可以在命令后加 `--png qr.png` 把二维码存成图片再扫。
- **成功后输出一行凭据**：个人账号通常为 `备注|token|refresh_token`；组织账号为 `备注|token|refresh_token|office_identity`。若没有 `refresh_token` 但带有组织身份，则输出 `备注|token||office_identity`（第三段留空）。整行填进 `RACCOON_TOKENS` 即可；带 `refresh_token` 才会自动续期（access 约 2~3 小时有效；refresh 约 30 天且会轮换，脚本自动落盘）。

> **旧版网页授权（`--web`）**：浏览器登录后把跳转到的 `office-raccoon://auth/callback?...` 完整地址粘贴回终端（若提示无法打开协议，直接复制地址栏即可）。

---

<a id="quickstart"></a>
## 🚀 快速开始

### ⬇️ 下载

不想用 git？直接到 **[Releases](https://github.com/L0NE-6/Raccoon-Daily/releases)** 下载：

- 完整包 zip（脚本 + 登录工具 + README + Actions 工作流 + 收款码）
- 各脚本单文件（青龙只需要上传签到脚本）
- `SHA256SUMS.txt` 完整性校验
### ❓ 常见问题

- **提示「今日未见积分入账」？** 可能是今天已经领过，或服务端账单延迟；`--query` 可以只查不领。
- **授权码失效？** 授权码一次性，拿到回调地址后尽快粘贴，过期就重新发起。
- **Token 会过期吗？** access 约 2~3 小时有效。带 `refresh_token`（新版登录工具默认输出）时脚本会自动续期、轮换结果自动落盘；没带的话过期后需重新跑登录工具。

---

<a id="qinglong"></a>
## 🐧 青龙面板

### 🚀 部署方式一：青龙面板（三步）

| 步骤 | 操作 |
| :---: | :--- |
| 1 | 安装依赖：`pip install -r requirements.txt`（或 `pip3 install requests`） |
| 2 | 把签到脚本上传到青龙「脚本管理」，或把仓库放进脚本目录 |
| 3 | 「环境变量」里添加 Token，新建定时任务（见下方 cron 示例） |

```cron
30 8 * * * python raccoon_daily.py
```

---

<a id="actions"></a>
## ☁️ GitHub Actions

### ☁️ 部署方式二：GitHub Actions（可选，默认手动触发）

1. Fork 本仓库（或直接使用本仓库，Secrets 只能配在你自己的仓库里）。
2. 打开 **Settings → Secrets and variables → Actions**，添加下表里的 Secrets。
3. 打开 **Actions** 标签页，选择 `Raccoon Daily`，点 **Run workflow** 手动跑一次验证。
4. 默认只支持**手动触发**（本仓库不跑定时，避免空跑）；fork 后想定时，把 `.github/workflows/daily.yml` 里 `schedule:` 两行取消注释（cron 用 UTC，北京时间减 8 小时），之后就会按该时间自动执行。

| Secret | 对应环境变量 | 必填 |
|---|---|---|
| `RACCOON_TOKENS` | RACCOON_TOKENS | 必填 |
| `PUSHPLUS_TOKEN` / `BARK_URL` / `WECOM_WEBHOOK` / `DINGTALK_WEBHOOK` / `DINGTALK_SECRET` | 同名推送变量 | 可选 |

> 公开仓库的 Secrets 是加密的，日志里不会回显；脚本也不会把 Token 写进仓库文件。

---

<a id="cli"></a>
## ⌨️ CLI 与环境变量

### 🧩 环境变量（支持多账号）

> 多账号用 **换行** 或 **`&`** 分隔，两种可以混用。`|` 是单条账号内部的字段分隔符，备注里不要再写 `|`。

```text
# 个人账号
主号|TOKEN|REFRESH_TOKEN

# 组织账号：office_identity 由登录工具输出，不要从备注或 Token 文本中猜测
团队号|TOKEN|REFRESH_TOKEN|OFFICE_IDENTITY
```

| 环境变量 | 单条格式 | 说明 |
|---|---|---|
| `RACCOON_STATE_FILE` | 文件路径（可选） | 新手奖励台账，默认脚本同目录 `raccoon_onboarding.json` |
| `RACCOON_TOKEN_FILE` | 文件路径（可选） | 续期缓存，默认脚本同目录 `raccoon_tokens.json` |
| `RACCOON_TOKENS` | `token` / `备注\|token` / `备注\|token\|refresh_token` / `备注\|token\|refresh_token\|office_identity` | 多账号换行或 `&`；第四段为可选组织身份，**带 refresh_token 才能自动续期** |

旧的一段、两段、三段格式继续兼容；第四段不带时按个人身份处理，不会发送 `X-Org-Code`。组织身份只从登录工具产出的 `officeIdentity` / `office_identity` 可信字段读取。
### ⌨️ 命令行参数

| 参数 | 作用 |
|---|---|
| `--query` | 只查今日入账，不触发发放 |
| `--skip-onboarding` | 只做每日签到，不碰新手奖励 |
| `--only 2` | 只跑第 2 个账号 |
| `--no-notify` | 关闭推送 |

---

<a id="result-codes"></a>
## 🚦 结果码

| 状态 | 含义 |
| :--- | :--- |
| `daily_grant` 入账 | 当日成功 |
| 今日未见积分入账 | 可能已领、账单延迟或未满足条件 |
| 401 | 登录失效 |
| 续期失败 | 需要重新扫码登录 |
| 回读异常 | 不宣称成功 |

---

<a id="success"></a>
## ✅ 成功判据

服务端余额与收入账单可核对到当日 `daily_grant`，且到期与清零字段一致时才算成功。

### 📊 运行效果示例

```text
[08:30:01] 👤 [1] 主号  token=eyJhbGci****abcd  身份=个人
[08:30:03]    ✅ 今日积分 +100（每日登录+100）
[08:30:04] 账号1 主号: ✅ 今日积分 +100（每日登录+100）
```

---

<a id="tests"></a>
## 🧪 测试

```powershell
$env:PYTHONUTF8 = "1"
python -m unittest discover -s tests -v
python -m py_compile raccoon_daily.py raccoon_login.py
```

测试覆盖签到、账单解析、组织身份与续期回归。

---

<a id="design"></a>
## 🧱 设计原则

- 每日成功由账单和余额决定，不由单步响应决定。
- 新手奖励使用本机台账，已结算账号不重复探测。
- Access Token 与 Refresh Token 分离处理。
- 组织身份只从显式凭据字段读取。

---

<a id="privacy"></a>
## 🔒 隐私与安全

凭据、状态文件、日志与运行缓存都属于账号级数据。仓库和 Issue 中只保留脱敏片段。

### 🔒 隐私说明

- 脚本**不含任何账号、手机号、Token 或设备信息**，全部由环境变量（或 GitHub Secrets）注入。
- 运行期生成的数据文件（见「数据文件说明」）都包含凭据，已被 `.gitignore` 排除。
- 请勿把 Token 写进脚本、提交到仓库或发到 Issue 里。

---

<a id="layout"></a>
## 📁 目录结构

### 📦 文件说明

| 文件 | 作用 |
|---|---|
| `raccoon_login.py` | 微信扫码登录（旧版网页授权用 `--web`） |
| `raccoon_daily.py` | 每日积分（多账号、推送） |
### 🗂️ 数据文件说明

| 文件 | 内容 | 是否提交 |
|---|---|---|
| `raccoon_tokens.json` | 续期缓存（access / refresh / 更新时间，按账号备注+序号索引） | ❌ 已 gitignore |
| `raccoon_onboarding.json` | 新手奖励台账（只存 token 哈希） | ❌ 已 gitignore |

> 以上文件都包含账号凭据，已在 `.gitignore` 中排除，**不要手动提交**。
### 📁 目录结构

```text
Raccoon-Daily/
├── raccoon_login.py
├── raccoon_daily.py
├── assets/
├── .github/workflows/daily.yml
├── CHANGELOG.md
├── LICENSE
├── README.md
└── requirements.txt
```

---

<a id="release"></a>
## 📦 版本与发布

当前标签为 `v1.1.1`。发布包不得包含 `raccoon_tokens.json`、新手奖励台账或账号导出文件。

### 📦 版本与发布

- 当前发布版：`v1.1.1`（2026-11-10）。
- 每次更新单独发一个 Release，历史版本保留可下载。
- 每个 Release 附带：完整包 zip + 各脚本单文件 + `SHA256SUMS.txt`。
- 下载页：<https://github.com/L0NE-6/Raccoon-Daily/releases>

---

<a id="disclaimer"></a>
## ⚠️ 免责声明

仓库内容用于账号持有人维护自身权益。使用前应确认账号、服务条款与所在地规则；作者不对账号限制、接口变化、网络失败或第三方部署造成的损失作出保证。

完整展示与转载规则见 [NOTICE.md](NOTICE.md)。

---

<a id="donate"></a>
## ☕ 赞赏码

### 支持与投喂

如果这个项目节省了你的时间，可以扫码支持维护。赞赏完全自愿，不影响代码、文档与 Issue 处理。

<div align="center">
<table>
<tr>
<td align="center"><strong>微信赞赏码</strong><br /><img src="assets/donate-wechat.png" width="260" alt="微信赞赏码" /></td>
<td align="center"><strong>支付宝赞赏码</strong><br /><img src="assets/donate-alipay.jpg" width="260" alt="支付宝赞赏码" /></td>
</tr>
</table>
</div>

---

<a id="feedback"></a>
## 💬 反馈与 Star History

### 反馈与贡献

- [提交 Issue](https://github.com/L0NE-6/Raccoon-Daily/issues)
- [提交 Pull Request](https://github.com/L0NE-6/Raccoon-Daily/pulls)
- [查看更新日志](CHANGELOG.md)

反馈请附脱敏日志、复现步骤、运行环境与实际结果。不要贴 Token、Cookie、JWT、手机号或运行状态文件。

<a href="https://star-history.com/#L0NE-6/Raccoon-Daily&Date">
  <img src="https://api.star-history.com/svg?repos=L0NE-6/Raccoon-Daily&type=Date" alt="Raccoon-Daily Star History" />
</a>
