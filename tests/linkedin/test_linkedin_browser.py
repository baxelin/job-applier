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


SKELETON_JOB_PAGE = """
<html><head><meta charset="utf-8"><title>Desenvolvedor Júnior | Empresa X | LinkedIn</title></head><body>
  <h1>Desenvolvedor Júnior</h1>
  <div style="height: 2000px"></div>
  <div componentkey="JobDetails_AboutTheJob_77"><div style="height: 200px"></div></div>
  <script>
    // Imita o LinkedIn: a seção "Sobre a vaga" só é preenchida depois que aparece na tela
    const section = document.querySelector("[componentkey^='JobDetails_AboutTheJob_']");
    new IntersectionObserver((entries, observer) => {
      if (!entries[0].isIntersecting) return;
      observer.disconnect();
      setTimeout(() => {
        section.innerHTML = '<span data-testid="expandable-text-box"><p>Vaga com Python.</p></span>';
      }, 500);
    }).observe(section);
  </script>
</body></html>
"""


RECREATED_SECTION_JOB_PAGE = """
<html><head><meta charset="utf-8"></head><body>
  <h1>Desenvolvedor Júnior</h1>
  <div style="height: 2000px"></div>
  <div componentkey="JobDetails_AboutTheJob_77"><div style="height: 200px"></div></div>
  <script>
    // Imita o LinkedIn: enquanto carrega, a seção é trocada por uma cópia várias vezes
    let swaps = 0;
    const timer = setInterval(() => {
      const section = document.querySelector("[componentkey^='JobDetails_AboutTheJob_']");
      if (++swaps < 60) {
        section.replaceWith(section.cloneNode(true));
        return;
      }
      clearInterval(timer);
      section.innerHTML = '<span data-testid="expandable-text-box"><p>Vaga com Python.</p></span>';
    }, 5);
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

        assert [card.linkedin_id for card in SearchResultsParser().cards(snapshot.html)] == ["1", "2", "3", "4"]

    def test_job_page_waits_until_the_description_skeleton_is_filled(self, tmp_path):
        page = local_page(tmp_path, "vaga.html", SKELETON_JOB_PAGE)
        with LinkedInBrowser(tmp_path / "profile", tmp_path / "debug", headless=True, job_url_for=lambda _: page) as browser:
            snapshot = browser.open_job("77")

        assert "Vaga com Python." in snapshot.text

    def test_job_page_tolerates_the_section_being_recreated_while_loading(self, tmp_path):
        page = local_page(tmp_path, "vaga.html", RECREATED_SECTION_JOB_PAGE)
        with LinkedInBrowser(tmp_path / "profile", tmp_path / "debug", headless=True, job_url_for=lambda _: page) as browser:
            snapshot = browser.open_job("77")

        assert "Vaga com Python." in snapshot.text

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
