import pytest

from job_applier.answering.option_matcher import OptionMatcher
from job_applier.models.form_field import FieldOption


def options(*labels: str) -> tuple[FieldOption, ...]:
    return tuple(FieldOption(label=label, control=f"_r_{index}_") for index, label in enumerate(labels))


@pytest.fixture
def matcher() -> OptionMatcher:
    return OptionMatcher()


class TestOptionMatcher:
    def test_picks_the_identical_option_ignoring_case_and_accents(self, matcher):
        assert matcher.pick(options("Básico", "Avancado"), ["AVANÇADO"]).label == "Avancado"

    @pytest.mark.parametrize(
        ("labels", "answer", "expected"),
        [
            (("Yes", "No"), "Não", "No"),
            (("Yes", "No"), "Sim", "Yes"),
            (("Sim", "Não"), "No", "Não"),
            (("Sim", "Não"), "Yes", "Sim"),
        ],
    )
    def test_translates_yes_and_no(self, matcher, labels, answer, expected):
        assert matcher.pick(options(*labels), [answer]).label == expected

    def test_picks_option_contained_in_the_answer(self, matcher):
        answer = "Avançado (B2 – certificado Cambridge)"

        assert matcher.pick(options("Básico", "Intermediário", "Avançado"), [answer]).label == "Avançado"

    def test_does_not_match_part_of_a_word(self, matcher):
        assert matcher.pick(options("Pós"), ["Compostos"]) is None

    def test_long_options_are_matched_by_their_beginning(self, matcher):
        levels = options(
            "B1 – Intermediate: I can understand the main points on familiar topics.",
            "B2 – Upper Intermediate: I can speak fluently enough to talk with native speakers.",
            "C1 – Advanced: I can express myself fluently and spontaneously.",
        )

        answer = matcher.pick(levels, ["Upper-intermediate (B2 – Cambridge certificate)"])

        assert answer.label.startswith("B2")

    def test_the_beginning_of_a_short_option_is_not_used(self, matcher):
        assert matcher.pick(options("Python", "Java"), ["Python – Java"]) is None

    def test_does_not_guess_between_two_options(self, matcher):
        assert matcher.pick(options("Remoto", "Híbrido"), ["Remoto ou híbrido"]) is None

    def test_yes_or_no_question_does_not_take_a_descriptive_answer(self, matcher):
        assert matcher.pick(options("Yes", "No"), ["Remoto ou híbrido"]) is None

    def test_tries_the_next_language_when_the_first_has_no_match(self, matcher):
        assert matcher.pick(options("Advanced"), ["Avançado", "Advanced"]).label == "Advanced"


class TestPickMany:
    def test_picks_every_option_listed_in_the_answer(self, matcher):
        picked = matcher.pick_many(options("Java Beginner", "Python Intermediate", "JavaScript Intermediate"),
                                   ["Python Intermediate, JavaScript Intermediate"])

        assert [option.label for option in picked] == ["Python Intermediate", "JavaScript Intermediate"]

    def test_identical_option_wins_over_contained_ones(self, matcher):
        picked = matcher.pick_many(options("AWS", "AWS Lambda"), ["AWS"])

        assert [option.label for option in picked] == ["AWS"]

    def test_does_not_match_part_of_a_word(self, matcher):
        assert matcher.pick_many(options("Java Intermediate"), ["JavaScript Intermediate"]) == ()

    def test_tries_the_next_language_when_the_first_has_no_match(self, matcher):
        picked = matcher.pick_many(options("Portuguese", "English"), ["Português, Inglês", "Portuguese, English"])

        assert [option.label for option in picked] == ["Portuguese", "English"]
