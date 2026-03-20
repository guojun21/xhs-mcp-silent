from __future__ import annotations

from xhs_mcp_silent.browser import ChromeLoginLauncher


def test_open_homepage_uses_explicit_user_data_dir_and_profile(monkeypatch) -> None:
    recorded = {}
    recorded["run"] = []

    class DummyCompletedProcess:
        returncode = 0

    def fake_run(command, stdout=None, stderr=None, check=None):
        recorded["run"].append(command)
        return DummyCompletedProcess()

    def fake_popen(command, stdout=None, stderr=None):
        recorded["popen"] = command
        raise AssertionError("popen fallback should not be used when open succeeds")

    monkeypatch.setattr("subprocess.run", fake_run)
    monkeypatch.setattr("subprocess.Popen", fake_popen)

    launcher = ChromeLoginLauncher(
        profile="Default",
        chrome_dir="/Users/test/Library/Application Support/Google/Chrome",
        chrome_binary="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    )
    result = launcher.open_homepage("https://www.xiaohongshu.com/")

    assert result.launched is True
    open_command = recorded["run"][0]
    assert open_command[:3] == ["open", "-na", "/Applications/Google Chrome.app"]
    assert "--user-data-dir=/Users/test/Library/Application Support/Google/Chrome" in open_command
    assert "--profile-directory=Default" in open_command
    assert recorded["run"][1] == ["osascript", "-e", 'tell application "Google Chrome" to activate']
