from __future__ import annotations

from Crypto.Cipher import AES

from xhs_mcp_silent.cookie_resolver import ChromeCookieResolver
from xhs_mcp_silent.models import ErrorCode, XhsSilentError


def encrypt_cookie_value(value: str, key: bytes, host_key: str) -> bytes:
    import hashlib

    raw = hashlib.sha256(host_key.encode("utf-8")).digest() + value.encode("utf-8")
    pad = 16 - (len(raw) % 16)
    raw += bytes([pad]) * pad
    cipher = AES.new(key, AES.MODE_CBC, iv=b" " * 16)
    return b"v10" + cipher.encrypt(raw)


def test_cookie_override_from_env() -> None:
    resolver = ChromeCookieResolver(env={"XHS_COOKIE": "a1=foo; webId=bar"})
    bundle = resolver.resolve()
    assert bundle.cookies == {"a1": "foo", "webId": "bar"}
    assert bundle.source == "env:XHS_COOKIE"


def test_cookie_missing_path_raises() -> None:
    resolver = ChromeCookieResolver(
        chrome_dir="/tmp/does-not-exist",
        env={},
    )
    try:
        resolver.resolve()
    except XhsSilentError as exc:
        assert exc.code == ErrorCode.COOKIE_MISSING
        assert "Chrome Cookies DB not found" in exc.message
    else:
        raise AssertionError("expected COOKIE_MISSING")


def test_decrypt_cookie_value_handles_host_hash_prefix() -> None:
    key = b"0123456789abcdef"
    host_key = ".xiaohongshu.com"
    encrypted = encrypt_cookie_value("cookie-value", key, host_key)
    value = ChromeCookieResolver.decrypt_cookie_value(encrypted, key, host_key)
    assert value == "cookie-value"

