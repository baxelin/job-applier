from datetime import date

import pytest

from job_applier.linkedin.posting_text_parser import PostingTextParser

TODAY = date(2026, 10, 29)


class TestApplicants:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("São Paulo · há 2 dias · 37 candidaturas", 37),
            ("Mais de 100 candidaturas", 100),
            ("Over 100 applicants", 100),
            ("1.234 candidatos", 1234),
            ("12 pessoas clicaram em candidatar-se", 12),
            ("São Paulo · há 2 dias", None),
        ],
    )
    def test_reads_number_of_applicants(self, text, expected):
        assert PostingTextParser().applicants(text) == expected


class TestPostedOn:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("há 3 horas", TODAY),
            ("há 2 dias", date(2026, 10, 27)),
            ("Repostada há 1 semana", date(2026, 10, 22)),
            ("há um mês", date(2026, 9, 29)),
            ("5 days ago", date(2026, 10, 24)),
            ("Reposted 2 weeks ago", date(2026, 10, 15)),
            ("an hour ago", TODAY),
            ("sem data", None),
        ],
    )
    def test_converts_relative_dates(self, text, expected):
        assert PostingTextParser().posted_on(text, TODAY) == expected
