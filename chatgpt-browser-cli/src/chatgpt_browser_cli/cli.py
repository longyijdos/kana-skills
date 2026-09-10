from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


DEFAULT_STATE = Path(".auth/chatgpt.json")
EDGE_DATA = Path.home() / "Library/Application Support/Microsoft Edge"
EDGE_EXECUTABLE = Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge")
CHROMIUM_EPOCH_OFFSET = 11_644_473_600


def proxy_from_environment() -> str | None:
    for name in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
        if value := os.environ.get(name):
            return value
    return None


def write_private_json(path: Path, value: object) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT, 0o600)
    try:
        os.fchmod(fd, 0o600)
        os.ftruncate(fd, 0)
        destination = os.fdopen(fd, "w")
        fd = -1
        with destination:
            json.dump(value, destination)
    finally:
        if fd != -1:
            os.close(fd)


def edge_user_agent() -> str:
    result = subprocess.run(
        [str(EDGE_EXECUTABLE), "--version"],
        check=True,
        capture_output=True,
        text=True,
    )
    match = re.search(r"\b(\d+)\.", result.stdout)
    if not match:
        raise RuntimeError("无法读取 Edge 主版本号")
    major = match.group(1)
    return (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        f"Chrome/{major}.0.0.0 Safari/537.36 Edg/{major}.0.0.0"
    )


def edge_profile_name(data_dir: Path) -> str:
    local_state = json.loads((data_dir / "Local State").read_text())
    return local_state.get("profile", {}).get("last_used", "Default")


def edge_cookie_db(data_dir: Path, profile: str) -> Path:
    profile_dir = data_dir / profile
    for relative in ("Network/Cookies", "Cookies"):
        candidate = profile_dir / relative
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"找不到 Edge Cookie 数据库：{profile_dir}")


def edge_safe_storage_password() -> bytes:
    result = subprocess.run(
        [
            "security",
            "find-generic-password",
            "-w",
            "-s",
            "Microsoft Edge Safe Storage",
        ],
        check=True,
        capture_output=True,
    )
    return result.stdout.rstrip(b"\n")


def decrypt_edge_cookie(encrypted: bytes, host: str, key: bytes) -> str:
    if not encrypted.startswith((b"v10", b"v11")):
        raise ValueError("不支持的 Edge Cookie 加密格式")

    decryptor = Cipher(algorithms.AES(key), modes.CBC(b" " * 16)).decryptor()
    padded = decryptor.update(encrypted[3:]) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    value = unpadder.update(padded) + unpadder.finalize()

    host_digest = hashlib.sha256(host.encode()).digest()
    if value.startswith(host_digest):
        value = value[len(host_digest) :]
    return value.decode()


def chromium_expiry(expires_utc: int, has_expires: int) -> float:
    if not has_expires or not expires_utc:
        return -1
    return expires_utc / 1_000_000 - CHROMIUM_EPOCH_OFFSET


def import_edge(args: argparse.Namespace) -> int:
    data_dir = Path(args.edge_data_dir).expanduser()
    profile = args.profile or edge_profile_name(data_dir)
    cookie_db = edge_cookie_db(data_dir, profile)
    password = edge_safe_storage_password()
    key = hashlib.pbkdf2_hmac(
        "sha1", password, b"saltysalt", iterations=1003, dklen=16
    )

    connection = sqlite3.connect(f"file:{cookie_db}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """
        SELECT host_key, name, value, encrypted_value, path, expires_utc,
               has_expires, is_secure, is_httponly, samesite
        FROM cookies
        WHERE host_key = 'chatgpt.com'
           OR host_key LIKE '%.chatgpt.com'
           OR host_key = 'openai.com'
           OR host_key LIKE '%.openai.com'
        """
    ).fetchall()
    connection.close()

    same_site = {-1: "Lax", 0: "None", 1: "Lax", 2: "Strict"}
    cookies = []
    for row in rows:
        if row["value"] != "":
            value = row["value"]
        elif row["encrypted_value"]:
            value = decrypt_edge_cookie(
                row["encrypted_value"], row["host_key"], key
            )
        else:
            value = ""
        cookies.append(
            {
                "name": row["name"],
                "value": value,
                "domain": row["host_key"],
                "path": row["path"],
                "expires": chromium_expiry(row["expires_utc"], row["has_expires"]),
                "httpOnly": bool(row["is_httponly"]),
                "secure": bool(row["is_secure"]),
                "sameSite": same_site.get(row["samesite"], "Lax"),
            }
        )

    if not cookies:
        raise RuntimeError(f"Edge profile {profile!r} 中没有 ChatGPT/OpenAI Cookie")

    state_path = Path(args.state).expanduser()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.parent.chmod(0o700)
    write_private_json(state_path, {"cookies": cookies, "origins": []})
    print(f"已从 Edge profile {profile!r} 导入 {len(cookies)} 个 Cookie：{state_path}")
    return 0


def _stealth_launch(playwright, state_path, proxy, user_agent=None, headed=False):
    """启动带伪装的无头 Edge 并创建与 ask 完全一致的 context。

    固定使用系统真 Edge：Client Hints（Sec-CH-UA）由真实内核上报；
    User-Agent 根据当前 Edge 版本生成，两者版本保持一致。
    """
    # 显式 --user-agent 永远优先；否则按当前 Edge 版本生成有头 UA，
    # 擦掉 headless Edge 自带的 HeadlessChrome 标记。
    effective_ua = user_agent or edge_user_agent()

    launch_options = {
        "headless": not headed,
        "channel": "msedge",
        # 伪装：禁用 Chromium 的 AutomationControlled 特性
        "args": ["--disable-blink-features=AutomationControlled"],
    }
    if proxy:
        launch_options["proxy"] = {"server": proxy}
    browser = playwright.chromium.launch(**launch_options)

    context_options = {"storage_state": str(state_path)}
    if effective_ua:
        context_options["user_agent"] = effective_ua
    context = browser.new_context(**context_options)
    # 伪装：屏蔽 navigator.webdriver 自动化标记（在页面脚本运行前注入）
    context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
    )
    context.grant_permissions(
        ["clipboard-read", "clipboard-write"],
        origin="https://chatgpt.com",
    )
    return browser, context


# ---------- 人类化行为层 ----------

def human_delay(min_ms=300, max_ms=900, idle_chance=0.08):
    """随机停顿；偶发一个 2~4s 的长停顿，模拟人走神/思考。"""
    if random.random() < idle_chance:
        time.sleep(random.uniform(2.0, 4.0))
    time.sleep(random.uniform(min_ms / 1000, max_ms / 1000))


def human_scroll(page, chance=0.5):
    """以一定概率模拟人类滚动浏览页面：分段滚动、方向有往复、带随机停留。"""
    if random.random() >= chance:
        return
    viewport_h = page.evaluate("window.innerHeight")
    # 1~3 段滚动，总距离不超过 1.5 个视口高，避免太规律
    segments = random.randint(1, 3)
    total = 0
    for _ in range(segments):
        delta = random.randint(300, int(viewport_h * 0.7))
        total += delta
        if total > viewport_h * 1.5:
            break
        page.mouse.wheel(0, delta)
        human_delay(200, 700)
    # 偶尔回滚一小段（人浏览时常往回看）
    if random.random() < 0.3 and total > 0:
        page.mouse.wheel(0, -random.randint(100, 400))
        human_delay(150, 500)


def human_move_mouse(page, target_x, target_y):
    """模拟人类鼠标轨迹移动到目标：分段、缓动、带随机抖动与误差递减。

    真实鼠标移动速度并不恒定，而是先快后慢、末段微调；这里把轨迹分成
    若干段，每段随机减速因子，让末段停留在一个有误差的邻域内再做最终
    定位——避免“一条直线精准命中”的机械特征。
    """
    start_x = random.randint(0, 800)
    start_y = random.randint(0, 400)
    page.mouse.move(start_x, start_y)
    human_delay(150, 500)
    steps = random.randint(5, 9)
    last_x, last_y = start_x, start_y
    for i in range(1, steps + 1):
        progress = i / steps
        eased = 1 - (1 - progress) ** 2  # ease-out：先快后慢
        # 误差随进度递减，模拟末段精调
        jitter = max(2, int((1 - progress) * random.uniform(10, 40)))
        cur_x = start_x + (target_x - start_x) * eased + random.uniform(-jitter, jitter)
        cur_y = start_y + (target_y - start_y) * eased + random.uniform(-jitter, jitter)
        page.mouse.move(cur_x, cur_y)
        last_x, last_y = cur_x, cur_y
        human_delay(20, 120)
    # 末段最终定位：从带误差的邻域精确移动到目标
    page.mouse.move(last_x + random.uniform(-5, 5), last_y + random.uniform(-5, 5))
    human_delay(80, 200)
    page.mouse.move(target_x, target_y)
    human_delay(150, 400)


def human_type(page, element, text):
    """模拟真实键盘输入：分批、块间随机停顿和偶发短暂停顿。

    真实用户（尤其中文输入法与熟练打字者）通过拼音选词成批上屏，按键连贯；
    这里按标点或长度分块，保持短促的输入节奏与自然的块间微停顿。
    长文本偶发一次轻微的思维停顿。
    """
    element.click()
    human_delay(150, 400)
    # 先按标点/换行切成“词块”，太长的按 12~24 字切，模拟输入法成词/成句上屏
    chunks = []
    for part in re.split(r"([，。！？；、,.!?;:\n])", text):
        if not part:
            continue
        if len(part) > 24:
            start = 0
            while start < len(part):
                size = random.randint(12, 24)
                chunks.append(part[start : start + size])
                start += size
        else:
            chunks.append(part)
    for i, chunk in enumerate(chunks):
        if chunk in "，。！？；、,.!?;:\n":
            # 标点符号：输入法通常随词块快速跟上
            element.type(chunk, delay=random.randint(15, 45))
            human_delay(60, 180)
            continue
        # 词块主体：熟练击键节奏（20~60ms）
        for ch in chunk:
            element.type(ch, delay=random.randint(20, 60))
        # 词块结束：自然选词/键入缓冲（50~200ms）
        human_delay(50, 200)
        # 长文本偶发轻微短暂停顿
        if len(text) > 120 and random.random() < 0.08:
            time.sleep(random.uniform(0.8, 1.8))
    # 输完稍作停顿再回车
    human_delay(300, 800)


FINGERPRINT_SCRIPT = """
() => {
  const uaData = navigator.userAgentData;
  return {
    webdriver: navigator.webdriver,
    userAgent: navigator.userAgent,
    brands: uaData ? uaData.brands.map(b => b.brand + ' ' + b.version) : null,
    uaPlatform: uaData ? uaData.platform : null,
    hasChrome: !!window.chrome,
    plugins: navigator.plugins.length,
    languages: navigator.languages,
    hardwareConcurrency: navigator.hardwareConcurrency,
  };
}
"""


def check(args: argparse.Namespace) -> int:
    """自检：输出 Cookie 本地有效期和当前浏览器指纹。"""
    state_path = Path(args.state).expanduser()
    if not state_path.is_file():
        raise FileNotFoundError(f"登录态不存在，请先运行 import-edge：{state_path}")
    cookies = json.loads(state_path.read_text()).get("cookies", [])

    with sync_playwright() as playwright:
        browser, context = _stealth_launch(
            playwright,
            state_path,
            args.proxy or proxy_from_environment(),
            args.user_agent,
        )
        page = context.new_page()
        page.goto("https://chatgpt.com/?temporary-chat=true", wait_until="domcontentloaded")
        fp = page.evaluate(FINGERPRINT_SCRIPT)
        browser.close()

    results = []

    def verdict(name, ok, detail):
        mark = "PASS" if ok is True else ("FAIL" if ok is False else "WARN")
        results.append((mark, name, detail))

    now = time.time()
    session_cookies = [cookie for cookie in cookies if cookie.get("expires", -1) == -1]
    expired_cookies = [
        cookie
        for cookie in cookies
        if cookie.get("expires", -1) != -1 and cookie["expires"] <= now
    ]
    active_expiries = [
        cookie["expires"]
        for cookie in cookies
        if cookie.get("expires", -1) > now
    ]
    if not cookies:
        cookie_ok = False
        cookie_detail = "状态文件中没有 Cookie"
    else:
        if len(expired_cookies) == len(cookies):
            cookie_ok = False
        elif expired_cookies:
            cookie_ok = None
        else:
            cookie_ok = True
        cookie_detail = (
            f"{len(active_expiries)} 个未过期，{len(session_cookies)} 个会话 Cookie，"
            f"{len(expired_cookies)} 个已过期"
        )
        if active_expiries:
            nearest_expiry = time.strftime(
                "%Y-%m-%d %H:%M:%S %Z", time.localtime(min(active_expiries))
            )
            cookie_detail += f"；最近到期：{nearest_expiry}"
        cookie_detail += "；仅检查 expires，不代表服务端登录态有效"
    verdict("Cookie 本地有效期", cookie_ok, cookie_detail)

    webdriver_clean = fp["webdriver"] in (None, False, "undefined")
    verdict(
        "navigator.webdriver",
        webdriver_clean,
        f"值为 {fp['webdriver']!r}，期望 undefined/false",
    )

    ua = fp["userAgent"]
    verdict(
        "User-Agent",
        "Headless" not in ua,
        ua,
    )
    brands = fp["brands"] or []
    brand_text = ", ".join(brands) if brands else "(无 userAgentData)"
    if any("HeadlessChrome" in b for b in brands):
        verdict("Client Hints brands", False, f"暴露 HeadlessChrome：{brand_text}")
    elif any(b.startswith("Edg") or b.startswith("Microsoft Edge") for b in brands):
        verdict("Client Hints brands", True, f"与 Edge UA 一致：{brand_text}")
    else:
        verdict("Client Hints brands", False, f"非 Edge brand，与 UA 不一致：{brand_text}")

    platform = fp["uaPlatform"] or "(无)"
    verdict("Client Hints platform", platform.startswith("mac"), platform)

    verdict("window.chrome", fp["hasChrome"], "存在（真实 Chromium 特征）" if fp["hasChrome"] else "缺失（可疑）")
    verdict("navigator.plugins", fp["plugins"] > 0, f"{fp['plugins']} 个插件（真实 Chrome 通常 >0）")
    verdict("navigator.languages", bool(fp["languages"]), ", ".join(fp["languages"]))
    verdict("hardwareConcurrency", fp["hardwareConcurrency"] > 1, str(fp["hardwareConcurrency"]))

    print("ChatGPT 浏览器伪装自检")
    print("=" * 60)
    for mark, name, detail in results:
        print(f"[{mark:4}] {name}")
        print(f"        {detail}")
    fails = sum(1 for mark, _, _ in results if mark == "FAIL")
    warns = sum(1 for mark, _, _ in results if mark == "WARN")
    print("=" * 60)
    print(f"结果：{len(results) - fails - warns} PASS / {warns} WARN / {fails} FAIL")
    return 1 if fails else 0


def ask(args: argparse.Namespace) -> int:
    state_path = Path(args.state).expanduser()
    if not state_path.is_file():
        raise FileNotFoundError(f"登录态不存在，请先运行 import-edge：{state_path}")

    timeout_ms = int(args.timeout * 1000)
    with sync_playwright() as playwright:
        browser, context = _stealth_launch(
            playwright,
            state_path,
            args.proxy or proxy_from_environment(),
            args.user_agent,
            headed=args.headed,
        )
        page = context.new_page()
        page.set_default_timeout(timeout_ms)
        page.goto(
            "https://chatgpt.com/?temporary-chat=true",
            wait_until="domcontentloaded",
        )

        prompt = page.locator("#prompt-textarea")
        try:
            prompt.wait_for(state="visible")
        except PlaywrightTimeoutError as error:
            raise RuntimeError(
                f"没有进入已登录的 ChatGPT 页面，当前地址：{page.url}"
            ) from error

        answers = page.locator('[data-message-author-role="assistant"]')
        previous_count = answers.count()
        if args.fast or args.bot:
            prompt.fill(args.question)
        else:
            # 人类化：读屏停顿 → 偶发滚动 → 移动鼠标 → 分批输入 → 审视后回车
            human_delay(1500, 3500)
            human_scroll(page, chance=0.6)
            box = prompt.bounding_box()
            if box:
                human_move_mouse(page, box["x"] + box["width"] * random.uniform(0.4, 0.8),
                                 box["y"] + box["height"] / 2)
            human_type(page, prompt, args.question)
            human_delay(400, 1000)
        prompt.press("Enter")

        page.wait_for_function(
            "count => document.querySelectorAll('[data-message-author-role=\"assistant\"]').length > count",
            arg=previous_count,
        )
        answer_turn = page.locator('section[data-turn="assistant"]').last
        stop = page.locator('[data-testid="stop-button"]')
        try:
            stop.wait_for(state="visible", timeout=5000)
        except PlaywrightTimeoutError:
            pass
        else:
            stop.wait_for(state="hidden")
        answer_turn.hover()
        copy_button = answer_turn.locator(
            'button[data-testid="copy-turn-action-button"]'
        )
        copy_button.wait_for(state="visible")
        copy_button.click()
        answer = page.evaluate("navigator.clipboard.readText()").strip()
        browser.close()

    if not answer:
        raise RuntimeError("ChatGPT 返回了空回答")
    print(answer)
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="chatgpt-cli", description="通过无头 Edge 调用 ChatGPT 网页"
    )
    commands = root.add_subparsers(dest="command", required=True)

    edge = commands.add_parser("import-edge", help="从 macOS Edge 导入登录态")
    edge.add_argument("--profile", help="Edge profile 目录名，默认读取最近使用项")
    edge.add_argument("--edge-data-dir", default=str(EDGE_DATA))
    edge.add_argument("--state", default=str(DEFAULT_STATE))
    edge.set_defaults(handler=import_edge)

    query = commands.add_parser("ask", help="在临时聊天中提问并输出回答")
    query.add_argument("question")
    query.add_argument("--state", default=str(DEFAULT_STATE))
    query.add_argument("--timeout", type=float, default=300)
    query.add_argument("--proxy", help="代理地址；默认读取 HTTPS_PROXY/HTTP_PROXY")
    query.add_argument("--user-agent", help="覆盖 User-Agent（默认根据当前 Edge 版本生成）")
    query.add_argument("--headed", action="store_true", help="调试时显示浏览器窗口")
    query.add_argument(
        "--fast",
        action="store_true",
        help="快速输入模式：关闭拟人击键（直接 fill 输入框），适合长文本或调试，但可能略微增加风控风险",
    )
    query.add_argument(
        "--bot",
        action="store_true",
        help=argparse.SUPPRESS,  # 兼容旧参数，作为 hidden alias
    )
    query.set_defaults(handler=ask)

    inspect = commands.add_parser("check", help="检查 Cookie 有效期和浏览器指纹")
    inspect.add_argument("--state", default=str(DEFAULT_STATE))
    inspect.add_argument("--proxy", help="代理地址；默认读取 HTTPS_PROXY/HTTP_PROXY")
    inspect.add_argument("--user-agent", help="覆盖 User-Agent（默认根据当前 Edge 版本生成）")
    inspect.set_defaults(handler=check)
    return root


def main() -> None:
    args = parser().parse_args()
    try:
        raise SystemExit(args.handler(args))
    except (FileNotFoundError, RuntimeError, subprocess.CalledProcessError, ValueError) as error:
        print(f"错误：{error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
