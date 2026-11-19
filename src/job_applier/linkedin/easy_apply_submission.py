import logging
from collections.abc import Callable
from datetime import date
from typing import Any

from job_applier.linkedin.easy_apply_form import ApplicationForm, EasyApplyFormError, EasyApplySubmissionUnconfirmedError
from job_applier.linkedin.easy_apply_run import EasyApplyRun
from job_applier.linkedin.rehearsal_evidence import RehearsalEvidence
from job_applier.linkedin.run_stop import StopRun
from job_applier.models.job_application import JobApplication, ScanStatus

logger = logging.getLogger(__name__)


class EasyApplySubmission(EasyApplyRun):
    """Candidatura real: preenche o formulário como o ensaio e, na tela final, clica em "Enviar candidatura".

    Entram primeiro as vagas que já passaram no ensaio, depois as novas, por aderência. Com daily_limit, para
    ao atingir o limite diário de envios (contado pela data do envio); sem ele, envia a fila toda. Cada envio
    deixa prints, o respostas.txt e o print da confirmação em data/envios, e a página depois do envio fica
    em data/debug, para conferir o layout da confirmação. Se a confirmação não aparecer, a vaga fica com erro para ser
    conferida no site e a execução para: tentar de novo às cegas poderia enviar a mesma candidatura duas vezes.
    """

    _SNAPSHOT_PREFIX = "envio"

    def __init__(
        self,
        *args: Any,
        daily_limit: int | None = None,
        retry_pending: bool = False,
        today: Callable[[], date] = date.today,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._retry_pending = retry_pending
        self._daily_limit = daily_limit
        self._today = today
        self._sent_before_run: int | None = None

    @property
    def finished_label(self) -> str:
        return "enviadas"

    def _jobs(self) -> list[JobApplication]:
        jobs = self._applications.list_ready_for_submission(self._retry_pending)
        return jobs if self._max_jobs is None else jobs[: self._max_jobs]

    def _ensure_can_continue(self) -> None:
        if self._daily_limit is None:
            return
        if self._sent_before_run is None:
            self._sent_before_run = self._applications.count_applied_on(self._today())
        if self._sent_before_run + self._tally[self.finished_label] >= self._daily_limit:
            raise StopRun(f"Limite diário de envios atingido ({self._daily_limit}).", ScanStatus.COMPLETED)

    def _finish(self, form: ApplicationForm, application: JobApplication, evidence: RehearsalEvidence) -> None:
        job_id = self._job_id(application)
        try:
            form.submit(form.read_step())
        except EasyApplySubmissionUnconfirmedError as error:
            snapshot = self._browser.save_snapshot(f"{self._SNAPSHOT_PREFIX}-{job_id}")
            self._tracker.record_failure(application, f"{error} Página salva em {snapshot}.")
            evidence.record_result(f"envio não confirmado: {error}")
            raise StopRun(f"{application.company} - {application.title}: {error} Página salva em {snapshot}.")
        except EasyApplyFormError as error:
            form.close_without_sending()
            self._tracker.record_failure(application, str(error))
            evidence.record_result(f"erro ao enviar: {error}")
            self._count_failure(self.FAILED, evidence.folder)
            return

        self._tracker.record_applied(application, f"Enviada; evidências em {evidence.folder.name}")
        evidence.record_result("candidatura enviada")
        self._count_success(self.finished_label)
        logger.info("Candidatura enviada: %s - %s", application.company, application.title)
        self._keep_confirmation(form, evidence, job_id)
        form.close_after_sending()

    def _keep_confirmation(self, form: ApplicationForm, evidence: RehearsalEvidence, job_id: str) -> None:
        """A candidatura já está registrada: um print que falha não pode interromper a execução."""
        try:
            form.save_screenshot(evidence.folder / "confirmacao.png")
            self._browser.save_snapshot(f"{self._SNAPSHOT_PREFIX}-{job_id}")
        except Exception as error:
            logger.warning("Não consegui guardar a confirmação do envio: %r", error)

    def _completion_message(self) -> str:
        return "Fila de envio percorrida."
