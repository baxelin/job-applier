from playwright.sync_api import sync_playwright


class FirefoxHealthCheck:
    """Confirma que o Playwright consegue abrir o Firefox no ambiente atual."""

    def run(self) -> str:
        with sync_playwright() as playwright:
            browser = playwright.firefox.launch(headless=True)
            version = browser.version
            browser.close()
        return f"Hello, world! Firefox {version} rodando com Playwright."
