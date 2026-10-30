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
    preenchido quando identificado com segurança: aria-label do link da vaga (layout antigo) ou do
    botão "Fechar vaga de <título>" (layout de 2026, em que o card é um componentkey com o id).
    """

    _ID_SOURCES = (
        ("componentkey", re.compile(r"^job-card-component-ref-(\d+)$")),
        ("data-occludable-job-id", re.compile(r"^(\d+)$")),
        ("data-job-id", re.compile(r"^(\d+)$")),
    )
    _JOB_LINK = re.compile(r"/jobs/view/(\d+)")
    _DISMISS_LABEL = re.compile(r"^Fechar vaga de\s+(.+)$")

    def cards(self, html: str) -> list[JobCard]:
        soup = BeautifulSoup(html, "html.parser")
        cards: dict[str, JobCard] = {}
        for element in soup.find_all(lambda tag: self._job_id(tag) is not None):
            job_id = self._job_id(element)
            if job_id not in cards:
                cards[job_id] = self._card(job_id, element)
        for link in soup.find_all("a", href=self._JOB_LINK):
            job_id = self._JOB_LINK.search(str(link["href"])).group(1)
            if job_id not in cards:
                cards[job_id] = self._card(job_id, link.find_parent("li") or link)
        return list(cards.values())

    @classmethod
    def _job_id(cls, element: Tag) -> str | None:
        for attribute, pattern in cls._ID_SOURCES:
            if match := pattern.match(str(element.get(attribute, ""))):
                return match.group(1)
        return None

    def _card(self, job_id: str, element: Tag) -> JobCard:
        return JobCard(linkedin_id=job_id, text=" ".join(element.get_text(" ").split()), title=self._title(element))

    def _title(self, element: Tag) -> str | None:
        link = element if element.name == "a" else element.find("a", href=self._JOB_LINK)
        if isinstance(link, Tag) and (label := str(link.get("aria-label", "")).strip()):
            return label
        dismiss = element.find(attrs={"aria-label": self._DISMISS_LABEL})
        return self._DISMISS_LABEL.match(str(dismiss["aria-label"])).group(1).strip() if dismiss else None
