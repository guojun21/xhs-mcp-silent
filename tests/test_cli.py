from __future__ import annotations

import argparse
import io
import json

import pytest

from xhs_mcp_silent.cli import (
    build_help_text,
    build_parser,
    format_comments,
    format_note_detail,
    format_search_results,
    run_async,
)
from xhs_mcp_silent.models import CheckCookieResult, CommentItem, NoteDetail, NoteSummary, XhsSilentError


class FakeLauncher:
    def __init__(self) -> None:
        self.calls = []

    def open_homepage(self, url: str = "https://www.xiaohongshu.com/"):
        self.calls.append(url)

        class _Result:
            launched = True
            profile = "Profile 1"
            error = ""

            @staticmethod
            def to_dict():
                return {
                    "launched": True,
                    "profile": "Profile 1",
                    "url": url,
                    "command": ["chrome"],
                    "error": "",
                }

        return _Result()


class GuestApi:
    async def check_cookie(self):
        return CheckCookieResult(
            valid=False,
            source="chrome:Profile 1",
            profile="Profile 1",
            cookie_path="/tmp/Cookies",
            reason="guest",
            user_id="u1",
        )


def test_build_parser_defaults_to_profile_1() -> None:
    args = build_parser().parse_args(["check-cookie"])
    assert args.profile == "Profile 1"


def test_build_help_text_overview_mentions_workflow() -> None:
    text = build_help_text("overview")
    assert "Recommended workflow" in text
    assert "Profile 1" in text


class SearchApi:
    async def search_notes(self, keywords: str, limit: int = 10):
        return [
            NoteSummary(
                note_id="1",
                title=f"{keywords} 标题",
                author="作者",
                liked_count=10,
                collected_count=2,
                comment_count=3,
                xsec_token="token",
                url="https://www.xiaohongshu.com/explore/1?xsec_token=token",
            )
        ][:limit]


class ErrorApi:
    async def search_notes(self, keywords: str, limit: int = 10):
        raise XhsSilentError("COOKIE_EXPIRED", "need login")


def test_format_search_results() -> None:
    result = format_search_results(
        [
            NoteSummary(
                note_id="1",
                title="测试标题",
                author="测试作者",
                liked_count=10,
                collected_count=2,
                comment_count=3,
                xsec_token="token",
                url="https://www.xiaohongshu.com/explore/1?xsec_token=token",
            )
        ],
        "测试",
    )
    assert "测试标题" in result
    assert "测试作者" in result
    assert "https://www.xiaohongshu.com/explore/1?xsec_token=token" in result


def test_format_note_detail() -> None:
    result = format_note_detail(
        NoteDetail(
            note_id="1",
            title="详情标题",
            author="作者",
            published_at="2026-03-20 12:00:00",
            liked_count=11,
            collected_count=4,
            comment_count=5,
            content="正文内容",
            cover_url="https://img.example/cover.jpg",
            url="https://www.xiaohongshu.com/explore/1?xsec_token=token",
        )
    )
    assert "详情标题" in result
    assert "正文内容" in result
    assert "封面: https://img.example/cover.jpg" in result


def test_format_comments() -> None:
    result = format_comments(
        [
            CommentItem(
                user_name="评论者",
                content="不错",
                created_at="2026-03-20 12:01:00",
                liked_count=6,
            )
        ]
    )
    assert "评论者" in result
    assert "不错" in result


@pytest.mark.asyncio
async def test_check_cookie_opens_login_on_guest_session() -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()
    launcher = FakeLauncher()
    args = argparse.Namespace(
        command="check-cookie",
        json=False,
        profile="Default",
        chrome_dir=None,
        cookie=None,
    )
    code = await run_async(args, api=GuestApi(), launcher=launcher, stdout=stdout, stderr=stderr)
    assert code == 1
    assert launcher.calls == ["https://www.xiaohongshu.com/"]
    assert "guest Xiaohongshu session" in stderr.getvalue()


@pytest.mark.asyncio
async def test_search_json_output() -> None:
    stdout = io.StringIO()
    args = argparse.Namespace(
        command="search",
        keywords="深圳 咖啡",
        limit=1,
        json=True,
        profile="Default",
        chrome_dir=None,
        cookie=None,
    )
    code = await run_async(args, api=SearchApi(), launcher=FakeLauncher(), stdout=stdout, stderr=io.StringIO())
    assert code == 0
    payload = json.loads(stdout.getvalue())
    assert payload[0]["title"] == "深圳 咖啡 标题"


@pytest.mark.asyncio
async def test_search_cookie_error_opens_login() -> None:
    stderr = io.StringIO()
    launcher = FakeLauncher()
    args = argparse.Namespace(
        command="search",
        keywords="深圳 咖啡",
        limit=1,
        json=False,
        profile="Default",
        chrome_dir=None,
        cookie=None,
    )
    code = await run_async(args, api=ErrorApi(), launcher=launcher, stdout=io.StringIO(), stderr=stderr)
    assert code == 1
    assert launcher.calls == ["https://www.xiaohongshu.com/"]
    assert "COOKIE_EXPIRED" in stderr.getvalue()


@pytest.mark.asyncio
async def test_help_command_outputs_text_without_api() -> None:
    stdout = io.StringIO()
    args = argparse.Namespace(
        command="help",
        topic="search",
        json=False,
        profile="Profile 1",
        profile_email=None,
        chrome_dir=None,
        cookie=None,
    )
    code = await run_async(args, stdout=stdout, stderr=io.StringIO())
    assert code == 0
    assert "Search Xiaohongshu notes by keyword." in stdout.getvalue()
