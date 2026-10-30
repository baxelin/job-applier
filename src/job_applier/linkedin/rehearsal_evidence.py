from pathlib import Path

from job_applier.linkedin.easy_apply_step_parser import EasyApplyStep
from job_applier.models.form_field import FormField
from job_applier.models.job_application import JobApplication


class RehearsalEvidence:
    """Pasta de um ensaio (data/ensaios): um print por tela e o respostas.txt com o que foi preenchido.

    O arquivo cresce a cada tela, então uma falha no meio do formulário não perde o que veio antes.
    """

    _ANSWERS_FILE = "respostas.txt"

    def __init__(self, folder: Path, application: JobApplication) -> None:
        self._folder = folder
        self._folder.mkdir(parents=True, exist_ok=True)
        self._write(
            f"Vaga: {application.company} - {application.title}\n"
            f"Link: {application.url}\n"
            f"CV do histórico: {application.resume_path}\n"
            f"Aderência: {application.fit_percentage}%\n"
        )

    @property
    def folder(self) -> Path:
        return self._folder

    def screenshot_path(self, screen: int) -> Path:
        return self._folder / f"tela-{screen:02d}.png"

    def record_screen(self, screen: int, step: EasyApplyStep) -> None:
        pages = f" (página {step.page} de {step.total_pages})" if step.page else ""
        self._write(f"\n[Tela {screen}{pages}]\n")

    def record_answer(self, field: FormField, answer: str) -> None:
        self._write(f"{field.question}: {answer}\n")

    def record_kept(self, field: FormField) -> None:
        self._write(f"{field.question}: {field.current_answer()} (já estava preenchido)\n")

    def record_unknown(self, field: FormField) -> None:
        options = f" Opções: {', '.join(option.label for option in field.options)}." if field.options else ""
        self._write(f"{field.question}: SEM RESPOSTA ({field.kind}).{options}\n")

    def record_resume(self, name: str) -> None:
        self._write(f"Currículo carregado: {name}\n")

    def record_result(self, result: str) -> None:
        self._write(f"\nResultado: {result}\n")

    def _write(self, text: str) -> None:
        with (self._folder / self._ANSWERS_FILE).open("a", encoding="utf-8") as answers:
            answers.write(text)
