#!/usr/bin/env python3
"""
🐻 小浣熊 每日签到 - 青龙脚本
------------------------------------------------------------

📌 功能
   小浣熊每日积分发放（三段式，成功判据是账单核对而不是某一步 200）：
   1. POST /api/web/desktop/v1/login/points/grant   一次性桌面登录奖励（失败不阻断）
   2. GET  /api/web/office/v3/setting_info          每日发放触发器（按天幂等）
   3. GET  /api/web/points/v1/bills                 拉账单，今日 points>0 才算签到成功

🔑 环境变量
   RACCOON_TOKENS   【必填】多账号用换行或 & 分隔：
       token
       备注|token
     token 为 xiaohuanxiong.com 的登录 JWT（带不带 Bearer 前缀都行）

   推送通道（均可选）：PUSHPLUS_TOKEN / BARK_URL / WECOM_WEBHOOK / DINGTALK_WEBHOOK / DINGTALK_SECRET

⌨️ 命令
   python raccoon_daily.py              正常签到
   python raccoon_daily.py --query      只查今日入账，不触发发放
   python raccoon_daily.py --only 2     只跑第 2 个账号
   python raccoon_daily.py --no-notify  不推送

📄 依赖：requests
"""
import base64
import hashlib
import hmac
import json
import os
import sys
import time

import requests

import urllib3
urllib3.disable_warnings()

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

ORIGIN = os.environ.get("RACCOON_MAIN_SITE_URL", "").strip() or "https://xiaohuanxiong.com"
GRANT_PATH = "/api/web/desktop/v1/login/points/grant"
SETTINGS_PATH = "/api/web/office/v3/setting_info"
BILLS_PATH = "/api/web/points/v1/bills?paging.limit=20&paging.offset=0"

ONLY = None
QUERY_ONLY = False
NO_NOTIFY = False


def log(msg):
    print("%s %s" % (time.strftime("[%H:%M:%S]"), msg), flush=True)


def mask(text, keep=6):
    text = str(text or "")
    if len(text) <= keep + 4:
        return text
    return text[:keep] + "****" + text[-4:]


def split_accounts(raw):
    out = []
    for chunk in (raw or "").replace("&", "\n").splitlines():
        chunk = chunk.strip().strip('"\'')
        if chunk and not chunk.startswith("#"):
            out.append(chunk)
    return out


def strip_bearer(token):
    token = (token or "").strip()
    if token.lower().startswith("bearer "):
        return token[7:].strip()
    return token


def request(method, url, headers=None, body=None, timeout=20, retries=3):
    last = None
    for attempt in range(retries):
        try:
            session = requests.Session()
            session.trust_env = False
            return session.request(method, url, headers=headers or {},
                                   json=body if body is not None else None,
                                   timeout=timeout, verify=False)
        except Exception as error:
            last = error
            if attempt + 1 < retries:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError("请求失败: %s" % last)


def json_of(response):
    try:
        return response.json()
    except Exception:
        return {}


def desktop_headers(token):
    return {
        "Authorization": "Bearer %s" % strip_bearer(token),
        "X-Client-Platform": "desktop-windows",
        "X-Client-Version": "v1.0.0",
        "Accept": "application/json",
    }


# ---------- 上游协议 ----------

def desktop_grant(token):
    """一次性桌面登录奖励；失败不算签到失败，只作为附加信息。"""
    try:
        response = request("POST", ORIGIN + GRANT_PATH, headers=desktop_headers(token),
                           body={}, timeout=20, retries=1)
        data = json_of(response)
        return {"granted": data.get("granted") is True}
    except Exception as error:
        return {"granted": False, "error": str(error)}


def trigger_daily(token):
    """GET setting_info 触发服务端按天发放；返回发放弹窗/提示原文。"""
    headers = desktop_headers(token)
    headers["X-Raccoon-Language"] = "zh"
    response = request("GET", ORIGIN + SETTINGS_PATH, headers=headers)
    if response.status_code == 401:
        raise RuntimeError("登录状态失效，重新登录一下吧该账号")
    if response.status_code != 200:
        raise RuntimeError("setting_info 返回 HTTP %s" % response.status_code)
    data = json_of(response)
    return {
        "popups": data.get("point_grant_popups"),
        "toast": data.get("point_grant_toast"),
    }


def bills_today(token):
    """拉账单，汇总本地今天且 points>0 的入账。"""
    response = request("GET", ORIGIN + BILLS_PATH, headers=desktop_headers(token), timeout=30)
    if response.status_code == 401:
        raise RuntimeError("登录状态失效，重新登录一下吧该账号")
    if response.status_code != 200:
        raise RuntimeError("账单接口返回 HTTP %s" % response.status_code)
    data = json_of(response)
    today = time.strftime("%Y-%m-%d")
    grants = []
    for item in data.get("items") or []:
        if not isinstance(item, dict):
            continue
        try:
            points = int(item.get("points") or 0)
        except Exception:
            continue
        created = str(item.get("created_at") or "")
        if points > 0 and created[:10] == today:
            grants.append({
                "name": item.get("event_name") or "积分发放",
                "points": points,
                "at": created.replace("T", " ")[11:19],
            })
    return grants


def do_checkin(account):
    desktop = {"granted": False}
    if not QUERY_ONLY:
        desktop = desktop_grant(account["token"])
        if desktop.get("granted"):
            log("   🖥️ 桌面登录奖励已发放")
        elif desktop.get("error"):
            log("   ℹ️ 桌面登录奖励未领取（老账号属正常）")

    settings = {}
    if not QUERY_ONLY:
        settings = trigger_daily(account["token"])
        if settings.get("toast") or settings.get("popups"):
            log("   🎁 上游发放提示: %s" % json.dumps(settings, ensure_ascii=False)[:160])

    grants = bills_today(account["token"])
    total = sum(item["points"] for item in grants)
    parts = []
    if desktop.get("granted"):
        parts.append("桌面登录奖励已发放")
    if total > 0:
        parts.append("今日积分 +%d（%s）" % (total, "，".join(
            "%s+%d" % (item["name"], item["points"]) for item in grants[:3])))
    else:
        parts.append("今日未见积分入账（可能已领取）")
    return total > 0, "；".join(parts)


# ---------- 推送 ----------

def post_json(url, payload, timeout=20):
    session = requests.Session()
    session.trust_env = False
    return session.post(url, json=payload, timeout=timeout, verify=False)


def _env(name):
    return os.environ.get(name, "").strip()


def notify_pushplus(title, content):
    token = _env("PUSHPLUS_TOKEN")
    if not token:
        return False
    try:
        text = (content[:18000] + "\n...(已截断)") if len(content) > 18000 else content
        answer = post_json("https://www.pushplus.plus/send",
                           {"token": token, "title": title, "content": text, "template": "txt"})
        return str(json_of(answer).get("code")) == "200"
    except Exception:
        return False


def notify_bark(title, content):
    endpoint = _env("BARK_URL").rstrip("/")
    if not endpoint:
        return False
    try:
        answer = post_json(endpoint, {"title": title, "body": content, "group": "小浣熊"})
        return json_of(answer).get("code") == 200
    except Exception:
        return False


def notify_wecom(title, content):
    hook = _env("WECOM_WEBHOOK")
    if not hook:
        return False
    if not hook.startswith("http"):
        hook = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=" + hook
    try:
        answer = post_json(hook, {"msgtype": "text",
                                  "text": {"content": ("%s\n%s" % (title, content))[:2000]}})
        return json_of(answer).get("errcode") == 0
    except Exception:
        return False


def notify_dingtalk(title, content):
    hook = _env("DINGTALK_WEBHOOK")
    if not hook:
        return False
    try:
        secret = _env("DINGTALK_SECRET")
        if secret:
            stamp = str(int(time.time() * 1000))
            digest = hmac.new(secret.encode(), ("%s\n%s" % (stamp, secret)).encode(),
                              hashlib.sha256).digest()
            hook += ("&" if "?" in hook else "?") + "timestamp=%s&sign=%s" % (
                stamp, requests.utils.quote(base64.b64encode(digest)))
        answer = post_json(hook, {"msgtype": "text",
                                  "text": {"content": "%s\n%s" % (title, content)}})
        return json_of(answer).get("errcode") == 0
    except Exception:
        return False


def notify_ql(title, content):
    try:
        from notify import send as panel_send
        panel_send(title, content)
        return True
    except Exception:
        pass
    endpoint = _env("QL_URL").rstrip("/")
    token = _env("QL_TOKEN")
    if not endpoint or not token:
        return False
    try:
        session = requests.Session()
        session.trust_env = False
        answer = session.post(endpoint + "/api/system/notify?token=" + token,
                              json={"title": title, "content": content}, timeout=15, verify=False)
        return str(json_of(answer).get("code")) in ("0", "200")
    except Exception:
        return False


def notify_all(title, content):
    handlers = (notify_pushplus, notify_bark, notify_wecom, notify_dingtalk, notify_ql)
    if not any(handler(title, content) for handler in handlers):
        log("（未配置推送渠道，本次只记录日志）")


# ---------- 账号解析与主流程 ----------

def parse_accounts(raw):
    accounts = []
    for index, line in enumerate(split_accounts(raw), 1):
        parts = [part.strip() for part in line.split("|")]
        if len(parts) >= 2:
            note, token = parts[0], parts[1]
        else:
            note, token = "账号%d" % index, parts[0]
        token = strip_bearer(token)
        if token:
            accounts.append({"note": note or ("账号%d" % index), "token": token})
    return accounts


def main():
    global ONLY, QUERY_ONLY, NO_NOTIFY
    args = sys.argv[1:]
    if "--query" in args:
        QUERY_ONLY = True
    if "--no-notify" in args:
        NO_NOTIFY = True
    if "--only" in args:
        try:
            ONLY = int(args[args.index("--only") + 1])
        except Exception:
            ONLY = None

    accounts = parse_accounts(os.environ.get("RACCOON_TOKENS", ""))
    if not accounts:
        log("❌ 未配置 RACCOON_TOKENS（多条用换行或 & 分隔；每条: token 或 备注|token）")
        return

    log("╔════════════════════════════════════╗")
    log("║ 🐻 小浣熊 每日签到                 ║")
    log("╚════════════════════════════════════╝")
    log("👥 账号数: %d  站点: %s" % (len(accounts), ORIGIN))

    report = []
    for index, account in enumerate(accounts, 1):
        if ONLY and index != ONLY:
            continue
        log("👤 [%d] %s  token=%s" % (index, account["note"], mask(account["token"])))
        try:
            success, message = do_checkin(account)
            log("   %s %s" % ("✅" if success else "ℹ️", message))
            report.append("账号%d %s: %s %s" % (index, account["note"], "✅" if success else "ℹ️", message))
        except Exception as error:
            log("   ❌ 异常: %s" % error)
            report.append("账号%d %s: ❌ %s" % (index, account["note"], error))
        time.sleep(1.5)

    summary = "🐻 小浣熊签到报告\n" + "\n".join(report) + "\n🕐 " + time.strftime("%Y-%m-%d %H:%M")
    log(summary)
    if not NO_NOTIFY:
        notify_all("🐻 小浣熊签到报告", summary)


if __name__ == "__main__":
    main()
