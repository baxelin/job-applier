import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag


@dataclass(frozen=True)
class JobCard:
    """Vaga como aparece na lista de resultados, antes de abrir a página dela."""

    linkedin_id: str
    text: str
    title: str | None = None


class SearchResultsParser:
    """Extrai, em ordem e sem repetição, os cards de vaga de uma página de busca do LinkedIn.

    O texto do card (título, empresa, local...) permite descartar vagas sem abri-las. O título só é
    preenchido quando identificado com segurança (aria-label do link da vaga).
    """

    _ID_ATTRIBUTES = ("data-occludable-job-id", "data-job-id")
    _JOB_LINK = re.compile(r"/jobs/view/(\d+)")

    def cards(self, html: str) -> list[JobCard]:
        soup = BeautifulSoup(html, "html.parser")
        cards: dict[str, JobCard] = {}
        for element in soup.select(", ".join(f"[{attribute}]" for attribute in self._ID_ATTRIBUTES)):
            job_id = next((str(element[name]) for name in self._ID_ATTRIBUTES if str(element.get(name, "")).isdigit()), None)
            if job_id and job_id not in cards:
                cards[job_id] = self._card(job_id, element)
        for link in soup.find_all("a", href=self._JOB_LINK):
            job_id = self._JOB_LINK.search(str(link["href"])).group(1)
            if job_id not in cards:
                cards[job_id] = self._card(job_id, link.find_parent("li") or link)
        return list(cards.values())

    def _card(self, job_id: str, element: Tag) -> JobCard:
        link = element if element.name == "a" else element.find("a", href=self._JOB_LINK)
        title = str(link.get("aria-label", "")).strip() if isinstance(link, Tag) else ""
        return JobCard(linkedin_id=job_id, text=" ".join(element.get_text(" ").split()), title=title or None)
