from pathlib import Path

from job_applier.resume.html_resume_renderer import HtmlResumeRenderer


class PdfExportError(Exception):
    """Falha ao gerar o PDF; a mensagem é pensada para o usuário final."""


class PdfExporter:
    """Converte o HTML do CV em PDF com o WeasyPrint.

    O WeasyPrint depende de bibliotecas do sistema (Pango) que existem no Docker e no CI,
    mas normalmente não no Windows. Por isso a importação é feita só na hora de exportar.
    """

    def __init__(self, assets_dir: Path = HtmlResumeRenderer.TEMPLATES_DIR) -> None:
        self._assets_dir = assets_dir

    @staticmethod
    def is_available() -> bool:
        try:
            import weasyprint  # noqa: F401
        except (ImportError, OSError):
            return False
        return True

    def export(self, html: str) -> bytes:
        try:
            from weasyprint import HTML
        except (ImportError, OSError) as error:
            raise PdfExportError(
                "O WeasyPrint não está disponível neste ambiente (faltam as bibliotecas do Pango). "
                "Gere os CVs pelo Docker: docker compose run --rm app python -m job_applier cv <vagas>"
            ) from error
        return HTML(string=html, base_url=str(self._assets_dir)).write_pdf()
