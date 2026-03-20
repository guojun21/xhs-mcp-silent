from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any

import execjs

from .models import ErrorCode, XhsSilentError


class XhsSigner:
    def __init__(self, js_path: str | Path | None = None) -> None:
        base_dir = Path(__file__).resolve().parent
        self.js_path = Path(js_path or base_dir / "vendor" / "xhsvm.js")
        self._compiled = None
        self._lock = Lock()

    def sign_request(self, uri: str, data: Any, cookie_string: str) -> dict[str, str]:
        try:
            payload = self._runtime().call("GetXsXt", uri, data, cookie_string)
            parsed = json.loads(payload)
            return {
                "x-s": str(parsed["X-s"]),
                "x-t": str(parsed["X-t"]),
            }
        except Exception as exc:
            raise XhsSilentError(
                ErrorCode.SIGN_FAILED,
                "Failed to generate x-s/x-t signature.",
                details={"uri": uri, "error": str(exc)},
            ) from exc

    def _runtime(self):
        if self._compiled is not None:
            return self._compiled
        with self._lock:
            if self._compiled is None:
                source = self.js_path.read_text(encoding="utf-8")
                self._compiled = execjs.compile(source)
        return self._compiled

