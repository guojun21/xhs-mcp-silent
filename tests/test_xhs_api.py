from __future__ import annotations

import pytest

from xhs_mcp_silent.models import CommentPage, NoteDetail
from xhs_mcp_silent.xhs_api import SEARCH_DEFAULT_FILTERS, XhsApi


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
                                "last_update_time": 1710900001000,
                                "type": "normal",
                                "user": {"nickname": "作者"},
                                "interact_info": {
                                    "liked_count": 1,
                                    "collected_count": 2,
                                    "comment_count": 3,
                                    "shared_count": 4,
                                    "liked": True,
                                    "collected": False,
                                },
                                "image_list": [{"url_pre": "https://img"}],
                                "tag_list": [{"name": "标签"}],
                                "share_info": {"un_share": False},
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
                            "id": "c1",
                            "note_id": "123",
                            "user_info": {"nickname": "用户A"},
                            "content": "评论A",
                            "create_time": 1710900000000,
                            "like_count": 7,
                            "liked": True,
                            "status": 0,
                            "show_tags": ["热评"],
                            "at_users": [],
                            "sub_comment_count": 1,
                            "sub_comment_cursor": "cursor-1",
                            "sub_comment_has_more": False,
                            "sub_comments": [
                                {
                                    "id": "sc1",
                                    "content": "子评论A",
                                    "create_time": 1710900002000,
                                    "like_count": 1,
                                    "user_info": {"nickname": "回复者"},
                                }
                            ],
                        },
                        {
                            "id": "c2",
                            "note_id": "123",
                            "user_info": {"nickname": "用户B"},
                            "content": "评论B",
                            "create_time": 1710900001000,
                            "like_count": 1,
                            "liked": False,
                            "status": 0,
                            "show_tags": [],
                            "at_users": [],
                            "sub_comment_count": 0,
                            "sub_comment_cursor": "",
                            "sub_comment_has_more": False,
                            "sub_comments": [],
                        },
                    ],
                    "cursor": "next-cursor",
                    "has_more": True,
                    "time": 1710900003000,
                    "user_id": "user-1",
                    "xsec_token": "page-token",
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


class SearchPayloadApi(XhsApi):
    def __init__(self) -> None:
        self.calls = []

    async def _request_json(self, uri: str, **kwargs):  # type: ignore[override]
        self.calls.append((uri, kwargs))
        if uri == "/api/sns/web/v1/search/notes":
            page = kwargs["data"]["page"]
            if page == 1:
                return {
                    "success": True,
                    "data": {
                        "has_more": True,
                        "items": [
                            {
                                "id": "123",
                                "modelType": "note",
                                "xsec_token": "token-1",
                                "note_card": {
                                    "display_title": "第一页",
                                    "user": {"nickname": "作者A"},
                                    "interact_info": {},
                                },
                            }
                        ],
                    },
                }
            return {
                "success": True,
                "data": {
                    "has_more": False,
                    "items": [
                        {
                            "id": "456",
                            "modelType": "note",
                            "xsec_token": "token-2",
                            "note_card": {
                                "display_title": "第二页",
                                "user": {"nickname": "作者B"},
                                "interact_info": {},
                            },
                        }
                    ],
                },
            }
        if uri == "/api/sns/web/v2/user/me":
            return {"success": True}
        raise AssertionError(f"unexpected uri: {uri}")

    async def check_cookie(self):  # type: ignore[override]
        from xhs_mcp_silent.models import CheckCookieResult

        return CheckCookieResult(valid=True, source="test", profile="Profile 1", cookie_path="/tmp/Cookies")


@pytest.mark.asyncio
async def test_search_notes_uses_reference_payload_and_paginates() -> None:
    api = SearchPayloadApi()
    items = await api.search_notes("深圳 约会", limit=2)

    assert [item.title for item in items] == ["第一页", "第二页"]
    assert len(api.calls) == 2

    first_uri, first_kwargs = api.calls[0]
    assert first_uri == "/api/sns/web/v1/search/notes"
    assert first_kwargs["data"]["page"] == 1
    assert first_kwargs["data"]["page_size"] == 20
    assert first_kwargs["data"]["filters"] == SEARCH_DEFAULT_FILTERS
    assert first_kwargs["data"]["image_formats"] == ["jpg", "webp", "avif"]

    second_uri, second_kwargs = api.calls[1]
    assert second_uri == "/api/sns/web/v1/search/notes"
    assert second_kwargs["data"]["page"] == 2
    assert second_kwargs["data"]["search_id"] == first_kwargs["data"]["search_id"]


@pytest.mark.asyncio
async def test_get_note_content_parsing() -> None:
    api = FakeApi()
    detail = await api.get_note_content("https://www.xiaohongshu.com/explore/123?xsec_token=token")
    assert isinstance(detail, NoteDetail)
    assert detail.title == "详情标题"
    assert detail.content == "正文"
    assert detail.shared_count == 4
    assert detail.tag_list == [{"name": "标签"}]


@pytest.mark.asyncio
async def test_get_note_comments_limit() -> None:
    api = FakeApi()
    comments = await api.get_note_comments("https://www.xiaohongshu.com/explore/123?xsec_token=token", limit=1)
    assert isinstance(comments, CommentPage)
    assert len(comments.comments) == 1
    assert comments.comments[0].user_name == "用户A"
    assert comments.comments[0].sub_comments[0]["content"] == "子评论A"
    assert comments.cursor == "next-cursor"


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
