#!/usr/bin/env python3
"""
🐻 小浣熊 登录工具（微信扫码登录）
------------------------------------------------------------
在电脑上生成登录二维码 → 用微信扫一扫 → 自动换取登录态（含续期凭据）。
这是官方客户端当前（v1.0.35）的登录方式；旧版网页授权保留为 --web 备选。

用法:
  python raccoon_login.py                 # 微信扫码登录（默认，推荐）
  python raccoon_login.py --png qr.png    # 扫码模式额外保存二维码图片
  python raccoon_login.py --note 主号     # 指定备注名
  python raccoon_login.py --no-verify     # 跳过登录后校验
  python raccoon_login.py --web           # 旧版网页授权（粘贴 office-raccoon:// 回调）

输出（直接作为 RACCOON_TOKENS 的一行）:
  备注|token|refresh_token      # 上游下发 refresh_token 时（推荐）
  备注|token                    # 上游没有下发 refresh_token 时

说明:
  · 扫码流程：本地生成 32 位 code → 二维码指向厂商落地页
    `…/login/mp?code=…&appname=商汤小浣熊官网` → 每 2 秒轮询
    `POST /api/web/auth/v1/login_with_qrcode_code` 直到 success。
  · 终端里显示二维码需要可选依赖 qrcode（`pip install qrcode`）；装不了可
    用 --png 保存图片、或改用 --web 旧流程。
  · access_token 约 2~3 小时有效，refresh_token 约 30 天且**会轮换** ——
    请把 refresh_token 一起填进 RACCOON_TOKENS，日签脚本会自动续期。

依赖：requests（二维码显示另需可选的 qrcode）。
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
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass

ORIGIN = os.environ.get("RACCOON_MAIN_SITE_URL", "").strip().rstrip("/") or "https://xiaohuanxiong.com"
AUTH_BASE = ORIGIN + "/api/web/auth/v1"
QR_LOGIN_PATH = "/login_with_qrcode_code"
EXCHANGE_PATH = "/login_with_authorization_code"
AUTHORIZE_PATH = "/code/authorize"
SETTINGS_PATH = "/api/web/office/v3/setting_info"
QR_APP_NAME = "商汤小浣熊官网"
OAUTH_APP_NAME = "办公小浣熊客户端"
CALLBACK_SCHEME = "office-raccoon"
CALLBACK_HOST = "auth"
CALLBACK_PATH = "/callback"
CLIENT_PLATFORM = "desktop-windows"
CLIENT_VERSION = "v1.0.35"
POLL_INTERVAL = 2.0
LOGIN_TIMEOUT = 300.0


def log(msg):
    print("%s %s" % (time.strftime("[%H:%M:%S]"), msg), flush=True)


def mask(text, keep=6):
    text = str(text or "")
    if len(text) <= keep + 4:
        return text
    return text[:keep] + "****" + text[-4:]


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


def api_headers(token=None):
    headers = {
        "Accept": "application/json",
        "X-Client-Platform": CLIENT_PLATFORM,
        "X-Client-Version": CLIENT_VERSION,
        "X-Raccoon-Language": "zh",
    }
    if token:
        headers["Authorization"] = "Bearer %s" % token
    return headers


# ---------- 新版：微信扫码登录 ----------


def new_qr_code():
    """32 位 hex code（与官方客户端 WordArray.random(16) 同形）。"""
    return uuid.uuid4().hex


def qr_url(code):
    query = urllib.parse.urlencode({"code": code, "appname": QR_APP_NAME})
    return ORIGIN + "/login/mp?" + query


def show_qr(url, png_path=None):
    """终端打印二维码；装了 qrcode 才显示。返回是否成功显示。"""
    shown = False
    try:
        import qrcode
    except Exception:
        return False
    try:
        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        qr.make(fit=True)
        try:
            qr.print_ascii(invert=True)
            shown = True
        except Exception:
            shown = False
        if png_path:
            try:
                image = qr.make_image(fill_color="black", back_color="white")
                image.save(png_path)
                log("🖼️ 二维码已保存: %s" % png_path)
            except Exception as error:
                log("⚠️ 二维码图片保存失败: %s" % error)
    except Exception as error:
        log("⚠️ 二维码显示失败: %s" % error)
    return shown


def poll_qr(code):
    """轮询一次扫码状态：pending / logging / canceled / success。"""
    try:
        response = request("POST", AUTH_BASE + QR_LOGIN_PATH, headers=api_headers(),
                           body={"qrcode_code": code}, retries=1)
        payload = json_of(response)
    except Exception:
        return {"status": "pending"}
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    status = str(data.get("status") or "")
    return {
        "status": status,
        "access": first_text(data.get("access_token")),
        "refresh": first_text(data.get("refresh_token")),
    }


def qr_login(png_path=None):
    """微信扫码登录主流程（超时 5 分钟，二维码过期自动刷新）。"""
    deadline = time.time() + LOGIN_TIMEOUT
    code = new_qr_code()
    url = qr_url(code)
    print("\n👉 请用微信扫一扫下面的二维码（登录「商汤小浣熊」）：")
    shown = show_qr(url, png_path)
    print("🔗 %s" % url)
    if not shown:
        print("   （未安装 qrcode，终端无法直接显示二维码：pip install qrcode 即可；")
        print("     或把上面的链接自行生成二维码后用微信扫，亦可用 --web 走旧版授权）")
    scanned = False
    while time.time() < deadline:
        state = poll_qr(code)
        status = state["status"]
        if status == "success" and state.get("access"):
            return {"token": state["access"], "refresh_token": state.get("refresh", "")}
        if status == "canceled":
            code = new_qr_code()
            url = qr_url(code)
            log("♻️ 二维码已过期，已刷新，请重新扫码")
            show_qr(url)
            print("🔗 %s" % url)
            scanned = False
        elif status == "logging" and not scanned:
            log("📱 已扫码，请在微信里确认")
            scanned = True
        time.sleep(POLL_INTERVAL)
    raise RuntimeError("登录超时（5 分钟），请重新运行")


# ---------- 旧版：网页授权（office-raccoon:// 回调） ----------


def build_authorize_url(state):
    query = urllib.parse.urlencode({
        "login_source": "desktop",
        "appname": OAUTH_APP_NAME,
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
    headers = api_headers()
    headers["Content-Type"] = "application/json"
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


def web_login():
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
    callback = input("🔗 请粘贴完整回调地址: ").strip()
    code = parse_callback(callback, state)
    return exchange_code(code)


def verify(token):
    log("🔎 校验 token ...")
    try:
        response = request("GET", ORIGIN + SETTINGS_PATH, headers=api_headers(token))
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
    use_web = "--web" in args
    note = ""
    png_path = ""
    if "--note" in args:
        try:
            note = args[args.index("--note") + 1]
        except Exception:
            note = ""
    if "--png" in args:
        try:
            png_path = args[args.index("--png") + 1]
        except Exception:
            png_path = ""

    print("╔══════════════════════════════════════════╗")
    print("║ 🐻 小浣熊 登录工具（微信扫码）           ║")
    print("╚══════════════════════════════════════════╝")

    credentials = web_login() if use_web else qr_login(png_path)
    log("✅ 登录成功  token=%s" % mask(credentials["token"]))
    if do_verify:
        verify(credentials["token"])

    parts = [note or "小浣熊", credentials["token"]]
    if credentials.get("refresh_token"):
        parts.append(credentials["refresh_token"])
    env_line = "|".join(parts)
    print("\n" + "-" * 50)
    print("✅ 将下面这行追加到 RACCOON_TOKENS")
    print("-" * 50)
    print(env_line)
    print("-" * 50)
    if credentials.get("refresh_token"):
        print("💡 已带 refresh_token：脚本会自动续期（约 30 天滚动）")
    else:
        print("💡 上游本次未下发 refresh_token：access 约 2~3 小时有效，过期需重新登录")
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
