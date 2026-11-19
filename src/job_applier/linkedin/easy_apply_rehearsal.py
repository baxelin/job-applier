import logging
from typing import Any

from job_applier.linkedin.easy_apply_form import ApplicationForm
from job_applier.linkedin.easy_apply_run import EasyApplyRun
from job_applier.linkedin.rehearsal_evidence import RehearsalEvidence
from job_applier.models.job_application import JobApplication

logger = logging.getLogger(__name__)


class EasyApplyRehearsal(EasyApplyRun):
    """Modo de ensaio: preenche o formulário de cada vaga simplificada e descarta antes de enviar.

    Cada vaga deixa prints e um respostas.txt em data/ensaios. Por padrão só entram vagas nunca tentadas;
    com retry_pending, as pendentes de pergunta e as com erro voltam para a fila depois das novas.
    """

    _SNAPSHOT_PREFIX = "ensaio"

    def __init__(self, *args: Any, retry_pending: bool = False, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._retry_pending = retry_pending

    @property
    def finished_label(self) -> str:
        return "prontas para envio"

    def _jobs(self) -> list[JobApplication]:
        return self._applications.list_ready_for_easy_apply(self._max_jobs, self._retry_pending)

    def _finish(self, form: ApplicationForm, application: JobApplication, evidence: RehearsalEvidence) -> None:
        self._discard(form, self._job_id(application))
        self._tracker.record_rehearsal_ready(application, f"Ensaio em {evidence.folder.name}")
        evidence.record_result("pronta para enviar (nada foi enviado)")
        self._count_success(self.finished_label)
        logger.info("Resultado: pronta para enviar, nada foi enviado (%s)", evidence.folder.name)

    def _completion_message(self) -> str:
        return "Ensaio concluído, nada foi enviado."
