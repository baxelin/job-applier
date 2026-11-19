import re
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum, auto

from bs4 import BeautifulSoup, Tag

from job_applier.matching.text_normalizer import TextNormalizer
from job_applier.models.form_field import FieldKind, FieldOption, FormField


class StepAction(Enum):
    ADVANCE = auto()
    SUBMIT_REACHED = auto()
    UNKNOWN = auto()


@dataclass(frozen=True)
class EasyApplyStep:
    """Uma tela do modal da Candidatura Simplificada."""

    page: int | None
    total_pages: int | None
    fields: tuple[FormField, ...]
    action: StepAction
    action_label: str | None
    upload_label: str | None
    resumes: tuple[FieldOption, ...]
    errors: tuple[str, ...]
    text: str

    @property
    def offers_resume_choice(self) -> bool:
        return bool(self.resumes)

    @property
    def selected_resume(self) -> str | None:
        return next((resume.label for resume in self.resumes if resume.selected), None)

    @property
    def newest_resume(self) -> FieldOption | None:
        """O LinkedIn lista os currículos do mais novo para o mais antigo: o recém-carregado fica no topo."""
        return self.resumes[0] if self.resumes else None

    def resume_names(self) -> tuple[str, ...]:
        return tuple(resume.label for resume in self.resumes)

    def resume_count(self, name: str) -> int:
        return sum(resume.label == name for resume in self.resumes)

    def resume_control(self, name: str) -> str:
        return next(resume.control for resume in self.resumes if resume.label == name)

    def fields_to_answer(self) -> tuple[FormField, ...]:
        return tuple(field for field in self.fields if field.required and field.is_empty())

    def identity(self) -> tuple[object, ...]:
        """O que distingue uma tela da outra, para saber se o modal avançou de verdade."""
        return self.page, self.action_label, tuple(field.question for field in self.fields)


class EasyApplyStepParser:
    """Lê o HTML do modal da Candidatura Simplificada (layout de out/2026) e monta um EasyApplyStep.

    O valor atual de cada campo não aparece no HTML comum, então EasyApplyForm o grava em data-live-value
    e data-live-checked numa cópia do modal. Classes CSS são embaralhadas e data-view-name e componentkey
    aparecem ou somem de uma vaga para outra, por isso os botões são reconhecidos pelo texto visível.
    Só os rótulos listados aqui avançam o formulário: qualquer outro botão encerra o preenchimento.
    """

    ADVANCE_LABELS = frozenset({"avancar", "avaliar", "revisar", "next", "review"})
    SUBMIT_LABELS = frozenset({"enviar candidatura", "submit application"})
    _UPLOAD_LABELS = frozenset({"carregar curriculo", "upload resume"})
    _PAGE_COUNT = re.compile(r"(\d+)\s+(?:de|of)\s+(\d+)\s+(?:paginas|pages)")
    _CHARACTER_LIMIT = re.compile(r"\d+\s*/\s*(\d+)")
    _RESUME_FILE = re.compile(r"\.(?:pdf|docx?)$", re.IGNORECASE)
    _RADIOS = "input[type='radio']"
    _HIDDEN_TYPES = frozenset({"hidden", "file"})
    _GROUPED_TYPES = frozenset({"radio", "checkbox"})
    _CONTROLS = ("input", "select", "textarea")
    _HELPER_TEXT = "[data-testid='text-input-helper-text']"
    _GROUP_ERROR = re.compile(r"^error-message-")
    _UNLABELED_FIELD = "Campo sem rótulo"

    def parse(self, html: str) -> EasyApplyStep:
        soup = BeautifulSoup(html, "html.parser")
        page, total_pages = self._page_count(soup)
        action, action_label = self._action(soup)
        resume_group = self._resume_group(soup)
        return EasyApplyStep(
            page=page,
            total_pages=total_pages,
            fields=self._fields(soup, resume_group),
            action=action,
            action_label=action_label,
            upload_label=self._first_label(soup, self._UPLOAD_LABELS),
            resumes=self._resumes(resume_group),
            errors=self._errors(soup),
            text=self._text_of(soup),
        )

    def _page_count(self, soup: BeautifulSoup) -> tuple[int | None, int | None]:
        match = self._PAGE_COUNT.search(TextNormalizer.normalize(soup.get_text(" ")))
        return (int(match.group(1)), int(match.group(2))) if match else (None, None)

    def _action(self, soup: BeautifulSoup) -> tuple[StepAction, str | None]:
        if label := self._first_label(soup, self.SUBMIT_LABELS):
            return StepAction.SUBMIT_REACHED, label
        if label := self._first_label(soup, self.ADVANCE_LABELS):
            return StepAction.ADVANCE, label
        return StepAction.UNKNOWN, None

    def _first_label(self, soup: BeautifulSoup, accepted: Iterable[str]) -> str | None:
        labels = (self._button_label(button) for button in soup.find_all("button"))
        return next((label for label in labels if TextNormalizer.normalize(label) in accepted), None)

    @staticmethod
    def _button_label(button: Tag) -> str:
        return " ".join(button.get_text(" ").split()) or str(button.get("aria-label", ""))

    def _resume_group(self, soup: BeautifulSoup) -> Tag | None:
        """Os currículos são rádios cujo nome é o arquivo, ao contrário das perguntas.

        O nome fica no input ou num elemento acima dele, e [role=radio] só existe em parte das vagas.
        """
        for radio in soup.select(self._RADIOS):
            if self._RESUME_FILE.search(self._accessible_name(radio)):
                return radio.find_parent("fieldset")
        return None

    def _resumes(self, group: Tag | None) -> tuple[FieldOption, ...]:
        if group is None:
            return ()
        return tuple(
            FieldOption(
                label=self._accessible_name(radio),
                control=str(radio.get("id")),
                selected=radio.get("data-live-checked") == "true",
            )
            for radio in group.select(self._RADIOS)
        )

    @staticmethod
    def _accessible_name(control: Tag) -> str:
        named = control if control.has_attr("aria-label") else control.find_parent(attrs={"aria-label": True})
        return str(named["aria-label"]) if named else ""

    def _fields(self, soup: BeautifulSoup, resume_group: Tag | None) -> tuple[FormField, ...]:
        fields: list[FormField] = []
        visited_groups: list[Tag] = []
        for control in soup.find_all(self._CONTROLS):
            group = control.find_parent("fieldset") if control.get("type") in self._GROUPED_TYPES else None
            if group is None:
                fields.extend(self._standalone_field(soup, control))
            elif group is not resume_group and not any(group is visited for visited in visited_groups):
                visited_groups.append(group)
                fields.append(self._group_field(group))
        return tuple(fields)

    def _standalone_field(self, soup: BeautifulSoup, control: Tag) -> list[FormField]:
        if control.get("type") in self._HIDDEN_TYPES:
            return []
        if control.get("type") in self._GROUPED_TYPES:
            return self._single_checkbox(soup, control)
        question = self._question_of(soup, control)
        return [
            FormField(
                kind=self._kind_of(control),
                question=self._clean_question(question),
                control=str(control.get("id")),
                required=control.has_attr("required") or question.endswith("*"),
                value=str(control.get("data-live-value", "")) if control.name != "select" else "",
                options=self._select_options(control),
                max_length=self._max_length(soup, control),
            )
        ]

    def _single_checkbox(self, soup: BeautifulSoup, control: Tag) -> list[FormField]:
        """Caixa solta, como "Siga a empresa": sem ser obrigatória, ela fica como o LinkedIn deixou.

        O texto dela vem depois do controle; o <p> anterior é de outro campo e poderia ter a marca "*".
        """
        question = str(control.get("aria-label", "")) or self._text_of(control.find_next("p"))
        if not question:
            return []
        label = self._clean_question(question)
        option = FieldOption(
            label=label, control=str(control.get("id")), selected=control.get("data-live-checked") == "true"
        )
        return [
            FormField(
                kind=FieldKind.CHECKBOX,
                question=label,
                control=str(control.get("id")),
                required=question.endswith("*"),
                options=(option,),
            )
        ]

    def _group_field(self, group: Tag) -> FormField:
        inputs = group.find_all("input")
        kind = FieldKind.RADIO if inputs[0].get("type") == "radio" else FieldKind.CHECKBOX
        question = self._text_of(group.find_previous("p"))
        return FormField(
            kind=kind,
            question=self._clean_question(question),
            required=question.endswith("*"),
            options=tuple(self._group_option(control) for control in inputs),
        )

    def _group_option(self, control: Tag) -> FieldOption:
        return FieldOption(
            label=self._option_label(control) or str(control.get("id")),
            control=str(control.get("id")),
            selected=control.get("data-live-checked") == "true",
        )

    def _option_label(self, control: Tag) -> str:
        """O texto da opção é o primeiro que aparece subindo a partir do input, sem sair do grupo."""
        for parent in control.parents:
            if parent.name == "fieldset":
                return ""
            if text := self._text_of(parent):
                return text
        return ""

    def _select_options(self, control: Tag) -> tuple[FieldOption, ...]:
        if control.name != "select":
            return ()
        current = control.get("data-live-value", "")
        return tuple(
            FieldOption(
                label=self._text_of(option), control=str(option.get("value")), selected=option.get("value") == current
            )
            for option in control.find_all("option")
            if option.get("value") and not option.has_attr("disabled")
        )

    def _question_of(self, soup: BeautifulSoup, control: Tag) -> str:
        label = soup.find("label", attrs={"for": control.get("id")})
        text = self._text_of(label) or str(control.get("aria-label", ""))
        return text or self._text_of(control.find_previous("p"))

    def _clean_question(self, question: str) -> str:
        return question.rstrip("* ") or self._UNLABELED_FIELD

    @staticmethod
    def _text_of(element: Tag | None) -> str:
        return " ".join(element.get_text(" ").split()) if element else ""

    @staticmethod
    def _kind_of(control: Tag) -> FieldKind:
        if control.name == "select":
            return FieldKind.SELECT
        if control.name == "textarea":
            return FieldKind.LONG_TEXT
        if control.has_attr("aria-autocomplete"):
            return FieldKind.TYPEAHEAD
        return FieldKind.NUMBER if control.get("type") == "number" else FieldKind.TEXT

    def _max_length(self, soup: BeautifulSoup, control: Tag) -> int | None:
        helper_id = control.get("aria-describedby")
        match = self._CHARACTER_LIMIT.search(self._text_of(soup.find(id=helper_id))) if helper_id else None
        return int(match.group(1)) if match else None

    def _errors(self, soup: BeautifulSoup) -> tuple[str, ...]:
        helpers = (self._text_of(helper) for helper in soup.select(self._HELPER_TEXT))
        group_errors = (self._text_of(error) for error in soup.find_all(id=self._GROUP_ERROR))
        texts = (*helpers, *group_errors)
        return tuple(text for text in texts if text and not self._CHARACTER_LIMIT.search(text))
