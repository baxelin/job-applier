from datetime import date

from job_applier.models.job_description import JobDescription
from job_applier.resume.resume_archive import ResumeArchive
from job_applier.resume.resume_generator import ResumeGenerator


class FakePdfExporter:
    def __init__(self) -> None:
        self.exported_html: list[str] = []

    def export(self, html: str) -> bytes:
        self.exported_html.append(html)
        return b"%PDF-fake"


class TestResumeGenerator:
    def test_generates_and_archives_tailored_resume(self, example_base_data, tmp_path):
        exporter = FakePdfExporter()
        generator = ResumeGenerator(
            example_base_data, ResumeArchive(tmp_path), exporter=exporter, today=lambda: date(2026, 10, 29)
        )
        job = JobDescription(
            company="Empresa X",
            title="Desenvolvedor Python Júnior",
            text="Buscamos pessoa desenvolvedora com Python, Docker e Kubernetes para o nosso time.",
        )

        generated = generator.generate(job)

        assert generated.path.name == "2026-10-29_Empresa-X_Desenvolvedor-Python-Junior.pdf"
        assert generated.path.read_bytes() == b"%PDF-fake"
        assert "Kubernetes" in generated.fit.missing_terms
        assert "MARIA EXEMPLO" in exporter.exported_html[0]
