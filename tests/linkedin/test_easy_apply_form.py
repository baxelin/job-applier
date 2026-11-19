import json
from pathlib import Path

import pytest

from job_applier.linkedin.easy_apply_form import EasyApplyForm, EasyApplyFormError, EasyApplyUnavailableError
from job_applier.linkedin.easy_apply_step_parser import EasyApplyStepParser, StepAction
from job_applier.linkedin.linkedin_browser import LinkedInBrowser
from job_applier.models.form_field import FieldAnswer
from job_applier.resume.resume_upload_file import ResumeUploadFile
from tests.linkedin.easy_apply_pages import (
    checkbox_group,
    labeled_input,
    modal,
    question_input,
    question_textarea,
    radio_group,
    resume_step,
    select_field,
)

RESUME = ResumeUploadFile(name="Curriculo_Ana_Silva.pdf", content=b"%PDF-fake")
UPLOADED_RADIO = '<input aria-label="{name}" id="_r_90_" name="radio-group-resume" type="radio" {checked}>'

CONTACT_SCREEN = modal(
    labeled_input("First name", value="Ana")
    + question_input("Pretensão salarial")
    + select_field("Nível de inglês", "_r_4_", {"basic": "Básico", "advanced": "Avançado"})
    + question_textarea("Descreva sua experiência", required=False),
)
RESUME_SCREEN = modal(resume_step(), progress="2 de 4 páginas")
QUESTIONS_SCREEN = modal(
    radio_group("Você é PcD?", {"_r_5_": "Yes", "_r_6_": "No"})
    + checkbox_group("Quais plataformas?", {"_r_7_": "AWS", "_r_8_": "Outra"}),
    buttons=("Voltar", "Avaliar"),
    progress="3 de 4 páginas",
)
REVIEW_SCREEN = modal(
    "<h3>Revise sua candidatura</h3><p>Curriculo_Ana_Silva.pdf</p>",
    buttons=("Enviar candidatura",),
    progress="4 de 4 páginas",
)
CONFIRMATION = """
<dialog data-testid="dialog" open>
  <button aria-label="Fechar" type="button"></button>
  <h2>Salvar esta candidatura?</h2>
  <button type="button"><span>Descartar</span></button>
  <button type="button"><span>Salvar</span></button>
</dialog>
"""


def fake_linkedin_page(
    screens: list[str],
    confirm_on_close: bool = True,
    selects_upload: bool = True,
    apply_button: bool = True,
    button_opens_form: bool = True,
) -> str:
    """Imita a vaga e o modal: telas em sequência, validação, upload pelo seletor de arquivos e descarte.

    O que não deveria acontecer fica registrado na própria página, em #events.
    """
    opens_form = "data-opens-form" if button_opens_form else ""
    button = f'<button aria-label="Usar a candidatura simplificada para esta vaga" {opens_form}>Candidatura</button>'
    checked = "checked" if selects_upload else ""
    uploaded_radio = json.dumps(UPLOADED_RADIO.format(name=RESUME.name, checked=checked))
    return f"""
    <html><head><meta charset="utf-8"><style>
      label[for] {{ display: inline-block; min-width: 20px; min-height: 20px; }}
      dialog {{ position: fixed; top: 20px; max-height: 600px; overflow-y: auto; }}
    </style></head><body>
      <h1>Desenvolvedor Júnior</h1>
      <h2>Sobre a vaga</h2>
      <span data-testid="expandable-text-box"><p>Vaga com Python.</p></span>
      <div role="dialog"><button>Close Modal Dialog</button><select><option>Legendas</option></select></div>
      {button if apply_button else ""}
      <div id="modal"></div>
      <div id="events"></div>
      <input id="file" type="file" hidden>
      <script>
        const screens = {json.dumps(screens)};
        const root = document.getElementById('modal');
        const events = document.getElementById('events');
        let current = 0;
        const show = () => {{ root.innerHTML = screens[current]; }};
        const isValid = () => [...root.querySelectorAll('[required]')].every(field => field.value);
        const addError = () => {{
          const helper = root.querySelector('[data-testid="text-input-helper-text"]');
          helper.innerHTML = '<p>Este campo é obrigatório</p>';
        }};

        document.addEventListener('click', event => {{
          const button = event.target.closest('button');
          if (!button) return;
          const label = button.innerText.trim() || button.getAttribute('aria-label') || '';
          if (button.hasAttribute('data-opens-form')) show();
          if (label === 'Enviar candidatura') events.textContent += ' ENVIADA';
          if (label === 'Salvar') events.textContent += ' SALVA';
          if (label === 'Avançar' || label === 'Avaliar') {{
            if (isValid()) {{ current += 1; show(); }} else addError();
          }}
          if (label === 'Carregar currículo') document.getElementById('file').click();
          if (label === 'Fechar') {{
            if ({json.dumps(confirm_on_close)}) root.insertAdjacentHTML('beforeend', {json.dumps(CONFIRMATION)});
            else root.innerHTML = '';
          }}
          if (label === 'Descartar') root.innerHTML = '';
        }});

        document.getElementById('file').addEventListener('change', event => {{
          events.textContent += ' UPLOAD:' + event.target.files[0].name;
          setTimeout(() => {{
            root.querySelector('fieldset').insertAdjacentHTML(
              'afterbegin', '<div>' + {uploaded_radio} + '<label for="_r_90_"></label></div>'
            );
          }}, 300);
        }});
      </script>
    </body></html>
    """


@pytest.fixture
def open_form(tmp_path):
    browsers = []

    def opened(screens: list[str], **page_options):
        page = tmp_path / "vaga.html"
        page.write_text(fake_linkedin_page(screens, **page_options), encoding="utf-8")
        browser = LinkedInBrowser(
            tmp_path / "profile", tmp_path / "debug", headless=True, job_url_for=lambda _: page.as_uri()
        ).__enter__()
        browsers.append(browser)
        browser.open_job("1")
        return browser.open_application_form()

    yield opened
    for browser in browsers:
        browser.__exit__(None, None, None)


def answer_field(form, question: str, answer: FieldAnswer) -> None:
    field = next(field for field in form.read_step().fields if field.question == question)
    form.fill(field, answer)


def field_named(form, question: str):
    return next(field for field in form.read_step().fields if field.question == question)


def go_to_next_screen(form):
    return form.advance(form.read_step())


class TestOpening:
    def test_opens_the_form_of_the_job(self, open_form):
        step = open_form([CONTACT_SCREEN]).read_step()

        assert step.page == 1
        assert step.action is StepAction.ADVANCE

    def test_ignores_other_dialogs_of_the_page(self, open_form):
        questions = [field.question for field in open_form([CONTACT_SCREEN]).read_step().fields]

        assert "First name" in questions
        assert "Legendas" not in questions

    def test_reports_job_without_the_button(self, open_form):
        with pytest.raises(EasyApplyUnavailableError, match="não mostra o botão"):
            open_form([CONTACT_SCREEN], apply_button=False)

    def test_reports_button_that_does_not_open_the_form(self, open_form, monkeypatch):
        monkeypatch.setattr(EasyApplyForm, "_ACTION_TIMEOUT_MS", 500)

        with pytest.raises(EasyApplyUnavailableError, match="não abriu o formulário"):
            open_form([CONTACT_SCREEN], button_opens_form=False)


class TestFilling:
    def test_fills_text_and_reads_the_value_back(self, open_form):
        form = open_form([CONTACT_SCREEN])

        answer_field(form, "Pretensão salarial", FieldAnswer(text="2400"))

        assert field_named(form, "Pretensão salarial").value == "2400"

    def test_keeps_the_value_that_was_already_there(self, open_form):
        assert field_named(open_form([CONTACT_SCREEN]), "First name").value == "Ana"

    def test_fills_long_text_and_reads_the_value_back(self, open_form):
        form = open_form([CONTACT_SCREEN])

        answer_field(form, "Descreva sua experiência", FieldAnswer(text="Dois anos com Python."))

        assert field_named(form, "Descreva sua experiência").value == "Dois anos com Python."

    def test_selects_an_option_and_reads_it_back(self, open_form):
        form = open_form([CONTACT_SCREEN])
        field = field_named(form, "Nível de inglês")

        form.fill(field, FieldAnswer.choosing(field.options[1]))

        assert field_named(form, "Nível de inglês").current_answer() == "Avançado"

    def test_marks_radio_and_checkbox_through_their_labels(self, open_form):
        form = open_form([QUESTIONS_SCREEN])
        radio = field_named(form, "Você é PcD?")
        checkbox = field_named(form, "Quais plataformas?")

        form.fill(radio, FieldAnswer.choosing(radio.options[1]))
        form.fill(checkbox, FieldAnswer.choosing(*checkbox.options))

        assert field_named(form, "Você é PcD?").current_answer() == "No"
        assert field_named(form, "Quais plataformas?").current_answer() == "AWS, Outra"
        assert form.read_step().fields_to_answer() == ()

    def test_reports_a_control_that_cannot_be_filled(self, open_form):
        form = open_form([CONTACT_SCREEN])
        field = field_named(form, "Pretensão salarial").model_copy(update={"control": "nao-existe"})
        form._ACTION_TIMEOUT_MS = 200

        with pytest.raises(EasyApplyFormError, match="Pretensão salarial"):
            form.fill(field, FieldAnswer(text="2400"))


class TestResumeUpload:
    def test_uploads_through_the_file_chooser_with_the_neutral_name(self, open_form):
        form = open_form([RESUME_SCREEN])

        form.upload_resume(form.read_step(), RESUME)

        assert form.read_step().selected_resume == RESUME.name
        assert f"UPLOAD:{RESUME.name}" in form.page_snapshot().text

    def test_selects_the_uploaded_resume_when_the_site_does_not(self, open_form):
        form = open_form([RESUME_SCREEN], selects_upload=False)

        form.upload_resume(form.read_step(), RESUME)

        assert form.read_step().selected_resume == RESUME.name


class TestAdvancing:
    def test_walks_to_the_next_screen(self, open_form):
        form = open_form([CONTACT_SCREEN, RESUME_SCREEN])
        answer_field(form, "Pretensão salarial", FieldAnswer(text="2400"))
        field = field_named(form, "Nível de inglês")
        form.fill(field, FieldAnswer.choosing(field.options[0]))

        assert go_to_next_screen(form).page == 2

    def test_validation_error_keeps_the_screen_and_shows_the_message(self, open_form):
        form = open_form([CONTACT_SCREEN, RESUME_SCREEN])
        form._MAX_CHECKS = 4

        assert go_to_next_screen(form) is None
        assert "Este campo é obrigatório" in form.read_step().errors


class TestNeverSends:
    def test_refuses_the_submit_screen(self, open_form):
        form = open_form([REVIEW_SCREEN])

        step = form.read_step()

        assert step.action is StepAction.SUBMIT_REACHED
        with pytest.raises(EasyApplyFormError, match="Recusado"):
            form.advance(step)
        assert "ENVIADA" not in form.page_snapshot().text

    def test_form_has_no_operation_that_sends(self, open_form):
        form = open_form([REVIEW_SCREEN])

        assert not [name for name in dir(form) if "send" in name and name != "close_without_sending"]
        assert not [name for name in dir(form) if "submit" in name]

    def test_submit_label_is_not_an_advance_label(self):
        assert not {"enviar candidatura", "submit application"} & EasyApplyStepParser.ADVANCE_LABELS


class TestClosing:
    def test_discards_the_application(self, open_form, tmp_path):
        form = open_form([REVIEW_SCREEN])

        form.close_without_sending()

        text = form.page_snapshot().text
        assert "Revise sua candidatura" not in text
        assert "ENVIADA" not in text
        assert "SALVA" not in text

    def test_closes_when_there_is_no_confirmation(self, open_form):
        form = open_form([REVIEW_SCREEN], confirm_on_close=False)
        form._CONFIRMATION_TIMEOUT_MS = 300

        form.close_without_sending()

        assert "Revise sua candidatura" not in form.page_snapshot().text


class TestScreenshot:
    def test_saves_the_print_and_restores_the_window(self, open_form, tmp_path):
        form = open_form([CONTACT_SCREEN])
        path: Path = tmp_path / "ensaios" / "pagina-01.png"

        form.save_screenshot(path)

        assert path.stat().st_size > 0
        assert form._page.viewport_size == {"width": 1366, "height": 860}
