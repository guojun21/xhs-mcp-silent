from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .cookie_resolver import DEFAULT_CHROME_DIR, DEFAULT_PROFILE


DEFAULT_LOGIN_URL = "https://www.xiaohongshu.com/"


@dataclass(frozen=True)
class BrowserLaunchResult:
    launched: bool
    profile: str
    url: str
    command: tuple[str, ...]
    error: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "launched": self.launched,
            "profile": self.profile,
            "url": self.url,
            "command": list(self.command),
            "error": self.error,
        }


class ChromeLoginLauncher:
    def __init__(
        self,
        *,
        profile: str = DEFAULT_PROFILE,
        chrome_dir: str | Path | None = None,
        chrome_binary: str | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self.profile = profile
        self.env = dict(os.environ if env is None else env)
        self.chrome_dir = Path(
            chrome_dir or self.env.get("XHS_CHROME_DIR") or DEFAULT_CHROME_DIR
        ).expanduser()
        self.chrome_binary = chrome_binary or self.env.get("XHS_CHROME_BIN") or self._default_chrome_binary()

    def open_homepage(self, url: str = DEFAULT_LOGIN_URL) -> BrowserLaunchResult:
        profile_args = [
            f"--user-data-dir={self.chrome_dir}",
            f"--profile-directory={self.profile}",
            "--new-window",
            url,
        ]
        commands = []
        chrome_app_path = self._chrome_app_path()
        if chrome_app_path:
            commands.append(["open", "-na", chrome_app_path, "--args", *profile_args])
        commands.append(["open", "-na", "Google Chrome", "--args", *profile_args])
        if self.chrome_binary:
            commands.append([self.chrome_binary, *profile_args])

        last_error = ""
        for command in commands:
            try:
                if command[0] == "open":
                    subprocess.run(
                        command,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=True,
                    )
                else:
                    subprocess.Popen(
                        command,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                self._activate_chrome()
                return BrowserLaunchResult(
                    launched=True,
                    profile=self.profile,
                    url=url,
                    command=tuple(command),
                )
            except Exception as exc:
                last_error = str(exc)

        return BrowserLaunchResult(
            launched=False,
            profile=self.profile,
            url=url,
            command=tuple(commands[-1]),
            error=last_error,
        )

    @staticmethod
    def _default_chrome_binary() -> str:
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            str(Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        ]
        for candidate in candidates:
            if Path(candidate).exists():
                return candidate
        return ""

    def _chrome_app_path(self) -> str:
        if not self.chrome_binary:
            return ""
        binary_path = Path(self.chrome_binary)
        try:
            app_path = binary_path.parents[2]
        except IndexError:
            return ""
        if app_path.exists() and app_path.suffix == ".app":
            return str(app_path)
        return ""

    @staticmethod
    def _activate_chrome() -> None:
        try:
            subprocess.run(
                ["osascript", "-e", 'tell application "Google Chrome" to activate'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except Exception:
            return
