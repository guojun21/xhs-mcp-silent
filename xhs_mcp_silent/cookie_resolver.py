from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2

from .models import CookieBundle, ErrorCode, XhsSilentError

DEFAULT_CHROME_DIR = Path.home() / "Library/Application Support/Google/Chrome"
DEFAULT_PROFILE = "Profile 1"
SAFE_STORAGE_SERVICE = "Chrome Safe Storage"
COOKIE_HOST_FILTER = "%xiaohongshu.com"


class ChromeCookieResolver:
    def __init__(
        self,
        *,
        chrome_dir: str | Path | None = None,
        profile: str | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self._env = dict(os.environ if env is None else env)
        self.chrome_dir = Path(chrome_dir or self._env.get("XHS_CHROME_DIR") or DEFAULT_CHROME_DIR).expanduser()
        self.profile = profile or self._env.get("XHS_CHROME_PROFILE") or DEFAULT_PROFILE
        self.cookie_override = (self._env.get("XHS_COOKIE") or "").strip()

    @property
    def cookie_path(self) -> Path:
        return self.chrome_dir / self.profile / "Cookies"

    def resolve(self) -> CookieBundle:
        if self.cookie_override:
            cookies = self._parse_cookie_string(self.cookie_override)
            if not cookies:
                raise XhsSilentError(ErrorCode.COOKIE_MISSING, "XHS_COOKIE is set but empty after parsing.")
            return CookieBundle(
                cookies=cookies,
                source="env:XHS_COOKIE",
                profile=self.profile,
                cookie_path="env:XHS_COOKIE",
            )

        if sys.platform != "darwin":
            raise XhsSilentError(
                ErrorCode.COOKIE_MISSING,
                "xhs-mcp-silent only supports macOS Chrome cookie reuse in V1.",
                details={"platform": sys.platform},
            )

        if not self.cookie_path.exists():
            raise XhsSilentError(
                ErrorCode.COOKIE_MISSING,
                "Chrome Cookies DB not found. Log in to xiaohongshu.com in Chrome first.",
                details={"cookie_path": str(self.cookie_path)},
            )

        key = self._get_chrome_safe_storage_key()
        cookies = self._read_cookies_from_db(key)
        if not cookies:
            raise XhsSilentError(
                ErrorCode.COOKIE_MISSING,
                "No Xiaohongshu cookies found in the selected Chrome profile.",
                details={"cookie_path": str(self.cookie_path), "profile": self.profile},
            )

        return CookieBundle(
            cookies=cookies,
            source=f"chrome:{self.profile}",
            profile=self.profile,
            cookie_path=str(self.cookie_path),
        )

    def _get_chrome_safe_storage_key(self) -> bytes:
        try:
            result = subprocess.run(
                ["security", "find-generic-password", "-s", SAFE_STORAGE_SERVICE, "-w"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except Exception as exc:
            raise XhsSilentError(
                ErrorCode.COOKIE_MISSING,
                "Failed to query Chrome Safe Storage from macOS Keychain.",
                details={"error": str(exc)},
            ) from exc

        if result.returncode != 0 or not result.stdout.strip():
            raise XhsSilentError(
                ErrorCode.COOKIE_MISSING,
                "Chrome Safe Storage key is unavailable in macOS Keychain.",
                details={"stderr": result.stderr.strip()},
            )

        password = result.stdout.strip().encode("utf-8")
        return PBKDF2(password, b"saltysalt", dkLen=16, count=1003)

    def _read_cookies_from_db(self, key: bytes) -> dict[str, str]:
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as handle:
                temp_path = Path(handle.name)
            shutil.copy2(self.cookie_path, temp_path)

            conn = sqlite3.connect(str(temp_path))
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT name, value, encrypted_value, host_key
                    FROM cookies
                    WHERE host_key LIKE ?
                    ORDER BY host_key, name
                    """,
                    (COOKIE_HOST_FILTER,),
                )
                resolved: dict[str, str] = {}
                for name, value, encrypted_value, host_key in cursor.fetchall():
                    cookie_value = value or ""
                    if not cookie_value and encrypted_value:
                        cookie_value = self.decrypt_cookie_value(encrypted_value, key, host_key)
                    if cookie_value:
                        resolved[name] = cookie_value
                return resolved
            finally:
                conn.close()
        except XhsSilentError:
            raise
        except Exception as exc:
            raise XhsSilentError(
                ErrorCode.COOKIE_MISSING,
                "Failed to read Chrome cookies database.",
                details={"cookie_path": str(self.cookie_path), "error": str(exc)},
            ) from exc
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink(missing_ok=True)

    @staticmethod
    def decrypt_cookie_value(encrypted_value: bytes, key: bytes, host_key: str) -> str:
        if not encrypted_value:
            return ""
        if encrypted_value[:3] not in {b"v10", b"v11"}:
            return encrypted_value.decode("utf-8", errors="ignore")

        payload = encrypted_value[3:]
        cipher = AES.new(key, AES.MODE_CBC, iv=b" " * 16)
        decrypted = cipher.decrypt(payload)

        pad = decrypted[-1]
        if 1 <= pad <= 16 and decrypted.endswith(bytes([pad]) * pad):
            decrypted = decrypted[:-pad]

        host_hash = hashlib.sha256(host_key.encode("utf-8")).digest()
        if decrypted.startswith(host_hash):
            decrypted = decrypted[32:]

        return decrypted.decode("utf-8", errors="ignore")

    @staticmethod
    def _parse_cookie_string(cookie_string: str) -> dict[str, str]:
        cookies: dict[str, str] = {}
        for raw_pair in cookie_string.split(";"):
            pair = raw_pair.strip()
            if not pair or "=" not in pair:
                continue
            name, value = pair.split("=", 1)
            name = name.strip()
            value = value.strip()
            if name and value:
                cookies[name] = value
        return cookies
