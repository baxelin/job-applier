import re
from collections.abc import Sequence
from datetime import date

from bs4 import BeautifulSoup, Tag

from job_applier.linkedin.posting_text_parser import PostingTextParser
from job_applier.matching.text_normalizer import TextNormalizer
from job_applier.models.job_description import JobDescription
from job_applier.models.job_posting import ApplyType, JobPosting


class JobExtractionError(Exception):
    """A página da vaga não tinha os dados obrigatórios; normalmente o LinkedIn mudou o layout."""

    def __init__(self, linkedin_id: str, missing_fields: Sequence[str]) -> None:
        super().__init__(f"Vaga {linkedin_id}: não encontrei {', '.join(missing_fields)} na página.")
        self.linkedin_id = linkedin_id


class JobPageParser:
    """Lê a página de uma vaga do LinkedIn e monta um JobPosting.

    O layout atual (2026) usa classes CSS embaralhadas que mudam a cada versão do site, então a
    leitura se apoia em âncoras estáveis: o <title> da página, os aria-labels e os componentkey
    com o id da vaga. Os seletores do layout antigo e da página de visitante ficam como alternativa.
    Quando o LinkedIn mudar o layout, basta acrescentar o novo seletor no início da lista do campo.
    """

    _TITLE = (
        ".job-details-jobs-unified-top-card__job-title h1",
        ".job-details-jobs-unified-top-card__job-title",
        ".jobs-unified-top-card__job-title",
        ".top-card-layout__title",
        "h1",
    )
    _COMPANY = (
        ".job-details-jobs-unified-top-card__company-name a",
        ".job-details-jobs-unified-top-card__company-name",
        ".jobs-unified-top-card__company-name",
        ".topcard__org-name-link",
    )
    _DESCRIPTION = (
        "[componentkey^='JobDetails_AboutTheJob_'] [data-testid='expandable-text-box']",
        "#job-details",
        ".jobs-description__content",
        ".jobs-description-content__text",
        ".show-more-less-html__markup",
        "[class*='jobs-description']",
    )
    _TOP_CARD = (
        ".job-details-jobs-unified-top-card__tertiary-description-container",
        ".job-details-jobs-unified-top-card__primary-description-container",
        ".jobs-unified-top-card__primary-description",
        ".topcard__flavor-row",
    )
    _COMPANY_LABEL = re.compile(r"^(?:Empresa|Company)\s+(.+?)\.?$")
    _NOTIFICATION_COUNT = re.compile(r"^\(\d+\)\s*")
    _SIMILAR_JOBS = re.compile(r"SimilarJobs")
    _EXPAND_BUTTONS = "[data-testid='expandable-text-button']"
    _EXPAND_LEFTOVERS = frozenset({"…", "...", "mais", "exibir mais", "see more", "show more", "… mais"})
    _APPLY_CONTROLS = (".jobs-apply-button", "button[aria-label]", "a[aria-label]", "button", ".apply-button")
    _EASY_APPLY_SIGNS = ("candidatura simplificada", "easy apply")
    _APPLY_SIGNS = ("candidatar-se", "candidatar", "apply")
    _CLOSED_SIGNS = ("nao aceita mais candidaturas", "no longer accepting applications")
    _SEPARATOR = re.compile(r"\s*[·•]\s*")
    _BLOCK_TAGS = ("p", "div", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "section")

    def __init__(self, text_parser: PostingTextParser | None = None) -> None:
        self._text_parser = text_parser or PostingTextParser()

    def parse(self, html: str, linkedin_id: str, today: date) -> JobPosting:
        soup = BeautifulSoup(html, "html.parser")
        document_title, document_company = self._from_document_title(soup)
        title = self._first_text(soup, self._TITLE) or document_title
        company = self._company_from_label(soup) or self._first_text(soup, self._COMPANY) or document_company
        description = self._description(soup)

        required = {"título": title, "empresa": company, "descrição": description}
        if missing := [name for name, value in required.items() if not value]:
            raise JobExtractionError(linkedin_id, missing)

        top_card = self._top_card(soup)
        return JobPosting(
            linkedin_id=linkedin_id,
            description=JobDescription(
                company=company,
                title=title,
                text=description,
                location=self._location(top_card),
                url=JobPosting.url_for(linkedin_id),
            ),
            apply_type=self._apply_type(soup),
            applicants=self._text_parser.applicants(top_card),
            posted_on=self._text_parser.posted_on(top_card, today),
        )

    def _from_document_title(self, soup: BeautifulSoup) -> tuple[str | None, str | None]:
        """O <title> da página tem o formato "Título da vaga | Empresa | LinkedIn"."""
        document_title = soup.title.get_text(" ", strip=True) if soup.title else ""
        parts = self._NOTIFICATION_COUNT.sub("", document_title).split(" | ")
        if len(parts) < 3 or parts[-1] != "LinkedIn":
            return None, None
        return " | ".join(parts[:-2]), parts[-2]

    def _company_from_label(self, soup: BeautifulSoup) -> str | None:
        element = soup.find(attrs={"aria-label": self._COMPANY_LABEL})
        return self._COMPANY_LABEL.match(str(element["aria-label"])).group(1) if element else None

    def _description(self, soup: BeautifulSoup) -> str | None:
        for button in soup.select(self._EXPAND_BUTTONS):
            button.decompose()
        description = self._first_text(soup, self._DESCRIPTION, keep_lines=True)
        if not description:
            return None
        lines = description.splitlines()
        while lines and lines[-1].casefold() in self._EXPAND_LEFTOVERS:
            lines.pop()
        return "\n".join(lines) or None

    def _top_card(self, soup: BeautifulSoup) -> str:
        """Linha "Local · há N dias · N candidatos": a primeira com "·" fora do bloco de vagas semelhantes."""
        if text := self._first_text(soup, self._TOP_CARD):
            return text
        for paragraph in soup.find_all("p"):
            text = " ".join(paragraph.get_text(" ").split())
            if "·" in text and not paragraph.find_parent(attrs={"componentkey": self._SIMILAR_JOBS}):
                return text
        return ""

    @classmethod
    def _first_text(cls, soup: BeautifulSoup, selectors: Sequence[str], keep_lines: bool = False) -> str | None:
        for selector in selectors:
            element = soup.select_one(selector)
            if isinstance(element, Tag) and (text := cls._text_of(element, keep_lines)):
                return text
        return None

    @classmethod
    def _text_of(cls, element: Tag, keep_lines: bool) -> str:
        if not keep_lines:
            return " ".join(element.get_text(" ").split())
        for line_break in element.find_all("br"):
            line_break.replace_with("\n")
        for block in element.find_all(cls._BLOCK_TAGS):
            block.insert_after("\n")
        lines = (" ".join(line.split()) for line in element.get_text().splitlines())
        return "\n".join(line for line in lines if line)

    def _location(self, top_card: str) -> str | None:
        first_part = self._SEPARATOR.split(top_card)[0].strip() if top_card else ""
        return first_part or None

    def _apply_type(self, soup: BeautifulSoup) -> ApplyType:
        page_text = TextNormalizer.normalize(soup.get_text(" "))
        if any(sign in page_text for sign in self._CLOSED_SIGNS):
            return ApplyType.CLOSED

        labels = [
            TextNormalizer.normalize(f"{control.get('aria-label', '')} {control.get_text(' ')}")
            for selector in self._APPLY_CONTROLS
            for control in soup.select(selector)
        ]
        if any(sign in label for label in labels for sign in self._EASY_APPLY_SIGNS):
            return ApplyType.EASY_APPLY
        if any(sign in label for label in labels for sign in self._APPLY_SIGNS):
            return ApplyType.EXTERNAL
        return ApplyType.UNKNOWN
