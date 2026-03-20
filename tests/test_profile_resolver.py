from __future__ import annotations

from pathlib import Path

import pytest

from xhs_mcp_silent.models import XhsSilentError
from xhs_mcp_silent.profile_resolver import ChromeProfileResolver


def test_resolve_profile_by_email(tmp_path: Path) -> None:
    chrome_dir = tmp_path / "Chrome"
    chrome_dir.mkdir()
    (chrome_dir / "Local State").write_text(
        '{"profile":{"info_cache":{"Profile 1":{"user_name":"oasismetallicablur@gmail.com"}}}}',
        encoding="utf-8",
    )
    resolver = ChromeProfileResolver(chrome_dir=chrome_dir)
    assert resolver.resolve_profile("oasismetallicablur@gmail.com") == "Profile 1"


def test_resolve_profile_returns_profile_name_directly(tmp_path: Path) -> None:
    resolver = ChromeProfileResolver(chrome_dir=tmp_path / "Chrome")
    assert resolver.resolve_profile("Profile 1") == "Profile 1"


def test_resolve_profile_by_missing_email_raises(tmp_path: Path) -> None:
    chrome_dir = tmp_path / "Chrome"
    chrome_dir.mkdir()
    (chrome_dir / "Local State").write_text('{"profile":{"info_cache":{}}}', encoding="utf-8")
    resolver = ChromeProfileResolver(chrome_dir=chrome_dir)
    with pytest.raises(XhsSilentError):
        resolver.resolve_profile("missing@example.com")
