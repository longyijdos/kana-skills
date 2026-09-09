# chatgpt-browser-cli

实验性 CLI：从 macOS Edge 导入 ChatGPT Cookie，然后驱动系统自带的
Edge（无头模式）开启临时聊天、发送问题，并通过“复制回复”输出完整
Markdown。

CLI 默认继承 `HTTPS_PROXY` 或 `HTTP_PROXY`，并在每次启动时根据当前
系统 Edge 版本生成 User-Agent。剪贴板权限由 Playwright context 授予，
不需要修改 macOS 设置。

## 伪装（anti-detection）

驱动的是**系统真 Edge**（`channel="msedge"`），因此 UA 与
Client Hints（`Sec-CH-UA`）由真实内核上报、原生一致，不像 bundled
Chromium 那样存在“UA 伪造但底层穿帮”的矛盾。在此基础上叠加：

- `--disable-blink-features=AutomationControlled` + init script 屏蔽
  `navigator.webdriver`
- 根据当前 Edge 版本生成有头 UA，覆盖 headless Edge 自带的
  `HeadlessChrome` 标记
- 人类化行为层：读屏停顿、概率滚动、鼠标缓动轨迹、按输入法节奏分批
  输入（`--fast` 可切换为直接输入，适合长文本，但可能增加风控风险）

`chatgpt-cli check` 可检查 Cookie JSON 中的本地有效期，并自检当前指纹
（webdriver / UA / Client Hints / plugins 等），逐项 PASS/WARN/FAIL。
Cookie 检查只比较本地 `expires`，不验证服务端登录态。

## 使用

```bash
uv sync
uv run playwright install chromium   # 仅首次，提供 Playwright 驱动
uv run chatgpt-cli import-edge
uv run chatgpt-cli ask "只回复：测试成功"
uv run chatgpt-cli check
```

`.auth/chatgpt.json` 包含明文登录凭据，只应保存在本机，不能提交或分发。
