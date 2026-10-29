import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from job_applier.config.base_data_loader import BaseDataLoader
from job_applier.config.job_file_reader import JobFileReader
from job_applier.config.json_model_loader import DataFileError
from job_applier.models.base_data import BaseData
from job_applier.resume.pdf_exporter import PdfExportError
from job_applier.resume.resume_generator import GeneratedResume, ResumeGenerator


class GenerateResumesCommand:
    """Gera um CV adaptado para cada vaga (.txt) informada e mostra a análise de cada uma."""

    def __init__(
        self,
        base_data_loader: BaseDataLoader,
        generator_factory: Callable[[BaseData], ResumeGenerator],
        job_reader: JobFileReader | None = None,
    ) -> None:
        self._base_data_loader = base_data_loader
        self._generator_factory = generator_factory
        self._job_reader = job_reader or JobFileReader()

    def run(self, paths: Sequence[Path]) -> int:
        try:
            generator = self._generator_factory(self._base_data_loader.load())
            jobs = [job for path in paths for job in self._job_reader.read_all(path)]
            for job in jobs:
                print(self._report(generator.generate(job)))
        except (DataFileError, PdfExportError) as error:
            print(f"Erro ao gerar CVs. {error}", file=sys.stderr)
            return 1
        return 0

    @staticmethod
    def _report(generated: GeneratedResume) -> str:
        focus = " + ".join(sorted(generated.analysis.focus))
        warning = "  ⚠ Parece vaga de SUPORTE (fora do alvo)" if generated.analysis.is_support_role else None
        lines = [
            f"[{generated.job.company}] {generated.job.title}",
            warning,
            f"  Idioma: {generated.analysis.locale} | Foco: {focus} | Aderência: {generated.fit.percentage}%",
            f"  Tem: {', '.join(generated.fit.matched_terms) or '-'}",
            f"  Falta: {', '.join(generated.fit.missing_terms) or '-'}",
            f"  CV: {generated.path}",
        ]
        return "\n".join(line for line in lines if line)
