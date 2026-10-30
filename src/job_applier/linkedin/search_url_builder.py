from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from job_applier.models.automation_settings import ExperienceLevel, JobFilters, SearchQuery, WorkplaceType


class LinkedInSearchUrlBuilder:
    """Monta a URL da busca de vagas do LinkedIn a partir das buscas e filtros do config.json."""

    RESULTS_PER_PAGE = 25
    _BASE_URL = "https://www.linkedin.com/jobs/search/"
    _EXPERIENCE_CODES = {
        ExperienceLevel.INTERNSHIP: "1",
        ExperienceLevel.ENTRY_LEVEL: "2",
        ExperienceLevel.ASSOCIATE: "3",
        ExperienceLevel.MID_SENIOR: "4",
        ExperienceLevel.DIRECTOR: "5",
        ExperienceLevel.EXECUTIVE: "6",
    }
    _WORKPLACE_CODES = {WorkplaceType.ON_SITE: "1", WorkplaceType.REMOTE: "2", WorkplaceType.HYBRID: "3"}

    def __init__(self, filters: JobFilters) -> None:
        self._filters = filters

    def build(self, search: SearchQuery, page: int = 0) -> str:
        if search.url:
            return self._with_page(str(search.url), page)

        workplace_types = search.workplace_types or self._filters.workplace_types
        parameters = {
            "keywords": search.keywords,
            "location": search.location,
            "f_E": self._codes(self._EXPERIENCE_CODES, self._filters.experience_levels),
            "f_WT": self._codes(self._WORKPLACE_CODES, workplace_types),
            "sortBy": "DD",
        }
        if self._filters.posted_within_hours:
            parameters["f_TPR"] = f"r{self._filters.posted_within_hours * 3600}"
        return self._with_page(f"{self._BASE_URL}?{urlencode(parameters)}", page)

    def _with_page(self, url: str, page: int) -> str:
        parts = urlsplit(url)
        parameters = [(key, value) for key, value in parse_qsl(parts.query) if key != "start"]
        if page:
            parameters.append(("start", str(page * self.RESULTS_PER_PAGE)))
        return urlunsplit(parts._replace(query=urlencode(parameters)))

    @staticmethod
    def _codes(codes: dict, values: list) -> str:
        return ",".join(sorted(codes[value] for value in values))
