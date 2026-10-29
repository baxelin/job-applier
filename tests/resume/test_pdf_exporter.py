import pytest

from job_applier.resume.pdf_exporter import PdfExporter


@pytest.mark.skipif(
    not PdfExporter.is_available(),
    reason="WeasyPrint sem as bibliotecas do Pango neste ambiente (roda no Docker e no CI)",
)
class TestPdfExporter:
    def test_exports_html_to_pdf(self):
        pdf = PdfExporter().export("<html><body><h1>Teste</h1></body></html>")

        assert pdf.startswith(b"%PDF")
