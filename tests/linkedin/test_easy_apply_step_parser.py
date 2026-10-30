import pytest

from job_applier.linkedin.easy_apply_step_parser import EasyApplyStepParser, StepAction
from job_applier.models.form_field import FieldKind
from tests.linkedin.easy_apply_pages import (
    checkbox_group,
    follow_company_checkbox,
    labeled_input,
    modal,
    question_input,
    question_textarea,
    radio_group,
    resume_step,
    select_field,
)


@pytest.fixture
def parser() -> EasyApplyStepParser:
    return EasyApplyStepParser()


class TestProgress:
    def test_reads_the_page_count(self, parser):
        step = parser.parse(modal("", progress="5 de 6 páginas"))

        assert (step.page, step.total_pages) == (5, 6)

    def test_reads_the_page_count_in_english(self, parser):
        step = parser.parse(modal("", progress="2 of 4 pages"))

        assert (step.page, step.total_pages) == (2, 4)

    def test_single_page_form_has_no_page_count(self, parser):
        step = parser.parse(modal("", progress=None))

        assert (step.page, step.total_pages) == (None, None)


class TestAction:
    @pytest.mark.parametrize("label", ["Avançar", "Avaliar", "Revisar", "Next", "Review"])
    def test_recognizes_buttons_that_move_the_form_forward(self, parser, label):
        step = parser.parse(modal("", buttons=("Voltar", label)))

        assert step.action is StepAction.ADVANCE
        assert step.action_label == label

    @pytest.mark.parametrize("label", ["Enviar candidatura", "Submit application"])
    def test_recognizes_the_submit_button(self, parser, label):
        step = parser.parse(modal("", buttons=(label,)))

        assert step.action is StepAction.SUBMIT_REACHED

    def test_submit_wins_over_any_other_button(self, parser):
        step = parser.parse(modal("", buttons=("Avançar", "Enviar candidatura")))

        assert step.action is StepAction.SUBMIT_REACHED

    def test_unknown_buttons_stop_the_form(self, parser):
        step = parser.parse(modal("", buttons=("Continuar a candidatura",)))

        assert step.action is StepAction.UNKNOWN
        assert step.action_label is None

    def test_confirmation_buttons_do_not_count_as_progress(self, parser):
        step = parser.parse(modal("", buttons=("Descartar", "Salvar")))

        assert step.action is StepAction.UNKNOWN


class TestFields:
    def test_reads_input_with_label_and_required_mark(self, parser):
        field = parser.parse(modal(labeled_input("First name", value="Ana"))).fields[0]

        assert field.kind is FieldKind.TEXT
        assert field.question == "First name"
        assert field.required
        assert field.value == "Ana"
        assert field.control == "_r_1_"

    def test_reads_question_from_aria_label_and_character_limit(self, parser):
        field = parser.parse(modal(question_input("Pretensão salarial (CLT bruto por mês)", limit=20))).fields[0]

        assert field.question == "Pretensão salarial (CLT bruto por mês)"
        assert field.max_length == 20

    def test_optional_input_is_not_required(self, parser):
        field = parser.parse(modal(labeled_input("Photo", required=False))).fields[0]

        assert not field.required

    def test_reads_number_input(self, parser):
        field = parser.parse(modal(labeled_input("Anos", input_type="number"))).fields[0]

        assert field.kind is FieldKind.NUMBER

    def test_reads_long_text(self, parser):
        field = parser.parse(modal(question_textarea("Descreva brevemente"))).fields[0]

        assert field.kind is FieldKind.LONG_TEXT
        assert field.required

    def test_reads_select_options_without_the_placeholder(self, parser):
        html = modal(select_field("Código do país", "_r_4_", {"ad": "Andorra (+376)", "br": "Brasil (+55)"}, "br"))
        field = parser.parse(html).fields[0]

        assert field.kind is FieldKind.SELECT
        assert [option.label for option in field.options] == ["Andorra (+376)", "Brasil (+55)"]
        assert field.current_answer() == "Brasil (+55)"

    def test_empty_select_needs_an_answer(self, parser):
        step = parser.parse(modal(select_field("Nível", "_r_4_", {"a": "Básico"})))

        assert [field.question for field in step.fields_to_answer()] == ["Nível"]

    def test_reads_radio_group_with_the_visible_options(self, parser):
        html = modal(radio_group("Você possui conhecimentos em POO?", {"_r_5_": "Yes", "_r_6_": "No"}))
        field = parser.parse(html).fields[0]

        assert field.kind is FieldKind.RADIO
        assert field.question == "Você possui conhecimentos em POO?"
        assert field.required
        assert [(option.label, option.control) for option in field.options] == [("Yes", "_r_5_"), ("No", "_r_6_")]

    def test_marked_radio_is_already_answered(self, parser):
        step = parser.parse(modal(radio_group("Pergunta?", {"_r_5_": "Yes", "_r_6_": "No"}, checked="_r_6_")))

        assert step.fields[0].current_answer() == "No"
        assert step.fields_to_answer() == ()

    def test_reads_checkbox_group(self, parser):
        html = modal(checkbox_group("Quais plataformas?", {"_r_7_": "AWS", "_r_8_": "Outra"}))
        field = parser.parse(html).fields[0]

        assert field.kind is FieldKind.CHECKBOX
        assert field.required
        assert [option.label for option in field.options] == ["AWS", "Outra"]

    def test_groups_keep_the_page_order(self, parser):
        html = modal(
            question_input("Primeira")
            + radio_group("Segunda", {"_r_5_": "Yes", "_r_6_": "No"})
            + question_textarea("Terceira")
        )

        assert [field.question for field in parser.parse(html).fields] == ["Primeira", "Segunda", "Terceira"]

    def test_select_has_no_character_limit(self, parser):
        html = modal(labeled_input("Primeiro", control="_a_") + select_field("Nível", "_r_4_", {"a": "Básico"}))

        assert parser.parse(html).fields[1].max_length is None

    def test_reads_radio_options_without_the_role_wrapper(self, parser):
        html = modal(
            """
            <p>Você aceita?*</p>
            <fieldset role="radiogroup"><div>
              <div><input aria-label="Você aceita?" id="_r_5_" type="radio"><label for="_r_5_"></label><p>Sim</p></div>
              <div><input aria-label="Você aceita?" id="_r_6_" type="radio"><label for="_r_6_"></label><p>Não</p></div>
            </div></fieldset>
            """
        )

        assert [option.label for option in parser.parse(html).fields[0].options] == ["Sim", "Não"]

    def test_only_empty_required_fields_need_an_answer(self, parser):
        html = modal(
            labeled_input("First name", control="_a_", value="Ana")
            + labeled_input("Photo", control="_b_", required=False)
            + question_input("Pretensão salarial", control="_c_")
        )

        assert [field.question for field in parser.parse(html).fields_to_answer()] == ["Pretensão salarial"]

    def test_follow_company_checkbox_is_left_alone(self, parser):
        step = parser.parse(modal(follow_company_checkbox(), buttons=("Enviar candidatura",)))

        assert step.fields_to_answer() == ()

    def test_unlabeled_checkbox_does_not_inherit_the_mark_of_the_previous_field(self, parser):
        html = modal(
            """
            <p>Resume*</p>
            <input id="_r_26_" type="checkbox" data-live-checked="true">
            <p>Siga a empresa X</p>
            """
        )
        field = parser.parse(html).fields[0]

        assert field.question == "Siga a empresa X"
        assert not field.required

    def test_typeahead_is_recognized(self, parser):
        html = modal(
            """
            <p>Location (city)*</p>
            <div data-expanded="false"><input aria-autocomplete="list" id="_r_1n_" data-live-value=""></div>
            """
        )
        field = parser.parse(html).fields[0]

        assert field.kind is FieldKind.TYPEAHEAD
        assert field.question == "Location (city)"
        assert field.required


class TestResume:
    @pytest.mark.parametrize("wrapped", [True, False], ids=["com-role-radio", "nome-no-input"])
    def test_resume_choice_is_not_a_question(self, parser, wrapped):
        step = parser.parse(modal(resume_step(wrapped=wrapped)))

        assert step.fields == ()
        assert step.offers_resume_choice
        assert step.upload_label == "Carregar currículo"

    @pytest.mark.parametrize("wrapped", [True, False], ids=["com-role-radio", "nome-no-input"])
    def test_reads_the_selected_resume(self, parser, wrapped):
        step = parser.parse(modal(resume_step(selected="CV mais antigo.pdf", wrapped=wrapped)))

        assert step.selected_resume == "CV mais antigo.pdf"

    def test_exposes_the_control_of_each_resume(self, parser):
        step = parser.parse(modal(resume_step()))

        assert step.resume_names() == ("CV antigo.pdf", "CV mais antigo.pdf")
        assert step.resume_control("CV mais antigo.pdf") == "_r_12_"

    def test_step_without_resume(self, parser):
        step = parser.parse(modal(question_input("Pergunta")))

        assert not step.offers_resume_choice
        assert step.upload_label is None
        assert step.selected_resume is None


class TestErrors:
    def test_reads_validation_messages_and_ignores_character_counters(self, parser):
        html = modal(
            question_input("Contada")
            + """
            <div>
              <input aria-label="Com erro" id="_r_9_" required type="text" data-live-value="">
              <div data-testid="text-input-helper-text" id="_r_9_-info"><p>Este campo é obrigatório</p></div>
            </div>
            """
        )

        assert parser.parse(html).errors == ("Este campo é obrigatório",)


class TestIdentity:
    def test_same_screen_keeps_its_identity_after_filling(self, parser):
        empty = parser.parse(modal(question_input("Pergunta")))
        filled = parser.parse(modal(question_input("Pergunta", value="2400")))

        assert empty.identity() == filled.identity()

    def test_next_page_changes_the_identity(self, parser):
        first = parser.parse(modal("", progress="1 de 3 páginas"))
        second = parser.parse(modal("", progress="2 de 3 páginas"))

        assert first.identity() != second.identity()
