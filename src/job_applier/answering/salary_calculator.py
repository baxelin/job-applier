import re

from job_applier.matching.text_normalizer import TextNormalizer
from job_applier.models.answer_book import SalaryRule


class SalaryCalculator:
    """Calcula a pretensão salarial: o mínimo da vaga, sem nunca ficar abaixo do piso.

    Só valores mensais em linhas que falam de salário contam, para não confundir com vale-refeição e outros
    benefícios nem com "R$ 30/hora" ou "R$ 3 mil". Vaga PJ multiplica piso e padrão por contractor_multiplier.
    Quem diz o regime é a pergunta ("CLT bruto por mês"); quando ela não diz, vale a vaga, e "CLT ou PJ"
    conta como CLT.
    """

    _SALARY_WORDS = re.compile(r"salario|salarial|remuneracao|bolsa|salary|compensation")
    _AMOUNT = re.compile(r"r\$\s*(\d{1,3}(?:\.\d{3})+|\d+)(?:,\d{2})?")
    _LOWEST_MONTHLY_AMOUNT = 500
    _CONTRACTOR = re.compile(r"(?<!\w)(?:pj|pessoa juridica)(?!\w)")
    _EMPLOYEE = re.compile(r"(?<!\w)clt(?!\w)")

    def __init__(self, rule: SalaryRule) -> None:
        self._rule = rule

    def expectation(self, question: str, job_text: str) -> int:
        multiplier = self._rule.contractor_multiplier if self._is_contractor(question, job_text) else 1
        minimum = round(self._rule.minimum * multiplier)
        job_minimum = self._job_minimum(job_text)
        if job_minimum is None:
            return round(self._rule.default * multiplier)
        return max(job_minimum, minimum)

    def _is_contractor(self, question: str, job_text: str) -> bool:
        for text in (TextNormalizer.normalize(question), TextNormalizer.normalize(job_text)):
            if self._EMPLOYEE.search(text):
                return False
            if self._CONTRACTOR.search(text):
                return True
        return False

    def _job_minimum(self, job_text: str) -> int | None:
        lines = TextNormalizer.normalize(job_text).splitlines()
        amounts = (
            int(amount.replace(".", ""))
            for line in lines
            if self._SALARY_WORDS.search(line)
            for amount in self._AMOUNT.findall(line)
        )
        return min((amount for amount in amounts if amount >= self._LOWEST_MONTHLY_AMOUNT), default=None)
