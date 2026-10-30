from urllib.parse import parse_qs, urlsplit

from job_applier.linkedin.search_url_builder import LinkedInSearchUrlBuilder
from job_applier.models.automation_settings import JobFilters, SearchQuery

FILTERS = JobFilters(
    experience_levels=["internship", "entry_level", "associate"],
    workplace_types=["remote", "hybrid", "on_site"],
    posted_within_hours=24,
)


def query(url: str) -> dict[str, list[str]]:
    return parse_qs(urlsplit(url).query)


class TestLinkedInSearchUrlBuilder:
    def test_builds_search_with_filters(self):
        url = LinkedInSearchUrlBuilder(FILTERS).build(SearchQuery(keywords="Desenvolvedor Júnior", location="Brasil"))

        assert url.startswith("https://www.linkedin.com/jobs/search/?")
        assert query(url) == {
            "keywords": ["Desenvolvedor Júnior"],
            "location": ["Brasil"],
            "f_E": ["1,2,3"],
            "f_WT": ["1,2,3"],
            "sortBy": ["DD"],
            "f_TPR": ["r86400"],
        }

    def test_search_workplace_types_override_the_global_filter(self):
        search = SearchQuery(keywords="Junior Developer", location="Worldwide", workplace_types=["remote"])

        assert query(LinkedInSearchUrlBuilder(FILTERS).build(search))["f_WT"] == ["2"]

    def test_pages_use_the_start_parameter(self):
        search = SearchQuery(keywords="Dev", location="Brasil")

        assert query(LinkedInSearchUrlBuilder(FILTERS).build(search, page=2))["start"] == ["50"]

    def test_custom_url_is_used_as_is_with_pagination(self):
        search = SearchQuery(
            keywords="ignorado", location="ignorado", url="https://www.linkedin.com/jobs/search/?geoId=1&start=99"
        )

        url = LinkedInSearchUrlBuilder(FILTERS).build(search, page=1)

        assert query(url) == {"geoId": ["1"], "start": ["25"]}
