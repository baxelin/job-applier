import pytest

from job_applier.matching.word_filter import WordFilter

TITLE_FILTER = WordFilter(["sênior", "sr.", "sr", "pleno", "tech lead", "suporte"])


class TestWordFilter:
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
        assert TITLE_FILTER.first_match_in(title) == word

    @pytest.mark.parametrize("title", ["SRE Júnior", "Desenvolvedor Júnior", "Plenamente remoto"])
    def test_only_matches_whole_words(self, title):
        assert TITLE_FILTER.first_match_in(title) is None

    @pytest.mark.parametrize("company", ["BairesDev", "bairesdev", "Jobol Recrutamento"])
    def test_blocks_companies_by_name(self, company):
        assert WordFilter(["BairesDev", "Jobol"]).first_match_in(company) is not None

    def test_does_not_block_companies_that_only_contain_the_name(self):
        assert WordFilter(["Jobol"]).first_match_in("Jobolândia Tech") is None
