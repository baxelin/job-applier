from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import HttpUrl

from job_applier.resume.resume_labels import ResumeLabels
from job_applier.resume.tailored_resume import TailoredResume


class HtmlResumeRenderer:
    """Gera o HTML do CV a partir do template, no mesmo formato do currículo original."""

    TEMPLATES_DIR = Path(__file__).parent / "templates"

    def __init__(self) -> None:
        self._environment = Environment(
            loader=FileSystemLoader(self.TEMPLATES_DIR),
            autoescape=select_autoescape(["html"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, resume: TailoredResume) -> str:
        return self._environment.get_template("resume.html").render(
            resume=resume,
            labels=ResumeLabels(resume.locale),
            localize=lambda text: text.in_locale(resume.locale),
            display_url=self._display_url,
        )

    @staticmethod
    def _display_url(url: HttpUrl) -> str:
        return str(url).removeprefix("https://").removeprefix("http://").removeprefix("www.").rstrip("/")
