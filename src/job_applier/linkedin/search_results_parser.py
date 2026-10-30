import re

from bs4 import BeautifulSoup


class SearchResultsParser:
    """Extrai, em ordem e sem repetição, os ids das vagas listadas numa página de busca do LinkedIn."""

    _ID_ATTRIBUTES = ("data-job-id", "data-occludable-job-id")
    _JOB_LINK = re.compile(r"/jobs/view/(\d+)")

    def job_ids(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        ids: dict[str, None] = {}
        for element in soup.select(", ".join(f"[{attribute}]" for attribute in self._ID_ATTRIBUTES)):
            for attribute in self._ID_ATTRIBUTES:
                value = str(element.get(attribute, ""))
                if value.isdigit():
                    ids[value] = None
        for link in soup.find_all("a", href=self._JOB_LINK):
            ids[self._JOB_LINK.search(str(link["href"])).group(1)] = None
        return list(ids)
