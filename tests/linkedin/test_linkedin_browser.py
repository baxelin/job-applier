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


DESCRIPTION_HTML = '<h2>Sobre a vaga</h2><span data-testid="expandable-text-box"><p>Vaga com Python.</p></span>'


# A coluna tem rolagem própria, como no LinkedIn: rolar o documento não mostraria a seção
SKELETON_JOB_PAGE = f"""
<html><head><meta charset="utf-8"><title>Desenvolvedor Júnior | Empresa X | LinkedIn</title></head><body>
  <main id="scroller" style="height: 500px; overflow-y: auto">
    <div data-testid="lazy-column">
      <h1>Desenvolvedor Júnior</h1>
      <div style="height: 2000px"></div>
      <div id="about"><div style="height: 200px"></div></div>
      <div style="height: 2000px"></div>
    </div>
  </main>
  <script>
    // Imita o LinkedIn: a seção "Sobre a vaga" só é preenchida depois que aparece na tela
    const section = document.getElementById('about');
    new IntersectionObserver((entries, observer) => {{
      if (!entries[0].isIntersecting) return;
      observer.disconnect();
      setTimeout(() => {{ section.innerHTML = '{DESCRIPTION_HTML}'; }}, 500);
    }}).observe(section);
  </script>
</body></html>
"""


READY_DESCRIPTION_JOB_PAGE = f"""
<html><head><meta charset="utf-8"></head><body>
  <h1>Desenvolvedor Júnior</h1>
  <div>{DESCRIPTION_HTML}</div>
</body></html>
"""


TEXT_ARRIVES_IN_PARTS_JOB_PAGE = """
<html><head><meta charset="utf-8"></head><body>
  <h1>Desenvolvedor Júnior</h1>
  <h2>Sobre a vaga</h2>
  <span data-testid="expandable-text-box" id="box"><p>Responsabilidades</p></span>
  <script>
    // Imita o LinkedIn: o início do texto aparece primeiro e as listas chegam depois
    setTimeout(() => {
      document.getElementById('box').insertAdjacentHTML('beforeend', '<ul><li>Vaga com Python.</li></ul>');
    }, 800);
  </script>
</body></html>
"""


COMPANY_LOADS_FIRST_JOB_PAGE = f"""
<html><head><meta charset="utf-8"></head><body>
  <h1>Desenvolvedor Júnior</h1>
  <div id="about"></div>
  <h2>Sobre a empresa</h2>
  <span data-testid="expandable-text-box"><p>Texto institucional.</p></span>
  <script>
    setTimeout(() => {{ document.getElementById('about').innerHTML = '{DESCRIPTION_HTML}'; }}, 2500);
  </script>
</body></html>
"""


RECREATED_SECTION_JOB_PAGE = f"""
<html><head><meta charset="utf-8"></head><body>
  <h1>Desenvolvedor Júnior</h1>
  <div style="height: 2000px"></div>
  <div id="about"><div style="height: 200px"></div></div>
  <script>
    // Imita o LinkedIn: enquanto carrega, a seção é trocada por uma cópia várias vezes
    let swaps = 0;
    const timer = setInterval(() => {{
      const section = document.getElementById('about');
      if (++swaps < 60) {{
        section.replaceWith(section.cloneNode(true));
        return;
      }}
      clearInterval(timer);
      section.innerHTML = '{DESCRIPTION_HTML}';
    }}, 5);
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

    @pytest.mark.parametrize(
        "html",
        [
            SKELETON_JOB_PAGE,
            READY_DESCRIPTION_JOB_PAGE,
            TEXT_ARRIVES_IN_PARTS_JOB_PAGE,
            COMPANY_LOADS_FIRST_JOB_PAGE,
            RECREATED_SECTION_JOB_PAGE,
        ],
        ids=[
            "esqueleto-preenchido-ao-rolar",
            "descricao-ja-pronta",
            "texto-chega-em-partes",
            "empresa-carrega-antes",
            "secao-recriada",
        ],
    )
    def test_job_page_waits_for_the_description_in_every_loading_state(self, tmp_path, html):
        page = local_page(tmp_path, "vaga.html", html)
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
