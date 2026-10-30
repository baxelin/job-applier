import pytest

from job_applier.answering.salary_calculator import SalaryCalculator
from job_applier.models.answer_book import SalaryRule


@pytest.fixture
def calculator() -> SalaryCalculator:
    rule = SalaryRule(patterns=["pretensão salarial"], minimum=2000, default=2400, contractor_multiplier=1.5)
    return SalaryCalculator(rule)


class TestSalaryCalculator:
    def test_uses_the_default_when_the_job_shows_no_salary(self, calculator):
        assert calculator.expectation("Pretensão salarial", "Vaga para dev Python.") == 2400

    def test_uses_the_job_minimum(self, calculator):
        assert calculator.expectation("Pretensão salarial", "Faixa salarial: R$ 3.000,00 a R$ 4.500,00") == 3000

    def test_never_goes_below_the_floor(self, calculator):
        assert calculator.expectation("Pretensão salarial", "Bolsa-auxílio de R$ 1.500") == 2000

    def test_ignores_amounts_of_benefits(self, calculator):
        assert calculator.expectation("Pretensão salarial", "Vale-refeição de R$ 900\nPlano de saúde") == 2400

    @pytest.mark.parametrize("text", ["Remuneração de R$ 30/hora", "Salário de R$ 3 mil"])
    def test_ignores_amounts_that_are_not_monthly(self, calculator, text):
        assert calculator.expectation("Pretensão salarial", text) == 2400

    def test_reads_amount_without_thousands_separator(self, calculator):
        assert calculator.expectation("Pretensão salarial", "Salário: R$ 2800") == 2800

    def test_multiplies_default_for_contractor_jobs(self, calculator):
        assert calculator.expectation("Pretensão salarial", "Contratação PJ") == 3600

    def test_multiplies_floor_for_contractor_jobs(self, calculator):
        text = "Contratação como pessoa jurídica\nRemuneração de R$ 2.500"

        assert calculator.expectation("Pretensão salarial", text) == 3000

    def test_contractor_job_keeps_a_minimum_above_the_multiplied_floor(self, calculator):
        assert calculator.expectation("Pretensão salarial", "Contratação PJ\nSalário: R$ 4.000") == 4000

    def test_job_open_to_both_regimes_counts_as_employee(self, calculator):
        assert calculator.expectation("Pretensão salarial", "Contratação CLT ou PJ") == 2400

    def test_the_question_decides_the_regime(self, calculator):
        assert calculator.expectation("Pretensão salarial (CLT bruto por mês)", "Contratação PJ") == 2400

    def test_question_about_contractor_pay_in_job_open_to_both(self, calculator):
        assert calculator.expectation("Pretensão salarial como PJ", "Contratação CLT ou PJ") == 3600

    def test_pj_inside_another_word_is_not_a_contractor_job(self, calculator):
        assert calculator.expectation("Pretensão salarial", "Trabalhe com projetos PJOTA") == 2400
