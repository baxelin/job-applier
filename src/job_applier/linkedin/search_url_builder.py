from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from job_applier.models.automation_settings import ExperienceLevel, JobFilters, SearchOrder, SearchQuery, WorkplaceType


class LinkedInSearchUrlBuilder:
    """Monta a URL da busca de vagas do LinkedIn a partir das buscas e filtros do config.json.

    Sem níveis de experiência no config, a busca não filtra por nível: muitas vagas júnior vêm sem nível
    ou com o nível errado no LinkedIn, e o título e a aderência já descartam o que não serve.
    """

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
    _ORDER_CODES = {SearchOrder.RELEVANCE: "R", SearchOrder.RECENT: "DD"}

    def __init__(self, filters: JobFilters) -> None:
        self._filters = filters

    def build(self, search: SearchQuery, page: int = 0, window_hours: int | None = None) -> str:
        """window_hours substitui filters.posted_within_hours (a janela desde a última busca completa)."""
        hours = window_hours or self._filters.posted_within_hours
        if search.url:
            url = str(search.url)
            return self._with_page(self._with_window(url, window_hours) if window_hours else url, page)

        workplace_types = search.workplace_types or self._filters.workplace_types
        parameters = {"keywords": search.keywords, "location": search.location}
        if self._filters.experience_levels:
            parameters["f_E"] = self._codes(self._EXPERIENCE_CODES, self._filters.experience_levels)
        parameters["f_WT"] = self._codes(self._WORKPLACE_CODES, workplace_types)
        parameters["sortBy"] = self._ORDER_CODES[self._filters.sort_by]
        if hours:
            parameters["f_TPR"] = self._window_code(hours)
        return self._with_page(f"{self._BASE_URL}?{urlencode(parameters)}", page)

    @staticmethod
    def _window_code(hours: int) -> str:
        return f"r{hours * 3600}"

    def _with_window(self, url: str, hours: int) -> str:
        parts = urlsplit(url)
        parameters = [(key, value) for key, value in parse_qsl(parts.query) if key != "f_TPR"]
        parameters.append(("f_TPR", self._window_code(hours)))
        return urlunsplit(parts._replace(query=urlencode(parameters)))

    def _with_page(self, url: str, page: int) -> str:
        parts = urlsplit(url)
        parameters = [(key, value) for key, value in parse_qsl(parts.query) if key != "start"]
        if page:
            parameters.append(("start", str(page * self.RESULTS_PER_PAGE)))
        return urlunsplit(parts._replace(query=urlencode(parameters)))

    @staticmethod
    def _codes(codes: dict, values: list) -> str:
        return ",".join(sorted(codes[value] for value in values))
