from job_applier.browser.firefox_health_check import FirefoxHealthCheck


class TestFirefoxHealthCheck:
    def test_run_launches_firefox_and_reports_version(self):
        message = FirefoxHealthCheck().run()

        assert message.startswith("Hello, world! Firefox ")
