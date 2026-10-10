#!/usr/bin/env python3
"""
🐻 小浣熊 每日签到 - 青龙脚本
------------------------------------------------------------

📌 功能
   小浣熊每日积分任务（成功判据是账单核对而不是某一步 200）：
   1. GET  /api/web/office/v3/setting_info   每日积分发放触发器（按天幂等）
   2. GET  /api/web/points/v1/bills          拉账单，今日 points>0 才算签到成功
      「今日」固定按北京时间（UTC+8）切日，不跟随宿主机时区
   3. 新手任务：首次电脑端 / 手机端登录奖励（各一次性，名义 3000 积分）
      - 两条端点互不共享额度：桌面端领过的账号，手机端那条照样能领
      - 领取结果记本机台账（raccoon_onboarding.json），结算过的不再重复探测 / 提示

🔑 环境变量
   RACCOON_TOKENS   【必填】多账号用换行或 & 分隔：
       token
       备注|token
     token 为 xiaohuanxiong.com 的登录 JWT（带不带 Bearer 前缀都行）
   RACCOON_STATE_FILE   可选，新手奖励台账文件路径（默认脚本同目录）

   推送通道（均可选）：PUSHPLUS_TOKEN / BARK_URL / WECOM_WEBHOOK / DINGTALK_WEBHOOK / DINGTALK_SECRET

⌨️ 命令
   python raccoon_daily.py                    正常签到 + 自动领取新手奖励
   python raccoon_daily.py --query            只查今日入账，不触发发放、不动新手奖励
   python raccoon_daily.py --skip-onboarding  只做每日签到，不碰新手奖励
   python raccoon_daily.py --only 2           只跑第 2 个账号
   python raccoon_daily.py --no-notify        不推送

📄 依赖：requests
"""
import base64
import hashlib
import hmac
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

import urllib3
urllib3.disable_warnings()

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

ORIGIN = os.environ.get("RACCOON_MAIN_SITE_URL", "").strip() or "https://xiaohuanxiong.com"
GRANT_PATH = "/api/web/desktop/v1/login/points/grant"
MOBILE_GRANT_PATH = "/api/web/mobile/v1/login/points/grant"
SETTINGS_PATH = "/api/web/office/v3/setting_info"
BILLS_PATH = "/api/web/points/v1/bills?paging.limit=20&paging.offset=0"

ONLY = None
QUERY_ONLY = False
NO_NOTIFY = False
ONBOARDING = True

BEIJING = timezone(timedelta(hours=8))
ONBOARDING_NOMINAL_POINTS = 3000
ONBOARDING_TASKS = (
    {"key": "desktop_login_grant", "title": "首次电脑端登录奖励",
     "path": GRANT_PATH, "mobile": False},
    {"key": "mobile_login_grant", "title": "首次手机端登录奖励",
     "path": MOBILE_GRANT_PATH, "mobile": True},
)


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


def trigger_daily(token):
    """GET setting_info 触发服务端按天发放；返回发放弹窗/提示原文。"""
    headers = desktop_headers(token)
    headers["X-Raccoon-Language"] = "zh"
    response = request("GET", ORIGIN + SETTINGS_PATH, headers=headers)
    if response.status_code == 401:
        raise RuntimeError("登录状态失效，重新登录一下吧该账号")
    if response.status_code != 200:
        raise RuntimeError("setting_info 返回 HTTP %s" % response.status_code)
    data = unwrap_api(json_of(response))
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
    data = unwrap_api(json_of(response))
    today = beijing_today()
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
    settings = {}
    if not QUERY_ONLY:
        settings = trigger_daily(account["token"])
        if settings.get("toast") or settings.get("popups"):
            log("   🎁 上游发放提示: %s" % json.dumps(settings, ensure_ascii=False)[:160])

    grants = bills_today(account["token"])
    total = sum(item["points"] for item in grants)
    parts = []
    if total > 0:
        parts.append("今日积分 +%d（%s）" % (total, "，".join(
            "%s+%d" % (item["name"], item["points"]) for item in grants[:3])))
    else:
        parts.append("今日未见积分入账（可能已领取）")

    if not QUERY_ONLY and ONBOARDING:
        try:
            parts.extend(claim_onboarding(account))
        except Exception as error:
            parts.append("新手奖励领取异常：%s" % error)
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


def unwrap_api(payload):
    """服务端统一包 {code, data}：code 非 0 抛错，data 非空取 data。"""
    if not isinstance(payload, dict):
        return {}
    code = payload.get("code")
    if isinstance(code, int) and code != 0:
        message = payload.get("message") or payload.get("msg") or ("返回异常 code=%s" % code)
        raise RuntimeError(str(message))
    data = payload.get("data")
    if isinstance(data, dict):
        return data
    return payload


def beijing_today():
    """北京时间（UTC+8）的今天；上游自然日以北京零点切分。"""
    return datetime.now(BEIJING).strftime("%Y-%m-%d")


def state_file_path():
    override = os.environ.get("RACCOON_STATE_FILE", "").strip()
    if override:
        return override
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "raccoon_onboarding.json")


def account_state_key(token):
    """用 token 的哈希做台账键，文件里不落 token 明文。"""
    return hashlib.sha256(strip_bearer(token).encode("utf-8")).hexdigest()[:16]


def load_onboarding_state():
    try:
        with open(state_file_path(), "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict) and isinstance(data.get("accounts"), dict):
            return data
    except Exception:
        pass
    return {"version": 1, "accounts": {}}


def save_onboarding_state(state):
    path = state_file_path()
    try:
        folder = os.path.dirname(os.path.abspath(path))
        if folder and not os.path.isdir(folder):
            os.makedirs(folder)
        temp = path + ".tmp"
        with open(temp, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(temp, path)
        return True
    except Exception as error:
        log("   ⚠️ 新手奖励台账写入失败: %s" % error)
        return False


def mobile_headers(token):
    return {
        "Authorization": "Bearer %s" % strip_bearer(token),
        "X-Client-Platform": "app-android",
        "X-Client-Version": "v1.0.3",
        "Accept": "application/json",
    }


def grant_login_points(token, mobile=False):
    """打一次首登奖励端点（幂等）；两端只差客户端身份头与路径。"""
    headers = mobile_headers(token) if mobile else desktop_headers(token)
    path = MOBILE_GRANT_PATH if mobile else GRANT_PATH
    response = request("POST", ORIGIN + path, headers=headers, body={}, timeout=20, retries=1)
    if response.status_code == 401:
        raise RuntimeError("登录状态失效，重新登录一下吧该账号")
    if response.status_code != 200:
        raise RuntimeError("登录奖励接口返回 HTTP %s" % response.status_code)
    return unwrap_api(json_of(response))


def claim_onboarding(account):
    """领取两条一次性登录奖励；台账里结算过的不发请求也不提示。"""
    state = load_onboarding_state()
    key = account_state_key(account["token"])
    ledger = state["accounts"].get(key)
    if not isinstance(ledger, dict):
        ledger = {}
    messages = []
    changed = False
    for task in ONBOARDING_TASKS:
        if ledger.get(task["key"]):
            continue
        try:
            data = grant_login_points(account["token"], mobile=task["mobile"])
        except Exception as error:
            messages.append("%s领取失败（%s）" % (task["title"], error))
            continue
        granted = data.get("granted") is True
        ledger[task["key"]] = int(time.time() * 1000)
        changed = True
        if granted:
            points = 0
            popup = data.get("popup")
            if isinstance(popup, dict):
                try:
                    points = int(popup.get("points") or 0)
                except Exception:
                    points = 0
            if points <= 0:
                points = ONBOARDING_NOMINAL_POINTS
            messages.append("%s +%d" % (task["title"], points))
        else:
            log("   ℹ️ %s此前已发放，跳过重复领取" % task["title"])
    if changed:
        state["accounts"][key] = ledger
        save_onboarding_state(state)
    return messages


def main():
    global ONLY, QUERY_ONLY, NO_NOTIFY, ONBOARDING
    args = sys.argv[1:]
    if "--query" in args:
        QUERY_ONLY = True
    if "--no-notify" in args:
        NO_NOTIFY = True
    if "--skip-onboarding" in args:
        ONBOARDING = False
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
