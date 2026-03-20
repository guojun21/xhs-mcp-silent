# xhs-mcp-silent

静默版小红书 CLI。它不会执行 Playwright/Chromium 自动化，而是直接复用 macOS Chrome 本地 profile 里的登录态。

## 能力

- `check-cookie`
- `search`
- `note`
- `comments`
- `login`
- `help`

V1 只做只读能力，不支持评论发布和发帖。CLI 在检测到 `guest/未登录` 时，会自动尝试打开 Chrome `Profile 1` 的小红书首页，提示先登录。

## 原理

1. 默认从 `~/Library/Application Support/Google/Chrome/Profile 1/Cookies` 读取小红书 cookies
2. 通过 `security find-generic-password -s "Chrome Safe Storage" -w` 获取 Chrome Safe Storage 密钥
3. 解密 cookies
4. 走小红书 Web 直连 HTTP 接口
5. 用内置 `xhsvm.js` 生成 `x-s/x-t`

`check_cookie` 会把 `guest` 会话判为无效，这种情况通常表示 Chrome 里还没真正登录网页版小红书。

## 运行要求

- macOS
- Chrome 已登录网页版小红书
- Python 3.10+
- Node.js 可执行文件在 PATH 中，用于运行 `PyExecJS`

## 快速开始

```bash
git clone https://github.com/guojun21/xhs-mcp-silent.git
cd xhs-mcp-silent
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e .
xhs-silent check-cookie
```

当前仓库默认 profile 是 `Profile 1`，也就是 `oasismetallicablur@gmail.com` 对应的 Chrome 目录。

也可以覆盖默认 profile：

```bash
xhs-silent --profile "Profile 1" check-cookie
```

也可以直接按邮箱选 profile：

```bash
xhs-silent --profile-email "oasismetallicablur@gmail.com" check-cookie
```

紧急调试时允许直接传 cookie：

```bash
xhs-silent --cookie "a1=...; webId=..." check-cookie
```

搜索与抓取：

```bash
xhs-silent search "深圳 咖啡" --limit 5
xhs-silent note "https://www.xiaohongshu.com/explore/xxxx?xsec_token=yyyy"
xhs-silent comments "https://www.xiaohongshu.com/explore/xxxx?xsec_token=yyyy" --limit 5
```

手动打开登录页：

```bash
xhs-silent login
```

结构化输出：

```bash
xhs-silent --json search "深圳 咖啡" --limit 3
```

## CLI 帮助

先看总览：

```bash
xhs-silent help
```

按主题查看：

```bash
xhs-silent help check-cookie
xhs-silent help search
xhs-silent help note
xhs-silent help comments
xhs-silent help profiles
xhs-silent help json
```

## 命令说明

### `check-cookie`

检查当前 profile 的小红书登录态。若 cookie 缺失、过期，或只是 guest session，会自动尝试打开正确的 Chrome profile 并跳到小红书首页。

```bash
xhs-silent check-cookie
xhs-silent --json check-cookie
```

### `login`

强制打开小红书首页到当前 profile。命令会显式传入 `--user-data-dir` 和 `--profile-directory`，避免 macOS 打开到错误 profile。

```bash
xhs-silent login
xhs-silent login --url https://www.xiaohongshu.com/explore
```

### `search`

按关键词搜索笔记。输出里的链接自带 `xsec_token`，后续拿这个完整 URL 去跑 `note` 和 `comments`。

```bash
xhs-silent search "深圳 咖啡" --limit 5
xhs-silent --json search "深圳 约会 餐厅" --limit 10
```

### `note`

抓取笔记正文和元信息。

```bash
xhs-silent note "https://www.xiaohongshu.com/explore/xxxx?xsec_token=yyyy"
xhs-silent --json note "https://www.xiaohongshu.com/explore/xxxx?xsec_token=yyyy"
```

### `comments`

抓取一级评论，适合判断排队、服务、踩雷、值不值得。

```bash
xhs-silent comments "https://www.xiaohongshu.com/explore/xxxx?xsec_token=yyyy" --limit 5
xhs-silent --json comments "https://www.xiaohongshu.com/explore/xxxx?xsec_token=yyyy" --limit 10
```

## 典型工作流

```bash
xhs-silent check-cookie
xhs-silent --json search "深圳 咖啡" --limit 5
xhs-silent --json note "<搜索结果里的完整 URL>"
xhs-silent --json comments "<搜索结果里的完整 URL>" --limit 5
```

## 环境变量

- `XHS_CHROME_DIR`: 覆盖 Chrome 用户目录
- `XHS_CHROME_BIN`: 覆盖 Chrome 可执行文件路径
- `XHS_COOKIE`: 紧急调试时直接传 cookie

## 退出码

- `0`: 成功
- `1`: 登录态问题或 Xiaohongshu 请求失败
- `2`: CLI 用法错误

## 默认 Profile

当前默认 profile 是 `Profile 1`，对应 `oasismetallicablur@gmail.com`。如果需要临时切换：

```bash
xhs-silent --profile "Profile 2" check-cookie
xhs-silent --profile-email "oasismetallicablur@gmail.com" check-cookie
```

## 测试

```bash
cd xhs-mcp-silent
source .venv/bin/activate
pytest
```
