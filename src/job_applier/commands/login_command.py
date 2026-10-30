from collections.abc import Callable

from job_applier.linkedin.linkedin_browser import LinkedInBrowser


class LoginCommand:
    """Abre o LinkedIn no perfil persistente para o login manual; a sessão fica salva para as próximas execuções."""

    NOVNC_URL = "http://localhost:6080/vnc.html?autoconnect=1&resize=scale"

    def __init__(self, browser_factory: Callable[[], LinkedInBrowser], timeout_minutes: int) -> None:
        self._browser_factory = browser_factory
        self._timeout_minutes = timeout_minutes

    def run(self) -> int:
        with self._browser_factory() as browser:
            if browser.is_logged_in():
                print("Você já está logado no LinkedIn. Nada a fazer.")
                return 0

            print(
                "Faça o login no LinkedIn pela janela do navegador.\n"
                f"No Docker, abra {self.NOVNC_URL} no seu navegador para ver e controlar o Firefox.\n"
                f"Aguardando até {self._timeout_minutes} minutos..."
            )
            if browser.wait_for_login(self._timeout_minutes * 60):
                print("Login concluído. A sessão ficou salva no perfil do navegador.")
                return 0

        print("Tempo esgotado sem login. Rode o comando de novo quando quiser tentar.")
        return 1
