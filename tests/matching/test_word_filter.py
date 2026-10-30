import pytest

from job_applier.matching.title_filter import TitleFilter

FILTER = TitleFilter(["sênior", "sr.", "sr", "pleno", "tech lead", "suporte"])


class TestTitleFilter:
    @pytest.mark.parametrize(
        ("title", "word"),
        [
            ("Desenvolvedor Python Senior", "sênior"),
            ("Desenvolvedor Sr. Java", "sr."),
            ("Analista PLENO", "pleno"),
            ("Tech Lead Frontend", "tech lead"),
            ("Analista de Suporte N1", "suporte"),
        ],
    )
    def test_finds_forbidden_words_ignoring_case_and_accents(self, title, word):
        assert FILTER.forbidden_word_in(title) == word

    @pytest.mark.parametrize("title", ["SRE Júnior", "Desenvolvedor Júnior", "Plenamente remoto"])
    def test_only_matches_whole_words(self, title):
        assert FILTER.forbidden_word_in(title) is None
