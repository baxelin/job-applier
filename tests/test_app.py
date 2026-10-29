from job_applier.app import Application


class FakeHealthCheck:
    def run(self) -> str:
        return "mensagem de teste"


class TestApplication:
    def test_run_prints_health_check_message(self, capsys):
        Application(health_check=FakeHealthCheck()).run()

        assert capsys.readouterr().out.strip() == "mensagem de teste"
