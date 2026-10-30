from pathlib import Path

from job_applier.linkedin.easy_apply_form import ApplicationForm, EasyApplyFormError
from job_applier.linkedin.easy_apply_step_parser import EasyApplyStep, EasyApplyStepParser
from job_applier.linkedin.page_snapshot import PageSnapshot
from job_applier.models.form_field import FieldAnswer, FormField
from job_applier.resume.resume_upload_file import ResumeUploadFile


class FakeApplicationForm(ApplicationForm):
    """Formulário em memória: telas em HTML, com o que for preenchido refletido no campo."""

    def __init__(
        self,
        screens: list[str],
        url: str = "https://www.linkedin.com/jobs/view/1/",
        stuck_on: int | None = None,
        ignores_answers: bool = False,
        errors_on_upload: bool = False,
    ) -> None:
        self._screens = screens
        self._url = url
        self._stuck_on = stuck_on
        self._ignores_answers = ignores_answers
        self._errors_on_upload = errors_on_upload
        self._current = 0
        self._parser = EasyApplyStepParser()
        self.filled: list[tuple[str, str]] = []
        self.uploaded: list[str] = []
        self.screenshots: list[Path] = []
        self.closed = False

    def read_step(self) -> EasyApplyStep:
        step = self._parser.parse(self._screens[self._current])
        filled = dict(self.filled)
        return EasyApplyStep(
            page=step.page,
            total_pages=step.total_pages,
            fields=tuple(self._with_filled_value(field, filled) for field in step.fields),
            action=step.action,
            action_label=step.action_label,
            upload_label=step.upload_label,
            resumes=step.resumes,
            errors=step.errors,
            text=step.text,
        )

    def _with_filled_value(self, field: FormField, filled: dict[str, str]) -> FormField:
        if self._ignores_answers or field.question not in filled:
            return field
        return field.model_copy(update={"value": filled[field.question]})

    def fill(self, field: FormField, answer: FieldAnswer) -> None:
        self.filled.append((field.question, answer.text))

    def upload_resume(self, step: EasyApplyStep, resume: ResumeUploadFile) -> None:
        if self._errors_on_upload:
            raise EasyApplyFormError("Não consegui carregar o currículo.")
        self.uploaded.append(resume.name)

    def advance(self, step: EasyApplyStep) -> EasyApplyStep | None:
        if self._current == self._stuck_on:
            return None
        self._current += 1
        return self.read_step()

    def close_without_sending(self) -> None:
        self.closed = True

    def save_screenshot(self, path: Path) -> None:
        self.screenshots.append(path)

    def page_snapshot(self) -> PageSnapshot:
        return PageSnapshot(url=self._url, html="", text="Formulário " * 1000)
