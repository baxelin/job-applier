from job_applier.models.base import Locale
from job_applier.models.resume import Period


class ResumeLabels:
    """Títulos, rótulos e datas do CV no idioma escolhido."""

    _LABELS = {
        Locale.PT: {
            "location": "Localização",
            "phone": "Telefone",
            "email": "E-mail",
            "website": "Portfólio",
            "summary": "RESUMO",
            "education": "EDUCAÇÃO",
            "experience": "EXPERIÊNCIAS",
            "projects": "PROJETOS",
            "additional": "INFORMAÇÕES ADICIONAIS",
            "skills": "Habilidades Técnicas",
            "languages": "Idiomas",
            "certifications": "Cursos e Certificações",
            "in_progress": "em andamento",
        },
        Locale.EN: {
            "location": "Location",
            "phone": "Phone",
            "email": "Email",
            "website": "Portfolio",
            "summary": "SUMMARY",
            "education": "EDUCATION",
            "experience": "EXPERIENCE",
            "projects": "PROJECTS",
            "additional": "ADDITIONAL INFORMATION",
            "skills": "Technical Skills",
            "languages": "Languages",
            "certifications": "Courses and Certifications",
            "in_progress": "in progress",
        },
    }
    _MONTHS = {
        Locale.PT: ("Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"),
        Locale.EN: ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
    }
    _PRESENT = {Locale.PT: "Atual", Locale.EN: "Present"}

    def __init__(self, locale: Locale) -> None:
        self._locale = locale

    def __getitem__(self, key: str) -> str:
        return self._LABELS[self._locale][key]

    def period(self, period: Period) -> str:
        end = self._year_month(period.end) if period.end else self._PRESENT[self._locale]
        return f"{self._year_month(period.start)} - {end}"

    def _year_month(self, value: str) -> str:
        year, month = value.split("-")
        return f"{self._MONTHS[self._locale][int(month) - 1]} {year}"
