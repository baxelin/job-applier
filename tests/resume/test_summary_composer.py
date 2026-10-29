import pytest

from job_applier.models.base import Locale
from job_applier.models.resume import Summary
from job_applier.resume.resume_labels import ResumeLabels
from job_applier.resume.summary_composer import SummaryComposer

SUMMARY = Summary(
    id="dev",
    tags=["dev"],
    text={"pt": "Desenvolvo com {stack} todos os dias.", "en": "I build with {stack} every day."},
)


class TestResumeLabelsEnumerate:
    @pytest.mark.parametrize(
        ("items", "expected"),
        [([], ""), (["A"], "A"), (["A", "B"], "A e B"), (["A", "B", "C"], "A, B e C")],
    )
    def test_joins_items_in_portuguese(self, items, expected):
        assert ResumeLabels(Locale.PT).enumerate(items) == expected

    def test_joins_items_in_english(self):
        assert ResumeLabels(Locale.EN).enumerate(["A", "B", "C"]) == "A, B and C"


class TestSummaryComposer:
    def test_fills_placeholder_with_the_first_skills(self):
        text = SummaryComposer(skill_count=3).compose(SUMMARY, ["Python", "MySQL", "Docker", "Git"], Locale.PT)

        assert text == "Desenvolvo com Python, MySQL e Docker todos os dias."

    def test_uses_the_job_language(self):
        text = SummaryComposer(skill_count=2).compose(SUMMARY, ["Node.js", "Vue.js", "Git"], Locale.EN)

        assert text == "I build with Node.js and Vue.js every day."

    def test_keeps_text_without_placeholder_unchanged(self):
        fixed = Summary(id="fixo", tags=["dev"], text={"pt": "Texto fixo.", "en": "Fixed text."})

        assert SummaryComposer(skill_count=3).compose(fixed, ["Python"], Locale.PT) == "Texto fixo."
