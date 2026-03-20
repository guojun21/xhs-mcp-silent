from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from urllib.parse import parse_qs, urlparse


class ErrorCode(str, Enum):
    COOKIE_MISSING = "COOKIE_MISSING"
    COOKIE_EXPIRED = "COOKIE_EXPIRED"
    SIGN_FAILED = "SIGN_FAILED"
    XHS_API_FAILED = "XHS_API_FAILED"


class XhsSilentError(RuntimeError):
    def __init__(
        self,
        code: ErrorCode | str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code.value if isinstance(code, ErrorCode) else str(code)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        payload = {"code": self.code, "message": self.message}
        if self.details:
            payload["details"] = self.details
        return payload


@dataclass(frozen=True)
class CookieBundle:
    cookies: dict[str, str]
    source: str
    profile: str
    cookie_path: str

    def as_cookie_string(self) -> str:
        return "; ".join(f"{key}={value}" for key, value in self.cookies.items())


@dataclass(frozen=True)
class NoteUrl:
    note_id: str
    xsec_token: str

    @classmethod
    def parse(cls, value: str) -> "NoteUrl":
        parsed = urlparse(value.strip())
        note_id = parsed.path.rstrip("/").split("/")[-1]
        xsec_token = parse_qs(parsed.query).get("xsec_token", [""])[0]
        if not note_id or not xsec_token:
            raise XhsSilentError(
                ErrorCode.XHS_API_FAILED,
                "URL must include both note id and xsec_token.",
                details={"url": value},
            )
        return cls(note_id=note_id, xsec_token=xsec_token)

    @property
    def url(self) -> str:
        return f"https://www.xiaohongshu.com/explore/{self.note_id}?xsec_token={self.xsec_token}"


@dataclass(frozen=True)
class CheckCookieResult:
    valid: bool
    source: str
    profile: str
    cookie_path: str
    reason: str = ""
    user_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NoteSummary:
    note_id: str
    title: str
    author: str
    liked_count: int
    collected_count: int
    comment_count: int
    xsec_token: str
    url: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NoteDetail:
    note_id: str
    title: str
    author: str
    author_user_id: str
    author_xsec_token: str
    author_avatar: str
    published_at: str
    published_time_ms: int
    last_update_at: str
    last_update_time_ms: int
    note_type: str
    liked_count: int
    collected_count: int
    comment_count: int
    shared_count: int
    liked: bool
    collected: bool
    content: str
    cover_url: str
    ip_location: str
    tag_list: list[dict[str, Any]]
    at_user_list: list[dict[str, Any]]
    image_list: list[dict[str, Any]]
    share_info: dict[str, Any]
    user: dict[str, Any]
    url: str
    raw_note_card: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CommentItem:
    comment_id: str
    note_id: str
    user_name: str
    user_id: str
    user_xsec_token: str
    user_avatar: str
    content: str
    created_at: str
    create_time_ms: int
    liked_count: int
    liked: bool
    status: int
    ip_location: str
    show_tags: list[Any]
    at_users: list[dict[str, Any]]
    sub_comment_count: int
    sub_comment_cursor: str
    sub_comment_has_more: bool
    sub_comments: list[dict[str, Any]]
    raw_comment: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CommentPage:
    comments: list[CommentItem]
    cursor: str
    has_more: bool
    time_ms: int
    fetched_at: str
    user_id: str
    xsec_token: str
    raw_page: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def format_millis_timestamp(value: int | float | None) -> str:
    if not value:
        return ""
    dt = datetime.fromtimestamp(float(value) / 1000, tz=timezone.utc).astimezone()
    return dt.strftime("%Y-%m-%d %H:%M:%S")
