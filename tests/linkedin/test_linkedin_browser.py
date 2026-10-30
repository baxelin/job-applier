from pathlib import Path

import pytest

from job_applier.linkedin.linkedin_browser import LinkedInBrowser
from job_applier.linkedin.search_results_parser import SearchResultsParser
from tests.linkedin.pages import job_page

LAZY_SEARCH_PAGE = """
<html><body>
  <div id="list" style="height: 300px; overflow-y: auto">
    <ul id="cards">
      <li data-occludable-job-id="1" style="height: 250px">Vaga 1</li>
      <li data-occludable-job-id="2" style="height: 250px">Vaga 2</li>
    </ul>
  </div>
  <script>
    // Imita o LinkedIn: novas vagas só aparecem quando a lista é rolada até o fim
    const list = document.getElementById('list');
    let next = 3;
    list.addEventListener('scroll', () => {
      if (next <= 4 && list.scrollTop + list.clientHeight >= list.scrollHeight - 10) {
        const card = document.createElement('li');
        card.setAttribute('data-occludable-job-id', String(next++));
        card.style.height = '250px';
        document.getElementById('cards').appendChild(card);
      }
    });
  </script>
</body></html>
"""


@pytest.fixture
def browser(tmp_path):
    with LinkedInBrowser(tmp_path / "profile", tmp_path / "debug", headless=True, scroll_steps=8) as opened:
        yield opened


def local_page(tmp_path: Path, name: str, html: str) -> str:
    path = tmp_path / name
    path.write_text(html, encoding="utf-8")
    return path.as_uri()


class TestLinkedInBrowser:
    def test_opens_page_and_returns_html_and_visible_text(self, browser, tmp_path):
        snapshot = browser.open(local_page(tmp_path, "vaga.html", job_page()), wait_for="h1")

        assert snapshot.url.startswith("file://")
        assert "Desenvolvedor Python Júnior" in snapshot.text
        assert "job-details-jobs-unified-top-card" in snapshot.html

    def test_scrolls_search_results_to_load_every_card(self, browser, tmp_path):
        snapshot = browser.open_search(local_page(tmp_path, "busca.html", LAZY_SEARCH_PAGE))

        assert SearchResultsParser().job_ids(snapshot.html) == ["1", "2", "3", "4"]

    def test_saves_html_and_screenshot_for_diagnosis(self, browser, tmp_path):
        browser.open(local_page(tmp_path, "vaga.html", job_page()))

        html_path = browser.save_snapshot("vaga-123")

        assert html_path.parent == tmp_path / "debug"
        assert "Desenvolvedor Python Júnior" in html_path.read_text(encoding="utf-8")
        assert html_path.with_suffix(".png").stat().st_size > 0

    def test_keeps_the_profile_between_sessions(self, tmp_path):
        page = local_page(tmp_path, "vaga.html", job_page())
        with LinkedInBrowser(tmp_path / "profile", tmp_path / "debug", headless=True) as first:
            first.open(page)

        assert any((tmp_path / "profile").iterdir())
