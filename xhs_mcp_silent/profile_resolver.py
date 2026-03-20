from __future__ import annotations

import json
from pathlib import Path

from .cookie_resolver import DEFAULT_CHROME_DIR
from .models import ErrorCode, XhsSilentError


class ChromeProfileResolver:
    def __init__(self, chrome_dir: str | Path | None = None) -> None:
        self.chrome_dir = Path(chrome_dir or DEFAULT_CHROME_DIR).expanduser()

    @property
    def local_state_path(self) -> Path:
        return self.chrome_dir / "Local State"

    def resolve_profile(self, profile_or_email: str) -> str:
        value = profile_or_email.strip()
        if not value:
            raise XhsSilentError(ErrorCode.COOKIE_MISSING, "Chrome profile cannot be empty.")
        if "@" not in value:
            return value

        local_state = self._read_local_state()
        info_cache = (((local_state.get("profile") or {}).get("info_cache")) or {})
        for profile_name, payload in info_cache.items():
            if str((payload or {}).get("user_name") or "").strip().lower() == value.lower():
                return profile_name

        raise XhsSilentError(
            ErrorCode.COOKIE_MISSING,
            "Chrome profile email was not found in Local State.",
            details={"email": value, "local_state_path": str(self.local_state_path)},
        )

    def _read_local_state(self) -> dict:
        if not self.local_state_path.exists():
            raise XhsSilentError(
                ErrorCode.COOKIE_MISSING,
                "Chrome Local State file was not found.",
                details={"local_state_path": str(self.local_state_path)},
            )
        try:
            return json.loads(self.local_state_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise XhsSilentError(
                ErrorCode.COOKIE_MISSING,
                "Failed to read Chrome Local State.",
                details={"local_state_path": str(self.local_state_path), "error": str(exc)},
            ) from exc
