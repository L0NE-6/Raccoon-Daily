#!/usr/bin/env python3
"""
🐻 小浣熊 网页授权登录工具
------------------------------------------------------------
在浏览器登录一次，把回调地址贴回来，即可拿到登录 token。

用法:
  python raccoon_login.py                     # 交互式（打开授权页 + 粘贴回调地址）
  python raccoon_login.py --callback "office-raccoon://auth/callback?code=...&state=..."
  python raccoon_login.py --note 主号         # 指定备注名
  python raccoon_login.py --no-verify         # 跳过登录后校验

输出（直接作为 RACCOON_TOKENS 的一行）:
  备注|token

回调地址哪里来:
  · 授权页登录成功后，浏览器会跳转到 office-raccoon://auth/callback?...
  · 若浏览器提示无法打开该协议，直接复制地址栏里的完整地址即可。

仅依赖 requests。
"""
import os
import sys
import time
import urllib.parse
import uuid
import webbrowser

import requests

import urllib3
urllib3.disable_warnings()

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

ORIGIN = os.environ.get("RACCOON_MAIN_SITE_URL", "").strip().rstrip("/") or "https://xiaohuanxiong.com"
AUTH_BASE = ORIGIN + "/api/web/auth/v1"
AUTHORIZE_PATH = "/code/authorize"
EXCHANGE_PATH = "/login_with_authorization_code"
SETTINGS_PATH = "/api/web/office/v3/setting_info"
APP_NAME = "办公小浣熊客户端"
CALLBACK_SCHEME = "office-raccoon"
CALLBACK_HOST = "auth"
CALLBACK_PATH = "/callback"


def log(msg):
    print("%s %s" % (time.strftime("[%H:%M:%S]"), msg), flush=True)


def request(method, url, headers=None, body=None, timeout=20, retries=2):
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


def first_text(*values):
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def build_authorize_url(state):
    query = urllib.parse.urlencode({
        "login_source": "desktop",
        "appname": APP_NAME,
        "state": state,
    })
    return ORIGIN + AUTHORIZE_PATH + "?" + query


def parse_callback(raw_url, expected_state):
    url = urllib.parse.urlsplit(str(raw_url or "").strip())
    host = (url.hostname or "").lower()
    if url.scheme != CALLBACK_SCHEME or host != CALLBACK_HOST or url.path != CALLBACK_PATH:
        raise ValueError("回调地址格式不正确，应为 office-raccoon://auth/callback?code=...&state=...")
    query = urllib.parse.parse_qs(url.query)
    code = first_text(*(query.get("code") or []))
    state = first_text(*(query.get("state") or []))
    if not code:
        raise ValueError("回调地址里没有 code")
    if state != expected_state:
        raise ValueError("回调地址里的 state 与本次发起的不一致，已拒绝（请重新发起）")
    return code


def exchange_code(code):
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/plain, */*"}
    response = request("POST", AUTH_BASE + EXCHANGE_PATH, headers=headers,
                       body={"authorization_code": code})
    payload = json_of(response)
    code_value = payload.get("code")
    if code_value == 200035:
        raise RuntimeError("授权码已失效：回调链接放太久或重复使用，请重新发起登录")
    if code_value not in (0, None) or response.status_code >= 400:
        message = first_text(payload.get("msg"), payload.get("message")) or ("HTTP %s" % response.status_code)
        raise RuntimeError("换取登录态失败：%s" % message)
    data = payload.get("data") or {}
    token = first_text(data.get("access_token"), data.get("accessToken"))
    if not token:
        raise RuntimeError("换取登录态成功但响应缺少 access_token")
    return {
        "token": token,
        "refresh_token": first_text(data.get("refresh_token"), data.get("refreshToken")),
    }


def verify(token):
    log("🔎 校验 token ...")
    headers = {
        "Authorization": "Bearer %s" % token,
        "X-Client-Platform": "desktop-windows",
        "X-Client-Version": "v1.0.0",
        "X-Raccoon-Language": "zh",
        "Accept": "application/json",
    }
    try:
        response = request("GET", ORIGIN + SETTINGS_PATH, headers=headers)
        if response.status_code == 200:
            log("✅ token 可用")
            return True
        if response.status_code in (401, 403):
            log("⚠️ token 未被接受（HTTP %s）" % response.status_code)
            return False
        log("⚠️ 校验返回 HTTP %s" % response.status_code)
    except Exception as error:
        log("⚠️ 校验异常：%s" % error)
    return False


def main():
    args = sys.argv[1:]
    do_verify = "--no-verify" not in args
    note = ""
    callback = ""
    if "--note" in args:
        try:
            note = args[args.index("--note") + 1]
        except Exception:
            note = ""
    if "--callback" in args:
        try:
            callback = args[args.index("--callback") + 1]
        except Exception:
            callback = ""

    print("╔══════════════════════════════════════════╗")
    print("║ 🐻 小浣熊 网页授权登录                    ║")
    print("╚══════════════════════════════════════════╝")

    state = uuid.uuid4().hex
    authorize_url = build_authorize_url(state)
    print("👉 请在浏览器打开下面的地址并完成登录：")
    print(authorize_url)
    try:
        webbrowser.open(authorize_url)
    except Exception:
        pass
    print("📋 登录成功后浏览器会跳到 office-raccoon://auth/callback?...")
    print("   若提示无法打开协议，直接复制地址栏里的完整地址。")

    if not callback:
        callback = input("🔗 请粘贴完整回调地址: ").strip()
    code = parse_callback(callback, state)
    credentials = exchange_code(code)
    log("✅ 换取登录态成功")
    if do_verify:
        verify(credentials["token"])

    env_line = "%s|%s" % (note or "小浣熊", credentials["token"])
    print("\n" + "-" * 50)
    print("✅ 将下面这行追加到 RACCOON_TOKENS")
    print("-" * 50)
    print(env_line)
    print("-" * 50)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n已取消")
        sys.exit(130)
    except Exception as error:
        print("❌ %s" % error)
        sys.exit(1)
