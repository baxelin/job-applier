from datetime import datetime

from tests.storage.conftest import application


class TestSqliteUnknownQuestionRepository:
    def test_registers_question_linked_to_the_last_job(self, applications, questions):
        job = applications.save(application())

        questions.register("Você tem CNH?", job.id, datetime(2026, 10, 29, 11, 0))

        [question] = questions.list_all()
        assert (question.question, question.occurrences) == ("Você tem CNH?", 1)
        assert (question.last_company, question.last_title) == ("Empresa X", "Dev Júnior")

    def test_repeated_question_ignoring_case_accents_and_spaces_counts_occurrences(self, questions):
        questions.register("Você tem CNH?", None, datetime(2026, 10, 29, 11, 0))
        questions.register("  voce  tem cnh? ", None, datetime(2026, 10, 30, 9, 0))

        [question] = questions.list_all()
        assert question.occurrences == 2
        assert question.first_seen_at == datetime(2026, 10, 29, 11, 0)
        assert question.last_seen_at == datetime(2026, 10, 30, 9, 0)

    def test_lists_most_frequent_first(self, questions):
        questions.register("Rara", None, datetime(2026, 10, 29))
        questions.register("Comum", None, datetime(2026, 10, 29))
        questions.register("Comum", None, datetime(2026, 10, 30))

        assert [question.question for question in questions.list_all()] == ["Comum", "Rara"]
