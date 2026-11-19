import pytest

from job_applier.answering.form_answerer import FormAnswerer
from job_applier.models.answer_book import AnswerBook
from job_applier.models.form_field import FieldKind, FieldOption, FormField
from job_applier.models.glossary import Glossary
from job_applier.models.resume import Resume
from tests.storage.conftest import application


def text_field(question: str, kind: FieldKind = FieldKind.TEXT, max_length: int | None = None) -> FormField:
    return FormField(kind=kind, question=question, control="_r_1_", required=True, max_length=max_length)


def choice_field(question: str, *labels: str, kind: FieldKind = FieldKind.RADIO) -> FormField:
    field_options = tuple(FieldOption(label=label, control=f"_r_{index}_") for index, label in enumerate(labels))
    return FormField(kind=kind, question=question, required=True, options=field_options)


@pytest.fixture
def answer_book(answer_book_data) -> AnswerBook:
    answer_book_data["answers"] = [
        {
            "id": "nivel-ingles",
            "patterns": ["nível de inglês", "inglês", "english"],
            "answer": {"pt": "Avançado (B2)", "en": "Upper-intermediate (B2)"},
        },
        {"id": "curso", "patterns": ["curso"], "answer": {"pt": "ADS", "en": "Systems Analysis"}},
        {
            "id": "formatura",
            "patterns": ["data de conclusão"],
            "answer": {"pt": "Julho de 2028", "en": "July 2028"},
        },
        {"id": "cidade", "patterns": ["city"], "answer": {"pt": "São Paulo", "en": "São Paulo, Brazil"}},
        {"id": "pcd", "patterns": ["pcd", "disability"], "answer": {"pt": "Não", "en": "No"}},
        {"id": "visto", "patterns": ["visa sponsorship"], "answer": None},
        {"id": "idiomas", "patterns": ["languages"], "answer": {"pt": "Português, Inglês", "en": "Portuguese, English"}},
    ]
    answer_book_data["skill_years"] = {
        "patterns": ["anos de experiência com", "years of experience"],
        "default_years": 0,
    }
    return AnswerBook.model_validate(answer_book_data)


@pytest.fixture
def answerer(answer_book, resume_data, glossary_data) -> FormAnswerer:
    resume_data["skills"].append({"term": "docker", "years": 1.5, "tags": ["devops"]})
    glossary_data["terms"].append({"id": "kubernetes", "name": "Kubernetes", "category": "devops", "synonyms": []})
    return FormAnswerer(answer_book, Resume.model_validate(resume_data), Glossary.model_validate(glossary_data))


class TestAnswers:
    def test_uses_the_language_of_the_job(self, answerer):
        field = text_field("Qual seu nível de inglês?")

        assert answerer.answer(field, application(locale="pt")).text == "Avançado (B2)"
        assert answerer.answer(field, application(locale="en")).text == "Upper-intermediate (B2)"

    def test_the_most_specific_pattern_wins(self, answerer):
        answer = answerer.answer(text_field("Qual a data de conclusão do curso?"), application())

        assert answer.text == "Julho de 2028"

    def test_patterns_match_whole_words_only(self, answerer):
        assert answerer.answer(text_field("What is your velocity on capacity planning?"), application()) is None

    def test_unknown_question_has_no_answer(self, answerer):
        assert answerer.answer(text_field("Por que você quer trabalhar aqui?"), application()) is None

    def test_null_answer_is_not_answered(self, answerer):
        assert answerer.answer(text_field("Do you need visa sponsorship?"), application(locale="en")) is None

    def test_answer_over_the_character_limit_is_not_used(self, answerer):
        field = text_field("Qual seu nível de inglês?", max_length=5)

        assert answerer.answer(field, application()) is None

    def test_number_field_does_not_take_text(self, answerer):
        field = text_field("Qual seu nível de inglês?", kind=FieldKind.NUMBER)

        assert answerer.answer(field, application()) is None

    def test_typeahead_is_left_for_a_person(self, answerer):
        field = text_field("City", kind=FieldKind.TYPEAHEAD)

        assert answerer.answer(field, application()) is None


class TestChoices:
    def test_picks_the_option_of_a_radio(self, answerer):
        field = choice_field("Você é PcD?", "Yes", "No")

        answer = answerer.answer(field, application())

        assert answer.text == "No"
        assert [option.control for option in answer.options] == ["_r_1_"]

    def test_picks_the_option_of_a_select(self, answerer):
        field = choice_field("Nível de inglês", "Básico", "Avançado", kind=FieldKind.SELECT)

        assert answerer.answer(field, application()).text == "Avançado"

    def test_options_can_be_in_the_other_language(self, answerer):
        field = choice_field("Nível de inglês", "Basic", "Upper-intermediate", kind=FieldKind.SELECT)

        assert answerer.answer(field, application(locale="pt")).text == "Upper-intermediate"

    def test_answer_outside_the_options_stays_unanswered(self, answerer):
        field = choice_field("Você tem inglês avançado?", "Yes", "No")

        assert answerer.answer(field, application()) is None

    def test_checkbox_marks_every_option_in_the_answer(self, answerer):
        field = choice_field("Which languages do you speak?", "English", "French", "Portuguese", kind=FieldKind.CHECKBOX)

        answer = answerer.answer(field, application(locale="en"))

        assert [option.label for option in answer.options] == ["English", "Portuguese"]
        assert answer.text == "English, Portuguese"

    def test_checkbox_without_matching_options_stays_unanswered(self, answerer):
        field = choice_field("Which languages do you speak?", "French", "German", kind=FieldKind.CHECKBOX)

        assert answerer.answer(field, application(locale="en")) is None


class TestSkillYears:
    def test_reads_years_from_the_resume(self, answerer):
        answer = answerer.answer(text_field("Quantos anos de experiência com Python?"), application())

        assert answer.text == "1"

    def test_keeps_fractions_of_a_year(self, answerer):
        answer = answerer.answer(text_field("How many years of experience with Docker?"), application())

        assert answer.text == "1.5"

    def test_skill_outside_the_resume_uses_the_default(self, answerer):
        answer = answerer.answer(text_field("Quantos anos de experiência com Kubernetes?"), application())

        assert answer.text == "0"

    def test_several_skills_use_the_lowest_value(self, answerer):
        question = "Anos de experiência com Docker e Kubernetes"

        assert answerer.answer(text_field(question), application()).text == "0"

    def test_fills_number_fields(self, answerer):
        field = text_field("Years of experience with Docker", kind=FieldKind.NUMBER)

        assert answerer.answer(field, application()).text == "1.5"

    def test_question_without_a_known_skill_stays_unanswered(self, answerer):
        field = text_field("How many years of experience in the financial sector?")

        assert answerer.answer(field, application()) is None


class TestSalary:
    def test_answers_with_the_salary_rule(self, answerer):
        answer = answerer.answer(text_field("Pretensão salarial (CLT bruto por mês)"), application())

        assert answer.text == "2400"

    def test_uses_the_description_of_the_job(self, answerer):
        job = application(description="Salário: R$ 3.200,00")

        assert answerer.answer(text_field("Pretensão salarial"), job).text == "3200"

    def test_job_abroad_stays_unanswered_because_the_currency_is_undefined(self, answerer):
        job = application(locale="en", location="Austin, Texas, United States")

        assert answerer.answer(text_field("Pretensão salarial"), job) is None

    def test_job_in_english_located_in_brazil_answers_in_reais(self, answerer):
        job = application(locale="en", location="Belo Horizonte, Minas Gerais, Brazil")

        assert answerer.answer(text_field("Pretensão salarial"), job).text == "2400"
