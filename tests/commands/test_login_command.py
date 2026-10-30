from job_applier.commands.login_command import LoginCommand


class FakeLoginBrowser:
    def __init__(self, logged_in: bool, logs_in_manually: bool) -> None:
        self._logged_in = logged_in
        self._logs_in_manually = logs_in_manually
        self.waited_seconds: float | None = None

    def __enter__(self):
        return self

    def __exit__(self, *exc_info) -> None:
        return None

    def is_logged_in(self) -> bool:
        return self._logged_in

    def wait_for_login(self, timeout_seconds: float) -> bool:
        self.waited_seconds = timeout_seconds
        return self._logs_in_manually


class TestLoginCommand:
    def test_does_nothing_when_already_logged_in(self, capsys):
        browser = FakeLoginBrowser(logged_in=True, logs_in_manually=False)

        assert LoginCommand(lambda: browser, timeout_minutes=10).run() == 0
        assert browser.waited_seconds is None
        assert "já está logado" in capsys.readouterr().out

    def test_waits_for_manual_login_showing_novnc_address(self, capsys):
        browser = FakeLoginBrowser(logged_in=False, logs_in_manually=True)

        assert LoginCommand(lambda: browser, timeout_minutes=10).run() == 0
        assert browser.waited_seconds == 600
        assert "localhost:6080" in capsys.readouterr().out

    def test_fails_when_time_runs_out(self, capsys):
        browser = FakeLoginBrowser(logged_in=False, logs_in_manually=False)

        assert LoginCommand(lambda: browser, timeout_minutes=1).run() == 1
        assert "Tempo esgotado" in capsys.readouterr().out
