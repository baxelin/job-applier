from job_applier.browser.firefox_health_check import FirefoxHealthCheck


class Application:
    """Ponto de entrada da aplicação."""

    def __init__(self, health_check: FirefoxHealthCheck | None = None) -> None:
        self._health_check = health_check or FirefoxHealthCheck()

    def run(self) -> None:
        print(self._health_check.run())
