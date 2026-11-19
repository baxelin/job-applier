from collections.abc import Sequence

from job_applier.answering.brazilian_location import BrazilianLocation
from job_applier.answering.option_matcher import OptionMatcher
from job_applier.answering.salary_calculator import SalaryCalculator
from job_applier.matching.keyword_extractor import KeywordExtractor
from job_applier.matching.word_filter import WordFilter
from job_applier.models.answer_book import Answer, AnswerBook
from job_applier.models.base import Locale
from job_applier.models.form_field import FieldAnswer, FieldKind, FormField
from job_applier.models.glossary import Glossary
from job_applier.models.job_application import JobApplication
from job_applier.models.resume import Resume


class FormAnswerer:
    """Responde um campo de formulário com as regras de respostas.json e os dados do CV.

    A ordem é: pretensão salarial, anos de experiência e, por fim, respostas prontas (vence o padrão mais
    longo que aparecer na pergunta, o mais específico). Devolve None quando não há resposta segura; nesse
    caso a candidatura fica pendente. Nada é inventado: resposta null, pergunta de salário em vaga no
    exterior (a moeda ainda não foi definida) e campo de busca com sugestões ficam sempre sem resposta.
    Vaga em inglês localizada no Brasil recebe a pretensão em reais, como as vagas em português.
    """

    _CHOICE_KINDS = frozenset({FieldKind.SELECT, FieldKind.RADIO, FieldKind.CHECKBOX})

    def __init__(
        self,
        answer_book: AnswerBook,
        resume: Resume,
        glossary: Glossary,
        matcher: OptionMatcher | None = None,
    ) -> None:
        self._book = answer_book
        self._years_by_skill = {skill.term: skill.years for skill in resume.skills}
        self._extractor = KeywordExtractor(glossary)
        self._salary = SalaryCalculator(answer_book.salary)
        self._salary_filter = WordFilter(answer_book.salary.patterns)
        self._years_filter = WordFilter(answer_book.skill_years.patterns)
        self._answer_filters = [(answer, WordFilter(answer.patterns)) for answer in answer_book.answers]
        self._matcher = matcher or OptionMatcher()
        self._brazil = BrazilianLocation()

    def answer(self, field: FormField, application: JobApplication) -> FieldAnswer | None:
        if field.kind is FieldKind.TYPEAHEAD:
            return None
        candidates = self._candidates(field.question, application)
        if not candidates:
            return None
        if field.kind in self._CHOICE_KINDS:
            return self._choice(field, candidates)
        return self._text(field, candidates[0])

    def _candidates(self, question: str, application: JobApplication) -> list[str]:
        """Respostas possíveis, primeiro no idioma da vaga; opções podem vir no outro idioma."""
        locale = Locale(application.locale)
        if self._salary_filter.first_match_in(question):
            return self._salary_answer(question, application, locale)
        if self._years_filter.first_match_in(question):
            return self._years_answer(question)
        answer = self._best_answer(question)
        if answer is None or answer.answer is None:
            return []
        other_locale = Locale.EN if locale is Locale.PT else Locale.PT
        return [answer.answer.in_locale(locale), answer.answer.in_locale(other_locale)]

    def _salary_answer(self, question: str, application: JobApplication, locale: Locale) -> list[str]:
        if locale is not Locale.PT and not self._brazil.contains(application.location):
            return []
        return [str(self._salary.expectation(question, application.description or ""))]

    def _years_answer(self, question: str) -> list[str]:
        """Sem tecnologia reconhecida na pergunta não há o que consultar no CV."""
        terms = self._extractor.extract(question)
        if not terms:
            return []
        default = self._book.skill_years.default_years
        return [f"{min(self._years_by_skill.get(term, default) for term in terms):g}"]

    def _best_answer(self, question: str) -> Answer | None:
        matches = [
            (len(pattern), answer)
            for answer, patterns in self._answer_filters
            if (pattern := patterns.first_match_in(question))
        ]
        return max(matches, key=lambda match: match[0], default=(0, None))[1]

    def _choice(self, field: FormField, candidates: Sequence[str]) -> FieldAnswer | None:
        if field.kind is FieldKind.CHECKBOX:
            options = self._matcher.pick_many(field.options, candidates)
        else:
            option = self._matcher.pick(field.options, candidates)
            options = (option,) if option else ()
        return FieldAnswer.choosing(*options) if options else None

    @staticmethod
    def _text(field: FormField, text: str) -> FieldAnswer | None:
        if field.max_length is not None and len(text) > field.max_length:
            return None
        if field.kind is FieldKind.NUMBER and not text.replace(".", "", 1).isdigit():
            return None
        return FieldAnswer(text=text)
