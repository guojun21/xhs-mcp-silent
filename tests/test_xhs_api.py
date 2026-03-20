from __future__ import annotations

import pytest

from xhs_mcp_silent.models import NoteDetail
from xhs_mcp_silent.xhs_api import XhsApi


class FakeApi(XhsApi):
    def __init__(self) -> None:
        pass

    async def _request_json(self, uri: str, **kwargs):  # type: ignore[override]
        if uri == "/api/sns/web/v1/search/notes":
            return {
                "success": True,
                "data": {
                    "items": [
                        {
                            "id": "123",
                            "xsec_token": "token",
                            "note_card": {
                                "display_title": "搜索标题",
                                "user": {"nickname": "作者"},
                                "interact_info": {
                                    "liked_count": 9,
                                    "collected_count": 4,
                                    "comment_count": 2,
                                },
                            },
                        }
                    ]
                },
            }
        if uri == "/api/sns/web/v1/feed":
            return {
                "success": True,
                "data": {
                    "items": [
                        {
                            "note_card": {
                                "title": "详情标题",
                                "desc": "正文",
                                "time": 1710900000000,
                                "user": {"nickname": "作者"},
                                "interact_info": {
                                    "liked_count": 1,
                                    "collected_count": 2,
                                    "comment_count": 3,
                                },
                                "image_list": [{"url_pre": "https://img"}],
                            }
                        }
                    ]
                },
            }
        if uri == "/api/sns/web/v2/comment/page":
            return {
                "success": True,
                "data": {
                    "comments": [
                        {
                            "user_info": {"nickname": "用户A"},
                            "content": "评论A",
                            "create_time": 1710900000000,
                            "like_count": 7,
                        },
                        {
                            "user_info": {"nickname": "用户B"},
                            "content": "评论B",
                            "create_time": 1710900001000,
                            "like_count": 1,
                        },
                    ]
                },
            }
        if uri == "/api/sns/web/v2/user/me":
            return {"success": True}
        raise AssertionError(f"unexpected uri: {uri}")

    async def check_cookie(self):  # type: ignore[override]
        from xhs_mcp_silent.models import CheckCookieResult

        return CheckCookieResult(valid=True, source="test", profile="Default", cookie_path="/tmp/Cookies")


@pytest.mark.asyncio
async def test_search_notes_parsing() -> None:
    api = FakeApi()
    items = await api.search_notes("测试", limit=5)
    assert len(items) == 1
    assert items[0].title == "搜索标题"


@pytest.mark.asyncio
async def test_get_note_content_parsing() -> None:
    api = FakeApi()
    detail = await api.get_note_content("https://www.xiaohongshu.com/explore/123?xsec_token=token")
    assert isinstance(detail, NoteDetail)
    assert detail.title == "详情标题"
    assert detail.content == "正文"


@pytest.mark.asyncio
async def test_get_note_comments_limit() -> None:
    api = FakeApi()
    comments = await api.get_note_comments("https://www.xiaohongshu.com/explore/123?xsec_token=token", limit=1)
    assert len(comments) == 1
    assert comments[0].user_name == "用户A"


class GuestCheckApi(XhsApi):
    def __init__(self) -> None:
        pass

    async def _request_json(self, uri: str, **kwargs):  # type: ignore[override]
        assert uri == "/api/sns/web/v2/user/me"
        return {"success": True, "data": {"user_id": "u1", "guest": True}}

    @property
    def resolver(self):  # type: ignore[override]
        class _Resolver:
            @staticmethod
            def resolve():
                from xhs_mcp_silent.models import CookieBundle

                return CookieBundle(
                    cookies={"a1": "v"},
                    source="test",
                    profile="Default",
                    cookie_path="/tmp/Cookies",
                )

        return _Resolver()


@pytest.mark.asyncio
async def test_check_cookie_marks_guest_session_invalid() -> None:
    api = GuestCheckApi()
    result = await api.check_cookie()
    assert result.valid is False
    assert result.reason == "guest"
    assert result.user_id == "u1"
