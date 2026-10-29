import pytest
from pydantic import ValidationError

from job_applier.models.answer_book import AnswerBook


class TestAnswerBook:
    def test_lists_answers_without_defined_value(self, answer_book_data):
        answer_book = AnswerBook.model_validate(answer_book_data)

        assert [answer.id for answer in answer_book.unanswered()] == ["pcd"]

    def test_rejects_duplicated_ids(self, answer_book_data):
        answer_book_data["answers"].append({"id": "pcd", "patterns": ["deficiência"]})

        with pytest.raises(ValidationError, match="Ids de respostas repetidos: pcd"):
            AnswerBook.model_validate(answer_book_data)

    def test_requires_at_least_one_pattern(self, answer_book_data):
        answer_book_data["answers"][0]["patterns"] = []

        with pytest.raises(ValidationError):
            AnswerBook.model_validate(answer_book_data)
