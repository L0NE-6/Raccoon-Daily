#!/usr/bin/env python3
"""
🐻 小浣熊 每日签到 - 青龙脚本
------------------------------------------------------------

📌 功能
   小浣熊每日积分任务（成功判据是可用每日积分而不是某一步 200）：
   1. GET /api/web/auth/v1/user_info        页面访问，延期每日积分（best-effort）
   2. GET /api/web/points/v1/balance         余额硬依赖，确认账户可用额度
   3. GET /api/web/points/v2/bills           只认 daily_grant、到期时间与清零配对
      「今日」和 01:30 宽限固定按北京时间（UTC+8），不跟随宿主机时区
   3. 新手任务：首次电脑端 / 手机端登录奖励（各一次性，名义 3000 积分）
      - 两条端点互不共享额度：桌面端领过的账号，手机端那条照样能领
      - 领取结果记本机台账（raccoon_onboarding.json），结算过的不再重复探测 / 提示

🔑 环境变量
   RACCOON_TOKENS   【必填】多账号用换行或 & 分隔：
       token
       备注|token
       备注|token|refresh_token   ← 推荐；access 只活 2~3 小时，带 RT 才能自动续期
       备注|token|refresh_token|office_identity   ← 组织账号可附带显式组织身份
     token 为 xiaohuanxiong.com 的登录 JWT（带不带 Bearer 前缀都行）
   RACCOON_TOKEN_FILE   可选，续期缓存文件路径（默认脚本同目录 raccoon_tokens.json）
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
USER_INFO_PATH = "/api/web/auth/v1/user_info"
BALANCE_PATH = "/api/web/points/v1/balance"
BILLS_PATH = "/api/web/points/v2/bills?paging.limit=60&type=income"
REFRESH_PATH = "/api/web/auth/v1/refresh"
CLIENT_NAME = "raccoon-work"
CLIENT_PLATFORM = "desktop-windows"
CLIENT_VERSION = "v1.1.5"
REFRESH_LEAD_SECONDS = 300
TOKEN_STORE_NAME = "raccoon_tokens.json"
ORG_IDENTITY_FIELDS = ("officeIdentity", "office_identity")

ONLY = None
QUERY_ONLY = False
NO_NOTIFY = False
ONBOARDING = True

BEIJING = timezone(timedelta(hours=8))
DAILY_GRANT = "daily_grant"
DAILY_EXPIRE = "daily_expire"
DAILY_FRESH_SECONDS = 90
GRANT_GRACE_HOUR = 1
GRANT_GRACE_MINUTE = 30
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


def first_text(*values):
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def credential_org_code(credentials):
    """Read an explicit organization identity from credential fields only."""
    if not isinstance(credentials, dict):
        return ""
    value = first_text(*(credentials.get(key) for key in ORG_IDENTITY_FIELDS))
    if not value or value == "personal":
        return ""
    if not value.isascii() or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError("小浣熊组织身份格式无效，请重新导入登录态")
    return value


def account_identity_label(credentials):
    try:
        return "组织" if credential_org_code(credentials) else "个人"
    except ValueError:
        return "组织字段异常"


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


def desktop_headers(token, credentials=None):
    headers = {
        "Authorization": "Bearer %s" % strip_bearer(token),
        "X-Client-Name": CLIENT_NAME,
        "X-Client-Platform": CLIENT_PLATFORM,
        "X-Client-Version": CLIENT_VERSION,
        "Accept": "application/json",
    }
    org_code = credential_org_code(credentials)
    if org_code:
        headers["X-Org-Code"] = org_code
    return headers


# ---------- 上游协议 ----------


def trigger_daily(token, credentials=None):
    """GET setting_info 触发服务端按天发放；返回发放弹窗/提示原文。"""
    headers = desktop_headers(token, credentials)
    headers["X-Raccoon-Language"] = "zh"
    response = request("GET", ORIGIN + SETTINGS_PATH, headers=headers)
    payload = json_of(response)
    if response.status_code in (401, 403) or payload.get("code") == 200003:
        raise AuthExpired("登录状态失效，请重新登录（或用 refresh_token 自动续期）")
    if response.status_code != 200:
        raise RuntimeError("setting_info 返回 HTTP %s" % response.status_code)
    data = unwrap_api(payload)
    return {
        "popups": data.get("point_grant_popups"),
        "toast": data.get("point_grant_toast"),
    }


def visit_page(token, credentials=None):
    """网页会话访问；每日积分登录延期依赖该接口。"""
    headers = desktop_headers(token, credentials)
    headers["X-Raccoon-Language"] = "zh"
    response = request("GET", ORIGIN + USER_INFO_PATH, headers=headers)
    payload = json_of(response)
    if response.status_code in (401, 403) or payload.get("code") == 200003:
        raise AuthExpired("登录状态失效，请重新登录（或用 refresh_token 自动续期）")
    if response.status_code != 200:
        raise RuntimeError("user_info 返回 HTTP %s" % response.status_code)
    code = payload.get("code")
    if isinstance(code, int) and code not in (0, 200):
        raise RuntimeError(payload.get("message") or payload.get("msg") or
                           ("user_info 返回业务错误 code=%s" % code))
    data = payload.get("data")
    return data if isinstance(data, dict) else {}


def account_balance(token, credentials=None):
    """读取余额；available_points 是签到硬依赖。"""
    response = request("GET", ORIGIN + BALANCE_PATH,
                       headers=desktop_headers(token, credentials), timeout=30)
    payload = json_of(response)
    if response.status_code in (401, 403) or payload.get("code") == 200003:
        raise AuthExpired("登录状态失效，请重新登录（或用 refresh_token 自动续期）")
    if response.status_code != 200:
        raise RuntimeError("余额接口返回 HTTP %s" % response.status_code)
    data = unwrap_api(payload)
    available = data.get("available_points")
    if isinstance(available, bool) or not isinstance(available, (int, float)):
        raise RuntimeError("余额响应缺少数字型 available_points")
    return data


def bill_items(token, credentials=None):
    """拉最近 60 条账单，返回原始流水列表。"""
    response = request("GET", ORIGIN + BILLS_PATH,
                       headers=desktop_headers(token, credentials), timeout=30)
    payload = json_of(response)
    if response.status_code in (401, 403) or payload.get("code") == 200003:
        raise AuthExpired("登录状态失效，请重新登录（或用 refresh_token 自动续期）")
    if response.status_code != 200:
        raise RuntimeError("账单接口返回 HTTP %s" % response.status_code)
    data = unwrap_api(payload)
    items = data.get("items")
    if not isinstance(items, list):
        raise RuntimeError("账单响应缺少列表型 items")
    return items


def parse_iso(value):
    """ISO8601 → 北京时间 aware datetime；坏值返回 None。"""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=BEIJING)
    return parsed.astimezone(BEIJING)


def positive_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if value > 0 else None


def pick_today_grant(items, now=None):
    """今日 daily_grant，按 CST 日期；同日多条取最大点数。"""
    current = now or datetime.now(BEIJING)
    today = current.astimezone(BEIJING).date()
    best = None
    best_points = None
    for item in items:
        if not isinstance(item, dict) or item.get("biz_type") != DAILY_GRANT:
            continue
        points = positive_number(item.get("points"))
        if points is None:
            continue
        reference = parse_iso(item.get("grant_at")) or parse_iso(item.get("created_at"))
        if reference is None or reference.date() != today:
            continue
        if best is None or points > best_points:
            best, best_points = item, points
    return best


def grant_grace_at(now=None):
    current = (now or datetime.now(BEIJING)).astimezone(BEIJING)
    return current.replace(hour=GRANT_GRACE_HOUR, minute=GRANT_GRACE_MINUTE,
                           second=0, microsecond=0)


def grant_key(item):
    grant = parse_iso(item.get("grant_at")) or parse_iso(item.get("created_at"))
    day = grant.date().isoformat() if grant else ""
    return day, float(item.get("points") or 0)


def expired_grant_keys(items):
    keys = set()
    for item in items:
        if not isinstance(item, dict) or item.get("biz_type") != DAILY_EXPIRE:
            continue
        points = item.get("points")
        if isinstance(points, bool) or not isinstance(points, (int, float)):
            continue
        keys.add(grant_key({**item, "points": abs(points)}))
    return keys


def pick_active_grants(items, now=None):
    """未过期且未被 daily_expire 消费的 daily_grant，按到期升序。"""
    current = (now or datetime.now(BEIJING)).astimezone(BEIJING)
    stamp = current.timestamp()
    expired = expired_grant_keys(items)
    active = []
    for item in items:
        if not isinstance(item, dict) or item.get("biz_type") != DAILY_GRANT:
            continue
        points = positive_number(item.get("points"))
        expire_at = parse_iso(item.get("expire_at"))
        if points is None or expire_at is None or expire_at.timestamp() <= stamp:
            continue
        if grant_key(item) in expired:
            continue
        active.append(item)
    active.sort(key=lambda item: parse_iso(item.get("expire_at")).timestamp())
    return active


def checkin_result(items, started, now=None):
    """账单 → 签到结论；成功、已签、可用旧额度与 01:30 宽限分开表达。"""
    current = (now or datetime.now(BEIJING)).astimezone(BEIJING)
    row = pick_today_grant(items, current)
    if row is not None:
        points = positive_number(row.get("points"))
        created = parse_iso(row.get("created_at"))
        fresh = bool(created and created.timestamp() >= started - DAILY_FRESH_SECONDS)
        expire_at = parse_iso(row.get("expire_at"))
        return {
            "ok": True,
            "credit": points,
            "already_checked_in": not fresh,
            "retry_at": None,
            "seal_until": None,
            "message": "每日积分 +%g" % points,
            "expire_at": expire_at,
        }
    active = pick_active_grants(items, current)
    if active:
        total = sum(positive_number(item.get("points")) for item in active)
        nearest = parse_iso(active[0].get("expire_at"))
        grace = grant_grace_at(current)
        seal_until = int(grace.timestamp()) if current < grace else None
        return {
            "ok": True,
            "credit": total,
            "already_checked_in": True,
            "retry_at": None,
            "seal_until": seal_until,
            "message": "今日额度可用 %g（本次未产生新发放，最早 %s 到期）" % (
                total, nearest.strftime("%Y-%m-%d")),
            "expire_at": nearest,
        }
    grace = grant_grace_at(current)
    retry_at = int(grace.timestamp()) if current < grace else None
    return {
        "ok": False,
        "credit": 0.0,
        "already_checked_in": False,
        "retry_at": retry_at,
        "seal_until": None,
        "message": "上游今日每日积分尚未同步；01:30 后重试" if retry_at
        else "上游今日每日积分尚未发放",
        "expire_at": None,
    }


def do_checkin(account):
    started = time.time()
    if not QUERY_ONLY:
        try:
            call_with_auth(account, lambda acc: visit_page(acc["token"], acc))
        except AuthExpired:
            raise
        except Exception as error:
            log("   ⚠️ 页面访问失败，继续核对每日积分: %s" % error)
        call_with_auth(account, lambda acc: account_balance(acc["token"], acc))

    items = call_with_auth(account, lambda acc: bill_items(acc["token"], acc))
    decision = checkin_result(items, started)
    parts = [decision["message"]]

    if not QUERY_ONLY and ONBOARDING:
        try:
            parts.extend(claim_onboarding(account))
        except Exception as error:
            parts.append("新手奖励领取异常：%s" % error)
    return decision["ok"], "；".join(parts)


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
        office_identity = ""
        if len(parts) >= 4:
            note, token, refresh, office_identity = parts[:4]
        elif len(parts) == 3:
            note, token, refresh = parts[0], parts[1], parts[2]
        elif len(parts) == 2:
            note, token, refresh = parts[0], parts[1], ""
        else:
            note, token, refresh = "账号%d" % index, parts[0], ""
        token = strip_bearer(token)
        if token:
            account = {"note": note or ("账号%d" % index), "token": token,
                       "refresh": strip_bearer(refresh),
                       "office_identity": office_identity}
            account["_key"] = account_store_key(account, index)
            accounts.append(account)
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


class AuthExpired(RuntimeError):
    """登录态失效（HTTP 401 / 业务码 200003），可用 refresh_token 尝试续期。"""


def token_store_path():
    override = os.environ.get("RACCOON_TOKEN_FILE", "").strip()
    if override:
        return override
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), TOKEN_STORE_NAME)


def load_token_store():
    try:
        with open(token_store_path(), "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict) and isinstance(data.get("accounts"), dict):
            return data
    except Exception:
        pass
    return {"version": 1, "accounts": {}}


def save_token_store(state):
    path = token_store_path()
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
        log("   ⚠️ 续期缓存写入失败: %s" % error)
        return False


def jwt_exp(token):
    """JWT 的 exp（秒）；读不到返回 0。"""
    try:
        parts = strip_bearer(token).split(".")
        pad = parts[1] + "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(pad))
        exp = payload.get("exp")
        if isinstance(exp, (int, float)):
            return float(exp)
        if isinstance(exp, str) and exp.strip():
            return float(exp.strip())
    except Exception:
        pass
    return 0.0


def account_store_key(account, index):
    """续期缓存的稳定键：备注 + 序号（token 每次续期都会变，不能拿它当键）。"""
    raw = "%s#%d" % (account.get("note") or "", index or 0)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def refresh_candidates(account):
    """可尝试的 refresh_token：本地缓存（最新一份）在前，环境变量里的在后。"""
    out = []
    entry = load_token_store()["accounts"].get(account.get("_key") or "")
    if isinstance(entry, dict) and entry.get("refresh"):
        out.append(str(entry["refresh"]).strip())
    if account.get("refresh"):
        out.append(str(account["refresh"]).strip())
    seen = set()
    result = []
    for item in out:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def refresh_account(account):
    """用 refresh_token 换新 access；refresh 轮换时一并落盘。"""
    candidates = refresh_candidates(account)
    if not candidates:
        raise AuthExpired("没有 refresh_token，无法自动续期；请用 raccoon_login.py 重新登录")
    last_error = None
    for refresh in candidates:
        response = request("POST", ORIGIN + REFRESH_PATH,
                           headers={"Content-Type": "application/json", "Accept": "application/json"},
                           body={"refresh_token": refresh}, timeout=20, retries=2)
        payload = json_of(response)
        code = payload.get("code")
        if response.status_code in (401, 403) or code == 200003:
            last_error = AuthExpired("refresh_token 已失效，请用 raccoon_login.py 重新登录")
            continue
        if response.status_code != 200 or code not in (0, None):
            message = first_text(payload.get("message"), payload.get("details"), payload.get("msg")) \
                or ("HTTP %s" % response.status_code)
            raise RuntimeError("续期失败：%s" % message)
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        access = first_text(data.get("access_token"))
        if not access:
            raise RuntimeError("续期响应缺少 access_token")
        new_refresh = first_text(data.get("refresh_token")) or refresh
        account["token"] = access
        account["refresh"] = new_refresh
        state = load_token_store()
        state["accounts"][account.get("_key") or account_state_key(access)] = {
            "access": access,
            "refresh": new_refresh,
            "updated": int(time.time() * 1000),
        }
        save_token_store(state)
        log("   🔄 登录态已续期（access 2~3 小时有效，refresh 已滚动保存）")
        return True
    raise last_error or RuntimeError("续期失败")


def ensure_token_fresh(account):
    """临期（5 分钟内）主动续期；已过期且无 RT 时直接报失效。"""
    exp = jwt_exp(account.get("token") or "")
    if not exp:
        return
    if exp - time.time() > REFRESH_LEAD_SECONDS:
        return
    if account.get("refresh") or load_token_store()["accounts"].get(account.get("_key") or ""):
        refresh_account(account)
    elif exp <= time.time():
        raise AuthExpired("access_token 已过期（约 2~3 小时有效），请用 raccoon_login.py 重新登录")


def call_with_auth(account, fn):
    """先做临期续期；遇到 401/200003 时用 refresh_token 续期并重试一次。"""
    ensure_token_fresh(account)
    try:
        return fn(account)
    except AuthExpired:
        refresh_account(account)
        return fn(account)


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


def mobile_headers(token, credentials=None):
    headers = {
        "Authorization": "Bearer %s" % strip_bearer(token),
        "X-Client-Platform": "app-android",
        "X-Client-Version": "v1.0.3",
        "Accept": "application/json",
    }
    org_code = credential_org_code(credentials)
    if org_code:
        headers["X-Org-Code"] = org_code
    return headers


def grant_login_points(token, mobile=False, credentials=None):
    """打一次首登奖励端点（幂等）；两端只差客户端身份头与路径。"""
    headers = (mobile_headers(token, credentials) if mobile
               else desktop_headers(token, credentials))
    path = MOBILE_GRANT_PATH if mobile else GRANT_PATH
    response = request("POST", ORIGIN + path, headers=headers, body={}, timeout=20, retries=1)
    payload = json_of(response)
    if response.status_code in (401, 403) or payload.get("code") == 200003:
        raise AuthExpired("登录状态失效，请重新登录（或用 refresh_token 自动续期）")
    if response.status_code != 200:
        raise RuntimeError("登录奖励接口返回 HTTP %s" % response.status_code)
    return unwrap_api(payload)


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
            data = call_with_auth(
                account,
                lambda acc, m=task["mobile"]: grant_login_points(
                    acc["token"], mobile=m, credentials=acc),
            )
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
        log("❌ 未配置 RACCOON_TOKENS（每条: token / 备注|token / 备注|token|refresh_token）")
        return

    log("╔════════════════════════════════════╗")
    log("║ 🐻 小浣熊 每日签到                 ║")
    log("╚════════════════════════════════════╝")
    log("👥 账号数: %d  站点: %s" % (len(accounts), ORIGIN))
    with_rt = sum(1 for account in accounts if account.get("refresh"))
    if with_rt:
        log("🔁 refresh_token 自动续期: %d/%d 个账号已启用" % (with_rt, len(accounts)))
    else:
        log("ℹ️ 未带 refresh_token：access 约 2~3 小时有效，过期后需用 raccoon_login.py 重新登录")

    report = []
    for index, account in enumerate(accounts, 1):
        if ONLY and index != ONLY:
            continue
        log("👤 [%d] %s  token=%s  身份=%s" % (
            index, account["note"], mask(account["token"]),
            account_identity_label(account)))
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
