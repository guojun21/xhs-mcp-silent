from __future__ import annotations

import pytest

from xhs_mcp_silent.models import NoteUrl, XhsSilentError


def test_note_url_parse_success() -> None:
    url = "https://www.xiaohongshu.com/explore/680a25a4000000001c02d251?xsec_token=ABC123"
    parsed = NoteUrl.parse(url)
    assert parsed.note_id == "680a25a4000000001c02d251"
    assert parsed.xsec_token == "ABC123"


def test_note_url_parse_requires_token() -> None:
    with pytest.raises(XhsSilentError):
        NoteUrl.parse("https://www.xiaohongshu.com/explore/680a25a4000000001c02d251")

