from job_applier.linkedin.search_results_parser import SearchResultsParser
from tests.linkedin.pages import search_page


class TestSearchResultsParser:
    def test_lists_job_ids_in_page_order_without_repetition(self):
        assert SearchResultsParser().job_ids(search_page("30", "10", "20")) == ["30", "10", "20"]

    def test_finds_ids_from_job_links(self):
        html = '<a href="https://www.linkedin.com/jobs/view/555/?trk=x">Vaga</a>'

        assert SearchResultsParser().job_ids(html) == ["555"]

    def test_empty_page_has_no_jobs(self):
        assert SearchResultsParser().job_ids("<html><body>Nenhuma vaga encontrada</body></html>") == []
