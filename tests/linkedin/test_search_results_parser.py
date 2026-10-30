from job_applier.linkedin.search_results_parser import SearchResultsParser
from tests.linkedin.pages import search_page


def ids(html: str) -> list[str]:
    return [card.linkedin_id for card in SearchResultsParser().cards(html)]


class TestSearchResultsParser:
    def test_lists_job_cards_in_page_order_without_repetition(self):
        assert ids(search_page("30", "10", "20")) == ["30", "10", "20"]

    def test_finds_ids_from_job_links(self):
        assert ids('<ul><li><a href="https://www.linkedin.com/jobs/view/555/?trk=x">Vaga</a></li></ul>') == ["555"]

    def test_empty_page_has_no_jobs(self):
        assert ids("<html><body>Nenhuma vaga encontrada</body></html>") == []

    def test_card_text_includes_the_company(self):
        [card] = SearchResultsParser().cards(search_page(("7", "Desenvolvedor Júnior", "BairesDev")))

        assert "BairesDev" in card.text

    def test_card_title_comes_from_the_link_aria_label(self):
        [card] = SearchResultsParser().cards(search_page(("7", "Desenvolvedor Python Sênior", "Empresa X")))

        assert card.title == "Desenvolvedor Python Sênior"

    def test_card_title_is_unknown_without_aria_label(self):
        html = '<ul><li><a href="/jobs/view/9/">Vaga</a><span>Empresa</span></li></ul>'

        [card] = SearchResultsParser().cards(html)

        assert card.title is None
        assert card.text == "Vaga Empresa"
