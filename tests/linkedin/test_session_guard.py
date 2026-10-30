import pytest

from job_applier.linkedin.page_snapshot import PageSnapshot
from job_applier.linkedin.session_guard import SessionBlockedError, SessionGuard


def snapshot(url: str = "https://www.linkedin.com/jobs/view/1/", text: str = "Vaga normal") -> PageSnapshot:
    return PageSnapshot(url=url, html="", text=text)


class TestSessionGuard:
    def test_normal_page_passes(self):
        SessionGuard().check(snapshot())

    @pytest.mark.parametrize(
        ("url", "reason"),
        [
            ("https://www.linkedin.com/checkpoint/challenge/abc", "verificação de segurança"),
            ("https://www.linkedin.com/authwall?trk=x", "sessão expirou"),
            ("https://www.linkedin.com/login?session_redirect=x", "sessão expirou"),
        ],
    )
    def test_stops_on_security_or_login_urls(self, url, reason):
        with pytest.raises(SessionBlockedError, match=f"(?i){reason}"):
            SessionGuard().check(snapshot(url=url))

    @pytest.mark.parametrize(
        "text",
        ["Vamos fazer uma verificação de segurança rápida", "Your account has been restricted", "Too Many Requests"],
    )
    def test_stops_on_captcha_or_restriction_pages(self, text):
        with pytest.raises(SessionBlockedError):
            SessionGuard().check(snapshot(text=text))

    def test_ignores_those_words_inside_long_job_descriptions(self):
        description = "Analista de segurança: realizar verificação de segurança nos sistemas. " + "Requisitos. " * 400

        SessionGuard().check(snapshot(text=description))
