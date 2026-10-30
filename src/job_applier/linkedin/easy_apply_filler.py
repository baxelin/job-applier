from dataclasses import dataclass
from enum import Enum, auto

from job_applier.answering.form_answerer import FormAnswerer
from job_applier.linkedin.easy_apply_form import ApplicationForm, EasyApplyFormError
from job_applier.linkedin.easy_apply_step_parser import EasyApplyStep, StepAction
from job_applier.linkedin.pacer import Pacer
from job_applier.linkedin.rehearsal_evidence import RehearsalEvidence
from job_applier.linkedin.session_guard import SessionGuard
from job_applier.models.form_field import FieldAnswer, FormField
from job_applier.models.job_application import JobApplication
from job_applier.resume.resume_upload_file import ResumeUploadFile


class FillStatus(Enum):
    READY_TO_SUBMIT = auto()
    UNKNOWN_QUESTIONS = auto()
    FAILED = auto()


@dataclass(frozen=True)
class FillOutcome:
    status: FillStatus
    questions: tuple[str, ...] = ()
    detail: str | None = None


class _StopFilling(Exception):
    def __init__(self, outcome: FillOutcome) -> None:
        super().__init__(outcome.detail)
        self.outcome = outcome


class EasyApplyFiller:
    """Percorre o formulário de uma vaga, tela a tela, até a tela que tem o botão de enviar.

    Só responde campos obrigatórios vazios: o que veio preenchido do perfil e os campos opcionais ficam
    como estão. Se uma tela tiver pergunta sem resposta, nada dela é preenchido e todas as perguntas
    dessa tela são devolvidas, para o usuário responder de uma vez. Cada tela confere se o que foi
    preenchido ficou no campo, e a última confere se o CV carregado é o que vai junto.
    """

    _MAX_SCREENS = 20

    def __init__(self, answerer: FormAnswerer, pacer: Pacer, guard: SessionGuard | None = None) -> None:
        self._answerer = answerer
        self._pacer = pacer
        self._guard = guard or SessionGuard()

    def fill(
        self,
        form: ApplicationForm,
        application: JobApplication,
        resume: ResumeUploadFile,
        evidence: RehearsalEvidence,
    ) -> FillOutcome:
        try:
            self._walk(form, application, resume, evidence)
        except _StopFilling as stop:
            return stop.outcome
        except EasyApplyFormError as error:
            return FillOutcome(FillStatus.FAILED, detail=str(error))
        return FillOutcome(FillStatus.READY_TO_SUBMIT)

    def _walk(
        self,
        form: ApplicationForm,
        application: JobApplication,
        resume: ResumeUploadFile,
        evidence: RehearsalEvidence,
    ) -> None:
        resume_uploaded = False
        for screen in range(1, self._MAX_SCREENS + 1):
            self._guard.check(form.page_snapshot())
            step = form.read_step()
            evidence.record_screen(screen, step)
            self._answer_fields(form, step, application, evidence, screen)
            resume_uploaded = self._upload_resume(form, step, resume, evidence) or resume_uploaded
            step = self._verified_step(form)
            form.save_screenshot(evidence.screenshot_path(screen))
            if step.action is StepAction.SUBMIT_REACHED:
                self._ensure_resume_is_attached(step, resume, resume_uploaded)
                return
            self._advance(form, step)
        raise self._failure(f"O formulário passou de {self._MAX_SCREENS} telas.")

    def _answer_fields(
        self,
        form: ApplicationForm,
        step: EasyApplyStep,
        application: JobApplication,
        evidence: RehearsalEvidence,
        screen: int,
    ) -> None:
        for field in step.fields:
            if field.required and not field.is_empty():
                evidence.record_kept(field)
        to_answer = step.fields_to_answer()
        answers = [(field, self._answerer.answer(field, application)) for field in to_answer]
        self._stop_on_unknown_questions(form, answers, evidence, screen)
        for field, answer in answers:
            form.fill(field, answer)
            evidence.record_answer(field, answer.text)

    @staticmethod
    def _stop_on_unknown_questions(
        form: ApplicationForm,
        answers: list[tuple[FormField, FieldAnswer | None]],
        evidence: RehearsalEvidence,
        screen: int,
    ) -> None:
        unknown = [field for field, answer in answers if answer is None]
        if not unknown:
            return
        for field in unknown:
            evidence.record_unknown(field)
        form.save_screenshot(evidence.screenshot_path(screen))
        questions = tuple(field.question for field in unknown)
        raise _StopFilling(FillOutcome(FillStatus.UNKNOWN_QUESTIONS, questions=questions))

    def _upload_resume(
        self, form: ApplicationForm, step: EasyApplyStep, resume: ResumeUploadFile, evidence: RehearsalEvidence
    ) -> bool:
        if step.upload_label is None:
            if step.offers_resume_choice:
                raise self._failure("A tela pede um currículo, mas não encontrei o botão de carregar.")
            return False
        form.upload_resume(step, resume)
        evidence.record_resume(resume.name)
        return True

    def _verified_step(self, form: ApplicationForm) -> EasyApplyStep:
        step = form.read_step()
        if missing := step.fields_to_answer():
            questions = ", ".join(field.question for field in missing)
            raise self._failure(f"Os campos continuaram vazios depois de preenchidos: {questions}.")
        return step

    def _ensure_resume_is_attached(self, step: EasyApplyStep, resume: ResumeUploadFile, uploaded: bool) -> None:
        if uploaded and resume.name not in step.text:
            raise self._failure(f"A tela final não mostra o currículo {resume.name}.")

    def _advance(self, form: ApplicationForm, step: EasyApplyStep) -> None:
        if step.action is not StepAction.ADVANCE:
            raise self._failure("A tela não tem nenhum botão conhecido para avançar.")
        self._pacer.between_actions()
        if form.advance(step) is None:
            errors = "; ".join(form.read_step().errors) or "sem mensagem de erro na tela"
            raise self._failure(f"A tela {step.page} não avançou ({errors}).")

    @staticmethod
    def _failure(detail: str) -> _StopFilling:
        return _StopFilling(FillOutcome(FillStatus.FAILED, detail=detail))
