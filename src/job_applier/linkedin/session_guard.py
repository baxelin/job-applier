from job_applier.linkedin.page_snapshot import PageSnapshot
from job_applier.matching.text_normalizer import TextNormalizer


class SessionBlockedError(Exception):
    """O LinkedIn pediu verificação, deslogou ou bloqueou a conta: a automação precisa parar na hora."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class SessionGuard:
    """Verifica cada página aberta e interrompe tudo ao primeiro sinal de captcha, logout ou bloqueio.

    O robô nunca tenta contornar essas situações: elas exigem uma pessoa.

    O sinal principal é a URL. Os textos só são procurados em páginas curtas (telas de verificação
    e de bloqueio), para não confundir com uma vaga que cite, por exemplo, "verificação de segurança".
    """

    _SHORT_PAGE_LENGTH = 4000

    _URL_SIGNS = (
        ("/checkpoint/", "O LinkedIn pediu uma verificação de segurança (checkpoint/captcha)."),
        ("/challenge", "O LinkedIn pediu uma verificação de segurança (challenge)."),
        ("/authwall", "A sessão expirou: o LinkedIn exigiu login. Rode o comando login de novo."),
        ("/login", "A sessão expirou: o LinkedIn redirecionou para o login. Rode o comando login de novo."),
        ("/uas/login", "A sessão expirou: o LinkedIn redirecionou para o login. Rode o comando login de novo."),
    )
    _TEXT_SIGNS = (
        ("verificacao de seguranca", "O LinkedIn pediu uma verificação de segurança (captcha)."),
        ("quick security check", "O LinkedIn pediu uma verificação de segurança (captcha)."),
        ("nao sou um robo", "O LinkedIn exibiu um captcha."),
        ("i'm not a robot", "O LinkedIn exibiu um captcha."),
        ("sua conta foi restrita", "A conta foi restrita pelo LinkedIn."),
        ("your account has been restricted", "A conta foi restrita pelo LinkedIn."),
        ("temporarily restricted", "A conta foi restrita temporariamente pelo LinkedIn."),
        ("restrita temporariamente", "A conta foi restrita temporariamente pelo LinkedIn."),
        ("too many requests", "O LinkedIn bloqueou por excesso de requisições."),
        ("muitas solicitacoes", "O LinkedIn bloqueou por excesso de requisições."),
    )

    def check(self, snapshot: PageSnapshot) -> None:
        url = snapshot.url.casefold()
        for sign, reason in self._URL_SIGNS:
            if sign in url:
                raise SessionBlockedError(reason)

        if len(snapshot.text) > self._SHORT_PAGE_LENGTH:
            return
        text = TextNormalizer.normalize(snapshot.text)
        for sign, reason in self._TEXT_SIGNS:
            if sign in text:
                raise SessionBlockedError(reason)
