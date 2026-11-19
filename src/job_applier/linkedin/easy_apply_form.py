import logging
import re
from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import FilePayload, Locator, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from job_applier.linkedin.easy_apply_step_parser import EasyApplyStep, EasyApplyStepParser, StepAction
from job_applier.linkedin.page_snapshot import PageSnapshot
from job_applier.matching.text_normalizer import TextNormalizer
from job_applier.models.form_field import FieldAnswer, FieldKind, FormField
from job_applier.resume.resume_upload_file import ResumeUploadFile

logger = logging.getLogger(__name__)


class EasyApplyUnavailableError(Exception):
    """A vaga não oferece mais a Candidatura Simplificada (encerrada, já aplicada ou layout novo)."""


class EasyApplyFormError(Exception):
    """O modal não se comportou como esperado; o preenchimento dessa vaga para aqui."""


class EasyApplySubmissionUnconfirmedError(EasyApplyFormError):
    """O botão de enviar foi clicado, mas a confirmação não apareceu: a vaga precisa ser conferida no site."""


class ApplicationForm(ABC):
    """O que o preenchimento precisa de um formulário de candidatura aberto.

    O formulário avança até a tela com o botão de enviar; só submit clica nele, e só nessa tela.
    """

    @abstractmethod
    def read_step(self) -> EasyApplyStep:
        """Lê a tela atual com os valores que estão nos campos agora."""

    @abstractmethod
    def fill(self, field: FormField, answer: FieldAnswer) -> None:
        """Preenche um campo com a resposta escolhida."""

    @abstractmethod
    def upload_resume(self, step: EasyApplyStep, resume: ResumeUploadFile) -> None:
        """Carrega o CV e confirma que ele ficou selecionado."""

    @abstractmethod
    def advance(self, step: EasyApplyStep) -> EasyApplyStep | None:
        """Vai para a próxima tela; devolve None se ela não mudar (normalmente erro de validação)."""

    @abstractmethod
    def submit(self, step: EasyApplyStep) -> None:
        """Clica em "Enviar candidatura" na tela final e espera a confirmação do LinkedIn.

        Lança EasyApplySubmissionUnconfirmedError se a confirmação não aparecer.
        """

    @abstractmethod
    def close_after_sending(self) -> None:
        """Fecha a janela de confirmação que aparece depois do envio, se ela existir."""

    @abstractmethod
    def close_without_sending(self) -> None:
        """Fecha o modal e descarta a candidatura."""

    @abstractmethod
    def save_screenshot(self, path: Path) -> None:
        """Salva um print da tela atual, com o formulário inteiro visível."""

    @abstractmethod
    def page_snapshot(self) -> PageSnapshot:
        """A página atual, para a verificação de captcha, logout ou bloqueio."""


class EasyApplyForm(ApplicationForm):
    """Controla pelo Playwright o modal <dialog> da Candidatura Simplificada.

    A página pode ter outros [role=dialog] (legendas de vídeo), por isso o seletor é o <dialog> aberto:
    o primeiro é o formulário, e o segundo, a confirmação de descarte.
    """

    _DIALOG = "dialog[open]"
    _LIVE_HTML_SCRIPT = """
        dialog => {
            const controls = 'input, select, textarea';
            const copy = dialog.cloneNode(true);
            const originals = dialog.querySelectorAll(controls);
            copy.querySelectorAll(controls).forEach((control, index) => {
                control.setAttribute('data-live-value', originals[index].value);
                control.setAttribute('data-live-checked', String(originals[index].checked));
            });
            return copy.outerHTML;
        }
    """
    _FORM_HEIGHT_SCRIPT = "dialog => Math.max(...[...dialog.querySelectorAll('*')].map(item => item.scrollHeight))"
    _CLOSE_BUTTON = re.compile(r"^(Fechar|Dismiss|Close)$")
    _AFTER_SENDING_BUTTON = re.compile(r"^(Concluído|Concluir|Done|Fechar|Dismiss|Close)$")
    _SENT_SIGNS = re.compile(
        r"candidatura (?:foi )?enviada|candidatou-se|application (?:was )?sent|applied \d+ \w+ ago"
    )
    _DISCARD_BUTTON = re.compile(r"^(Descartar|Discard)$")
    _PDF_MIME_TYPE = "application/pdf"
    _CHECK_INTERVAL_MS = 500
    _MAX_CHECKS = 20
    _ACTION_TIMEOUT_MS = 15_000
    _CONFIRMATION_TIMEOUT_MS = 5_000
    _SCREENSHOT_MARGIN_PX = 220
    _DIALOG_SHARE_OF_WINDOW = 0.75
    _SCREENSHOT_MAX_HEIGHT_PX = 8_000
    _SCREENSHOT_LAYOUT_WAIT_MS = 400

    def __init__(self, page: Page, parser: EasyApplyStepParser | None = None) -> None:
        self._page = page
        self._parser = parser or EasyApplyStepParser()

    def wait_until_ready(self) -> None:
        """Espera o modal mostrar uma tela conhecida; se não mostrar, quem lê a tela decide o que fazer."""
        try:
            self._page.wait_for_selector(self._DIALOG, timeout=self._ACTION_TIMEOUT_MS)
        except PlaywrightTimeoutError as error:
            raise EasyApplyUnavailableError("O botão de Candidatura Simplificada não abriu o formulário.") from error
        self._settled_step(lambda step: step.action is not StepAction.UNKNOWN)

    def read_step(self) -> EasyApplyStep:
        try:
            html = self._form().evaluate(self._LIVE_HTML_SCRIPT, timeout=self._ACTION_TIMEOUT_MS)
        except PlaywrightError as error:
            raise EasyApplyFormError(f"Não consegui ler o formulário: {error.message}") from error
        return self._parser.parse(html)

    def fill(self, field: FormField, answer: FieldAnswer) -> None:
        try:
            self._apply(field, answer)
        except PlaywrightError as error:
            raise EasyApplyFormError(f"Não consegui preencher '{field.question}': {error.message}") from error

    def _apply(self, field: FormField, answer: FieldAnswer) -> None:
        if not answer.options:
            self._control(field.control).fill(answer.text, timeout=self._ACTION_TIMEOUT_MS)
        elif field.kind is FieldKind.SELECT:
            self._control(field.control).select_option(value=answer.options[0].control, timeout=self._ACTION_TIMEOUT_MS)
        else:
            for option in answer.options:
                self._click_choice(option.control)

    def upload_resume(self, step: EasyApplyStep, resume: ResumeUploadFile) -> None:
        copies_before = step.resume_count(resume.name)
        payload = FilePayload(name=resume.name, mimeType=self._PDF_MIME_TYPE, buffer=resume.content)
        try:
            with self._page.expect_file_chooser(timeout=self._ACTION_TIMEOUT_MS) as chooser:
                self._button(step.upload_label).click(timeout=self._ACTION_TIMEOUT_MS)
            chooser.value.set_files(payload)
        except PlaywrightError as error:
            raise EasyApplyFormError(f"Não consegui carregar o currículo: {error.message}") from error
        self._ensure_new_copy_selected(resume, copies_before)

    def _ensure_new_copy_selected(self, resume: ResumeUploadFile, copies_before: int) -> None:
        """O LinkedIn guarda os currículos já carregados, e os de cada idioma têm sempre o mesmo nome.

        Escolher pelo nome poderia marcar o CV de outra vaga: vale a cópia nova, que aparece a mais e no
        topo da lista, conferida pelo controle da opção.
        """
        listed = self._settled_step(
            lambda step: step.resume_count(resume.name) > copies_before
            and step.newest_resume is not None
            and step.newest_resume.label == resume.name
        )
        if listed is None:
            raise EasyApplyFormError(f"O currículo {resume.name} não apareceu no topo da lista depois do upload.")
        new_copy = listed.newest_resume
        if not new_copy.selected:
            self._click_choice(new_copy.control)
        selected = next((option for option in self.read_step().resumes if option.selected), None)
        if selected is None or selected.control != new_copy.control:
            raise EasyApplyFormError(f"O currículo {resume.name} carregado agora não ficou selecionado.")

    def advance(self, step: EasyApplyStep) -> EasyApplyStep | None:
        label = step.action_label or ""
        if TextNormalizer.normalize(label) not in EasyApplyStepParser.ADVANCE_LABELS:
            raise EasyApplyFormError(f"Recusado: '{label}' não é um botão de avançar.")
        try:
            self._button(label).click(timeout=self._ACTION_TIMEOUT_MS)
        except PlaywrightError as error:
            raise EasyApplyFormError(f"Não consegui clicar em '{label}': {error.message}") from error
        return self._settled_step(lambda current: current.identity() != step.identity())

    def submit(self, step: EasyApplyStep) -> None:
        label = step.action_label or ""
        is_submit_button = TextNormalizer.normalize(label) in EasyApplyStepParser.SUBMIT_LABELS
        if step.action is not StepAction.SUBMIT_REACHED or not is_submit_button:
            raise EasyApplyFormError(f"Recusado: '{label}' não é o botão de enviar a candidatura.")
        try:
            self._button(label).click(timeout=self._ACTION_TIMEOUT_MS)
        except PlaywrightError as error:
            raise EasyApplyFormError(f"Não consegui clicar em '{label}': {error.message}") from error
        if not self._sent_confirmation_appears():
            raise EasyApplySubmissionUnconfirmedError(
                "Cliquei em enviar, mas o LinkedIn não mostrou a confirmação. Conferir a vaga no site antes de "
                "tentar de novo."
            )

    def _sent_confirmation_appears(self) -> bool:
        for _ in range(self._MAX_CHECKS):
            self._page.wait_for_timeout(self._CHECK_INTERVAL_MS)
            if self._SENT_SIGNS.search(TextNormalizer.normalize(self._page.inner_text("body"))):
                return True
        return False

    def close_after_sending(self) -> None:
        """Melhor esforço: a candidatura já foi enviada, então um aviso de confirmação que não fecha não é erro."""
        buttons = self._page.locator(self._DIALOG).get_by_role("button", name=self._AFTER_SENDING_BUTTON)
        try:
            if buttons.count():
                buttons.first.click(timeout=self._CONFIRMATION_TIMEOUT_MS)
        except PlaywrightError as error:
            logger.info("A confirmação do envio não fechou: %s", error.message)

    def close_without_sending(self) -> None:
        try:
            self._form().get_by_role("button", name=self._CLOSE_BUTTON).first.click(timeout=self._ACTION_TIMEOUT_MS)
            self._discard_if_asked()
            self._page.locator(self._DIALOG).first.wait_for(state="hidden", timeout=self._ACTION_TIMEOUT_MS)
        except PlaywrightError as error:
            raise EasyApplyFormError(f"Não consegui fechar o modal: {error.message}") from error

    def _discard_if_asked(self) -> None:
        discard = self._page.get_by_role("button", name=self._DISCARD_BUTTON)
        try:
            discard.click(timeout=self._CONFIRMATION_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            logger.info("O modal fechou sem pedir confirmação de descarte.")

    def save_screenshot(self, path: Path) -> None:
        """O modal rola por dentro e o print só pega o que está na tela: aumenta a janela só para o print.

        O modal ocupa uma fração da altura da janela, então ela precisa ser maior que o formulário.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        if not self._page.locator(self._DIALOG).count():
            self._page.screenshot(path=path)
            return
        size = self._page.viewport_size
        form_height = self._form().evaluate(self._FORM_HEIGHT_SCRIPT) + self._SCREENSHOT_MARGIN_PX
        height = round(form_height / self._DIALOG_SHARE_OF_WINDOW)
        self._page.set_viewport_size(
            {"width": size["width"], "height": min(max(height, size["height"]), self._SCREENSHOT_MAX_HEIGHT_PX)}
        )
        self._page.wait_for_timeout(self._SCREENSHOT_LAYOUT_WAIT_MS)
        self._page.screenshot(path=path)
        self._page.set_viewport_size(size)

    def page_snapshot(self) -> PageSnapshot:
        return PageSnapshot(url=self._page.url, html=self._page.content(), text=self._page.inner_text("body"))

    def _settled_step(self, is_expected: Callable[[EasyApplyStep], bool]) -> EasyApplyStep | None:
        """Espera a tela esperada e confere de novo: o conteúdo do modal também chega em partes."""
        previous: EasyApplyStep | None = None
        for _ in range(self._MAX_CHECKS):
            self._page.wait_for_timeout(self._CHECK_INTERVAL_MS)
            step = self.read_step()
            if is_expected(step) and previous is not None and step.identity() == previous.identity():
                return step
            previous = step
        return None

    def _form(self) -> Locator:
        return self._page.locator(self._DIALOG).first

    def _control(self, control_id: str | None) -> Locator:
        return self._form().locator(f"[id='{control_id}']")

    def _click_choice(self, control_id: str) -> None:
        """Os inputs de rádio e de caixa ficam escondidos; quem aparece e recebe o clique é o <label>."""
        self._form().locator(f"label[for='{control_id}']").click(timeout=self._ACTION_TIMEOUT_MS)

    def _button(self, label: str | None) -> Locator:
        return self._form().get_by_role("button", name=label, exact=True).last
