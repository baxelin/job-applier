import logging
import random
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import Self

from playwright.sync_api import BrowserContext, Page, Playwright, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from job_applier.linkedin.page_snapshot import PageSnapshot
from job_applier.models.job_posting import JobPosting

logger = logging.getLogger(__name__)


class JobBrowser(ABC):
    """O que a varredura precisa de um navegador."""

    @abstractmethod
    def open_search(self, url: str) -> PageSnapshot:
        """Abre uma página de busca e rola a lista para carregar todas as vagas."""

    @abstractmethod
    def open_job(self, linkedin_id: str) -> PageSnapshot:
        """Abre a página de uma vaga."""

    @abstractmethod
    def save_snapshot(self, name: str) -> Path:
        """Salva HTML e screenshot da página atual para diagnóstico; devolve o caminho do HTML."""


class LinkedInBrowser(JobBrowser):
    """Firefox controlado pelo Playwright com perfil persistente (a sessão do LinkedIn fica salva).

    No Docker roda com interface numa tela virtual (Xvfb), visível pelo noVNC em http://localhost:6080.
    """

    _LOGIN_URL = "https://www.linkedin.com/login"
    _FEED_URL = "https://www.linkedin.com/feed/"
    _LOGGED_IN_URL_PARTS = ("/feed", "/jobs", "/in/", "/mynetwork")
    _CONTENT_TIMEOUT_MS = 15_000
    _JOB_SECTION = "[componentkey^='JobDetails_AboutTheJob_']"
    _JOB_DESCRIPTION = (
        "[componentkey^='JobDetails_AboutTheJob_'] [data-testid='expandable-text-box'], "
        "#job-details, .show-more-less-html__markup"
    )
    _SEARCH_CARD = "[componentkey^='job-card-component-ref-'], [data-job-id], [data-occludable-job-id]"
    _SCROLL_PAUSE_MS = (400, 900)
    _SCROLL_INTO_VIEW_SCRIPT = "selector => document.querySelector(selector)?.scrollIntoView({block: 'center'})"
    _SCROLL_RESULTS_SCRIPT = """
        cardSelector => {
            const card = document.querySelector(cardSelector);
            let element = card;
            while (element && element !== document.body) {
                const style = getComputedStyle(element);
                if (/(auto|scroll)/.test(style.overflowY) && element.scrollHeight > element.clientHeight) break;
                element = element.parentElement;
            }
            const target = element && element !== document.body ? element : document.scrollingElement;
            target.scrollBy(0, 700);
        }
    """

    def __init__(
        self,
        profile_dir: Path,
        snapshots_dir: Path,
        headless: bool = False,
        scroll_steps: int = 10,
        job_url_for: Callable[[str], str] = JobPosting.url_for,
    ) -> None:
        self._profile_dir = profile_dir
        self._snapshots_dir = snapshots_dir
        self._headless = headless
        self._scroll_steps = scroll_steps
        self._job_url_for = job_url_for
        self._playwright: Playwright | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    def __enter__(self) -> Self:
        self._profile_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = sync_playwright().start()
        self._context = self._playwright.firefox.launch_persistent_context(
            str(self._profile_dir),
            headless=self._headless,
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            viewport={"width": 1366, "height": 860},
        )
        self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: TracebackType | None
    ) -> None:
        if self._context:
            self._context.close()
        if self._playwright:
            self._playwright.stop()

    def open(self, url: str, wait_for: str = "body") -> PageSnapshot:
        self._current_page().goto(url, wait_until="domcontentloaded")
        self._wait_for(wait_for)
        return self._snapshot()

    def open_search(self, url: str) -> PageSnapshot:
        self.open(url, wait_for=f"{self._SEARCH_CARD}, a[href*='/jobs/view/']")
        page = self._current_page()
        for _ in range(self._scroll_steps):
            page.evaluate(self._SCROLL_RESULTS_SCRIPT, self._SEARCH_CARD)
            page.wait_for_timeout(random.randint(*self._SCROLL_PAUSE_MS))
        return self._snapshot()

    def open_job(self, linkedin_id: str) -> PageSnapshot:
        """A seção "Sobre a vaga" nasce como esqueleto vazio e só é preenchida quando fica visível,
        então rola até ela e espera o texto da descrição, não apenas o contêiner.

        A rolagem é feita num único passo em JavaScript porque o LinkedIn recria a seção enquanto
        carrega; segurar uma referência ao elemento (locator) falha quando ele sai do DOM."""
        page = self._current_page()
        page.goto(self._job_url_for(linkedin_id), wait_until="domcontentloaded")
        if self._wait_for(self._JOB_SECTION):
            page.evaluate(self._SCROLL_INTO_VIEW_SCRIPT, self._JOB_SECTION)
        self._wait_for(self._JOB_DESCRIPTION)
        return self._snapshot()

    def save_snapshot(self, name: str) -> Path:
        self._snapshots_dir.mkdir(parents=True, exist_ok=True)
        base = self._snapshots_dir / f"{datetime.now():%Y-%m-%d_%H-%M-%S}_{name}"
        page = self._current_page()
        html_path = base.with_suffix(".html")
        html_path.write_text(page.content(), encoding="utf-8")
        page.screenshot(path=base.with_suffix(".png"), full_page=True)
        return html_path

    def is_logged_in(self) -> bool:
        self.open(self._FEED_URL)
        return self._is_logged_in_url(self._current_page().url)

    def wait_for_login(self, timeout_seconds: float, poll_seconds: float = 2) -> bool:
        """Abre a tela de login e espera a pessoa entrar manualmente (pelo noVNC no Docker)."""
        self.open(self._LOGIN_URL)
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if self._is_logged_in_url(self._current_page().url):
                return True
            time.sleep(poll_seconds)
        return False

    def _wait_for(self, selector: str) -> bool:
        page = self._current_page()
        try:
            page.wait_for_selector(selector, timeout=self._CONTENT_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            logger.info("A página não mostrou '%s' a tempo: %s", selector, page.url)
            return False
        return True

    def _is_logged_in_url(self, url: str) -> bool:
        return any(part in url for part in self._LOGGED_IN_URL_PARTS)

    def _snapshot(self) -> PageSnapshot:
        page = self._current_page()
        return PageSnapshot(url=page.url, html=page.content(), text=page.inner_text("body"))

    def _current_page(self) -> Page:
        if self._page is None:
            raise RuntimeError("Use o navegador dentro de um bloco 'with'.")
        return self._page
