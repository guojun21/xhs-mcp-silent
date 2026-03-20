from __future__ import annotations

import json
import random
import time
from collections.abc import Iterable
from typing import Any

from curl_cffi.requests import AsyncSession

from .cookie_resolver import ChromeCookieResolver
from .models import (
    CheckCookieResult,
    CommentItem,
    CommentPage,
    ErrorCode,
    NoteDetail,
    NoteSummary,
    NoteUrl,
    XhsSilentError,
    format_millis_timestamp,
)
from .xhs_signer import XhsSigner

DEFAULT_HEADERS = {
    "content-type": "application/json;charset=UTF-8",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/135.0.0.0 Safari/537.36"
    ),
}

SEARCH_PAGE_SIZE = 20
SEARCH_DEFAULT_FILTERS = [
    {"tags": ["general"], "type": "sort_type"},
    {"tags": ["不限"], "type": "filter_note_type"},
    {"tags": ["不限"], "type": "filter_note_time"},
    {"tags": ["不限"], "type": "filter_note_range"},
    {"tags": ["不限"], "type": "filter_pos_distance"},
]

X_S_COMMON = (
    "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"
)


class XhsApi:
    def __init__(
        self,
        resolver: ChromeCookieResolver | None = None,
        signer: XhsSigner | None = None,
    ) -> None:
        self.resolver = resolver or ChromeCookieResolver()
        self.signer = signer or XhsSigner()
        self.base_url = "https://edith.xiaohongshu.com"

    async def check_cookie(self) -> CheckCookieResult:
        bundle = self.resolver.resolve()
        payload = await self._request_json("/api/sns/web/v2/user/me", method="GET", allow_api_error=True)
        data = payload.get("data") or {}
        success = bool(payload.get("success") is True)
        guest = bool(data.get("guest", False))
        return CheckCookieResult(
            valid=bool(success and not guest),
            source=bundle.source,
            profile=bundle.profile,
            cookie_path=bundle.cookie_path,
            reason="guest" if guest else ("" if success else "api_rejected"),
            user_id=str(data.get("user_id") or ""),
        )

    async def search_notes(self, keywords: str, limit: int = 10) -> list[NoteSummary]:
        capped_limit = max(1, limit)
        search_id = self._search_id()
        results: list[NoteSummary] = []
        seen_ids: set[str] = set()
        page = 1

        while len(results) < capped_limit:
            payload = await self._request_json(
                "/api/sns/web/v1/search/notes",
                method="POST",
                data=self._build_search_payload(keywords, page=page, search_id=search_id),
            )
            data = payload.get("data") or {}
            items = data.get("items") or []
            for item in items:
                if not self._can_parse_note_summary(item):
                    continue
                note = self._parse_note_summary(item)
                if note.note_id in seen_ids:
                    continue
                seen_ids.add(note.note_id)
                results.append(note)
                if len(results) >= capped_limit:
                    break
            if len(results) >= capped_limit:
                break
            if not data.get("has_more") or not items:
                break
            page += 1

        return results[:capped_limit]

    async def get_note_content(self, url: str) -> NoteDetail:
        note = NoteUrl.parse(url)
        payload = await self._request_json(
            "/api/sns/web/v1/feed",
            method="POST",
            data={
                "source_note_id": note.note_id,
                "image_formats": ["jpg", "webp", "avif"],
                "extra": {"need_body_topic": "1"},
                "xsec_source": "pc_feed",
                "xsec_token": note.xsec_token,
            },
            sign=True,
            extra_headers={"x-s-common": X_S_COMMON},
        )
        items = ((payload.get("data") or {}).get("items") or [])
        if not items:
            raise await self._api_error_from_payload(payload, "No note detail found.")
        note_card = (items[0].get("note_card") or {})
        interact = note_card.get("interact_info") or {}
        user = note_card.get("user") or {}
        images = note_card.get("image_list") or []
        cover_url = ""
        if images and images[0].get("url_pre"):
            cover_url = images[0]["url_pre"]
        published_time_ms = int(note_card.get("time") or 0)
        last_update_time_ms = int(note_card.get("last_update_time") or 0)
        return NoteDetail(
            note_id=note.note_id,
            title=note_card.get("title", ""),
            author=user.get("nickname", ""),
            author_user_id=str(user.get("user_id") or ""),
            author_xsec_token=str(user.get("xsec_token") or ""),
            author_avatar=str(user.get("avatar") or user.get("image") or ""),
            published_at=format_millis_timestamp(published_time_ms),
            published_time_ms=published_time_ms,
            last_update_at=format_millis_timestamp(last_update_time_ms),
            last_update_time_ms=last_update_time_ms,
            note_type=str(note_card.get("type") or ""),
            liked_count=int(interact.get("liked_count") or 0),
            collected_count=int(interact.get("collected_count") or 0),
            comment_count=int(interact.get("comment_count") or 0),
            shared_count=int(interact.get("shared_count") or interact.get("share_count") or 0),
            liked=bool(interact.get("liked", False)),
            collected=bool(interact.get("collected", False)),
            content=note_card.get("desc", ""),
            cover_url=cover_url,
            ip_location=str(note_card.get("ip_location") or ""),
            tag_list=list(note_card.get("tag_list") or []),
            at_user_list=list(note_card.get("at_user_list") or []),
            image_list=list(images),
            share_info=dict(note_card.get("share_info") or {}),
            user=dict(user),
            url=note.url,
            raw_note_card=dict(note_card),
        )

    async def get_note_comments(
        self,
        url: str,
        limit: int = 10,
        *,
        cursor: str = "",
        all_pages: bool = False,
    ) -> CommentPage:
        note = NoteUrl.parse(url)
        capped_limit = max(1, limit)
        current_cursor = cursor
        collected: list[CommentItem] = []
        page_data: dict[str, Any] = {}

        while len(collected) < capped_limit:
            payload = await self._request_json(
                "/api/sns/web/v2/comment/page",
                method="GET",
                params={
                    "note_id": note.note_id,
                    "cursor": current_cursor,
                    "top_comment_id": "",
                    "image_formats": "jpg,webp,avif",
                    "xsec_token": note.xsec_token,
                },
            )
            page_data = payload.get("data") or {}
            comments = page_data.get("comments") or []
            for item in comments:
                collected.append(self._parse_comment_item(item))
                if len(collected) >= capped_limit:
                    break
            if len(collected) >= capped_limit:
                break
            if not all_pages or not page_data.get("has_more") or not comments:
                break
            current_cursor = str(page_data.get("cursor") or "")

        time_ms = int(page_data.get("time") or 0)
        return CommentPage(
            comments=collected[:capped_limit],
            cursor=str(page_data.get("cursor") or ""),
            has_more=bool(page_data.get("has_more", False)),
            time_ms=time_ms,
            fetched_at=format_millis_timestamp(time_ms),
            user_id=str(page_data.get("user_id") or ""),
            xsec_token=str(page_data.get("xsec_token") or ""),
            raw_page=dict(page_data),
        )

    async def _request_json(
        self,
        uri: str,
        *,
        method: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        sign: bool = False,
        extra_headers: dict[str, str] | None = None,
        allow_api_error: bool = False,
    ) -> dict[str, Any]:
        bundle = self.resolver.resolve()
        headers = dict(DEFAULT_HEADERS)
        if extra_headers:
            headers.update(extra_headers)
        if sign:
            headers.update(self.signer.sign_request(uri, data or params or {}, bundle.as_cookie_string()))

        try:
            async with AsyncSession(verify=True, impersonate="chrome124") as session:
                response = await session.request(
                    method=method.upper(),
                    url=f"{self.base_url}{uri}",
                    params=params,
                    json=data,
                    cookies=bundle.cookies,
                    headers=headers,
                    quote=False,
                )
                body = response.content
        except XhsSilentError:
            raise
        except Exception as exc:
            raise XhsSilentError(
                ErrorCode.XHS_API_FAILED,
                "Request to Xiaohongshu API failed.",
                details={"uri": uri, "error": str(exc)},
            ) from exc

        try:
            payload = json.loads(body)
        except Exception as exc:
            raise XhsSilentError(
                ErrorCode.XHS_API_FAILED,
                "Xiaohongshu API returned non-JSON content.",
                details={"uri": uri, "status_code": response.status_code, "error": str(exc)},
            ) from exc

        if payload.get("success") is True:
            return payload
        if "success" not in payload and response.status_code < 400:
            return payload
        if allow_api_error:
            return payload
        raise await self._api_error_from_payload(payload, "Xiaohongshu API returned an error.")

    async def _api_error_from_payload(self, payload: dict[str, Any], fallback_message: str) -> XhsSilentError:
        cookie_status = await self.check_cookie()
        if not cookie_status.valid:
            message = "Chrome profile cookies are expired. Log in to xiaohongshu.com in Chrome and retry."
            if cookie_status.reason == "guest":
                message = (
                    "Chrome profile contains a guest Xiaohongshu session, not a logged-in account. "
                    "Log in to xiaohongshu.com in Chrome and retry."
                )
            return XhsSilentError(
                ErrorCode.COOKIE_EXPIRED,
                message,
                details=cookie_status.to_dict(),
            )
        return XhsSilentError(
            ErrorCode.XHS_API_FAILED,
            str(payload.get("msg") or payload.get("message") or fallback_message),
            details={"payload": payload},
        )

    @staticmethod
    def _can_parse_note_summary(item: dict[str, Any]) -> bool:
        model_type = str(item.get("modelType") or item.get("model_type") or "")
        if model_type and model_type != "note":
            return False
        note_card = item.get("note_card") or {}
        return bool(item.get("id")) and bool(note_card)

    @staticmethod
    def _build_search_payload(keywords: str, *, page: int, search_id: str) -> dict[str, Any]:
        return {
            "keyword": keywords,
            "page": page,
            "page_size": SEARCH_PAGE_SIZE,
            "search_id": search_id,
            "sort": "general",
            "note_type": 0,
            "ext_flags": [],
            "filters": SEARCH_DEFAULT_FILTERS,
            "geo": "",
            "image_formats": ["jpg", "webp", "avif"],
        }

    @staticmethod
    def _parse_note_summary(item: dict[str, Any]) -> NoteSummary:
        note_card = item.get("note_card") or {}
        interact = note_card.get("interact_info") or {}
        note_id = str(item.get("id") or "")
        xsec_token = str(item.get("xsec_token") or "")
        return NoteSummary(
            note_id=note_id,
            title=note_card.get("display_title") or note_card.get("title") or "",
            author=(note_card.get("user") or {}).get("nickname", ""),
            liked_count=int(interact.get("liked_count") or 0),
            collected_count=int(interact.get("collected_count") or 0),
            comment_count=int(interact.get("comment_count") or 0),
            xsec_token=xsec_token,
            url=f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={xsec_token}",
        )

    @staticmethod
    def _normalize_sub_comment(item: dict[str, Any]) -> dict[str, Any]:
        user = item.get("user_info") or {}
        normalized = dict(item)
        normalized["created_at"] = format_millis_timestamp(item.get("create_time"))
        normalized["create_time_ms"] = int(item.get("create_time") or 0)
        normalized["liked_count"] = int(item.get("like_count") or 0)
        normalized["user_name"] = str(user.get("nickname") or "")
        normalized["user_id"] = str(user.get("user_id") or "")
        normalized["user_xsec_token"] = str(user.get("xsec_token") or "")
        normalized["user_avatar"] = str(user.get("image") or user.get("avatar") or "")
        return normalized

    @classmethod
    def _parse_comment_item(cls, item: dict[str, Any]) -> CommentItem:
        user = item.get("user_info") or {}
        sub_comments = [cls._normalize_sub_comment(sub) for sub in (item.get("sub_comments") or [])]
        return CommentItem(
            comment_id=str(item.get("id") or ""),
            note_id=str(item.get("note_id") or ""),
            user_name=str(user.get("nickname") or ""),
            user_id=str(user.get("user_id") or ""),
            user_xsec_token=str(user.get("xsec_token") or ""),
            user_avatar=str(user.get("image") or user.get("avatar") or ""),
            content=str(item.get("content") or ""),
            created_at=format_millis_timestamp(item.get("create_time")),
            create_time_ms=int(item.get("create_time") or 0),
            liked_count=int(item.get("like_count") or 0),
            liked=bool(item.get("liked", False)),
            status=int(item.get("status") or 0),
            ip_location=str(item.get("ip_location") or ""),
            show_tags=list(item.get("show_tags") or []),
            at_users=list(item.get("at_users") or []),
            sub_comment_count=int(item.get("sub_comment_count") or 0),
            sub_comment_cursor=str(item.get("sub_comment_cursor") or ""),
            sub_comment_has_more=bool(item.get("sub_comment_has_more", False)),
            sub_comments=sub_comments,
            raw_comment=dict(item),
        )

    @staticmethod
    def _base36encode(number: int, alphabet: Iterable[str] = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ") -> str:
        alphabet = "".join(alphabet)
        sign = "-" if number < 0 else ""
        number = abs(number)
        base36 = ""
        while number:
            number, index = divmod(number, len(alphabet))
            base36 = alphabet[index] + base36
        return sign + (base36 or alphabet[0])

    def _search_id(self) -> str:
        prefix = int(time.time() * 1000) << 64
        suffix = random.randint(0, 2147483646)
        return self._base36encode(prefix + suffix)
