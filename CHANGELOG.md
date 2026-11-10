# 更新日志

## v1.1.1（2026-11-10）

- 账单请求从 `type=all` 改为服务端收入过滤 `type=income`，保留最近 60 条窗口。
- 修复活跃账号消费流水较多时，每日 `daily_grant` 被挤出 60 条窗口并误报“今日尚未发放”的问题。
- income 响应仍只认 `biz_type=daily_grant`；`reward_grant` 等其他收入不会冒充每日签到。
- 宽限、到期清零、未过期旧额度和余额硬校验逻辑不变；全套 `27` 项测试通过。

## v1.1.0（2026-11-10）

- 签到流程对齐当前 Raccoon：`user_info` 页面访问 → 余额硬校验 → `bills v2` 最近 60 条核验。
- 只认 `biz_type=daily_grant`；日期优先 `grant_at`，缺失才用 `created_at`，按 UTC+8 切日。
- 同日多条每日积分取最大点数；`created_at` 落在本次调用前 90 秒内视为本次新到账，否则按已签到。
- 今日没有新 `daily_grant` 时，未过期且未被 `daily_expire` 清零的旧每日积分仍可判已签，额度为所有有效条目合计。
- `daily_expire` 按“CST 日期 + 绝对点数”与发放配对；过期、缺少 `expire_at`、点数非正或 bool 均不计入。
- 00:00-01:29:59 账单尚未同步时不密集重试：有可用旧额度则成功并提示 01:30 再确认，无可用额度则失败并提示 01:30 后重跑。
- 余额 `available_points` 必须为数字且非 bool；`user_info` 失败为 best-effort，不阻断余额和账单核验。
- `--query` 只读账单，不访问 user_info 或余额，不触发奖励领取。
- 新增签到语义、宽限边界、过期/清零、余额和账单形状回归；全套 `26` 项测试通过。

## v1.0.6（2026-11-04）

- 对齐官方小浣熊客户端 `1.1.5` 请求头：桌面端增加 `X-Client-Name: raccoon-work`，并同步 `X-Client-Platform` 与 `X-Client-Version: v1.1.5`。
- 新增可选 `RACCOON_TOKENS` 第四段 `office_identity`：仅从登录工具产出的可信凭据字段解析；个人身份或空值不发送 `X-Org-Code`，组织身份条件发送，日志不输出组织码明文。
- 登录工具会从 `auth.json`、扫码或网页授权响应中保留 `office_identity`，并输出四段凭据；原有 `token`、`备注|token`、`备注|token|refresh_token` 格式继续兼容。
- 新增 13 项回归测试，覆盖个人/组织条件头、官方版本头、空/畸形组织字段、登录凭据透传，以及首次电脑端 / 手机端奖励防重。
- 说明：本次验证基于协议证据与本地单元测试，尚未使用真实账号完成线上回读验证。

## v1.0.5（2026-10-28）

- 修复：桌面客户端新版把配置目录迁到 `%USERPROFILE%\.office-raccoon\agent\config\`，`--auth-file` 默认路径随之更新；旧版 `~/.box-agent/config/auth.json` 与 `%LOCALAPPDATA%` / `%APPDATA%` 下的配置继续自动探测，找不到时列出全部候选路径并提示手动指定（issue #1）。
- 参照上游 `wicm84266964/Buddy2api` v2.2.12 的路径迁移处理（新旧目录同时扫描）。

## v1.0.4（2026-10-17）

- 新增：登录工具支持 `--auth-file` 导入桌面客户端 `auth.json`（`access_token` / `refresh_token`），与扫码登录二选一；默认读取 `~/.box-agent/config/auth.json`。
- 对齐上游 v3.0.8 的凭证文件导入能力（小浣熊 / CatPaw auth.json 导入）。

## v1.0.3（2026-10-16）

- 适配小浣熊**新版登录**（官方客户端 v1.0.35）：登录工具默认改为**微信扫码**（本地生成 code → 商汤落地页 → `login_with_qrcode_code` 轮询换取登录态），旧版网页授权保留为 `--web`。
- 新增：**登录态自动续期** —— `RACCOON_TOKENS` 支持 `备注|token|refresh_token`；access 约 2~3 小时有效，脚本临期自动用 refresh_token 换新，refresh 轮换结果落盘 `raccoon_tokens.json`（防丢失）。
- 更新：桌面端身份头对齐 v1.0.35（`X-Client-Version`）；接口返回 401 / 业务码 200003 时自动续期并重试一次。
- 说明：只填 token（旧格式）仍可用，但过期后需重新登录；建议用新登录工具重取一行带 refresh_token 的。

## v1.0.2（2026-10-10）

- 新增：新手任务自动领取首次电脑端 / 手机端登录奖励（各一次性，名义各 3000 积分）；领取结果记本机台账 `raccoon_onboarding.json`（只存 token 哈希，不落明文），结算过的账号不再重复探测，`--skip-onboarding` 可关闭。
- 优化：账单「今日入账」核对固定按北京时间（UTC+8）切日，非中国时区部署口径一致。
- 优化：接口响应统一解包 `{code, data}`，code 非 0 时按上游文案报错。

## v1.0.1（2026-10-09）

- Actions 工作流默认改为**仅手动触发**：上游仓库不再空跑定时任务。
- fork 后如需定时，取消 `.github/workflows/daily.yml` 里 `schedule:` 的注释即可。
- README 同步补充 fork 启用定时的说明。

## v1.0.0（2026-10-09）

- 首个公开版本
- 首个版本：小浣熊每日积分脚本 + 网页授权登录工具，支持多账号与账单核对。

> 每个版本单独发布 Release，历史版本保留可下载。
