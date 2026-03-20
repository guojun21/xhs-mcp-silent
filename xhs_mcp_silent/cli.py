from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from dataclasses import asdict, is_dataclass
from typing import Any, TextIO

from .browser import ChromeLoginLauncher
from .cookie_resolver import ChromeCookieResolver, DEFAULT_PROFILE
from .models import CommentItem, NoteDetail, NoteSummary, XhsSilentError
from .profile_resolver import ChromeProfileResolver
from .xhs_api import XhsApi

logger = logging.getLogger(__name__)

HELP_TOPICS = {
    "overview": {
        "summary": "What this CLI does and the recommended workflow.",
        "body": [
            "xhs-silent is a local Xiaohongshu CLI for macOS.",
            "It reuses Chrome cookies, signs requests with x-s/x-t, and never starts Playwright or Chromium automation.",
            "",
            "Recommended workflow:",
            "1. xhs-silent check-cookie",
            "2. xhs-silent search \"关键词\" --limit 5",
            "3. xhs-silent note \"<搜索结果里的完整 URL>\"",
            "4. xhs-silent comments \"<搜索结果里的完整 URL>\" --limit 5",
            "",
            f"Default Chrome profile: {DEFAULT_PROFILE}",
        ],
    },
    "check-cookie": {
        "summary": "Verify whether the current Chrome profile can access Xiaohongshu.",
        "body": [
            "Use this before search if you are unsure about login state.",
            "If the cookie is missing, expired, or only a guest session, the CLI will try to open Xiaohongshu in Chrome for login.",
            "",
            "Example:",
            "xhs-silent check-cookie",
            "xhs-silent --json check-cookie",
        ],
    },
    "login": {
        "summary": "Open Xiaohongshu homepage in the configured Chrome profile.",
        "body": [
            "Use this to force open the login page in the active Chrome profile.",
            "The command explicitly passes --user-data-dir and --profile-directory so the correct profile is used.",
            "",
            "Example:",
            "xhs-silent login",
            "xhs-silent login --url https://www.xiaohongshu.com/explore",
        ],
    },
    "search": {
        "summary": "Search Xiaohongshu notes by keyword.",
        "body": [
            "This is the broad-recall command.",
            "Search results include full note URLs with xsec_token. Feed those URLs into note/comments.",
            "",
            "Example:",
            "xhs-silent search \"深圳 咖啡\" --limit 5",
            "xhs-silent --json search \"深圳 约会 餐厅\" --limit 10",
        ],
    },
    "note": {
        "summary": "Fetch note content and metadata from a Xiaohongshu note URL.",
        "body": [
            "Use the full URL returned by search. The URL must include xsec_token.",
            "",
            "Example:",
            "xhs-silent note \"https://www.xiaohongshu.com/explore/...?...\"",
            "xhs-silent --json note \"https://www.xiaohongshu.com/explore/...?...\"",
        ],
    },
    "comments": {
        "summary": "Fetch first-level comments from a Xiaohongshu note URL.",
        "body": [
            "Use this when queue, service quality, or consumer sentiment matters.",
            "",
            "Example:",
            "xhs-silent comments \"https://www.xiaohongshu.com/explore/...?...\" --limit 5",
            "xhs-silent --json comments \"https://www.xiaohongshu.com/explore/...?...\" --limit 10",
        ],
    },
    "profiles": {
        "summary": "Explain how profile selection works.",
        "body": [
            f"Default profile: {DEFAULT_PROFILE}",
            "Override by profile directory:",
            "xhs-silent --profile \"Profile 2\" check-cookie",
            "",
            "Resolve by Google account email:",
            "xhs-silent --profile-email \"oasismetallicablur@gmail.com\" check-cookie",
        ],
    },
    "json": {
        "summary": "Explain JSON output mode.",
        "body": [
            "Add --json to any command to get structured output that is easier for scripts and agents to parse.",
            "",
            "Example:",
            "xhs-silent --json search \"深圳 咖啡\" --limit 3",
        ],
    },
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="xhs-silent",
        description="Silent Xiaohongshu CLI that reuses the local Chrome profile on macOS.",
    )
    parser.add_argument("--profile", default=DEFAULT_PROFILE, help=f"Chrome profile directory name. Default: {DEFAULT_PROFILE}.")
    parser.add_argument("--profile-email", help="Resolve a Chrome profile by the signed-in Google account email.")
    parser.add_argument("--chrome-dir", help="Override Chrome user data dir.")
    parser.add_argument("--cookie", help="Emergency cookie override, equivalent to XHS_COOKIE.")
    parser.add_argument("--json", action="store_true", help="Print structured JSON output.")

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check-cookie", help="Check whether the current Chrome profile can access Xiaohongshu.")
    help_parser = subparsers.add_parser("help", help="Show command-specific help.")
    help_parser.add_argument(
        "topic",
        nargs="?",
        default="overview",
        choices=sorted(HELP_TOPICS.keys()),
        help="Help topic to show.",
    )

    login_parser = subparsers.add_parser("login", help=f"Open Xiaohongshu homepage in Chrome {DEFAULT_PROFILE} profile.")
    login_parser.add_argument("--url", default="https://www.xiaohongshu.com/", help="URL to open for login.")

    search_parser = subparsers.add_parser("search", help="Search Xiaohongshu notes by keyword.")
    search_parser.add_argument("keywords", help="Search keywords.")
    search_parser.add_argument("--limit", type=int, default=10, help="Maximum number of results. Default: 10.")

    note_parser = subparsers.add_parser("note", help="Get note detail from a Xiaohongshu note URL.")
    note_parser.add_argument("url", help="Note URL with xsec_token.")

    comments_parser = subparsers.add_parser("comments", help="Get first-level comments from a Xiaohongshu note URL.")
    comments_parser.add_argument("url", help="Note URL with xsec_token.")
    comments_parser.add_argument("--limit", type=int, default=10, help="Maximum number of comments. Default: 10.")
    return parser


def resolve_profile_name(args: argparse.Namespace) -> str:
    resolver = ChromeProfileResolver(chrome_dir=args.chrome_dir)
    if getattr(args, "profile_email", None):
        return resolver.resolve_profile(args.profile_email)
    return resolver.resolve_profile(args.profile)


def build_api(args: argparse.Namespace) -> XhsApi:
    env = dict(os.environ)
    if args.cookie:
        env["XHS_COOKIE"] = args.cookie
    profile = resolve_profile_name(args)
    resolver = ChromeCookieResolver(
        chrome_dir=args.chrome_dir,
        profile=profile,
        env=env,
    )
    return XhsApi(resolver=resolver)


def build_login_launcher(args: argparse.Namespace) -> ChromeLoginLauncher:
    return ChromeLoginLauncher(profile=resolve_profile_name(args), chrome_dir=args.chrome_dir)


def print_payload(payload: Any, *, as_json: bool, stdout: TextIO) -> None:
    if as_json:
        print(json.dumps(to_jsonable(payload), ensure_ascii=False, indent=2), file=stdout)
        return
    print(payload, file=stdout)


def to_jsonable(payload: Any) -> Any:
    if hasattr(payload, "to_dict"):
        return payload.to_dict()
    if is_dataclass(payload):
        return asdict(payload)
    if isinstance(payload, list):
        return [to_jsonable(item) for item in payload]
    if isinstance(payload, dict):
        return {key: to_jsonable(value) for key, value in payload.items()}
    return payload


def format_search_results(items: list[NoteSummary], keywords: str) -> str:
    if not items:
        return f"未找到与“{keywords}”相关的笔记。"
    lines = [f"搜索结果（{len(items)} 条）：", ""]
    for index, item in enumerate(items, start=1):
        lines.extend(
            [
                f"{index}. {item.title or '(无标题)'}",
                f"作者: {item.author or '(未知)'}",
                f"点赞: {item.liked_count}  收藏: {item.collected_count}  评论: {item.comment_count}",
                f"链接: {item.url}",
                "",
            ]
        )
    return "\n".join(lines).strip()


def format_note_detail(item: NoteDetail) -> str:
    parts = [
        f"标题: {item.title or '(无标题)'}",
        f"作者: {item.author or '(未知)'}",
        f"发布时间: {item.published_at or '(未知)'}",
        f"点赞数: {item.liked_count}",
        f"评论数: {item.comment_count}",
        f"收藏数: {item.collected_count}",
        f"链接: {item.url}",
        "",
        "内容:",
        item.content or "(无正文)",
    ]
    if item.cover_url:
        parts.extend(["", f"封面: {item.cover_url}"])
    return "\n".join(parts)


def format_comments(items: list[CommentItem]) -> str:
    if not items:
        return "暂无评论。"
    lines = [f"评论（{len(items)} 条）：", ""]
    for index, item in enumerate(items, start=1):
        lines.extend(
            [
                f"{index}. {item.user_name or '(未知用户)'}（{item.created_at or '未知时间'}）",
                item.content or "(空评论)",
                f"点赞: {item.liked_count}",
                "",
            ]
        )
    return "\n".join(lines).strip()


def build_help_text(topic: str) -> str:
    entry = HELP_TOPICS[topic]
    lines = [f"Topic: {topic}", f"Summary: {entry['summary']}", ""]
    lines.extend(entry["body"])
    if topic == "overview":
        lines.extend(["", "Available topics:", ", ".join(sorted(HELP_TOPICS.keys()))])
    return "\n".join(lines).strip()


def _append_login_hint(
    message: str,
    *,
    launcher: ChromeLoginLauncher,
    as_json: bool,
    stderr: TextIO,
) -> None:
    result = launcher.open_homepage()
    if as_json:
        payload = {
            "login_prompt": {
                "message": message,
                "browser": result.to_dict(),
            }
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=stderr)
        return

    lines = [message]
    if result.launched:
        lines.append(
            f"已尝试打开 Chrome profile `{result.profile}` 的小红书首页。请先完成登录，再重新执行命令。"
        )
    else:
        lines.append(
            f"自动打开 Chrome 失败：{result.error or 'unknown error'}。请手动打开小红书网页版并在 profile `{result.profile}` 中登录。"
        )
    print("\n".join(lines), file=stderr)


def _handle_error(
    exc: XhsSilentError,
    *,
    launcher: ChromeLoginLauncher,
    as_json: bool,
    stderr: TextIO,
) -> int:
    if exc.code in {"COOKIE_MISSING", "COOKIE_EXPIRED"}:
        _append_login_hint(
            f"{exc.code}: {exc.message}",
            launcher=launcher,
            as_json=as_json,
            stderr=stderr,
        )
        return 1

    if as_json:
        print(json.dumps(exc.to_dict(), ensure_ascii=False, indent=2), file=stderr)
    else:
        print(f"{exc.code}: {exc.message}", file=stderr)
    return 1


async def run_async(
    args: argparse.Namespace,
    *,
    api: XhsApi | None = None,
    launcher: ChromeLoginLauncher | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr

    try:
        if args.command == "help":
            text = build_help_text(args.topic)
            print_payload({"topic": args.topic, "help": text} if args.json else text, as_json=args.json, stdout=stdout)
            return 0

        api = api or build_api(args)
        launcher = launcher or build_login_launcher(args)

        if args.command == "login":
            result = launcher.open_homepage(url=args.url)
            payload = result.to_dict()
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2), file=stdout)
            elif result.launched:
                print(
                    f"已打开 Chrome profile `{result.profile}` 的小红书首页，请登录后再执行其他命令。",
                    file=stdout,
                )
            else:
                print(
                    f"打开 Chrome 失败：{result.error or 'unknown error'}",
                    file=stderr,
                )
                return 1
            return 0

        if args.command == "check-cookie":
            result = await api.check_cookie()
            if result.valid:
                print_payload(result, as_json=args.json, stdout=stdout)
                return 0
            message = "COOKIE_EXPIRED: Chrome profile is not logged in to Xiaohongshu."
            if result.reason == "guest":
                message = "COOKIE_EXPIRED: Chrome profile contains a guest Xiaohongshu session, not a logged-in account."
            _append_login_hint(message, launcher=launcher, as_json=args.json, stderr=stderr)
            return 1

        if args.command == "search":
            items = await api.search_notes(args.keywords, limit=args.limit)
            print_payload(
                items if args.json else format_search_results(items, args.keywords),
                as_json=args.json,
                stdout=stdout,
            )
            return 0

        if args.command == "note":
            detail = await api.get_note_content(args.url)
            print_payload(detail if args.json else format_note_detail(detail), as_json=args.json, stdout=stdout)
            return 0

        if args.command == "comments":
            comments = await api.get_note_comments(args.url, limit=args.limit)
            print_payload(comments if args.json else format_comments(comments), as_json=args.json, stdout=stdout)
            return 0
    except XhsSilentError as exc:
        logger.exception("xhs-silent command failed")
        return _handle_error(exc, launcher=launcher, as_json=args.json, stderr=stderr)

    print(f"Unknown command: {args.command}", file=stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    args = build_parser().parse_args(argv)
    return asyncio.run(run_async(args))
