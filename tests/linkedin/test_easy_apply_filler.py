import pytest

from job_applier.answering.form_answerer import FormAnswerer
from job_applier.linkedin.easy_apply_filler import EasyApplyFiller, FillStatus
from job_applier.linkedin.pacer import Pacer
from job_applier.linkedin.rehearsal_evidence import RehearsalEvidence
from job_applier.linkedin.session_guard import SessionBlockedError
from job_applier.resume.resume_upload_file import ResumeUploadFile
from tests.linkedin.easy_apply_pages import (
    labeled_input,
    modal,
    question_input,
    question_textarea,
    radio_group,
    resume_step,
)
from tests.linkedin.fake_application_form import FakeApplicationForm
from tests.storage.conftest import application

RESUME = ResumeUploadFile(name="Curriculo_Ana_Silva.pdf", content=b"%PDF-fake")
REVIEW = modal(f"<p>{RESUME.name}</p>", buttons=("Enviar candidatura",), progress="3 de 3 páginas")
CONTACT = modal(labeled_input("First name", value="Ana") + question_input("Pretensão salarial"))
RESUME_SCREEN = modal(resume_step(), progress="2 de 3 páginas", buttons=("Voltar", "Avaliar"))


@pytest.fixture
def pauses() -> list[float]:
    return []


@pytest.fixture
def filler(example_base_data, pauses) -> EasyApplyFiller:
    answerer = FormAnswerer(example_base_data.answer_book, example_base_data.resume, example_base_data.glossary)
    return EasyApplyFiller(answerer, Pacer(example_base_data.settings, sleep=pauses.append))


@pytest.fixture
def evidence(tmp_path) -> RehearsalEvidence:
    return RehearsalEvidence(tmp_path / "ensaio", application())


def answers_file(evidence: RehearsalEvidence) -> str:
    return (evidence.folder / "respostas.txt").read_text(encoding="utf-8")


class TestFilling:
    def test_walks_the_form_up_to_the_submit_screen(self, filler, evidence):
        form = FakeApplicationForm([CONTACT, RESUME_SCREEN, REVIEW])

        outcome = filler.fill(form, application(), RESUME, evidence)

        assert outcome.status is FillStatus.READY_TO_SUBMIT
        assert form.filled == [("Pretensão salarial", "3500")]
        assert form.uploaded == [RESUME.name]

    def test_handles_form_with_a_single_page(self, filler, evidence):
        form = FakeApplicationForm(
            [modal(resume_step() + f"<p>{RESUME.name}</p>", buttons=("Enviar candidatura",), progress=None)]
        )

        outcome = filler.fill(form, application(), RESUME, evidence)

        assert outcome.status is FillStatus.READY_TO_SUBMIT
        assert form.uploaded == [RESUME.name]

    def test_keeps_values_that_came_from_the_profile(self, filler, evidence):
        form = FakeApplicationForm([CONTACT, REVIEW])

        filler.fill(form, application(), RESUME, evidence)

        assert "First name" not in dict(form.filled)
        assert "First name: Ana (já estava preenchido)" in answers_file(evidence)

    def test_leaves_optional_fields_alone(self, filler, evidence):
        screen = modal(question_textarea("Nível de inglês", required=False))
        form = FakeApplicationForm([screen, REVIEW])

        outcome = filler.fill(form, application(), RESUME, evidence)

        assert outcome.status is FillStatus.READY_TO_SUBMIT
        assert form.filled == []

    def test_waits_between_screens_like_the_rest_of_the_automation(self, filler, evidence, pauses):
        filler.fill(FakeApplicationForm([CONTACT, RESUME_SCREEN, REVIEW]), application(), RESUME, evidence)

        assert len(pauses) == 2

    def test_takes_a_screenshot_of_each_screen(self, filler, evidence):
        form = FakeApplicationForm([CONTACT, RESUME_SCREEN, REVIEW])

        filler.fill(form, application(), RESUME, evidence)

        assert [path.name for path in form.screenshots] == ["tela-01.png", "tela-02.png", "tela-03.png"]

    def test_writes_every_answer_to_the_evidence_file(self, filler, evidence):
        filler.fill(FakeApplicationForm([CONTACT, RESUME_SCREEN, REVIEW]), application(), RESUME, evidence)

        text = answers_file(evidence)
        assert "[Tela 1 (página 1 de 3)]" in text
        assert "Pretensão salarial: 3500" in text
        assert f"Currículo carregado: {RESUME.name}" in text


class TestUnknownQuestions:
    def test_stops_and_returns_every_question_of_the_screen(self, filler, evidence):
        screen = modal(
            question_input("Pretensão salarial", control="_a_")
            + question_input("Por que nós?", control="_b_")
            + radio_group("Tem CNH?", {"_c_": "Yes", "_d_": "No"})
        )
        form = FakeApplicationForm([screen, REVIEW])

        outcome = filler.fill(form, application(), RESUME, evidence)

        assert outcome.status is FillStatus.UNKNOWN_QUESTIONS
        assert outcome.questions == ("Por que nós?", "Tem CNH?")
        assert form.filled == []

    def test_keeps_a_print_and_the_options_of_the_question(self, filler, evidence):
        form = FakeApplicationForm([modal(radio_group("Tem CNH?", {"_c_": "Yes", "_d_": "No"})), REVIEW])

        filler.fill(form, application(), RESUME, evidence)

        assert [path.name for path in form.screenshots] == ["tela-01.png"]
        assert "Tem CNH?: SEM RESPOSTA (opcao_unica). Opções: Yes, No." in answers_file(evidence)


class TestFailures:
    def test_reports_screen_that_does_not_advance(self, filler, evidence):
        form = FakeApplicationForm([CONTACT, REVIEW], stuck_on=0)

        outcome = filler.fill(form, application(), RESUME, evidence)

        assert outcome.status is FillStatus.FAILED
        assert "A tela 1 não avançou" in outcome.detail

    def test_reports_unknown_buttons_without_clicking(self, filler, evidence):
        form = FakeApplicationForm([modal("", buttons=("Continuar a candidatura",)), REVIEW])

        outcome = filler.fill(form, application(), RESUME, evidence)

        assert outcome.status is FillStatus.FAILED
        assert "nenhum botão conhecido" in outcome.detail

    def test_reports_answers_that_did_not_stick(self, filler, evidence):
        form = FakeApplicationForm([CONTACT, REVIEW], ignores_answers=True)

        outcome = filler.fill(form, application(), RESUME, evidence)

        assert outcome.status is FillStatus.FAILED
        assert "continuaram vazios" in outcome.detail

    def test_reports_failed_upload(self, filler, evidence):
        form = FakeApplicationForm([RESUME_SCREEN, REVIEW], errors_on_upload=True)

        outcome = filler.fill(form, application(), RESUME, evidence)

        assert outcome.status is FillStatus.FAILED
        assert "carregar o currículo" in outcome.detail

    def test_does_not_go_on_without_a_way_to_attach_the_resume(self, filler, evidence):
        screen = modal(resume_step().replace("Carregar currículo", "Remover"), buttons=("Avançar",))
        form = FakeApplicationForm([screen, REVIEW])

        outcome = filler.fill(form, application(), RESUME, evidence)

        assert outcome.status is FillStatus.FAILED
        assert "botão de carregar" in outcome.detail

    def test_final_screen_must_show_the_uploaded_resume(self, filler, evidence):
        other_review = modal("<p>CV antigo.pdf</p>", buttons=("Enviar candidatura",))
        form = FakeApplicationForm([RESUME_SCREEN, other_review])

        outcome = filler.fill(form, application(), RESUME, evidence)

        assert outcome.status is FillStatus.FAILED
        assert "não mostra o currículo" in outcome.detail

    def test_gives_up_on_endless_forms(self, filler, evidence):
        form = FakeApplicationForm([modal("")] * 30)

        outcome = filler.fill(form, application(), RESUME, evidence)

        assert outcome.status is FillStatus.FAILED
        assert "passou de 20 telas" in outcome.detail


class TestSessionGuard:
    def test_stops_when_the_site_asks_for_a_verification(self, filler, evidence):
        form = FakeApplicationForm([CONTACT], url="https://www.linkedin.com/checkpoint/challenge/1")

        with pytest.raises(SessionBlockedError):
            filler.fill(form, application(), RESUME, evidence)
