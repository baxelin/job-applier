from datetime import date

from job_applier.models.job_description import JobDescription
from job_applier.resume.resume_archive import ResumeArchive

JOB = JobDescription(company="Empresa", title="Dev Júnior", text="...")
DAY = date(2026, 10, 29)


class TestResumeArchive:
    def test_saves_pdf_creating_the_directory(self, tmp_path):
        path = ResumeArchive(tmp_path / "cvs").save(b"%PDF-1", JOB, DAY)

        assert path == tmp_path / "cvs" / "2026-10-29_Empresa_Dev-Junior.pdf"
        assert path.read_bytes() == b"%PDF-1"

    def test_never_overwrites_previous_resumes(self, tmp_path):
        archive = ResumeArchive(tmp_path)

        paths = [archive.save(content, JOB, DAY) for content in (b"1", b"2", b"3")]

        assert [path.name for path in paths] == [
            "2026-10-29_Empresa_Dev-Junior.pdf",
            "2026-10-29_Empresa_Dev-Junior_2.pdf",
            "2026-10-29_Empresa_Dev-Junior_3.pdf",
        ]
        assert paths[0].read_bytes() == b"1"
