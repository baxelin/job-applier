import pytest

from job_applier.resume.resume_upload_file import ResumeUploadFileLoader
from tests.storage.conftest import application


@pytest.fixture
def loader(example_base_data, tmp_path) -> ResumeUploadFileLoader:
    pdf = tmp_path / "data" / "cvs" / "2026-10-29_Empresa-X_Dev-Junior.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-fake")
    return ResumeUploadFileLoader(tmp_path, example_base_data.resume.contact)


class TestResumeUploadFileLoader:
    def test_reads_the_pdf_of_the_job_with_the_neutral_name(self, loader):
        upload = loader.load(application(locale="pt"))

        assert upload.name.startswith("Curriculo_")
        assert "Empresa" not in upload.name
        assert upload.content == b"%PDF-fake"

    def test_name_follows_the_language_of_the_job(self, loader):
        assert loader.load(application(locale="en")).name.startswith("Resume_")

    def test_job_without_resume_is_an_error(self, loader):
        with pytest.raises(FileNotFoundError):
            loader.load(application(resume_path=None))
