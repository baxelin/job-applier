from job_applier.matching.word_filter import WordFilter


class BrazilianLocation:
    """Diz se o local de uma vaga fica no Brasil, pelo país ou pelo estado que o LinkedIn mostra.

    O LinkedIn escreve o local de vários jeitos ("Brasil", "Belo Horizonte, Minas Gerais, Brazil",
    "Rio de Janeiro e Região", "Greater São Paulo Area"). Na dúvida responde que não: a vaga fica
    pendente, o que é melhor do que responder um salário em reais para uma vaga no exterior.
    Pará fica de fora porque "para" é uma palavra comum; o local dessas vagas traz o país.
    """

    _PLACES = (
        "brasil", "brazil", "acre", "alagoas", "amapá", "amazonas", "bahia", "ceará", "distrito federal",
        "espírito santo", "goiás", "maranhão", "mato grosso", "mato grosso do sul", "minas gerais", "paraíba",
        "paraná", "pernambuco", "piauí", "rio de janeiro", "rio grande do norte", "rio grande do sul",
        "rondônia", "roraima", "santa catarina", "são paulo", "sergipe", "tocantins",
    )  # fmt: skip

    def __init__(self) -> None:
        self._filter = WordFilter(self._PLACES)

    def contains(self, location: str | None) -> bool:
        return bool(location) and self._filter.first_match_in(location) is not None
