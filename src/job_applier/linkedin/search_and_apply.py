from job_applier.linkedin.easy_apply_submission import EasyApplySubmission
from job_applier.linkedin.job_scanner import JobScanner, ScanResult


class SearchAndApply:
    """Busca e candidatura na mesma execução: cada vaga simplificada recebe o envio logo depois do CV.

    O scanner já vem ligado ao envio (on_easy_apply_resume=submission.apply_to), no mesmo navegador. Vagas
    externas, ignoradas e as que ficam pendentes de pergunta seguem como na busca e no envio separados.
    Um envio sem confirmação, um bloqueio do LinkedIn ou falhas seguidas encerram tudo.
    """

    def __init__(self, scanner: JobScanner, submission: EasyApplySubmission) -> None:
        self._scanner = scanner
        self._submission = submission

    def run(self) -> ScanResult:
        result = self._scanner.run()
        return ScanResult(
            status=result.status,
            reason=f"{result.reason} Candidaturas: {self._submission.summary()}.",
            jobs_seen=result.jobs_seen,
            jobs_recorded=result.jobs_recorded,
        )
