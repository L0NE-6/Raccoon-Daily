<div align="center">

# 🐻 Raccoon Daily

**小浣熊每日积分 · 网页授权登录 · 单文件青龙脚本 · 多账号**

<img src="https://img.shields.io/badge/Python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/%E9%9D%92%E9%BE%99%E9%9D%A2%E6%9D%BF-%E5%8D%95%E6%96%87%E4%BB%B6%E8%BF%90%E8%A1%8C-4EAA25?style=flat-square" />
<img src="https://img.shields.io/badge/%E5%A4%9A%E8%B4%A6%E5%8F%B7-%E6%8D%A2%E8%A1%8C%E6%88%96%20%26%20%E5%88%86%E9%9A%94-2088FF?style=flat-square" />
<img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" />

</div>

---

## ✨ 这是什么

小浣熊每日积分领取：桌面登录奖励 → 每日发放触发器 → 拉账单核对今日入账，按「账单里真的看到入账」判断成功，不虚报。

## 📦 文件说明

| 文件 | 作用 |
|---|---|
| `raccoon_login.py` | 网页授权登录，回填回调地址换 Token |
| `raccoon_daily.py` | 每日积分（多账号、推送） |

## 🔑 先获取 Token

```bash
python raccoon_login.py
```

浏览器登录成功后会跳到 `office-raccoon://auth/callback?...`，把这个完整地址粘贴回终端，工具校验 `state` 后输出一行 `备注|token`。

## 🧩 环境变量（支持多账号）

> 多账号用 **换行** 或 **`&`** 分隔，两种可以混用。`|` 是单条账号内部的字段分隔符，备注里不要再写 `|`。

| 环境变量 | 单条格式 |
|---|---|
| `RACCOON_TOKENS` | `token` / `备注\|token` |

## 🚀 青龙部署

1. 安装依赖：`pip install -r requirements.txt`
2. 把签到脚本上传到青龙（或把整个仓库放进脚本目录）。
3. 在「环境变量」里添加上面的变量，值按单条格式填写。
4. 新建定时任务，参考：

```cron
30 8 * * * python raccoon_daily.py
```

## ⚙️ 常用参数

- `--query`：只查今日入账，不触发发放
- `--only 2`：只跑第 2 个账号
- `--no-notify`：关闭推送

## 📢 推送（可选）

支持 `PUSHPLUS_TOKEN`、`BARK_URL`、`WECOM_WEBHOOK`、`DINGTALK_WEBHOOK`、`DINGTALK_SECRET`；青龙面板自带通知也会自动尝试。配了哪个用哪个，都没配就只打日志。

## ⚠️ 注意事项

- 授权码是一次性的，拿到回调地址后尽快粘贴。
- Token 校验只读账号设置，不会触发签到。

## 🔒 安全

- 环境变量和运行期生成的 JSON 缓存都包含账号凭据，不要提交到公开仓库、不要外发。
- 仓库里的 `.gitignore` 已排除缓存文件；如果自己改过目录结构，请确认缓存文件没有被 `git add`。

## 📄 License

MIT © 2026 [L0NE-6](https://github.com/L0NE-6)
