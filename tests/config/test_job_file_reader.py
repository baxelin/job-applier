import pytest

from job_applier.config.job_file_reader import JobFileReader
from job_applier.config.json_model_loader import DataFileNotFoundError, InvalidDataFileError

VALID_CONTENT = """Empresa: Empresa Exemplo
Vaga: Desenvolvedor Python Júnior
---
Buscamos pessoa desenvolvedora com Python e Docker.
"""


class TestJobFileReader:
    def test_reads_header_and_description(self, tmp_path):
        path = tmp_path / "vaga.txt"
        path.write_text(VALID_CONTENT, encoding="utf-8")

        job = JobFileReader().read(path)

        assert (job.company, job.title) == ("Empresa Exemplo", "Desenvolvedor Python Júnior")
        assert job.text == "Buscamos pessoa desenvolvedora com Python e Docker."

    def test_reads_optional_location_and_link(self, tmp_path):
        path = tmp_path / "vaga.txt"
        path.write_text(
            "Empresa: X\nVaga: Y\nLocal: São Paulo\nLink: https://www.linkedin.com/jobs/view/123/\n"
            "Seniority level: Entry level\n---\nPython",
            encoding="utf-8",
        )

        job = JobFileReader().read(path)

        assert job.location == "São Paulo"
        assert str(job.url) == "https://www.linkedin.com/jobs/view/123/"

    def test_ignores_utf8_bom_saved_by_notepad(self, tmp_path):
        path = tmp_path / "vaga.txt"
        path.write_text(VALID_CONTENT, encoding="utf-8-sig")

        assert JobFileReader().read(path).company == "Empresa Exemplo"

    def test_requires_separator_line(self, tmp_path):
        path = tmp_path / "vaga.txt"
        path.write_text("Empresa: X\nVaga: Y\nDescrição sem separador", encoding="utf-8")

        with pytest.raises(InvalidDataFileError, match="Falta a linha '---'"):
            JobFileReader().read(path)

    def test_requires_company_and_title(self, tmp_path):
        path = tmp_path / "vaga.txt"
        path.write_text("Vaga: Y\n---\nDescrição", encoding="utf-8")

        with pytest.raises(InvalidDataFileError, match="company"):
            JobFileReader().read(path)

    def test_reports_missing_file(self, tmp_path):
        with pytest.raises(DataFileNotFoundError):
            JobFileReader().read(tmp_path / "inexistente.txt")

    def test_reads_every_txt_file_of_a_directory_in_name_order(self, tmp_path):
        (tmp_path / "b.txt").write_text(VALID_CONTENT.replace("Empresa Exemplo", "B"), encoding="utf-8")
        (tmp_path / "a.txt").write_text(VALID_CONTENT.replace("Empresa Exemplo", "A"), encoding="utf-8")
        (tmp_path / "notas.md").write_text("ignorado", encoding="utf-8")

        jobs = JobFileReader().read_all(tmp_path)

        assert [job.company for job in jobs] == ["A", "B"]
